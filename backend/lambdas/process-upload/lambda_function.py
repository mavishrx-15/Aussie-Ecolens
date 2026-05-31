import urllib.parse
import boto3
import hashlib
import cv2
import os
from datetime import datetime
from io import BytesIO
from PIL import Image
import json

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
lambda_client = boto3.client("lambda")

table = dynamodb.Table("media_files")

ML_LAMBDA_NAME = "wildlife-ml-inference"
VIDEO_LAMBDA_NAME = "video-frame-extractor"


def is_supported_image(key):
    return key.lower().endswith((".jpg", ".jpeg", ".png"))


def is_supported_video(key):
    return key.lower().endswith((".mp4", ".mov", ".avi"))


def get_s3_file_bytes(bucket, key):
    response = s3.get_object(
        Bucket=bucket,
        Key=key
    )

    return response["Body"].read()


def calculate_s3_sha256(bucket, key):
    hasher = hashlib.sha256()

    response = s3.get_object(
        Bucket=bucket,
        Key=key
    )

    for chunk in response["Body"].iter_chunks(
        chunk_size=1024 * 1024
    ):
        hasher.update(chunk)

    return hasher.hexdigest()


def get_upload_metadata(bucket, key):
    response = s3.head_object(
        Bucket=bucket,
        Key=key
    )

    metadata = response.get("Metadata", {})

    return {
        "user_id": metadata.get("user_id"),
        "user_email": metadata.get("user_email"),
        "file_id": metadata.get("file_id"),
        "file_type": metadata.get("file_type"),
        "original_file_name": metadata.get("original_file_name")
    }


def is_valid_image(file_bytes):
    try:
        image = Image.open(BytesIO(file_bytes))
        image.verify()

        image = Image.open(BytesIO(file_bytes))
        width, height = image.size

        return width > 0 and height > 0

    except Exception:
        return False


def calculate_sha256(file_bytes):
    return hashlib.sha256(file_bytes).hexdigest()


def delete_upload(bucket, key):
    s3.delete_object(
        Bucket=bucket,
        Key=key
    )


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

    existing_key = existing_item.get("original_key")

    if existing_key == key:
        print("Retry detected for already processed file")
        return True

    print("Duplicate file detected")
    print(f"Existing file key: {existing_key}")
    print(f"Duplicate upload key: {key}")

    delete_upload(bucket, key)

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


def upload_image_thumbnail(bucket, file_key, file_bytes):
    file_id = file_key.split("/")[-1].rsplit(".", 1)[0]

    thumbnail_key = f"thumbnails/{file_id}.jpg"

    thumbnail = create_thumbnail(file_bytes)

    s3.put_object(
        Bucket=bucket,
        Key=thumbnail_key,
        Body=thumbnail,
        ContentType="image/jpeg"
    )

    print(f"Thumbnail uploaded: {thumbnail_key}")

    return thumbnail_key


def create_video_thumbnail(bucket, key, file_id):
    local_video_path = f"/tmp/{file_id}.mp4"

    try:
        s3.download_file(bucket, key, local_video_path)

        video = cv2.VideoCapture(local_video_path)

        try:
            fps = video.get(cv2.CAP_PROP_FPS)
            frame_count = video.get(cv2.CAP_PROP_FRAME_COUNT)

            duration_ms = 0

            if fps > 0:
                duration_ms = (frame_count / fps) * 1000

            thumbnail_time = min(1000, duration_ms / 2)

            video.set(cv2.CAP_PROP_POS_MSEC, thumbnail_time)
            success, frame = video.read()

            if not success:
                video.set(cv2.CAP_PROP_POS_FRAMES, 0)
                success, frame = video.read()

        finally:
            video.release()

        if not success:
            raise Exception("Could not extract video thumbnail frame")

        success, jpeg_bytes = cv2.imencode(".jpg", frame)

        if not success:
            raise Exception("Could not encode frame")

        frame_bytes = jpeg_bytes.tobytes()

        thumbnail = create_thumbnail(frame_bytes)

        thumbnail_key = f"thumbnails/{file_id}.jpg"

        s3.put_object(
            Bucket=bucket,
            Key=thumbnail_key,
            Body=thumbnail,
            ContentType="image/jpeg"
        )

        return thumbnail_key

    finally:
        if os.path.exists(local_video_path):
            os.remove(local_video_path)


def start_ml_processing(bucket, key, file_id):
    lambda_client.invoke(
        FunctionName=ML_LAMBDA_NAME,
        InvocationType="Event",
        Payload=json.dumps({
            "bucket": bucket,
            "key": key,
            "file_id": file_id,
            "file_type": "image"
        })
    )

    print("ML Lambda invoked asynchronously")


