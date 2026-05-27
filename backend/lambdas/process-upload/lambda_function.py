import urllib.parse
import boto3
import hashlib
import uuid
from datetime import datetime
from io import BytesIO
from PIL import Image
import json

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
lambda_client = boto3.client("lambda")

table = dynamodb.Table("media_files")

ML_LAMBDA_NAME = "wildlife-ml-inference"


def is_supported_image(key):
    return key.lower().endswith((".jpg", ".jpeg", ".png"))


def get_s3_file_bytes(bucket, key):
    response = s3.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def calculate_sha256(file_bytes):
    return hashlib.sha256(file_bytes).hexdigest()


def find_duplicate_by_checksum(checksum):
    response = table.scan()

    for item in response.get("Items", []):
        if item.get("checksum") == checksum:
            return item

    return None


def handle_deduplication(bucket, key, checksum):
    existing_item = find_duplicate_by_checksum(checksum)

    if not existing_item:
        return False

    print("Duplicate file detected")

    print(f"Existing file key: {existing_item.get('original_key')}")
    print(f"Duplicate upload key: {key}")

    s3.delete_object(
        Bucket=bucket,
        Key=key
    )

    print("Duplicate upload deleted from S3")

    return True


def create_thumbnail(file_bytes, max_size=(300, 300)):
    image = Image.open(BytesIO(file_bytes))
    image.thumbnail(max_size)

    output = BytesIO()

    image.convert("RGB").save(
        output,
        format="JPEG",
        quality=80
    )

    output.seek(0)

    return output


def upload_thumbnail(bucket, file_key, file_bytes):
    filename = file_key.split("/")[-1]

    thumbnail_key = (
        f"thumbnails/"
        f"{filename.rsplit('.', 1)[0]}_thumb.jpg"
    )

    thumbnail = create_thumbnail(file_bytes)

    s3.put_object(
        Bucket=bucket,
        Key=thumbnail_key,
        Body=thumbnail,
        ContentType="image/jpeg"
    )

    print(f"Thumbnail uploaded: {thumbnail_key}")

    return thumbnail_key


def start_ml_processing(bucket, key, file_id):
    lambda_client.invoke(
        FunctionName=ML_LAMBDA_NAME,
        InvocationType="Event",
        Payload=json.dumps({
            "bucket": bucket,
            "key": key,
            "file_id": file_id
        })
    )

    print("ML Lambda invoked asynchronously")


def save_metadata(
    checksum,
    file_id,
    original_key,
    thumbnail_key,
    file_type
):
    table.put_item(
        Item={
            "file_id": file_id,
            "checksum": checksum,
            "original_key": original_key,
            "thumbnail_key": thumbnail_key,
            "file_type": file_type,
            "tags": [],
            "tag_names": [],
            "detections": [],
            "uploaded_at": (
                datetime.utcnow().isoformat() + "Z"
            ),
            "uploaded_by": "placeholder-user",
            "uploaded_email": "placeholder@email.com",
            "status": "pending"
        }
    )

    print("Pending metadata saved to DynamoDB")


def process_image_upload(bucket, key, size):
    if key.endswith("/"):
        print(f"Skipping folder object: {key}")
        return

    if size == 0:
        print(f"Empty upload detected, deleting: {key}")

        s3.delete_object(
            Bucket=bucket,
            Key=key
        )

        print("Empty upload deleted from S3")

        return

    if not is_supported_image(key):
        print(f"Unsupported file type, deleting: {key}")

        s3.delete_object(
            Bucket=bucket,
            Key=key
        )

        print("Unsupported upload deleted from S3")

        return

    file_bytes = get_s3_file_bytes(bucket, key)

    checksum = calculate_sha256(file_bytes)

    print(f"SHA256: {checksum}")

    is_duplicate = handle_deduplication(
        bucket,
        key,
        checksum
    )

    if is_duplicate:
        return

    thumbnail_key = upload_thumbnail(
        bucket,
        key,
        file_bytes
    )

    file_id = str(uuid.uuid4())

    save_metadata(
        checksum=checksum,
        file_id=file_id,
        original_key=key,
        thumbnail_key=thumbnail_key,
        file_type="image"
    )

    start_ml_processing(
        bucket=bucket,
        key=key,
        file_id=file_id
    )


def lambda_handler(event, context):
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]

        key = urllib.parse.unquote_plus(
            record["s3"]["object"]["key"]
        )

        size = record["s3"]["object"]["size"]

        process_image_upload(
            bucket,
            key,
            size
        )

    return {
        "statusCode": 200
    }