#!/usr/bin/env bash
set -euo pipefail

REGION="${REGION:-ap-southeast-2}"
TABLE_NAME="${TABLE_NAME:-media_files}"
FUNCTION_NAME="${FUNCTION_NAME:-fit5225-query-api}"
API_NAME="${API_NAME:-fit5225-query-api}"
BUCKET_NAME="${BUCKET_NAME:-}"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-}"
TAGGER_FUNCTION_NAME="${TAGGER_FUNCTION_NAME:-}"
PRESIGN_URLS="${PRESIGN_URLS:-1}"
PRESIGN_SECONDS="${PRESIGN_SECONDS:-3600}"
COGNITO_USER_POOL_ID="${COGNITO_USER_POOL_ID:-}"
COGNITO_CLIENT_ID="${COGNITO_CLIENT_ID:-}"
ROLE_ARN="${ROLE_ARN:-}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/.build"
ZIP_FILE="$BUILD_DIR/query-api.zip"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

json_escape() {
  python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"
}

aws_text() {
  aws "$@" --output text 2>/dev/null || true
}

wait_for_role() {
  local role_name="$1"
  echo "Waiting for IAM role propagation..."
  for _ in $(seq 1 12); do
    if aws iam get-role --role-name "$role_name" >/dev/null 2>&1; then
      sleep 5
      return
    fi
    sleep 5
  done
}

ensure_bucket_name() {
  if [[ -n "$BUCKET_NAME" ]]; then
    return
  fi

  echo "BUCKET_NAME is not set. Trying to infer one from S3..."
  BUCKET_NAME="$(aws s3api list-buckets \
    --query "Buckets[?contains(Name, 'media') || contains(Name, 'upload') || contains(Name, 'wildlife') || contains(Name, 'fit5225')].Name | [0]" \
    --output text 2>/dev/null || true)"

  if [[ -z "$BUCKET_NAME" || "$BUCKET_NAME" == "None" ]]; then
    echo "Could not infer the media bucket."
    echo "Re-run with: BUCKET_NAME=<your-s3-bucket> bash scripts/deploy_cloudshell.sh"
    exit 1
  fi

  echo "Using inferred bucket: $BUCKET_NAME"
}

ensure_role() {
  if [[ -n "$ROLE_ARN" ]]; then
    echo "Using provided Lambda role: $ROLE_ARN"
    return
  fi

  ROLE_ARN="$(aws_text iam get-role --role-name LabRole --query "Role.Arn")"
  if [[ -n "$ROLE_ARN" && "$ROLE_ARN" != "None" ]]; then
    echo "Using existing AWS Academy LabRole: $ROLE_ARN"
    return
  fi

  local role_name="fit5225-query-lambda-role"
  ROLE_ARN="$(aws_text iam get-role --role-name "$role_name" --query "Role.Arn")"
  if [[ -n "$ROLE_ARN" && "$ROLE_ARN" != "None" ]]; then
    echo "Using existing role: $ROLE_ARN"
    return
  fi

  echo "Creating Lambda execution role: $role_name"
  local trust_policy
  trust_policy='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

  ROLE_ARN="$(aws iam create-role \
    --role-name "$role_name" \
    --assume-role-policy-document "$trust_policy" \
    --query "Role.Arn" \
    --output text)"

  aws iam attach-role-policy \
    --role-name "$role_name" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

  local account_id table_arn bucket_arn object_arn policy_doc
  account_id="$(aws sts get-caller-identity --query Account --output text)"
  table_arn="arn:aws:dynamodb:${REGION}:${account_id}:table/${TABLE_NAME}"
  bucket_arn="arn:aws:s3:::${BUCKET_NAME}"
  object_arn="arn:aws:s3:::${BUCKET_NAME}/*"

  policy_doc="$(cat <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:DescribeTable",
        "dynamodb:Scan",
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": "${table_arn}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "${object_arn}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "${bucket_arn}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": "*"
    }
  ]
}
JSON
)"

  aws iam put-role-policy \
    --role-name "$role_name" \
    --policy-name fit5225-query-api-policy \
    --policy-document "$policy_doc"

  wait_for_role "$role_name"
}

