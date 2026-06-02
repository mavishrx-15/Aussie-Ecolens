import base64
import json
import os
from copy import deepcopy
from decimal import Decimal
from urllib.parse import quote, unquote, urlparse


DDB_TYPES = {"S", "N", "BOOL", "NULL", "M", "L", "SS", "NS"}

_LOCAL_ITEMS_CACHE = None
_DDB_TABLE = None
_S3_CLIENT = None
_LAMBDA_CLIENT = None


class BadRequest(Exception):
    pass


class NotFound(Exception):
    pass


def lambda_handler(event, context):
    try:
        method = get_method(event)
        path = get_path(event)

        if method == "OPTIONS":
            return api_response(200, {"ok": True})

        body = get_json_body(event)

        if method == "POST" and route_is(path, "/query/tags"):
            return api_response(200, query_by_tag_counts(body))

        if method == "POST" and route_is(path, "/query/species"):
            return api_response(200, query_by_species(body))

        if method == "POST" and route_is(path, "/query/thumbnail"):
            return api_response(200, query_by_thumbnail_url(body))

        if method == "POST" and route_is(path, "/query/file-tags"):
            return api_response(200, query_by_uploaded_file_tags(body))

        if method == "POST" and route_is(path, "/tags/bulk"):
            return api_response(200, bulk_modify_tags(body))

        if (method == "DELETE" and route_is(path, "/files")) or (
            method == "POST" and route_is(path, "/files/delete")
        ):
            return api_response(200, delete_files(body))

        raise NotFound(f"No route for {method} {path}")
    except BadRequest as exc:
        return api_response(400, {"error": str(exc)})
    except NotFound as exc:
        return api_response(404, {"error": str(exc)})
    except Exception as exc:
        print(f"Unhandled error: {repr(exc)}")
        payload = {"error": "Internal server error"}
        if os.environ.get("DEBUG") == "1":
            payload["detail"] = str(exc)
        return api_response(500, payload)


def get_method(event):
    if not isinstance(event, dict):
        return "POST"
    return (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
        or "POST"
    ).upper()


def get_path(event):
    if not isinstance(event, dict):
        return "/"
    return (event.get("rawPath") or event.get("path") or "/").rstrip("/") or "/"


def route_is(path, suffix):
    return path == suffix or path.endswith(suffix)


def get_json_body(event):
    if not isinstance(event, dict):
        return {}

    if "body" not in event:
        return event

    raw_body = event.get("body")
    if raw_body in (None, ""):
        return {}

    if isinstance(raw_body, (dict, list)):
        return raw_body

    if event.get("isBase64Encoded"):
        raw_body = base64.b64decode(raw_body).decode("utf-8")

    try:
        return json.loads(raw_body)
    except json.JSONDecodeError:
        raise BadRequest("Request body must be valid JSON")


def api_response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
        },
        "body": json.dumps(payload, default=json_default),
    }


def json_default(value):
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    return str(value)


def query_by_tag_counts(body):
    required = parse_count_query(body)
    results = find_items_matching_counts(required)
    return build_query_response(required, results, url_mode="preview")


def query_by_species(body):
    species = parse_tag_list(
        body.get("species") or body.get("tags") or body.get("tag_names")
        if isinstance(body, dict)
        else body
    )

    if not species and isinstance(body, dict):
        species = [key for key in body.keys() if key not in {"urls", "operation"}]

    if not species:
        raise BadRequest("Please provide at least one species name")

    required = {normalise_tag(name): 1 for name in species}
    results = find_items_matching_counts(required)
    return build_query_response(required, results, url_mode="preview")


def query_by_thumbnail_url(body):
    if not isinstance(body, dict):
        raise BadRequest("Body must include thumbnail_url or url")

    thumbnail_url = body.get("thumbnail_url") or body.get("url")
    if not thumbnail_url:
        raise BadRequest("Missing thumbnail_url")

    for item in scan_all_items():
        if url_matches_item_field(thumbnail_url, item, "thumbnail_key"):
            result = build_result(item)
            return {
                "thumbnail_url": result["thumbnail_url"],
                "full_url": result["full_url"],
                "file_id": result["file_id"],
            }

    raise NotFound("No image found for that thumbnail URL")


