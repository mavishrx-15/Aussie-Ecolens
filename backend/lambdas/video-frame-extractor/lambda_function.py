import json
import os
import cv2
import boto3
import tempfile
from decimal import Decimal

s3 = boto3.client("s3")
lambda_client = boto3.client("lambda")
dynamodb = boto3.resource("dynamodb")

table = dynamodb.Table("media_files")

ML_LAMBDA_NAME = "wildlife-ml-inference"


def lambda_handler(event, context):
    if event.get("temporary_query"):
        print("Handling Temporary Query")
        return handle_temporary_query_video(event)

    print("Handling Video Tagging Upload")
    return handle_permanent_video_upload(event)


def handle_permanent_video_upload(event):
    bucket = event["bucket"]
    key = event["key"]
    file_id = event["file_id"]

    local_video_path = None
    saved_frames = []

    try:
        local_video_path = download_video(bucket, key)
        saved_frames = extract_frames(bucket, key, file_id, local_video_path)

        if len(saved_frames) == 0:
            raise ValueError("No frames extracted from video")

        table.update_item(
            Key={"file_id": file_id},
            UpdateExpression="""
                SET #status = :status,
                    expected_frames = :expected_frames
            """,
            ExpressionAttributeNames={
                "#status": "status"
            },
            ExpressionAttributeValues={
                ":status": "pending",
                ":expected_frames": len(saved_frames)
            }
        )

        for frame_key in saved_frames:
            lambda_client.invoke(
                FunctionName=ML_LAMBDA_NAME,
                InvocationType="Event",
                Payload=json.dumps({
                    "bucket": bucket,
                    "key": frame_key,
                    "file_id": file_id,
                    "file_type": "frame",
                    "parent_video_id": file_id
                })
            )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "frames": len(saved_frames)
            })
        }

    except Exception as e:
        print(f"Video frame extraction failed: {e}")

        table.update_item(
            Key={"file_id": file_id},
            UpdateExpression="""
                SET #status = :status,
                    processing_error = :error
            """,
            ExpressionAttributeNames={
                "#status": "status"
            },
            ExpressionAttributeValues={
                ":status": "failed",
                ":error": str(e)
            }
        )

        raise

    finally:
        cleanup_local_file(local_video_path)


def handle_temporary_query_video(event):
    bucket = event["bucket"]
    key = event["key"]
    file_id = event.get("file_id") or get_file_id_from_key(key)

    local_video_path = None
    saved_frames = []

    try:
        local_video_path = download_video(bucket, key)
        saved_frames = extract_frames(bucket, key, file_id, local_video_path, max_frames=2)

        if len(saved_frames) == 0:
            raise ValueError("No frames extracted from query video")

        all_tags = {}

        for frame_key in saved_frames:
            print(f"Inferencing on frame {frame_key}")
            response = lambda_client.invoke(
                FunctionName=ML_LAMBDA_NAME,
                InvocationType="RequestResponse",
                Payload=json.dumps({
                    "bucket": bucket,
                    "key": frame_key,
                    "file_type": "image",
                    "temporary_query": True
                }).encode("utf-8")
            )

            if "FunctionError" in response:
                raise ValueError("ML inference failed for query video frame")

            raw_payload = response["Payload"].read().decode("utf-8")
            result = json.loads(raw_payload) if raw_payload else {}

            if isinstance(result, dict) and "body" in result:
                result = json.loads(result["body"])

            merge_tags(all_tags, result)

        print(f"Frames Inferenced, returning...")

        tags = [
            {
                "common_name": name,
                "scientific_name": name.replace(" ", "_").lower(),
                "count": count,
                "source": "ml"
            }
            for name, count in all_tags.items()
        ]

        return {
            "statusCode": 200,
            "body": json.dumps({
                "tag_names": list(all_tags.keys()),
                "tags": tags
            })
        }

    finally:
        for frame_key in saved_frames:
            try:
                s3.delete_object(Bucket=bucket, Key=frame_key)
            except Exception as e:
                print(f"Failed to delete temp frame {frame_key}: {e}")

        cleanup_local_file(local_video_path)


def download_video(bucket, key):
    suffix = "." + key.split(".")[-1]

    print("Downloading video")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        s3.download_fileobj(bucket, key, tmp)
        local_video_path = tmp.name

    print(f"Downloaded video to {local_video_path}")

    return local_video_path


def extract_frames(bucket, key, file_id, local_video_path, max_frames=30):
    saved_frames = []

    print("Opening video")
    video = cv2.VideoCapture(local_video_path)

    if not video.isOpened():
        raise ValueError("Could not open video")

    fps = video.get(cv2.CAP_PROP_FPS)

    if not fps or fps <= 0:
        fps = 25

    frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_seconds = max(1, int(frame_count / fps))

    print(f"FPS: {fps}")
    print(f"Frame count: {frame_count}")
    print(f"Duration: {duration_seconds}s")

    frame_number = 0

    try:
        for second in range(min(duration_seconds, max_frames)):
            timestamp_ms = second * 1000

            video.set(cv2.CAP_PROP_POS_MSEC, timestamp_ms)

            success, frame = video.read()

            if not success:
                print(f"Could not read frame at {second}s")
                continue

            frame_key = (
                f"temp/frames/{file_id}/"
                f"frame_{frame_number:04d}.jpg"
            )

            success, encoded = cv2.imencode(".jpg", frame)

            if not success:
                raise ValueError("Could not encode frame")

            s3.put_object(
                Bucket=bucket,
                Key=frame_key,
                Body=encoded.tobytes(),
                ContentType="image/jpeg"
            )

            saved_frames.append(frame_key)
            frame_number += 1

            print(f"Saved frame: {frame_key}")

    finally:
        video.release()

    print(f"Extracted {len(saved_frames)} frames")

    return saved_frames


def merge_tags(all_tags, result):
    for tag in result.get("tags", []):
        if not isinstance(tag, dict):
            continue

        name = tag.get("common_name") or tag.get("scientific_name")

        if not name:
            continue

        count = safe_int(tag.get("count", 1), default=1)
        all_tags[name] = max(all_tags.get(name, 0), count)

    if not result.get("tags"):
        for name in result.get("tag_names", []):
            if name:
                all_tags[name] = max(all_tags.get(name, 0), 1)


def safe_int(value, default=0):
    try:
        return int(Decimal(str(value)))
    except Exception:
        return default


def get_file_id_from_key(key):
    return os.path.splitext(os.path.basename(key))[0]


def cleanup_local_file(path):
    if path and os.path.exists(path):
        os.remove(path)
        print("Deleted local video file")