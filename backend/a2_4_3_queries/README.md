# Aussie EcoLens Query API

AWS Lambda implementation for the query and media-management component of the
FIT5225 Assignment 2 project.

## Contributor Scope

This module implements the Section 4.3 query APIs. It exposes REST endpoints
through API Gateway and works with media metadata stored in DynamoDB and media
objects stored in Amazon S3.

The Lambda supports:

- querying files by species tags and minimum occurrence counts;
- querying files by one or more species names;
- resolving an original image URL from a thumbnail URL;
- querying existing files using tags detected from a temporary query file;
- adding or removing tags for multiple files;
- deleting files from both S3 and DynamoDB.

## Architecture

```text
Client
  -> API Gateway
  -> Query Lambda
      -> DynamoDB media_files table
      -> S3 media bucket
      -> Optional tagger Lambda for temporary-file queries
```

## Project Structure

```text
a2_4_3_queries/
|-- src/
|   `-- app.py                  # Lambda handler and query logic
|-- tests/
|   |-- sample_items.json       # Local test fixture
|   `-- test_app.py             # Unit tests
|-- scripts/
|   |-- deploy_cloudshell.sh    # AWS CloudShell deployment script
|   `-- test_api.sh             # Deployed API smoke tests
|-- template.yaml               # AWS SAM template
`-- README.md
```

## API Endpoints

Set the deployed API URL before running the examples:

```bash
export BASE_URL="https://<api-id>.execute-api.<region>.amazonaws.com"
```

If JWT authentication is enabled, also add:

```bash
-H "Authorization: Bearer <token>"
```

### Query by Tags and Minimum Counts

```http
POST /query/tags
```

Returns files containing all requested tags with at least the specified number
of occurrences.

```bash
curl -X POST "$BASE_URL/query/tags" \
  -H "Content-Type: application/json" \
  -d '{"cattle": 3}'
```

The example returns files containing at least three cattle.

### Query by Species

```http
POST /query/species
```

```bash
curl -X POST "$BASE_URL/query/species" \
  -H "Content-Type: application/json" \
  -d '{"species": ["dingo"]}'
```

Multiple species use AND matching: every requested species must be present.

### Resolve an Original File from a Thumbnail

```http
POST /query/thumbnail
```

```bash
curl -X POST "$BASE_URL/query/thumbnail" \
  -H "Content-Type: application/json" \
  -d '{"thumbnail_url": "https://<bucket>.s3.amazonaws.com/thumbnails/<file>_thumb.jpg"}'
```

### Query Using Tags from a Temporary File

```http
POST /query/file-tags
```

For a simple integration test, pass already detected tags:

```bash
curl -X POST "$BASE_URL/query/file-tags" \
  -H "Content-Type: application/json" \
  -d '{"detected_tags": ["cattle"]}'
```

For the full workflow, configure `TAGGER_FUNCTION_NAME` and send a Base64
encoded temporary file:

```json
{
  "filename": "query.jpg",
  "content_type": "image/jpeg",
  "file_base64": "<base64-data>"
}
```

### Bulk Add or Remove Tags

```http
POST /tags/bulk
```

Use `operation: 1` to add tags:

```bash
curl -X POST "$BASE_URL/tags/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://<bucket>.s3.amazonaws.com/raw/<file>.JPG"],
    "tags": ["night"],
    "operation": 1
  }'
```

Use `operation: 0` to remove tags:

```bash
curl -X POST "$BASE_URL/tags/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://<bucket>.s3.amazonaws.com/raw/<file>.JPG"],
    "tags": ["night"],
    "operation": 0
  }'
```

### Delete Files

```http
DELETE /files
POST /files/delete
```

Both routes delete the original S3 object, the thumbnail if present, and the
corresponding DynamoDB record.

```bash
curl -X DELETE "$BASE_URL/files" \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://<bucket>.s3.amazonaws.com/raw/<test-file>.JPG"]}'
```

Use this endpoint carefully. It performs a destructive operation.

## DynamoDB Data Model

The Lambda expects a DynamoDB table containing media metadata. The primary key
is `file_id`.

| Field | Description |
| --- | --- |
| `file_id` | Unique file identifier and DynamoDB partition key |
| `file_type` | Media type, such as `image` or `video` |
| `original_key` | S3 key for the original file |
| `thumbnail_key` | S3 key for the thumbnail, when available |
| `tags` | Tag records containing `common_name`, `scientific_name`, `count`, and `source` |
| `tag_names` | Simplified tag-name list used for display and matching |

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `TABLE_NAME` | Yes | DynamoDB media metadata table |
| `MEDIA_BUCKET` | Yes | S3 bucket containing original files and thumbnails |
| `PUBLIC_BASE_URL` | No | Optional public URL prefix, such as a CloudFront domain |
| `TAGGER_FUNCTION_NAME` | No | Lambda function used to detect tags for temporary query files |
| `PRESIGN_URLS` | No | Set to `1` to return presigned S3 URLs; defaults to `1` |
| `PRESIGN_SECONDS` | No | Presigned URL lifetime in seconds; defaults to `3600` |

## Local Tests

The tests use `tests/sample_items.json`, so they do not require an AWS account.

```bash
python3 -m unittest discover -s tests -v
```

The test suite covers:

- tag count queries and AND matching;
- species queries;
- thumbnail-to-original URL resolution;
- temporary-file tag queries using provided detections;
- bulk tag addition and removal;
- local-mode deletion.

## Deployment

### AWS CloudShell Script

From the `a2_4_3_queries` directory:

```bash
REGION=ap-southeast-2 \
TABLE_NAME=media_files \
BUCKET_NAME=<media-bucket-name> \
bash scripts/deploy_cloudshell.sh
```

The script packages the Lambda, configures its IAM role, creates or updates the
HTTP API Gateway routes, and prints the API URL.

Optional Cognito JWT protection can be enabled during deployment:

```bash
COGNITO_USER_POOL_ID=<user-pool-id> \
COGNITO_CLIENT_ID=<client-id> \
bash scripts/deploy_cloudshell.sh
```

### AWS SAM Template

The included `template.yaml` provides an alternative AWS SAM deployment
configuration:

```bash
sam build
sam deploy --guided
```

## Deployed API Smoke Test

After deployment:

```bash
BASE_URL="https://<api-id>.execute-api.<region>.amazonaws.com" \
bash scripts/test_api.sh
```

## Implementation Note

The assignment implementation uses DynamoDB `Scan` so that it remains simple
and compatible with the existing table structure. For a larger production
dataset, the table design should be extended with suitable indexes or a
dedicated search layer.

## Security Note

Do not commit AWS credentials, JWT tokens, `.env` files, build artifacts, or
active unprotected API URLs. Protect write and delete endpoints with an
authorizer before exposing them publicly.