def query_by_uploaded_file_tags(body):
    if not isinstance(body, dict):
        raise BadRequest("Body must be a JSON object")

    detected_tags = detect_tags_for_query_file(body)
    required = {normalise_tag(tag): 1 for tag in detected_tags}
    results = find_items_matching_counts(required)
    return build_query_response(required, results, url_mode="full")


def bulk_modify_tags(body):
    if not isinstance(body, dict):
        raise BadRequest("Body must be a JSON object")

    urls = parse_url_list(body.get("urls") or body.get("file_urls"))
    tags = parse_tag_list(body.get("tags"))
    operation = body.get("operation")

    if not urls:
        raise BadRequest("Missing urls list")
    if not tags:
        raise BadRequest("Missing tags list")
    if operation not in (0, 1, "0", "1"):
        raise BadRequest("operation must be 1 for add or 0 for remove")

    add_tags = int(operation) == 1
    items_by_url, missing_urls = find_items_by_urls(urls)
    updated = []

    for url, item in items_by_url.items():
        if add_tags:
            changed = add_manual_tags(item, tags)
        else:
            changed = remove_tags(item, tags)

        if changed:
            save_item(item)

        updated.append(
            {
                "input_url": url,
                "file_id": item.get("file_id"),
                "changed": changed,
                "tags": item.get("tag_names", []),
            }
        )

    return {
        "operation": "add" if add_tags else "remove",
        "updated_count": len(updated),
        "updated": updated,
        "missing_urls": missing_urls,
    }


def delete_files(body):
    if not isinstance(body, dict):
        raise BadRequest("Body must be a JSON object")

    urls = parse_url_list(body.get("urls") or body.get("file_urls"))
    if not urls:
        raise BadRequest("Missing urls list")

    items_by_url, missing_urls = find_items_by_urls(urls)
    deleted = []

    seen_file_ids = set()
    for item in items_by_url.values():
        file_id = item.get("file_id")
        if file_id in seen_file_ids:
            continue
        seen_file_ids.add(file_id)

        deleted_keys = delete_storage_objects(item)
        delete_item(item)
        deleted.append({"file_id": file_id, "deleted_keys": deleted_keys})

    return {
        "deleted_count": len(deleted),
        "deleted": deleted,
        "missing_urls": missing_urls,
    }


def parse_count_query(body):
    if isinstance(body, dict) and "tags" in body and isinstance(body["tags"], dict):
        raw_counts = body["tags"]
    elif isinstance(body, dict):
        raw_counts = body
    else:
        raise BadRequest('Tag count query must be a JSON object, e.g. {"koala": 3}')

    required = {}
    for name, count in raw_counts.items():
        if name in {"urls", "operation", "thumbnail_url", "url"}:
            continue

        if isinstance(count, dict):
            count = count.get("count", 1)

        try:
            count = int(Decimal(str(count)))
        except Exception:
            raise BadRequest(f"Invalid minimum count for tag '{name}'")

        if count < 1:
            raise BadRequest("Minimum counts must be at least 1")

        required[normalise_tag(name)] = count

    if not required:
        raise BadRequest("Please provide at least one tag count")

    return required


def parse_tag_list(raw_tags):
    if raw_tags is None:
        return []

    if isinstance(raw_tags, str):
        return [raw_tags.strip()] if raw_tags.strip() else []

    if isinstance(raw_tags, dict):
        return [str(key).strip() for key in raw_tags.keys() if str(key).strip()]

    if isinstance(raw_tags, list):
        tags = []
        for tag in raw_tags:
            if isinstance(tag, dict):
                value = tag.get("common_name") or tag.get("name") or tag.get("scientific_name")
            else:
                value = tag
            if value is not None and str(value).strip():
                tags.append(str(value).strip())
        return tags

    return []


