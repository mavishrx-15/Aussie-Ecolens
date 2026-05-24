import json
import boto3
import tempfile
from model_service import WildlifeModelService

s3 = boto3.client("s3")
model_service = None

def get_model_service():
    global model_service

    if model_service is None:
        print("Cold start: loading model service")
        model_service = WildlifeModelService()
    else:
        print("Warm start: reusing loaded model service")

    return model_service

def lambda_handler(event, context):
    if "body" in event and isinstance(event["body"], str):
        event = json.loads(event["body"])

    bucket = event["bucket"]
    key = event["key"]

    suffix = "." + key.split(".")[-1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        s3.download_fileobj(bucket, key, tmp)
        image_path = tmp.name

    service = get_model_service()
    result = service.process_image(image_path)

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(result)
    }