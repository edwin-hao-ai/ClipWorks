# P0：真实出片 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用户输入一句话，系统在 5 分钟内真实输出一个可下载的 MP4 视频。

**Architecture:** 以 Remotion 为主渲染引擎，通过 Celery + Redis 实现异步渲染队列；后端负责任务调度与状态持久化，渲染服务在独立 Docker 容器中执行真实出片；前端通过轮询或 SSE 获取进度，并用 HTML5 `<video>` 展示成片。

**Tech Stack:** FastAPI, Celery, Redis, Remotion, React/Next.js, PostgreSQL, Docker Compose

## Global Constraints

- 保持现有 FastAPI + SQLAlchemy + PostgreSQL 后端结构
- 保持现有 Next.js 14 + Tailwind 前端结构
- 保持现有 Docker Compose 部署方式
- 所有新增代码必须带测试
- 不引入新的付费云服务（先本地/容器内跑通）
- 不破坏现有 HTML 预览能力（新增真实视频预览并行）

---

## Task 1: 安装 Celery 与配置异步队列

**Files:**
- Create: `backend/app/celery_app.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/config.py`
- Modify: `docker-compose.yml`
- Test: `backend/tests/test_celery.py`

**Interfaces:**
- Consumes: `REDIS_URL` from environment
- Produces: `celery_app` instance imported by render task worker

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_celery.py
from app.celery_app import celery_app


def test_celery_app_loads():
    assert celery_app is not None
    assert celery_app.conf.broker_url is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/edwinhao/ClipWorks/backend
.venv/bin/python -m pytest tests/test_celery.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.celery_app'`

- [ ] **Step 3: Add Celery dependency**

```toml
# backend/pyproject.toml under [project.dependencies]
celery[redis]>=5.3.0
redis>=5.0.0
```

- [ ] **Step 4: Create Celery app**

```python
# backend/app/celery_app.py
import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "clipworks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks.render_task"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    worker_prefetch_multiplier=1,
)
```

- [ ] **Step 5: Update config to expose REDIS_URL**

```python
# backend/app/config.py
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://clipworks:clipworks@localhost:5432/clipworks")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RENDERER_URL = os.getenv("RENDERER_URL", "http://localhost:8001")
ASSETS_DIR = os.path.abspath(os.getenv("ASSETS_DIR", "/app/data/assets"))
```

- [ ] **Step 6: Update docker-compose to run Celery worker**

```yaml
# docker-compose.yml add service:
  worker:
    build: ./backend
    env_file:
      - ./backend/.env
    environment:
      DATABASE_URL: postgresql+psycopg2://clipworks:clipworks@postgres:5432/clipworks
      REDIS_URL: redis://redis:6379/0
      RENDERER_URL: http://renderer:8000
    volumes:
      - ./backend:/app
      - ./data/assets:/app/data/assets
    depends_on:
      - postgres
      - redis
      - renderer
    command: celery -A app.celery_app worker --loglevel=info --concurrency=1
```

- [ ] **Step 7: Run test to verify it passes**

```bash
cd /Users/edwinhao/ClipWorks/backend
.venv/bin/python -m pytest tests/test_celery.py -v
```

Expected: PASS

- [ ] **Step 8: Commit**

```bash
cd /Users/edwinhao/ClipWorks
git add backend/
git commit -m "feat(queue): add Celery + Redis async task setup"
```

---

## Task 2: 把渲染任务迁移到 Celery

**Files:**
- Create: `backend/app/tasks/__init__.py`
- Create: `backend/app/tasks/render_task.py`
- Modify: `backend/app/routers/renders.py`
- Test: `backend/tests/test_render_task.py`
- Test: update `backend/tests/test_render_integration.py`

**Interfaces:**
- Consumes: `RenderService().render(job, project, request)` and existing `_render_video_task` logic
- Produces: `render_video_task.delay(job_id, project_id, prompt, engine)` Celery task

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_render_task.py
from unittest.mock import patch, MagicMock
from app.tasks.render_task import render_video_task


def test_render_video_task_is_celery_task():
    assert hasattr(render_video_task, "delay")


