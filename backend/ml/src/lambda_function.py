import json
import boto3
import tempfile
from model_service import WildlifeModelService

s3 = boto3.client("s3")
model_service = WildlifeModelService()

def lambda_handler(event, context):
    bucket = event["bucket"]
    key = event["key"]

    suffix = "." + key.split(".")[-1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        s3.download_fileobj(bucket, key, tmp)
        image_path = tmp.name

    result = model_service.process_image(image_path)

    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }