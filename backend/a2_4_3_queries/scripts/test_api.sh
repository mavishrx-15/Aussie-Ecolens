#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-${BASE_URL:-}}"
TOKEN="${TOKEN:-}"

if [[ -z "$BASE_URL" ]]; then
  echo "Usage: BASE_URL=https://... bash scripts/test_api.sh"
  echo "   or: bash scripts/test_api.sh https://..."
  exit 1
fi

BASE_URL="${BASE_URL%/}"

AUTH_ARGS=()
if [[ -n "$TOKEN" ]]; then
  AUTH_ARGS=(-H "Authorization: Bearer ${TOKEN}")
fi

post_json() {
  local path="$1"
  local body="$2"
  echo
  echo "### POST ${path}"
  curl -sS -X POST "${BASE_URL}${path}" \
    -H "Content-Type: application/json" \
    "${AUTH_ARGS[@]}" \
    -d "$body"
  echo
}

post_json "/query/tags" '{"cattle": 3}'
post_json "/query/tags" '{"cattle": 4}'
post_json "/query/species" '{"species": ["dingo"]}'
post_json "/query/species" '{"species": ["australian brushturkey"]}'
post_json "/query/file-tags" '{"detected_tags": ["cattle"]}'

cat <<'EOF'

Manual checks for the remaining endpoints:

1. Thumbnail to full image:
curl -X POST "$BASE_URL/query/thumbnail" \
  -H "Content-Type: application/json" \
  -d '{"thumbnail_url":"https://<bucket>.s3.amazonaws.com/thumbnails/<file>_thumb.jpg"}'

2. Bulk add/remove tag:
curl -X POST "$BASE_URL/tags/bulk" \
  -H "Content-Type: application/json" \
  -d '{"urls":["https://<bucket>.s3.amazonaws.com/raw/<file>.JPG"],"tags":["demo"],"operation":1}'

curl -X POST "$BASE_URL/tags/bulk" \
  -H "Content-Type: application/json" \
  -d '{"urls":["https://<bucket>.s3.amazonaws.com/raw/<file>.JPG"],"tags":["demo"],"operation":0}'

3. Delete files is destructive, only run it on a test upload:
curl -X DELETE "$BASE_URL/files" \
  -H "Content-Type: application/json" \
  -d '{"urls":["https://<bucket>.s3.amazonaws.com/raw/<test-file>.JPG"]}'
EOF