@patch("app.tasks.render_task.RenderService")
@patch("app.tasks.render_task.SessionLocal")
def test_render_video_task_updates_job_on_success(mock_session_local, mock_service_cls):
    mock_session = MagicMock()
    mock_session_local.return_value = mock_session
    mock_job = MagicMock()
    mock_project = MagicMock()
    mock_session.query.return_value.filter.return_value.first.side_effect = [mock_job, mock_project]
    mock_service = MagicMock()
    mock_service_cls.return_value = mock_service
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.output_url = "/api/static/test.mp4"
    mock_result.html_output_url = "/api/static/test/index.html"
    mock_result.error_message = None
    mock_service.render.return_value = mock_result

    render_video_task.run("job-1", "proj-1", "prompt", "mock")

    assert mock_job.status == "completed"
    assert mock_job.output_url == "/api/static/test.mp4"
    mock_session.commit.assert_called()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/edwinhao/ClipWorks/backend
.venv/bin/python -m pytest tests/test_render_task.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.tasks.render_task'`

- [ ] **Step 3: Create Celery render task**

```python
# backend/app/tasks/__init__.py

# backend/app/tasks/render_task.py
import logging
from datetime import datetime, timezone
from typing import Optional

from app.agent import generate_html
from app.celery_app import celery_app
from app.config import ASSETS_DIR
from app.database import SessionLocal
from app.models import Project, RenderJob
from app.rendering.provider import RenderRequest
from app.rendering.service import RenderService

logger = logging.getLogger(__name__)


def _maybe_plan_and_persist(project: Project, prompt: Optional[str], db) -> dict:
    from app.agent import plan_video, build_composition
    from app.routers.compositions import build_composition_json
    from app.models import Track, Clip

    comp_json = build_composition_json(project.composition) if project.composition else {"tracks": []}

    tracks = comp_json.get("tracks", [])
    is_default = False
    if not tracks:
        is_default = True
    elif len(tracks) == 2 and {t.get("type") for t in tracks} == {"video", "text"}:
        for t in tracks:
            if t.get("type") == "text":
                for c in t.get("clips", []):
                    if c.get("text_content") == "ClipWorks":
                        is_default = True

    if is_default:
        plan = plan_video(source_url=project.source_url, user_prompt=prompt)
        comp_json = build_composition(plan)
        # persist
        if project.composition is not None:
            for track in project.composition.tracks:
                db.delete(track)
            db.flush()
            for t_data in comp_json.get("tracks", []):
                track = Track(
                    composition_id=project.composition.id,
                    type=t_data["type"],
                    index=t_data["index"],
                    name=t_data.get("name"),
                )
                db.add(track)
                db.flush()
                for c_data in t_data.get("clips", []):
                    clip = Clip(
                        track_id=track.id,
                        asset_id=c_data.get("asset_id"),
                        start_time=c_data.get("start_time", 0),
                        duration=c_data.get("duration", 5),
                        position=c_data.get("position", {}),
                        style=c_data.get("style", {}),
                        text_content=c_data.get("text_content"),
                    )
                    db.add(clip)
            db.commit()
            db.refresh(project)
            comp_json = build_composition_json(project.composition)

    return comp_json


def _build_assets(project: Project, db) -> dict:
    from app.config import ASSETS_DIR
    from app.services.assets import resolve_image_asset, persist_asset
    from app.services.scraper import scrape_url
    import os

    assets = {}
    if not project.source_url:
        return assets

    scraped = scrape_url(project.source_url)
    if scraped.get("images"):
        first_image = scraped["images"][0]
        asset_data = resolve_image_asset(first_image, project.id, db)
        local_path = asset_data.get("local_path")
        if local_path:
            persist_asset(project.id, asset_data, db)
            rel = os.path.relpath(local_path, ASSETS_DIR).replace(os.path.sep, "/")
            assets["background_image"] = f"/api/static/{rel}"
    assets["scraped"] = scraped
    return assets


def _collect_raw_assets(project: Project) -> list[str]:
    paths = []
    for asset in project.assets:
        if asset.type == "video" and asset.local_path:
            paths.append(asset.local_path)
    return paths


def _write_project_html(project_id: str, composition: dict, assets: dict) -> tuple[str, str]:
    import os
    project_dir = os.path.join(ASSETS_DIR, project_id)
    os.makedirs(project_dir, exist_ok=True)
    html_path = os.path.join(project_dir, "index.html")
    html = generate_html(composition, assets)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    rel = os.path.relpath(html_path, ASSETS_DIR).replace(os.path.sep, "/")
    return html_path, f"/api/static/{rel}"


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def render_video_task(self, job_id: str, project_id: str, prompt: Optional[str] = None, engine: Optional[str] = None):
    db = SessionLocal()
    try:
        job = db.query(RenderJob).filter(RenderJob.id == job_id).first()
        project = db.query(Project).filter(Project.id == project_id).first()
        if not job or not project:
            return

        job.status = "running"
        db.commit()

        comp_json = _maybe_plan_and_persist(project, prompt, db)
        assets = _build_assets(project, db)
        raw_assets = _collect_raw_assets(project)

        html_path, html_url = _write_project_html(project_id, comp_json, assets)
        job.html_output_path = html_path
        job.html_output_url = html_url
        db.commit()

        request = RenderRequest(
            engine=engine,
            composition=comp_json,
            assets=assets,
            raw_assets=raw_assets,
            user_prompt=prompt,
            source_url=project.source_url,
        )
        result = RenderService().render(job, project, request)
        if result.success:
            job.status = "completed"
            job.progress = 100
            job.output_url = result.output_url
            if result.html_output_url:
                job.html_output_url = result.html_output_url
            job.completed_at = datetime.now(timezone.utc)
            project.status = "ready"
        else:
            job.status = "failed"
            job.error_message = result.error_message
            project.status = "failed"
        db.commit()
    except Exception as exc:
        logger.exception("Render task failed")
        db.rollback()
        if job:
            job.status = "failed"
            job.error_message = str(exc)
        if project:
            project.status = "failed"
        db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()
```

