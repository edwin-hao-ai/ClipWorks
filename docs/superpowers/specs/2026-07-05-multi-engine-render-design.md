# ClipWorks 多引擎真实 MP4 渲染设计

> 目标：在保留现有后端/前端流程的前提下，抽象统一的 `RenderProvider` 接口，同时接入 HyperFrames、Remotion、video-use 三个渲染引擎，由 Agent 根据输入场景调度使用。

---

## 1. 背景与现状

当前后端 `backend/app/routers/renders.py` 已经实现了：

- `/projects/{id}/renders/agent-generate`：Agent 驱动的生成入口。
- `_agent_render()`：plan → composition → HTML → HyperFrames CLI 的流水线。
- `_run_hyperframes_render()`：调用 `npx hyperframes render <html> <mp4>`。
- `_mock_render()`：当 HyperFrames 不可用时回退到 sample MP4。

问题：

1. `backend/Dockerfile` 只基于 `python:3.11-slim`，没有 Node.js / FFmpeg，导致容器内 HyperFrames CLI 不可用。
2. 代码里只有 HyperFrames 一条路径，没有 Remotion / video-use 的接入点。
3. 引擎选择、降级、错误处理都耦合在 `renders.py` 里，扩展困难。

---

## 2. 总体架构

```text
┌─────────────────────────────────────────────────────────────┐
│                        ClipWorks Backend                     │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ RenderRouter │  │ RenderProvider   │  │ EngineSelector│ │
│  │  /renders/*  │──│  (abstract)      │──│  (Agent rule) │ │
│  └──────────────┘  └──────────────────┘  └──────────────┘  │
│           │                    │                            │
│           │        ┌───────────┼───────────┐                │
│           │        ▼           ▼           ▼                │
│           │   HyperFrames  Remotion    VideoUse             │
│           │    Provider    Provider    Provider             │
│           │        │           │           │                │
│           └────────┴───────────┴───────────┘                │
│                              │                              │
└──────────────────────────────┼──────────────────────────────┘
                               │ HTTP
┌──────────────────────────────▼──────────────────────────────┐
│                      renderer service                        │
│  FastAPI/Node.js mixed service with:                         │
│  - Node.js 22 + FFmpeg + Playwright                          │
│  - /render/hyperframes                                       │
│  - /render/remotion                                          │
│  - /render/video-use                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. RenderProvider 抽象

新增 `backend/app/rendering/provider.py`：

```python
from typing import Protocol
from dataclasses import dataclass
from app.models import Project, RenderJob

@dataclass
class RenderRequest:
    engine: str | None          # "hyperframes", "remotion", "video-use"
    user_prompt: str | None
    source_url: str | None
    composition: dict
    assets: dict
    raw_assets: list[str] | None  # local paths for video-use

@dataclass
class RenderResult:
    success: bool
    output_url: str | None
    html_output_url: str | None
    error_message: str | None

class RenderProvider(Protocol):
    name: str

    def can_handle(self, request: RenderRequest) -> bool: ...
    async def render(self, job: RenderJob, project: Project, request: RenderRequest) -> RenderResult: ...
```

所有 provider 实现该协议。后端 `RenderService` 按以下顺序选择 provider：

1. 若 `request.engine` 显式指定，则匹配对应 provider。
2. 否则调用 `EngineSelector.select(request)` 得到默认引擎。
3. 按 `selected_provider → 其他能处理的 provider → mock` 的顺序尝试，直到成功或全部失败。

---

## 4. 三个 Provider

### 4.1 HyperFramesProvider

- **职责**：把 composition/ assets 转成 HTML，然后调用 renderer 的 `/render/hyperframes` 得到 MP4。
- **输入**：`composition` dict、`assets` dict（含 `background_image` 等）。
- **实现**：复用 `generate_html()` 生成 HTML，写入项目目录，向 renderer 发送 HTML 路径和目标 MP4 路径。
- **Renderer 端点**：`POST /render/hyperframes`
  - Body: `{ "html_path": "/app/data/assets/{project_id}/index.html", "output_path": ".../output.mp4", "duration": 20, "fps": 30 }`
  - 运行 `npx hyperframes render <html_path> <output_path>`，返回 `{output_url, html_output_url}`。

### 4.2 RemotionProvider

- **职责**：用 Remotion 将 composition 渲染成 MP4。适合模板化、批量、精确动画场景。
- **输入**：`composition` dict。
- **实现**：
  - renderer 服务内置一个最小 Remotion 项目（`services/renderer/remotion/`），包含一个通用 `Composition` 组件，接收 `composition` props。
  - backend 把 composition JSON 写入项目目录的 `composition.json`。
  - 调用 renderer `/render/remotion`，传入 `composition_path` 和 `output_path`。
  - renderer 运行 `npx remotion render MyComp out.mp4 --props=composition.json`。
- **Renderer 端点**：`POST /render/remotion`
  - Body: `{ "composition_path": "...", "output_path": "..." }`
  - 返回 `{output_url}`。

### 4.3 VideoUseProvider

- **职责**：用 browser-use/video-use 对原始视频素材做浏览器自动化剪辑（加字幕、剪片段、调顺序等）。
- **输入**：`raw_assets`（素材本地路径列表）、`user_prompt`（剪辑指令）。
- **实现**：
  - 当用户上传原始素材并说“帮我剪一个 30 秒预告片”时，EngineSelector 选择 video-use。
  - backend 调用 renderer `/render/video-use`，传入素材路径和指令。
  - renderer 用 Python `video-use` / `browser-use` 库编排浏览器/FFmpeg 完成剪辑，输出 MP4。
- **Renderer 端点**：`POST /render/video-use`
  - Body: `{ "asset_paths": [...], "instruction": "...", "output_path": "..." }`
  - 返回 `{output_url}`。

---

## 5. renderer 服务

### 5.1 位置

`services/renderer/`

```text
services/renderer/
├── Dockerfile
├── main.py              # FastAPI app with /render/* endpoints
├── requirements.txt
├── package.json
├── hyperframes/         # HyperFrames render helper
├── remotion/            # Remotion project
│   ├── src/
│   │   ├── index.tsx
│   │   └── compositions/
│   │       └── GenericComp.tsx
│   └── remotion.config.ts
└── video_use/           # video-use helper script
    └── edit_video.py
