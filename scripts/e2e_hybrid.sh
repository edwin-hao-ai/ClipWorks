#!/usr/bin/env bash
set -euo pipefail

# scripts/e2e_hybrid.sh
# 验证 hybrid 渲染链路：创建项目 -> 触发 hybrid 渲染 -> 校验 scene 片段与最终 MP4。

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR/backend"

source .venv/bin/activate 2>/dev/null || true

API="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"
COOKIE_JAR="/tmp/clipworks_e2e_hybrid_cookies.txt"
STATUS_FILE="/tmp/clipworks_e2e_hybrid_status.json"
rm -f "$COOKIE_JAR" "$STATUS_FILE"

echo "==> E2E Hybrid render test against $API"

# 1) 确保用户存在（mock auth）
curl -s -c "$COOKIE_JAR" -b "$COOKIE_JAR" -X POST "$API/auth/mock-login?provider=google" >/dev/null

# 2) 创建项目
PROJECT_JSON=$(curl -s -b "$COOKIE_JAR" -X POST "$API/projects/" \
  -H "Content-Type: application/json" \
  -d '{"title":"Hybrid E2E","source_url":"https://example.com","target_format":"16:9","target_duration":10}')
PROJECT_ID=$(echo "$PROJECT_JSON" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Project: $PROJECT_ID"

# 3) 触发 hybrid 渲染
JOB_JSON=$(curl -s -b "$COOKIE_JAR" -X POST "$API/projects/$PROJECT_ID/renders/agent-generate" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"一句话介绍 ClipWorks","engine":"hybrid"}')
JOB_ID=$(echo "$JOB_JSON" | python -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
echo "Job: $JOB_ID"

# 4) 轮询等待完成（最多 10 分钟）
for i in $(seq 1 120); do
  STATUS_JSON=$(curl -s -b "$COOKIE_JAR" "$API/projects/$PROJECT_ID/renders/$JOB_ID")
  STATUS=$(echo "$STATUS_JSON" | python -c "import sys,json; print(json.load(sys.stdin)['status'])")
  echo "  [$i] status=$STATUS"
  if [ "$STATUS" = "completed" ]; then
    echo "$STATUS_JSON" > "$STATUS_FILE"
    break
  elif [ "$STATUS" = "failed" ]; then
    echo "FAILED"
    echo "$STATUS_JSON"
    exit 1
  fi
  sleep 5
done

if [ ! -f "$STATUS_FILE" ]; then
  echo "FAIL: job did not complete within timeout"
  exit 1
fi

# 5) 校验最终输出信息
STATUS=$(cat "$STATUS_FILE")
OUTPUT_URL=$(echo "$STATUS" | python -c "import sys,json; print(json.load(sys.stdin).get('output_url',''))")
echo "Output URL: $OUTPUT_URL"

if echo "$OUTPUT_URL" | grep -q "sample.mp4"; then
  echo "FAIL: fallback to sample.mp4 detected"
  exit 1
fi

if [ -z "$OUTPUT_URL" ] || [ "$OUTPUT_URL" = "null" ]; then
  echo "FAIL: no output_url"
  exit 1
fi

# 6) 校验最终 MP4 存在且时长合理
OUTPUT_PATH="$ROOT_DIR/data/assets/$PROJECT_ID/output.mp4"
if [ ! -f "$OUTPUT_PATH" ]; then
  echo "Missing output MP4: $OUTPUT_PATH"
  exit 1
fi
DURATION=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUTPUT_PATH")
echo "Output duration: $DURATION"
if (( $(echo "$DURATION < 1" | bc -l) )); then
  echo "Output too short"
  exit 1
fi

# 7) 校验 scene 片段存在
SCENE_COUNT=$(find "$ROOT_DIR/data/assets/$PROJECT_ID" -name 'scene_*.mp4' | wc -l | tr -d ' ')
echo "Scene clips: $SCENE_COUNT"
if [ "$SCENE_COUNT" -lt 1 ]; then
  echo "No scene clips found"
  exit 1
fi

echo "==> Hybrid E2E PASSED"
