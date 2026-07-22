#!/bin/bash
set -e

API="http://localhost:8000"
COOKIE_JAR="/tmp/clipworks_e2e_cookies.txt"
STATUS_FILE="/tmp/clipworks_e2e_status.json"
rm -f "$COOKIE_JAR" "$STATUS_FILE"

echo "=== 1. Login ==="
curl -s -c "$COOKIE_JAR" -b "$COOKIE_JAR" -X POST "$API/auth/mock-login?provider=google" | jq .

echo "=== 2. Create project ==="
PROJECT=$(curl -s -c "$COOKIE_JAR" -b "$COOKIE_JAR" -X POST "$API/projects/" \
  -H "Content-Type: application/json" \
  -d '{"title": "E2E HyperFrames Test", "source_url": "https://example.com"}')
echo "$PROJECT" | jq .
PROJECT_ID=$(echo "$PROJECT" | jq -r '.id')

echo "=== 3. Trigger agent-generate (default engine is hyperframes) ==="
JOB=$(curl -s -c "$COOKIE_JAR" -b "$COOKIE_JAR" -X POST "$API/projects/$PROJECT_ID/renders/agent-generate" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"make a 2 second demo clip"}')
echo "$JOB" | jq .
JOB_ID=$(echo "$JOB" | jq -r '.job_id')

echo "=== 4. Poll job status ==="
STATUS=""
for i in {1..240}; do
  STATUS=$(curl -s -c "$COOKIE_JAR" -b "$COOKIE_JAR" "$API/projects/$PROJECT_ID/renders/$JOB_ID")
  echo "[$i] $(echo "$STATUS" | jq -c .)"
  JOB_STATUS=$(echo "$STATUS" | jq -r '.status')
  if [ "$JOB_STATUS" = "completed" ] || [ "$JOB_STATUS" = "failed" ]; then
    echo "$STATUS" > "$STATUS_FILE"
    break
  fi
  sleep 5
done

if [ ! -f "$STATUS_FILE" ]; then
  echo "FAIL: job did not complete within timeout"
  exit 1
fi

echo "=== 5. Verify output ==="
STATUS=$(cat "$STATUS_FILE")
OUTPUT_URL=$(echo "$STATUS" | jq -r '.output_url')
echo "Output URL: $OUTPUT_URL"

if echo "$OUTPUT_URL" | grep -q "sample.mp4"; then
  echo "FAIL: fallback to sample.mp4 detected"
  exit 1
fi

if [ -z "$OUTPUT_URL" ] || [ "$OUTPUT_URL" = "null" ]; then
  echo "FAIL: no output_url"
  exit 1
fi

echo "=== 6. Download and check MP4 ==="
FULL_URL="$API$OUTPUT_URL"
curl -s -L "$FULL_URL" -o /tmp/clipworks_e2e_output.mp4
FILE_SIZE=$(stat -f%z /tmp/clipworks_e2e_output.mp4)
echo "Downloaded size: $FILE_SIZE bytes"

if [ "$FILE_SIZE" -lt 1000 ]; then
  echo "FAIL: output too small"
  exit 1
fi

FILE_TYPE=$(file /tmp/clipworks_e2e_output.mp4)
echo "File type: $FILE_TYPE"

if echo "$FILE_TYPE" | grep -qi "mp4\|iso media\|apple quicktime"; then
  echo "PASS: real MP4 generated via HyperFrames e2e"
else
  echo "FAIL: not an MP4"
  exit 1
fi
