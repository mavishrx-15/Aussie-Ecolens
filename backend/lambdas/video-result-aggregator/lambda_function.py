import json
import os
import boto3

from decimal import Decimal

s3 = boto3.client("s3")
sns = boto3.client("sns")
dynamodb = boto3.resource("dynamodb")

media_table = dynamodb.Table("media_files")
frame_results_table = dynamodb.Table("frame_results")

TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
UPLOAD_BUCKET = "aussie-ecolens-uploads-068799539438-ap-southeast-2-an"


def publish_notification(file_id, tags):
    if not tags:
        return

    sns.publish(
        TopicArn=TOPIC_ARN,
        Subject="New Wildlife Video Observation",
        Message=(
            f"New wildlife video processed.\n\n"
            f"File ID: {file_id}\n"
            f"Detected species: {', '.join(tags)}"
        ),
        MessageAttributes={
            "species": {
                "DataType": "String.Array",
                "StringValue": json.dumps(tags)
            }
        }
    )


def convert_floats(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))

    if isinstance(obj, list):
        return [convert_floats(item) for item in obj]

    if isinstance(obj, dict):
        return {key: convert_floats(value) for key, value in obj.items()}

    return obj


def lambda_handler(event, context):
    file_id = event["file_id"]

    media_response = media_table.get_item(
        Key={"file_id": file_id}
    )

    if "Item" not in media_response:
        raise ValueError(f"Video not found: {file_id}")

    media_item = media_response["Item"]

    if media_item.get("status") == "completed":
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Already completed"
            })
        }

    expected_frames = int(
        media_item.get("expected_frames", 0)
    )

    if expected_frames <= 0:
        raise ValueError(
            f"Invalid expected_frames: {expected_frames}"
        )

    response = frame_results_table.scan(
        FilterExpression="video_id = :video_id",
        ExpressionAttributeValues={
            ":video_id": file_id
        }
    )

    frame_items = response.get("Items", [])

    if len(frame_items) < expected_frames:
        return {
            "statusCode": 202,
            "body": json.dumps({
                "message": "Waiting for more frame results",
                "frames_ready": len(frame_items),
                "expected_frames": expected_frames
            })
        }

    tag_counts = {}
    detections = []

    for frame_item in frame_items:
        result = frame_item.get("result", {})

        detections.extend(
            result.get("detections", [])
        )

        for tag in result.get("tags", []):
            common_name = tag["common_name"]

            if common_name not in tag_counts:
                tag_counts[common_name] = {
                    "common_name": common_name,
                    "scientific_name": tag["scientific_name"],
                    "count": 0,
                    "source": "ml"
                }

            tag_counts[common_name]["count"] += tag["count"]

    tags = list(tag_counts.values())
    tag_names = [
        tag["common_name"]
        for tag in tags
    ]

    media_table.update_item(
        Key={"file_id": file_id},
        UpdateExpression="""
            SET #status = :status,
                tags = :tags,
                tag_names = :tag_names,
                detections = :detections
        """,
        ExpressionAttributeNames={
            "#status": "status"
        },
        ExpressionAttributeValues={
            ":status": "completed",
            ":tags": convert_floats(tags),
            ":tag_names": tag_names,
            ":detections": convert_floats(detections)
        }
    )

    publish_notification(
        file_id=file_id,
        tags=tag_names
    )

    for frame_item in frame_items:
        frame_results_table.delete_item(
            Key={
                "frame_id": frame_item["frame_id"]
            }
        )

        s3.delete_object(
            Bucket=UPLOAD_BUCKET,
            Key=frame_item["frame_key"]
        )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Video processing completed",
            "frames": len(frame_items),
            "species": tag_names
        })
    }