package_lambda() {
  rm -rf "$BUILD_DIR"
  mkdir -p "$BUILD_DIR"
  cp "$ROOT_DIR/src/app.py" "$BUILD_DIR/app.py"
  (cd "$BUILD_DIR" && zip -q "$ZIP_FILE" app.py)
}

ensure_lambda() {
  local exists lambda_arn
  exists="$(aws_text lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" --query "Configuration.FunctionName")"

  if [[ -z "$exists" || "$exists" == "None" ]]; then
    echo "Creating Lambda function: $FUNCTION_NAME"
    aws lambda create-function \
      --function-name "$FUNCTION_NAME" \
      --runtime python3.12 \
      --role "$ROLE_ARN" \
      --handler app.lambda_handler \
      --zip-file "fileb://${ZIP_FILE}" \
      --timeout 30 \
      --memory-size 256 \
      --region "$REGION" >/dev/null
  else
    echo "Updating Lambda function code: $FUNCTION_NAME"
    aws lambda update-function-code \
      --function-name "$FUNCTION_NAME" \
      --zip-file "fileb://${ZIP_FILE}" \
      --region "$REGION" >/dev/null
    aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION"
  fi

  echo "Updating Lambda environment variables"
  local env_file
  env_file="$BUILD_DIR/env.json"
  python3 - <<PY > "$env_file"
import json
env = {
    "Variables": {
        "TABLE_NAME": "${TABLE_NAME}",
        "MEDIA_BUCKET": "${BUCKET_NAME}",
        "PUBLIC_BASE_URL": "${PUBLIC_BASE_URL}",
        "TAGGER_FUNCTION_NAME": "${TAGGER_FUNCTION_NAME}",
        "PRESIGN_URLS": "${PRESIGN_URLS}",
        "PRESIGN_SECONDS": "${PRESIGN_SECONDS}",
    }
}
print(json.dumps(env))
PY
  aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --region "$REGION" \
    --environment "file://${env_file}" >/dev/null
  aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION"

  lambda_arn="$(aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" --query "Configuration.FunctionArn" --output text)"
  echo "$lambda_arn"
}