def parse_url_list(raw_urls):
    if raw_urls is None:
        return []
    if isinstance(raw_urls, str):
        return [raw_urls.strip()] if raw_urls.strip() else []
    if isinstance(raw_urls, list):
        return [str(url).strip() for url in raw_urls if str(url).strip()]
    return []


def find_items_matching_counts(required_counts):
    matched = []
    for item in scan_all_items():
        item_counts = item_tag_counts(item)
        if all(item_counts.get(tag, 0) >= min_count for tag, min_count in required_counts.items()):
            matched.append(item)
    return matched


def build_query_response(query, items, url_mode):
    results = [build_result(item) for item in items]
    url_field = "full_url" if url_mode == "full" else "preview_url"
    return {
        "query": query,
        "count": len(results),
        "urls": [result[url_field] for result in results if result.get(url_field)],
        "results": results,
    }


def build_result(item):
    file_type = item.get("file_type", "image")
    original_key = item.get("original_key")
    thumbnail_key = item.get("thumbnail_key")

    full_url = key_to_url(original_key)
    thumbnail_url = key_to_url(thumbnail_key) if thumbnail_key else None
    preview_url = thumbnail_url if file_type == "image" and thumbnail_url else full_url

    return {
        "file_id": item.get("file_id"),
        "file_type": file_type,
        "preview_url": preview_url,
        "thumbnail_url": thumbnail_url,
        "full_url": full_url,
        "tags": item.get("tags", []),
        "tag_names": item.get("tag_names", []),
    }


def item_tag_counts(item):
    counts = {}
    tags = item.get("tags") or []

    if tags:
        for tag in tags:
            if not isinstance(tag, dict):
                continue
            count = safe_int(tag.get("count", 1), default=1)
            remember_count(counts, tag.get("common_name"), count)
            remember_count(counts, tag.get("scientific_name"), count)

        for tag_name in item.get("tag_names", []):
            remember_count(counts, tag_name, 1)
        return counts

    detection_counts = {}
    for detection in item.get("detections", []):
        if not isinstance(detection, dict):
            continue
        for field in ("common_name", "scientific_name"):
            name = detection.get(field)
            if name:
                norm = normalise_tag(name)
                detection_counts[norm] = detection_counts.get(norm, 0) + 1

    return detection_counts


def remember_count(counts, name, count):
    if not name:
        return
    norm = normalise_tag(name)
    counts[norm] = max(counts.get(norm, 0), count)


def normalise_tag(name):
    return " ".join(str(name).strip().lower().replace("_", " ").split())


def safe_int(value, default=0):
    try:
        return int(Decimal(str(value)))
    except Exception:
        return default


def key_to_url(key):
    if not key:
        return None

    key = str(key)
    if key.startswith("http://") or key.startswith("https://"):
        return key

    public_base_url = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    if public_base_url:
        return f"{public_base_url}/{quote(key, safe='/')}"

    bucket_name = os.environ.get("MEDIA_BUCKET") or os.environ.get("S3_BUCKET")
    if (
        bucket_name
        and os.environ.get("PRESIGN_URLS") == "1"
        and not os.environ.get("LOCAL_ITEMS_FILE")
    ):
        expires_in = safe_int(os.environ.get("PRESIGN_SECONDS", "3600"), default=3600)
        return get_s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )

    if bucket_name:
        return f"https://{bucket_name}.s3.amazonaws.com/{quote(key, safe='/')}"

    return key


def url_to_key(url_or_key):
    if not url_or_key:
        return ""

    value = str(url_or_key).strip()
    public_base_url = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    if public_base_url and value.startswith(public_base_url + "/"):
        return unquote(value[len(public_base_url) + 1 :])

    if not value.startswith("http://") and not value.startswith("https://"):
        return unquote(value.lstrip("/"))

    parsed = urlparse(value)
    key = unquote(parsed.path.lstrip("/"))

    bucket_name = os.environ.get("MEDIA_BUCKET") or os.environ.get("S3_BUCKET")
    if bucket_name and key.startswith(bucket_name + "/"):
        key = key[len(bucket_name) + 1 :]

    return key


