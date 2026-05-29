import json
import os
import cv2
import boto3
import tempfile

s3 = boto3.client("s3")
lambda_client = boto3.client("lambda")
dynamodb = boto3.resource("dynamodb")

table = dynamodb.Table("media_files")

ML_LAMBDA_NAME = "wildlife-ml-inference"


def lambda_handler(event, context):
    bucket = event["bucket"]
    key = event["key"]
    file_id = event["file_id"]

    local_video_path = None
    saved_frames = []

    try:
        suffix = "." + key.split(".")[-1]

        print("Downloading video")

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            s3.download_fileobj(bucket, key, tmp)
            local_video_path = tmp.name

        print(f"Downloaded video to {local_video_path}")

        print("Opening video")
        video = cv2.VideoCapture(local_video_path)

        if not video.isOpened():
            raise ValueError("Could not open video")

        print("Video opened")

        fps = video.get(cv2.CAP_PROP_FPS)

        if not fps or fps <= 0:
            fps = 25

        frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_seconds = max(1, int(frame_count / fps))

        print(f"FPS: {fps}")
        print(f"Frame count: {frame_count}")
        print(f"Duration: {duration_seconds}s")

        frame_number = 0
        max_frames = 5

        for second in range(min(duration_seconds, max_frames)):
            timestamp_ms = second * 1000

            print(f"Seeking to {second}s")

            video.set(cv2.CAP_PROP_POS_MSEC, timestamp_ms)

            success, frame = video.read()

            if not success:
                print(f"Could not read frame at {second}s")
                continue

            frame_key = (
                f"temp/frames/{file_id}/"
                f"frame_{frame_number:04d}.jpg"
            )

            print(f"Encoding frame {frame_number}")

            success, encoded = cv2.imencode(".jpg", frame)

            if not success:
                raise ValueError("Could not encode frame")

            print(f"Uploading frame {frame_key}")

            s3.put_object(
                Bucket=bucket,
                Key=frame_key,
                Body=encoded.tobytes(),
                ContentType="image/jpeg"
            )

            saved_frames.append(frame_key)

            frame_number += 1

            print(f"Saved frame: {frame_key}")

        video.release()

        print(f"Extracted {len(saved_frames)} frames")

        if len(saved_frames) == 0:
            raise ValueError("No frames extracted from video")

        print("Updating media metadata")

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

        print("Invoking ML lambdas")

        for frame_key in saved_frames:
            print(f"Invoking ML lambda for {frame_key}")

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

            print(f"Invoked ML lambda for {frame_key}")

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
        if local_video_path and os.path.exists(local_video_path):
            os.remove(local_video_path)
            print("Deleted local video file")