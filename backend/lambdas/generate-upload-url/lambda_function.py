import json
import boto3
import uuid
import os
from botocore.config import Config

AWS_REGION = "ap-southeast-2"
BUCKET_NAME = "aussie-ecolens-uploads-068799539438-ap-southeast-2-an"

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    endpoint_url=f"https://s3.{AWS_REGION}.amazonaws.com",
    config=Config(signature_version="s3v4")
)

def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}"))

    filename = body.get("filename")

    if not filename:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "filename is required"})
        }

    extension = filename.lower().split(".")[-1]

    content_types = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png"
    }

    content_type = content_types.get(
        extension,
        "application/octet-stream"
    )

    safe_filename = filename.replace(" ", "_")
    unique_key = f"raw/{uuid.uuid4()}_{safe_filename}"

    upload_url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": BUCKET_NAME,
            "Key": unique_key,
            "ContentType": content_type
        },
        ExpiresIn=300
    )

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({
            "uploadUrl": upload_url,
            "key": unique_key
        })
    }