def url_matches_item_field(input_url, item, field_name):
    wanted_key = url_to_key(input_url)
    wanted_text = str(input_url).strip()
    field_value = item.get(field_name)

    if not field_value:
        return False

    candidates = {
        str(field_value),
        url_to_key(field_value),
        key_to_url(field_value),
    }
    return wanted_key in candidates or wanted_text in candidates


def find_items_by_urls(urls):
    items_by_url = {}
    missing_urls = []
    items = scan_all_items()

    for url in urls:
        match = None
        for item in items:
            if item_matches_url(item, url):
                match = item
                break

        if match:
            items_by_url[url] = match
        else:
            missing_urls.append(url)

    return items_by_url, missing_urls


def item_matches_url(item, input_url):
    return (
        url_matches_item_field(input_url, item, "original_key")
        or url_matches_item_field(input_url, item, "thumbnail_key")
    )


def add_manual_tags(item, tags):
    existing = item_tag_counts(item)
    changed = False
    item.setdefault("tags", [])

    for tag in tags:
        norm = normalise_tag(tag)
        if norm in existing:
            continue

        item["tags"].append(
            {
                "common_name": tag,
                "scientific_name": tag.replace(" ", "_").lower(),
                "count": 1,
                "source": "manual",
            }
        )
        existing[norm] = 1
        changed = True

    if changed:
        sync_tag_names(item)
    return changed


def remove_tags(item, tags):
    remove_set = {normalise_tag(tag) for tag in tags}
    old_tags = item.get("tags", [])
    old_tag_names = item.get("tag_names", [])
    new_tags = []

    for tag in old_tags:
        if not isinstance(tag, dict):
            new_tags.append(tag)
            continue
        tag_names = {
            normalise_tag(tag.get("common_name", "")),
            normalise_tag(tag.get("scientific_name", "")),
        }
        if tag_names.isdisjoint(remove_set):
            new_tags.append(tag)

    changed = len(new_tags) != len(old_tags) or any(
        normalise_tag(name) in remove_set for name in old_tag_names
    )
    if changed:
        item["tags"] = new_tags
        sync_tag_names(item)
    return changed


def sync_tag_names(item):
    names = []
    seen = set()
    for tag in item.get("tags", []):
        if not isinstance(tag, dict):
            continue
        name = tag.get("common_name") or tag.get("scientific_name")
        if not name:
            continue
        norm = normalise_tag(name)
        if norm not in seen:
            names.append(name)
            seen.add(norm)
    item["tag_names"] = names


def detect_tags_for_query_file(body):
    for field in ("detected_tags", "species", "tags"):
        tags = parse_tag_list(body.get(field))
        if tags:
            return tags

    function_name = os.environ.get("TAGGER_FUNCTION_NAME")
    if not function_name:
        raise BadRequest(
            "No detected_tags were provided and TAGGER_FUNCTION_NAME is not configured"
        )

    payload = {
        "filename": body.get("filename"),
        "content_type": body.get("content_type"),
        "file_base64": body.get("file_base64"),
        "temporary_query": True,
    }

    if not payload["file_base64"]:
        raise BadRequest("Missing file_base64 for file tag query")

    response = get_lambda_client().invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode("utf-8"),
    )

    raw_payload = response["Payload"].read().decode("utf-8")
    detected = json.loads(raw_payload) if raw_payload else {}
    if isinstance(detected, dict) and "body" in detected:
        detected = json.loads(detected["body"])

    tags = parse_tag_list(
        detected.get("tag_names")
        or detected.get("tags")
        or [item.get("common_name") for item in detected.get("detections", [])]
    )

    if not tags:
        raise NotFound("No species tags were detected in the query file")

    return tags


def scan_all_items():
    local_items_file = os.environ.get("LOCAL_ITEMS_FILE")
    if local_items_file:
        return scan_local_items(local_items_file)

    table = get_table()
    items = []
    scan_kwargs = {}

    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    return items


def scan_local_items(local_items_file):
    global _LOCAL_ITEMS_CACHE
    if _LOCAL_ITEMS_CACHE is None:
        with open(local_items_file, "r", encoding="utf-8") as handle:
            raw_items = json.load(handle)
        _LOCAL_ITEMS_CACHE = [normalise_ddb_item(item) for item in raw_items]
    return _LOCAL_ITEMS_CACHE


def save_item(item):
    local_items_file = os.environ.get("LOCAL_ITEMS_FILE")
    if local_items_file:
        replace_local_item(item)
        return

    get_table().put_item(Item=item)


def replace_local_item(item):
    global _LOCAL_ITEMS_CACHE
    if _LOCAL_ITEMS_CACHE is None:
        return

    file_id = item.get("file_id")
    for index, current in enumerate(_LOCAL_ITEMS_CACHE):
        if current.get("file_id") == file_id:
            _LOCAL_ITEMS_CACHE[index] = deepcopy(item)
            return
    _LOCAL_ITEMS_CACHE.append(deepcopy(item))


def delete_item(item):
    local_items_file = os.environ.get("LOCAL_ITEMS_FILE")
    if local_items_file:
        delete_local_item(item)
        return

    get_table().delete_item(Key={"file_id": item["file_id"]})


def delete_local_item(item):
    global _LOCAL_ITEMS_CACHE
    if _LOCAL_ITEMS_CACHE is None:
        return

    file_id = item.get("file_id")
    _LOCAL_ITEMS_CACHE = [
        current for current in _LOCAL_ITEMS_CACHE if current.get("file_id") != file_id
    ]


def delete_storage_objects(item):
    bucket_name = os.environ.get("MEDIA_BUCKET") or os.environ.get("S3_BUCKET")
    keys = [
        url_to_key(item.get("original_key")),
        url_to_key(item.get("thumbnail_key")),
    ]
    keys = [key for key in keys if key]

    if os.environ.get("LOCAL_ITEMS_FILE") or not bucket_name:
        return keys

    s3_client = get_s3_client()
    for key in keys:
        s3_client.delete_object(Bucket=bucket_name, Key=key)

    return keys


def get_table():
    global _DDB_TABLE
    if _DDB_TABLE is None:
        table_name = os.environ.get("TABLE_NAME")
        if not table_name:
            raise BadRequest("TABLE_NAME environment variable is not configured")
        import boto3

        _DDB_TABLE = boto3.resource("dynamodb").Table(table_name)
    return _DDB_TABLE


def get_s3_client():
    global _S3_CLIENT
    if _S3_CLIENT is None:
        import boto3

        _S3_CLIENT = boto3.client("s3")
    return _S3_CLIENT


def get_lambda_client():
    global _LAMBDA_CLIENT
    if _LAMBDA_CLIENT is None:
        import boto3

        _LAMBDA_CLIENT = boto3.client("lambda")
    return _LAMBDA_CLIENT


def normalise_ddb_item(item):
    if not isinstance(item, dict):
        return item

    if all(is_ddb_attribute(value) for value in item.values()):
        return {key: ddb_value_to_python(value) for key, value in item.items()}

    return item


def is_ddb_attribute(value):
    return isinstance(value, dict) and len(value) == 1 and next(iter(value.keys())) in DDB_TYPES


def ddb_value_to_python(value):
    attr_type, attr_value = next(iter(value.items()))

    if attr_type == "S":
        return attr_value
    if attr_type == "N":
        number = Decimal(str(attr_value))
        if number == number.to_integral_value():
            return int(number)
        return number
    if attr_type == "BOOL":
        return bool(attr_value)
    if attr_type == "NULL":
        return None
    if attr_type == "M":
        return {key: ddb_value_to_python(val) for key, val in attr_value.items()}
    if attr_type == "L":
        return [ddb_value_to_python(val) for val in attr_value]
    if attr_type == "SS":
        return list(attr_value)
    if attr_type == "NS":
        return [Decimal(str(val)) for val in attr_value]

    return attr_value