- [ ] **Step 4: Update renders router to enqueue Celery task**

```python
# backend/app/routers/renders.py
# Remove old async _render_video_task and render_video_task functions
# Import the Celery task
from app.tasks.render_task import render_video_task

# In both /generate and /agent-generate endpoints, replace:
# background_tasks.add_task(render_video_task, ...)
# with:
render_video_task.delay(job.id, project_id, prompt, engine)
```

- [ ] **Step 5: Run tests**

```bash
cd /Users/edwinhao/ClipWorks/backend
.venv/bin/python -m pytest tests/test_render_task.py tests/test_render_integration.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/edwinhao/ClipWorks
git add backend/
git commit -m "feat(queue): migrate render jobs to Celery"
```

---

## Task 3: 稳定 Remotion 真实渲染链路

**Files:**
- Modify: `services/renderer/Dockerfile`
- Modify: `services/renderer/main.py`
- Modify: `services/renderer/remotion/src/compositions/GenericComp.tsx`
- Modify: `services/renderer/remotion/package.json`
- Modify: `backend/app/rendering/providers/remotion.py`
- Test: `services/renderer/tests/test_remotion.py`
- Test: `backend/tests/rendering/test_remotion_provider.py`

**Interfaces:**
- Consumes: `composition.json` from backend
- Produces: real MP4 file at `{ASSETS_DIR}/{project_id}/output.mp4`

- [ ] **Step 1: Verify Remotion render test exists and passes**

```bash
cd /Users/edwinhao/ClipWorks/services/renderer
python3 -m pytest tests/test_remotion.py -v
```

- [ ] **Step 2: Update renderer Dockerfile to ensure Remotion deps**

```dockerfile
# services/renderer/Dockerfile (ensure this line exists after npm install)
COPY services/renderer/remotion ./remotion
RUN cd remotion && npm install
```

- [ ] **Step 3: Update renderer main.py Remotion endpoint to return output_url on success**

Current code already does this. Verify:

```python
return {"success": True, "output_url": _relative_url(req.output_path), "error": None}
```

- [ ] **Step 4: Improve GenericComp to handle missing duration**

```tsx
// services/renderer/remotion/src/compositions/GenericComp.tsx
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";

interface Clip {
  start_time: number;
  duration: number;
  text_content?: string;
  style?: Record<string, any>;
}

interface Track {
  type: string;
  clips: Clip[];
}

export const GenericComp: React.FC<{ composition: { duration?: number; tracks?: Track[] } }> = ({
  composition,
}) => {
  const frame = useCurrentFrame();
  const fps = 30;
  const currentTime = frame / fps;
  const tracks = composition.tracks || [];
  const activeClip = tracks
    .flatMap((t) => t.clips || [])
    .find((c) => currentTime >= c.start_time && currentTime < c.start_time + c.duration);

  return (
    <AbsoluteFill style={{ backgroundColor: "#0f0f1a", justifyContent: "center", alignItems: "center" }}>
      <div style={{ color: "#fff", fontSize: 64, textAlign: "center", padding: 40 }}>
        {activeClip?.text_content || "ClipWorks"}
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 5: Build renderer image and run container**

```bash
cd /Users/edwinhao/ClipWorks
docker-compose up -d --build renderer
```

- [ ] **Step 6: Test real Remotion render via API**

Create a composition JSON and post to renderer:

```bash
mkdir -p /tmp/remotion-test
cat > /tmp/remotion-test/composition.json <<'EOF'
{"composition": {"duration": 3, "tracks": [{"type": "text", "clips": [{"start_time": 0, "duration": 3, "text_content": "Hello Real Video"}]}]}}
EOF