ensure_http_api() {
  local lambda_arn="$1"
  local api_id integration_id authorizer_id

  api_id="$(aws_text apigatewayv2 get-apis --region "$REGION" --query "Items[?Name=='${API_NAME}'].ApiId | [0]")"
  if [[ -z "$api_id" || "$api_id" == "None" ]]; then
    echo "Creating HTTP API: $API_NAME"
    local cors_file
    cors_file="$BUILD_DIR/cors.json"
    cat > "$cors_file" <<JSON
{
  "AllowOrigins": ["*"],
  "AllowMethods": ["GET", "POST", "DELETE", "OPTIONS"],
  "AllowHeaders": ["Content-Type", "Authorization"]
}
JSON
    api_id="$(aws apigatewayv2 create-api \
      --name "$API_NAME" \
      --protocol-type HTTP \
      --cors-configuration "file://${cors_file}" \
      --region "$REGION" \
      --query "ApiId" \
      --output text)"
  else
    echo "Using existing HTTP API: $api_id"
  fi

  integration_id="$(aws_text apigatewayv2 get-integrations --api-id "$api_id" --region "$REGION" --query "Items[?IntegrationUri=='${lambda_arn}'].IntegrationId | [0]")"
  if [[ -z "$integration_id" || "$integration_id" == "None" ]]; then
    echo "Creating Lambda proxy integration"
    integration_id="$(aws apigatewayv2 create-integration \
      --api-id "$api_id" \
      --integration-type AWS_PROXY \
      --integration-uri "$lambda_arn" \
      --payload-format-version "2.0" \
      --region "$REGION" \
      --query "IntegrationId" \
      --output text)"
  else
    echo "Using existing integration: $integration_id"
  fi

  if [[ -n "$COGNITO_USER_POOL_ID" && -n "$COGNITO_CLIENT_ID" ]]; then
    local issuer audience
    issuer="https://cognito-idp.${REGION}.amazonaws.com/${COGNITO_USER_POOL_ID}"
    audience="$COGNITO_CLIENT_ID"
    authorizer_id="$(aws_text apigatewayv2 get-authorizers --api-id "$api_id" --region "$REGION" --query "Items[?Name=='CognitoJwtAuthorizer'].AuthorizerId | [0]")"
    if [[ -z "$authorizer_id" || "$authorizer_id" == "None" ]]; then
      echo "Creating Cognito JWT authorizer"
      local jwt_file
      jwt_file="$BUILD_DIR/jwt.json"
      cat > "$jwt_file" <<JSON
{
  "Audience": ["${audience}"],
  "Issuer": "${issuer}"
}
JSON
      authorizer_id="$(aws apigatewayv2 create-authorizer \
        --api-id "$api_id" \
        --authorizer-type JWT \
        --name CognitoJwtAuthorizer \
        --identity-source '$request.header.Authorization' \
        --jwt-configuration "file://${jwt_file}" \
        --region "$REGION" \
        --query "AuthorizerId" \
        --output text)"
    else
      echo "Using existing Cognito authorizer: $authorizer_id"
    fi
  fi

  local routes=(
    "POST /query/tags"
    "POST /query/species"
    "POST /query/thumbnail"
    "POST /query/file-tags"
    "POST /tags/bulk"
    "DELETE /files"
    "POST /files/delete"
  )

  for route_key in "${routes[@]}"; do
    local route_id
    route_id="$(aws_text apigatewayv2 get-routes --api-id "$api_id" --region "$REGION" --query "Items[?RouteKey=='${route_key}'].RouteId | [0]")"
    if [[ -n "$route_id" && "$route_id" != "None" ]]; then
      echo "Route already exists: $route_key"
      continue
    fi

    echo "Creating route: $route_key"
    if [[ -n "${authorizer_id:-}" ]]; then
      aws apigatewayv2 create-route \
        --api-id "$api_id" \
        --route-key "$route_key" \
        --target "integrations/${integration_id}" \
        --authorization-type JWT \
        --authorizer-id "$authorizer_id" \
        --region "$REGION" >/dev/null
    else
      aws apigatewayv2 create-route \
        --api-id "$api_id" \
        --route-key "$route_key" \
        --target "integrations/${integration_id}" \
        --region "$REGION" >/dev/null
    fi
  done

  local stage_id stage_name
  stage_name='$default'
  stage_id="$(aws_text apigatewayv2 get-stages --api-id "$api_id" --region "$REGION" --query "Items[?StageName=='${stage_name}'].StageName | [0]")"
  if [[ -z "$stage_id" || "$stage_id" == "None" ]]; then
    echo "Creating default auto-deploy stage"
    aws apigatewayv2 create-stage \
      --api-id "$api_id" \
      --stage-name '$default' \
      --auto-deploy \
      --region "$REGION" >/dev/null
  fi

  local account_id source_arn
  account_id="$(aws sts get-caller-identity --query Account --output text)"
  source_arn="arn:aws:execute-api:${REGION}:${account_id}:${api_id}/*/*/*"
  aws lambda add-permission \
    --function-name "$FUNCTION_NAME" \
    --statement-id "AllowInvokeFrom${api_id}" \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "$source_arn" \
    --region "$REGION" >/dev/null 2>&1 || true

  echo "https://${api_id}.execute-api.${REGION}.amazonaws.com"
}

need aws
need zip
need python3

echo "Region: $REGION"
aws sts get-caller-identity --query "{Account:Account,Arn:Arn}" --output table

aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$REGION" >/dev/null
ensure_bucket_name
ensure_role
package_lambda
LAMBDA_ARN="$(ensure_lambda | tail -n 1)"
API_URL="$(ensure_http_api "$LAMBDA_ARN" | tail -n 1)"

cat <<EOF

Deployment completed.

API URL:
${API_URL}

Quick test:
curl -X POST "${API_URL}/query/tags" \\
  -H "Content-Type: application/json" \\
  -d '{"cattle": 3}'

If Cognito authorizer was enabled, add:
  -H "Authorization: Bearer <id-token-or-access-token>"

EOF
