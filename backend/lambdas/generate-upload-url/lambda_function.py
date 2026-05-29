import json
import boto3
import uuid
from botocore.config import Config

AWS_REGION = "ap-southeast-2"
BUCKET_NAME = "aussie-ecolens-uploads-068799539438-ap-southeast-2-an"

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    endpoint_url=f"https://s3.{AWS_REGION}.amazonaws.com",
    config=Config(signature_version="s3v4")
)

def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body)
    }


def get_user_claims(event):
    claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("jwt", {})
        .get("claims", {})
    )

    user_id = claims.get("sub")
    email = claims.get("email")

    return user_id, email

def get_file_info(file_name):
    extension = file_name.lower().rsplit(".", 1)[-1]

    allowed_types = {
        "jpg": ("image", "image/jpeg"),
        "jpeg": ("image", "image/jpeg"),
        "png": ("image", "image/png"),
        "mp4": ("video", "video/mp4"),
        "mov": ("video", "video/quicktime"),
        "avi": ("video", "video/x-msvideo")
    }

    return extension, allowed_types.get(extension)


def lambda_handler(event, context):
    user_id, email = get_user_claims(event)

    if not user_id:
        return response(401, {"error": "Unauthorised"})

    body = json.loads(event.get("body", "{}"))
    file_name = body.get("fileName")

    if not file_name:
        return response(400, {"error": "fileName is required"})

    extension, file_info = get_file_info(file_name)

    if not file_info:
        return response(400, {
            "error": "Unsupported file type",
            "allowed": ["jpg", "jpeg", "png", "mp4", "mov", "avi"]
        })

    file_type, content_type = file_info
    file_id = str(uuid.uuid4())

    key = f"raw/{file_type}s/{file_id}.{extension}"

    upload_url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": BUCKET_NAME,
            "Key": key,
            "ContentType": content_type,
            "Metadata": {
                "user_id": user_id,
                "user_email": email or "",
                "original_file_name": file_name,
                "file_id": file_id,
                "file_type": file_type
            }
        },
        ExpiresIn=300
    )

    return response(200, {
        "uploadUrl": upload_url,
        "key": key,
        "fileId": file_id,
        "fileType": file_type,
        "fileName": file_name,
        "contentType": content_type,
        "userId": user_id,
        "userEmail": email
    })