curl -X POST http://localhost:8001/render/remotion \
  -H "Content-Type: application/json" \
  -d "{\"composition_path\":\"/tmp/remotion-test/composition.json\",\"output_path\":\"/tmp/remotion-test/output.mp4\"}"
```

Verify `/tmp/remotion-test/output.mp4` exists and is valid video.

- [ ] **Step 7: Run backend Remotion provider test**

```bash
cd /Users/edwinhao/ClipWorks/backend
.venv/bin/python -m pytest tests/rendering/test_remotion_provider.py -v
```

- [ ] **Step 8: Commit**

```bash
cd /Users/edwinhao/ClipWorks
git add services/renderer/
git commit -m "feat(renderer): stabilize Remotion real MP4 rendering"
```

---

## Task 4: 前端接入真实视频预览与下载

**Files:**
- Create: `frontend/src/components/project/VideoPreview.tsx`
- Modify: `frontend/src/components/project/PreviewPlayer.tsx`
- Modify: `frontend/src/components/project/PropertyPanel.tsx`
- Test: `frontend/src/components/project/VideoPreview.test.tsx`

**Interfaces:**
- Consumes: `output_url` and `html_output_url` from render job
- Produces: `<VideoPreview outputUrl={...} htmlOutputUrl={...} />` component

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/project/VideoPreview.test.tsx
import { render, screen } from "@testing-library/react";
import { VideoPreview } from "./VideoPreview";

describe("VideoPreview", () => {
  it("renders video when output_url is present", () => {
    render(<VideoPreview outputUrl="/api/static/test.mp4" htmlOutputUrl="/api/static/test/index.html" />);
    expect(screen.getByText("成片预览")).toBeInTheDocument();
    const video = document.querySelector("video");
    expect(video).toBeInTheDocument();
    expect(video?.getAttribute("src")).toBe("/api/static/test.mp4");
  });

  it("falls back to html preview when no output_url", () => {
    render(<VideoPreview outputUrl={null} htmlOutputUrl="/api/static/test/index.html" />);
    expect(screen.getByText("HTML 预览")).toBeInTheDocument();
    const iframe = document.querySelector("iframe");
    expect(iframe).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/edwinhao/ClipWorks/frontend
npm test -- VideoPreview.test.tsx
```

Expected: FAIL

- [ ] **Step 3: Implement VideoPreview component**

```tsx
// frontend/src/components/project/VideoPreview.tsx
"use client";

interface VideoPreviewProps {
  outputUrl: string | null;
  htmlOutputUrl: string | null;
}

export function VideoPreview({ outputUrl, htmlOutputUrl }: VideoPreviewProps) {
  if (outputUrl) {
    return (
      <div className="w-full h-full flex flex-col">
        <div className="text-sm text-content-secondary mb-2 px-1">成片预览</div>
        <video
          src={outputUrl}
          controls
          className="w-full rounded-lg bg-black"
          style={{ maxHeight: "calc(100% - 28px)" }}
        />
        <a
          href={outputUrl}
          download
          className="mt-3 inline-flex items-center justify-center px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          下载 MP4
        </a>
      </div>
    );
  }

  if (htmlOutputUrl) {
    return (
      <div className="w-full h-full flex flex-col">
        <div className="text-sm text-content-secondary mb-2 px-1">HTML 预览</div>
        <iframe
          src={htmlOutputUrl}
          className="w-full flex-1 rounded-lg bg-black border-0"
          title="HTML preview"
        />
      </div>
    );
  }

  return (
    <div className="w-full h-full flex items-center justify-center text-content-tertiary text-sm">
      暂无预览
    </div>
  );
}
```

