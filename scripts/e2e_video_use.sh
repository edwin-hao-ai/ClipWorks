#!/bin/bash
# video-use 引擎真实产品链路 e2e：上传视频 -> agent-generate -> 引擎应为 video-use 且出真实 MP4
set -e

API="http://localhost:8000"
COOKIE_JAR="/tmp/clipworks_vu_cookies.txt"
rm -f "$COOKIE_JAR"

echo "=== 0. 生成测试视频（renderer 容器内 ffmpeg，落到共享卷）==="
mkdir -p data/assets/tmp_vu_e2e
docker compose exec -T renderer ffmpeg -y \
  -f lavfi -i testsrc2=duration=6:size=640x360:rate=30 \
  -f lavfi -i sine=frequency=440:duration=6 \
  -c:v libx264 -pix_fmt yuv420p -c:a aac \
  /app/data/assets/tmp_vu_e2e/clip.mp4 >/dev/null 2>&1
ls -la data/assets/tmp_vu_e2e/clip.mp4

echo "=== 1. Login ==="
curl -s -c "$COOKIE_JAR" -b "$COOKIE_JAR" -X POST "$API/auth/mock-login?provider=google" | jq -r '.email'

echo "=== 2. Create project (upload 来源) ==="
PROJECT=$(curl -s -c "$COOKIE_JAR" -b "$COOKIE_JAR" -X POST "$API/projects/" \
  -H "Content-Type: application/json" \
  -d '{"title": "video-use e2e", "source_type": "upload"}')
PROJECT_ID=$(echo "$PROJECT" | jq -r '.id')
echo "project: $PROJECT_ID"

echo "=== 3. Upload video asset ==="
curl -s -c "$COOKIE_JAR" -b "$COOKIE_JAR" -X POST "$API/projects/$PROJECT_ID/assets/" \
  -F "file=@data/assets/tmp_vu_e2e/clip.mp4" | jq -r '{id, type, source, local_path}'

echo "=== 4. agent-generate（不指定引擎，应由 engine_selector 选 video-use）==="
JOB=$(curl -s -c "$COOKIE_JAR" -b "$COOKIE_JAR" -X POST "$API/projects/$PROJECT_ID/renders/agent-generate" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"把我上传的素材剪成一个短片"}')
JOB_ID=$(echo "$JOB" | jq -r '.job_id')
echo "job: $JOB_ID"

echo "=== 5. Poll ==="
FINAL=""
for i in $(seq 1 120); do
  RESP=$(curl -s -c "$COOKIE_JAR" -b "$COOKIE_JAR" "$API/projects/$PROJECT_ID/renders/$JOB_ID")
  ST=$(echo "$RESP" | jq -r '.status')
  PROG=$(echo "$RESP" | jq -r '.progress')
  echo "[$i] status=$ST progress=$PROG"
  if [ "$ST" = "completed" ] || [ "$ST" = "failed" ]; then
    FINAL="$RESP"
    break
  fi
  sleep 5
done

echo "=== 6. Verify ==="
echo "$FINAL" | jq -r '.logs[].message' | grep -E '引擎|音轨|清点|质量' || true
OUT_URL=$(echo "$FINAL" | jq -r '.output_url')
PLACEHOLDER=$(echo "$FINAL" | jq -r '.is_placeholder')
echo "output_url: $OUT_URL  is_placeholder: $PLACEHOLDER"

if docker compose logs worker --tail 200 2>/dev/null | grep -q 'render/video-use "HTTP/1.1 200'; then
  echo "PASS: worker 日志确认 /render/video-use 调用成功"
else
  echo "FAIL: worker 日志未见 video-use 调用"
  exit 1
fi
if [ "$OUT_URL" != "null" ] && [ "$PLACEHOLDER" = "false" ]; then
  curl -s -o /tmp/vu_e2e_out.mp4 "http://localhost:8000$OUT_URL"
  ls -la /tmp/vu_e2e_out.mp4
  file /tmp/vu_e2e_out.mp4
  echo "PASS: video-use 产出真实 MP4"
else
  echo "FAIL: 没有真实输出"
  exit 1
fi
echo "PROJECT_ID=$PROJECT_ID"
