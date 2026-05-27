import json
import os
import boto3
import tempfile

from decimal import Decimal

from model_service import WildlifeModelService

s3 = boto3.client("s3")

dynamodb = boto3.resource("dynamodb")

table = dynamodb.Table("media_files")

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
        return [
            convert_floats(item)
            for item in obj
        ]

    if isinstance(obj, dict):
        return {
            key: convert_floats(value)
            for key, value in obj.items()
        }

    return obj


def convert_decimals(obj):
    if isinstance(obj, Decimal):
        return float(obj)

    if isinstance(obj, list):
        return [
            convert_decimals(item)
            for item in obj
        ]

    if isinstance(obj, dict):
        return {
            key: convert_decimals(value)
            for key, value in obj.items()
        }

    return obj


def update_metadata(
    file_id,
    status,
    result=None,
    error=None
):
    if status == "completed":
        result = convert_floats(result)

        table.update_item(
            Key={
                "file_id": file_id
            },

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

                ":tags": result.get(
                    "tags",
                    []
                ),

                ":tag_names": result.get(
                    "tag_names",
                    []
                ),

                ":detections": result.get(
                    "detections",
                    []
                )
            }
        )

    else:
        table.update_item(
            Key={
                "file_id": file_id
            },

            UpdateExpression="""
                SET #status = :status,
                    processing_error = :error
            """,

            ExpressionAttributeNames={
                "#status": "status"
            },

            ExpressionAttributeValues={
                ":status": "failed",

                ":error": (
                    error
                    or "Unknown ML processing error"
                )
            }
        )


def lambda_handler(event, context):
    if (
        "body" in event
        and isinstance(event["body"], str)
    ):
        event = json.loads(event["body"])

    bucket = event["bucket"]

    key = event["key"]

    file_id = event.get("file_id")

    if not file_id:
        raise ValueError(
            "file_id is required"
        )

    suffix = "." + key.split(".")[-1]

    image_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as tmp:

            s3.download_fileobj(
                bucket,
                key,
                tmp
            )

            image_path = tmp.name

        service = get_model_service()

        result = service.process_image(
            image_path
        )

        update_metadata(
            file_id=file_id,
            status="completed",
            result=result
        )

        print(
            "ML processing completed "
            "and metadata updated"
        )

        return {
            "statusCode": 200,

            "body": json.dumps(
                convert_decimals(result)
            )
        }

    except Exception as e:
        print(
            f"ML processing failed: {e}"
        )

        update_metadata(
            file_id=file_id,
            status="failed",
            error=str(e)
        )

        raise

    finally:
        if (
            image_path
            and os.path.exists(image_path)
        ):
            os.remove(image_path)