- [ ] **Step 4: Integrate into PreviewPlayer**

```tsx
// frontend/src/components/project/PreviewPlayer.tsx
// Replace the iframe-only preview with VideoPreview
import { VideoPreview } from "./VideoPreview";

// In render, use:
<VideoPreview outputUrl={job?.output_url || null} htmlOutputUrl={job?.html_output_url || null} />
```

- [ ] **Step 5: Run tests**

```bash
cd /Users/edwinhao/ClipWorks/frontend
npm test -- VideoPreview.test.tsx
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/edwinhao/ClipWorks
git add frontend/
git commit -m "feat(ui): add real MP4 video preview and download"
```

---

## Task 5: 端到端集成验证

**Files:**
- None (manual / scripted verification)

**Interfaces:**
- End-to-end flow: create project → render → get real MP4

- [ ] **Step 1: Start all services**

```bash
cd /Users/edwinhao/ClipWorks
docker-compose up -d
```

- [ ] **Step 2: Verify Celery worker is running**

```bash
docker-compose logs -f worker
```

Expected: worker connected to redis, waiting for tasks

- [ ] **Step 3: Run e2e script**

```bash
cd /Users/edwinhao/ClipWorks
rm -f /tmp/cookies.txt
curl -s -c /tmp/cookies.txt -b /tmp/cookies.txt -X POST "http://localhost:8000/auth/mock-login?provider=demo" > /dev/null
PROJECT=$(curl -s -c /tmp/cookies.txt -b /tmp/cookies.txt -X POST http://localhost:8000/projects/ -H "Content-Type: application/json" -d '{"title":"P0 E2E","source_url":"","source_type":"url"}')
PROJECT_ID=$(echo $PROJECT | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "PROJECT_ID: $PROJECT_ID"

JOB=$(curl -s -c /tmp/cookies.txt -b /tmp/cookies.txt -X POST "http://localhost:8000/projects/$PROJECT_ID/renders/agent-generate" -H "Content-Type: application/json" -d '{"prompt":"make a 3s intro","engine":"remotion"}')
JOB_ID=$(echo $JOB | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
echo "JOB_ID: $JOB_ID"

for i in $(seq 1 30); do
  STATUS=$(curl -s -c /tmp/cookies.txt -b /tmp/cookies.txt "http://localhost:8000/projects/$PROJECT_ID/renders/$JOB_ID")
  echo "Poll $i: $STATUS"
  echo "$STATUS" | grep -q '"status":"completed"' && break
  echo "$STATUS" | grep -q '"status":"failed"' && exit 1
  sleep 5
done

OUTPUT_URL=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin)['output_url'])")
echo "OUTPUT_URL: $OUTPUT_URL"
curl -s -o /dev/null -w "MP4 HTTP: %{http_code}  Size: %{size_download}\n" "http://localhost:8000$OUTPUT_URL"
```

Expected:
- Job completes within 2-3 minutes
- OUTPUT_URL points to `/api/static/{project_id}/output.mp4`
- MP4 HTTP 200 and size > 0

- [ ] **Step 4: Verify frontend displays video**

Open `http://localhost:3000/projects/{PROJECT_ID}` and confirm:
- 渲染完成后预览区显示 `<video>` 标签
- 点击下载可拿到真实 MP4

- [ ] **Step 5: Commit verification notes**

```bash
cd /Users/edwinhao/ClipWorks
git add docs/superpowers/plans/2026-07-05-p0-real-video-output.md
git commit -m "docs(plan): mark P0 e2e verification complete"
```

---

## Self-Review

**Spec coverage:**
- ✅ 真实 MP4 输出：Task 3（Remotion）+ Task 2（Celery 队列）
- ✅ 异步任务：Task 1 + Task 2
- ✅ 进度/状态：Task 2 保持 job 状态更新，前端轮询已有
- ✅ 视频预览：Task 4
- ✅ 失败重试：Task 2 中 `max_retries=2`

**Placeholder scan:**
- 无 TBD/TODO
- 所有代码块完整
- 所有命令具体

**Type consistency：**
- `render_video_task` 签名保持一致：`(job_id, project_id, prompt, engine)`
- `RenderRequest` 字段沿用现有定义

**已知风险：**
- Remotion Docker 镜像构建耗时较长，需提前执行
- 若 Remotion 在容器内失败，先回退到 HyperFrames 或 mock 验证队列链路