def start_video_processing(bucket, key, file_id):
    lambda_client.invoke(
        FunctionName=VIDEO_LAMBDA_NAME,
        InvocationType="Event",
        Payload=json.dumps({
            "bucket": bucket,
            "key": key,
            "file_id": file_id
        })
    )

    print("Video extractor invoked asynchronously")


def save_metadata(
    checksum,
    file_id,
    original_key,
    thumbnail_key,
    file_type,
    uploaded_by,
    uploaded_email,
    original_file_name
):
    table.put_item(
        Item={
            "file_id": file_id,
            "checksum": checksum,
            "original_key": original_key,
            "thumbnail_key": thumbnail_key,
            "file_type": file_type,
            "original_file_name": original_file_name,
            "tags": [],
            "tag_names": [],
            "detections": [],
            "uploaded_at": datetime.utcnow().isoformat() + "Z",
            "uploaded_by": uploaded_by,
            "uploaded_email": uploaded_email,
            "status": "pending"
        }
    )

    print("Pending metadata saved to DynamoDB")


def validate_common_upload(bucket, key, size, expected_type):
    if key.endswith("/"):
        print(f"Skipping folder object: {key}")
        return None

    if size == 0:
        print(f"Empty upload detected: {key}")
        delete_upload(bucket, key)
        return None

    upload_metadata = get_upload_metadata(bucket, key)

    if not upload_metadata["user_id"] or not upload_metadata["file_id"]:
        print("Missing uploader metadata, deleting upload")
        delete_upload(bucket, key)
        return None

    if upload_metadata["file_type"] != expected_type:
        print("File type metadata does not match path, deleting upload")
        delete_upload(bucket, key)
        return None

    return upload_metadata


def process_image_upload(bucket, key, size):
    if not is_supported_image(key):
        delete_upload(bucket, key)
        return

    upload_metadata = validate_common_upload(
        bucket=bucket,
        key=key,
        size=size,
        expected_type="image"
    )

    if not upload_metadata:
        return

    file_bytes = get_s3_file_bytes(bucket, key)

    if not is_valid_image(file_bytes):
        delete_upload(bucket, key)
        return

    checksum = calculate_sha256(file_bytes)

    if handle_deduplication(bucket, key, checksum):
        return

    thumbnail_key = upload_image_thumbnail(
        bucket,
        key,
        file_bytes
    )

    save_metadata(
        checksum=checksum,
        file_id=upload_metadata["file_id"],
        original_key=key,
        thumbnail_key=thumbnail_key,
        file_type="image",
        uploaded_by=upload_metadata["user_id"],
        uploaded_email=upload_metadata["user_email"],
        original_file_name=upload_metadata["original_file_name"]
    )

    start_ml_processing(
        bucket=bucket,
        key=key,
        file_id=upload_metadata["file_id"]
    )


def process_video_upload(bucket, key, size):
    if not is_supported_video(key):
        delete_upload(bucket, key)
        return

    upload_metadata = validate_common_upload(
        bucket=bucket,
        key=key,
        size=size,
        expected_type="video"
    )

    if not upload_metadata:
        return

    checksum = calculate_s3_sha256(bucket, key)

    if handle_deduplication(bucket, key, checksum):
        return

    thumbnail_key = create_video_thumbnail(
        bucket=bucket,
        key=key,
        file_id=upload_metadata["file_id"]
    )

    save_metadata(
        checksum=checksum,
        file_id=upload_metadata["file_id"],
        original_key=key,
        thumbnail_key=thumbnail_key,
        file_type="video",
        uploaded_by=upload_metadata["user_id"],
        uploaded_email=upload_metadata["user_email"],
        original_file_name=upload_metadata["original_file_name"]
    )

    start_video_processing(
        bucket=bucket,
        key=key,
        file_id=upload_metadata["file_id"]
    )


def process_media_upload(bucket, key, size):
    if key.startswith("raw/images/"):
        process_image_upload(bucket, key, size)

    elif key.startswith("raw/videos/"):
        process_video_upload(bucket, key, size)

    else:
        print(f"Skipping unsupported raw path: {key}")


def lambda_handler(event, context):
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]

        key = urllib.parse.unquote_plus(
            record["s3"]["object"]["key"]
        )

        size = record["s3"]["object"]["size"]

        process_media_upload(bucket, key, size)

    return {
        "statusCode": 200
    }