```

### 5.2 Dockerfile 要点

```dockerfile
FROM node:22-bookworm
RUN apt-get update && apt-get install -y ffmpeg python3 python3-pip
# Install Playwright dependencies for video-use / browser-use
RUN pip3 install --no-cache-dir browser-use playwright
RUN python3 -m playwright install chromium
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 5.3 端点

- `GET /health`：返回各引擎可用性（node、ffmpeg、hyperframes、remotion、playwright）。
- `POST /render/hyperframes`：HTML → MP4。
- `POST /render/remotion`：composition JSON → MP4。
- `POST /render/video-use`：raw assets + instruction → MP4。

所有端点都把输出写到 `/app/data/assets/{project_id}/`，并通过共享卷让 backend 暴露为 `/api/static/`。

---

## 6. Agent 调度规则

新增 `backend/app/rendering/engine_selector.py`：

```python
def select(request: RenderRequest) -> str:
    if request.raw_assets:
        return "video-use"
    if request.user_prompt and any(k in request.user_prompt for k in ["模板", "批量", "react", "remotion"]):
        return "remotion"
    return "hyperframes"
```

规则可随需求扩展。Agent `/agent/chat` 也可以返回 `{"engine": "..."}` 显式指定引擎。

---

## 7. Docker Compose 改动

```yaml
services:
  renderer:
    build: ./services/renderer
    volumes:
      - ./data/assets:/app/data/assets
    environment:
      - ASSETS_DIR=/app/data/assets
    ports:
      - "8001:8000"

  backend:
    environment:
      - RENDERER_URL=http://renderer:8000
    depends_on:
      - renderer
```

backend 通过 `RENDERER_URL` 访问 renderer。

---

## 8. 数据流

1. 用户在工作台点击“开始生成视频”。
2. `RenderRouter` 创建 `RenderJob`，状态 `queued`。
3. `RenderService` 组装 `RenderRequest`。
4. `EngineSelector` 选择默认引擎（或被显式指定）。
5. 按优先级尝试 provider：
   - provider 调用 renderer HTTP 端点。
   - renderer 执行实际渲染，输出到共享卷。
   - provider 返回 `RenderResult`。
6. backend 更新 `RenderJob` 的 `output_url`、`status`、`error_message`。
7. 前端轮询 `/renders/{job_id}`，获取真实 MP4 URL。

---

## 9. 降级与错误处理

- 每个 provider 在 renderer 不可用时返回 `success=False` 并记录原因。
- `RenderService` 捕获异常后继续尝试下一个 provider。
- 若全部失败，回退到 `_mock_render()`，保持 UI 可用，并在 `error_message` 中说明失败原因。
- renderer 服务启动时运行 `/health` 自检，backend 启动时检查 renderer 健康状态并记录日志。

---

## 10. 测试策略

- **backend 单元测试**：mock `httpx`/`requests` 调用 renderer，验证 provider 选择、降级、错误处理。
- **renderer 单元测试**：
  - `/health` 返回各引擎状态。
  - 对每个端点，验证输出文件被创建（可用轻量 HTML/composition 测试，不必全链路渲染真实视频）。
- **集成测试**：在 CI 中构建 renderer 镜像并调用 `/render/hyperframes`，断言返回 `output_url` 且文件存在。
- **后端 `tests/test_agent.py`**：补充 `test_engine_selector_*`。

---

## 11. 边界与限制

- 真实视频渲染依赖 Node.js/FFmpeg/Playwright，首次 Docker 构建可能较慢。
- Remotion 模板先提供一个通用 `GenericComp`，后续可扩展为多个模板。
- video-use 需要原始素材；若无素材则 EngineSelector 不会选择它。
- 当前设计把 renderer 作为独立服务；后续如需水平扩展，可独立部署 renderer 集群。

---

## 12. 交付物

- `backend/app/rendering/`：provider 接口、三个 provider、engine selector、render service。
- `backend/app/routers/renders.py`：改造成使用 `RenderService`。
- `services/renderer/`：独立渲染服务，含 Dockerfile、FastAPI、Remotion 项目、video-use helper。
- `docker-compose.yml`：新增 `renderer` service 和 `RENDERER_URL`。
- 新增/更新的测试文件。
- 本设计文档。
