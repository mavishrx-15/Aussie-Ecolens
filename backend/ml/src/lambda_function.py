import json
import os
import boto3
import tempfile

from decimal import Decimal
from model_service import WildlifeModelService

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
lambda_client = boto3.client("lambda")

table = dynamodb.Table("media_files")
frame_results_table = dynamodb.Table("frame_results")

AGGREGATOR_LAMBDA_NAME = "video-result-aggregator"

model_service = None


def get_model_service():
    global model_service

    if model_service is None:
        print("Cold start: loading model service")
        model_service = WildlifeModelService()
    else:
        print("Warm start: reusing loaded model service")

    return model_service


def convert_floats(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))

    if isinstance(obj, list):
        return [convert_floats(item) for item in obj]

    if isinstance(obj, dict):
        return {key: convert_floats(value) for key, value in obj.items()}

    return obj


def convert_decimals(obj):
    if isinstance(obj, Decimal):
        return float(obj)

    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]

    if isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}

    return obj


def update_metadata(file_id, status, result=None, error=None):
    if status == "completed":
        result = convert_floats(result)

        table.update_item(
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
                ":tags": result.get("tags", []),
                ":tag_names": result.get("tag_names", []),
                ":detections": result.get("detections", [])
            }
        )

    else:
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
                ":error": error or "Unknown ML processing error"
            }
        )


def save_frame_result(file_id, key, result):
    frame_id = f"{file_id}#{os.path.basename(key)}"

    frame_results_table.put_item(
        Item={
            "frame_id": frame_id,
            "video_id": file_id,
            "frame_key": key,
            "result": convert_floats(result)
        }
    )


def invoke_aggregator(file_id):
    lambda_client.invoke(
        FunctionName=AGGREGATOR_LAMBDA_NAME,
        InvocationType="Event",
        Payload=json.dumps({
            "file_id": file_id
        })
    )


def lambda_handler(event, context):
    if "body" in event and isinstance(event["body"], str):
        event = json.loads(event["body"])

    bucket = event["bucket"]
    key = event["key"]
    file_id = event.get("file_id")
    file_type = event.get("file_type", "image")
    temporary_query = event.get("temporary_query", False)

    if not file_id and not temporary_query:
        raise ValueError("file_id is required")

    print(f"Processing file_id={file_id}, file_type={file_type}, key={key}, temporary_query={temporary_query}")

    suffix = "." + key.split(".")[-1]
    local_file_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            s3.download_fileobj(bucket, key, tmp)
            local_file_path = tmp.name

        service = get_model_service()

        if file_type in ["image", "frame"]:
            result = service.process_image(local_file_path)
        else:
            raise ValueError(f"Unsupported file_type: {file_type}")

        if temporary_query:
            print("Temporary query mode: returning ML result without saving metadata")
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "tag_names": result.get("tag_names", []),
                    "tags": result.get("tags", [])
                })
            }

        if file_type == "image":
            update_metadata(file_id=file_id, status="completed", result=result)

        elif file_type == "frame":
            save_frame_result(file_id=file_id, key=key, result=result)
            invoke_aggregator(file_id=file_id)

        print("ML processing completed")

        return {
            "statusCode": 200,
            "body": json.dumps(convert_decimals(result))
        }

    except Exception as e:
        print(f"ML processing failed: {e}")

        if not temporary_query and file_id:
            update_metadata(file_id=file_id, status="failed", error=str(e))

        raise

    finally:
        if local_file_path and os.path.exists(local_file_path):
            os.remove(local_file_path)