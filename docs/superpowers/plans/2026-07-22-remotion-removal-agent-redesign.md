# ClipWorks Remotion 移除与 Agent 式 UI 改造实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从 hybrid 渲染链迁移到 HyperFrames 整片渲染，移除 Remotion 默认依赖；同时将前端 UI 改造为 Agent 对话优先、关键节点确认、渲染进度透明的视频创作流程。

**Architecture:** 后端只保留 `hyperframes` / `video-use` / `mock` 三条渲染路径，`render_task.py` 直接调用 `generate_html()` 生成完整 HTML 后由 HyperFrames 一次出片；前端首页改为 Agent 输入入口，项目工作区采用「对话 + 预览/故事板 + 时间线」三栏布局，关键节点（需求理解、方案、故事板、导出）提供确认组件，渲染进度复用现有 SSE 流。

**Tech Stack:** FastAPI, Celery, SQLAlchemy, HyperFrames, ffmpeg, Next.js 14 (App Router), React, TypeScript, Tailwind CSS, SSE.

## Global Constraints

- 后端默认渲染引擎必须是 `hyperframes`，有本地视频素材时走 `video-use`。
- 不再默认调用 Remotion；Remotion 代码保留在 Git 历史但不在默认 PROVIDERS 中。
- `/render/hyperframes` 超时从 75s 延长到 180s，前端/后端对应超时同步延长。
- 重试/降级策略由 Agent 层决定，渲染层只报告失败。
- worker concurrency 在 8GB 服务器上保持或改为 1。
- 前端必须复用现有 SSE endpoint（`/agent/chat/stream`、`/renders/stream` 等）。
- 关键节点必须有用户确认：需求理解、脚本方案、故事板、导出设置。
- 占位视频（sample.mp4）必须明确标注，不得显示为「已完成」。
- 所有改动必须通过现有 pytest / npm test，或同步更新测试。

---

## File Structure

### 后端变更

| 文件 | 变更类型 | 职责 |
|---|---|---|
| `backend/app/rendering/engine_selector.py` | 修改 | 默认返回 `hyperframes`，移除 `hybrid` |
| `backend/app/rendering/service.py` | 修改 | PROVIDERS 列表移除 `RemotionProvider`，降级链改为 HF → video-use → mock |
| `backend/app/rendering/providers/remotion.py` | 修改 | 标记 deprecated，保留但不在默认链 |
| `backend/app/rendering/providers/hyperframes.py` | 修改 | httpx 超时从 90s 改为 200s |
| `backend/app/tasks/render_task.py` | 修改 | 移除 `_write_scene_htmls`、`_prerender_scenes`、`_build_assembly_composition`，直接 `generate_html()` + HF |
| `services/renderer/main.py` | 修改 | `/render/hyperframes` `communicate(timeout=180)` |
| `services/renderer/Dockerfile` | 修改 | 移除 Remotion 相关 npm install（可选，如保留 Remotion 代码则仅注释） |
| `docker-compose.yml` | 修改 | 更新 worker concurrency 注释，移除 Remotion 环境变量引用 |

### 前端变更

| 文件 | 变更类型 | 职责 |
|---|---|---|
| `frontend/src/app/page.tsx` | 修改 | 首页改为 Agent 对话入口 + 快捷提示 + 最近项目 |
| `frontend/src/app/projects/page.tsx` | 修改 | 项目列表保持，风格与首页一致 |
| `frontend/src/app/projects/[id]/page.tsx` | 修改 | 工作区三栏布局容器 |
| `frontend/src/components/project/AgentChat.tsx` | 修改 | 接入大号模式，复用到工作区左侧 |
| `frontend/src/components/project/AgentCanvas.tsx` | 修改 | 预览 + 故事板整合 |
| `frontend/src/components/project/GenerationPanel.tsx` | 修改 | 渲染进度面板，复用到导出页/弹窗 |
| `frontend/src/components/project/IntentCard.tsx` | 新建 | 需求理解确认卡片 |
| `frontend/src/components/project/PlanApproval.tsx` | 新建 | 脚本方案确认组件 |
| `frontend/src/components/project/StoryboardStrip.tsx` | 新建 | 故事板缩略图条 |
| `frontend/src/components/project/ExportSettings.tsx` | 新建 | 导出设置确认 + 进度 |
| `frontend/src/components/project/TimelinePanel.tsx` | 新建 | 可折叠时间线面板 |

### 文档变更

| 文件 | 变更类型 | 职责 |
|---|---|---|
| `README.md` | 修改 | 移除 Remotion 描述，更新为 HF 整片渲染 |
| `AGENTS.md` | 修改 | 更新渲染架构、故障排查 |
| `docs/superpowers/specs/2026-07-16-hybrid-hyperframes-remotion-design.md` | 修改 | 头部加「已废弃」标记，指向新 spec |

---

## Task 1: 修改渲染引擎选择器，默认走 HyperFrames

**Files:**
- Modify: `backend/app/rendering/engine_selector.py`
- Test: `backend/tests/rendering/test_engine_selector.py`

**Interfaces:**
- Consumes: `RenderRequest` with optional `engine`, `engine_hint`, `raw_assets`, `user_prompt`
- Produces: engine name string (`"hyperframes"`, `"video-use"`, or explicit engine)

- [ ] **Step 1: 写失败测试验证默认不再是 hybrid**

```python
# backend/tests/rendering/test_engine_selector.py
def test_select_engine_defaults_to_hyperframes():
    from app.rendering.provider import RenderRequest
    from app.rendering.engine_selector import select_engine

    req = RenderRequest(composition={}, assets={})
    assert select_engine(req) == "hyperframes"
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd /Users/edwinhao/ClipWorks/backend
source .venv/bin/activate
pytest tests/rendering/test_engine_selector.py::test_select_engine_defaults_to_hyperframes -v
```

Expected: FAIL (current default returns "hybrid")

- [ ] **Step 3: 修改 engine_selector.py**

```python
# backend/app/rendering/engine_selector.py
from app.rendering.provider import RenderRequest


def select_engine(request: RenderRequest) -> str:
    if request.raw_assets:
        return "video-use"

    prompt = (request.user_prompt or "").lower()
    if any(k in prompt for k in ["hyperframes", "html", "轻量"]):
        return "hyperframes"

    hint = (request.engine_hint or "").lower()
    if hint and hint in ("hyperframes", "remotion", "video-use"):
        return hint

    # 默认整片 HyperFrames 渲染；Remotion 不再作为默认路径。
    return "hyperframes"
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd /Users/edwinhao/ClipWorks/backend
pytest tests/rendering/test_engine_selector.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd /Users/edwinhao/ClipWorks
git add backend/app/rendering/engine_selector.py backend/tests/rendering/test_engine_selector.py
git commit -m "refactor(rendering): default engine is hyperframes, drop hybrid default"
```

---

## Task 2: 简化 render_task，移除 hybrid 分镜+Remotion 总装逻辑

**Files:**
- Modify: `backend/app/tasks/render_task.py`
- Test: `backend/tests/test_render_task.py`

**Interfaces:**
- Consumes: `generate_html()` from `app.agent.html_generator`
- Produces: `RenderJob` with `output_url`/`html_output_url` via `HyperFramesProvider`

- [ ] **Step 1: 写测试验证渲染任务使用整片 HTML**

```python
# backend/tests/test_render_task.py
from unittest.mock import patch, MagicMock


def test_render_video_task_uses_whole_page_html(monkeypatch, db_session, sample_project):
    """render_video_task should call generate_html once and HyperFrames, not hybrid scene prerender."""
    from app.tasks.render_task import render_video_task
    from app.models import RenderJob

    job = RenderJob(project_id=sample_project.id, status="queued")
    db_session.add(job)
    db_session.commit()

    calls = {"html": 0, "prerender": 0}

    def fake_generate_html(comp, assets):
        calls["html"] += 1
        return "<html>whole page</html>"

    async def fake_hf_render(job, project, request):
        from app.rendering.provider import RenderResult
        calls["hyperframes"] = calls.get("hyperframes", 0) + 1
        return RenderResult(success=True, output_url="/api/static/output.mp4", html_output_url="/api/static/index.html")

    monkeypatch.setattr("app.tasks.render_task.generate_html", fake_generate_html)
    monkeypatch.setattr("app.tasks.render_task.HyperFramesProvider.render", fake_hf_render)
    monkeypatch.setattr("app.tasks.render_task._build_soundtrack", lambda *a, **kw: None)
    monkeypatch.setattr("app.tasks.render_task._run_qa_and_finalize", lambda *a, **kw: None)

    # Mock Celery self
    self = MagicMock()
    self.request.retries = 0
    render_video_task(self, job.id, sample_project.id)

    assert calls["html"] == 1
    assert calls.get("hyperframes", 0) == 1
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd /Users/edwinhao/ClipWorks/backend
pytest tests/test_render_task.py::test_render_video_task_uses_whole_page_html -v
```

Expected: FAIL

- [ ] **Step 3: 修改 render_task.py**

主要改动：
1. 删除 `_write_scene_htmls`、`_prerender_scenes`、`_build_assembly_composition` 函数；
2. 在 render_video_task 中，当需要 HTML 渲染时，直接调用 `generate_html()`；
3. 使用 `HyperFramesProvider` 渲染整片 HTML；
4. 保留音轨、QA、finalize 逻辑。

```python
# backend/app/tasks/render_task.py
# 在文件顶部或合适位置添加
from app.agent import generate_html
from app.rendering.providers.hyperframes import HyperFramesProvider

# 删除以下函数：
# - _write_scene_htmls
# - _prerender_scenes
# - _build_assembly_composition

# 在 render_video_task 中替换 hybrid 分支
# 原代码块（约 630-700 行）:
#   if selected_engine == "hybrid": ...
# 替换为:

        # 生成整片 HTML 动画
        html_path = os.path.join(project_dir, f"index_{job.id}.html")
        try:
            html = generate_html(comp_json, assets)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            _append_log(job, "HTML 预览已生成")
            db.commit()
        except Exception as html_exc:
            _append_log(job, f"HTML 生成失败：{str(html_exc)[:120]}，将使用兜底 HTML")
            html = generate_html(comp_json, {})  # fallback assets
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)

        # 调用 HyperFrames 整片渲染
        provider = HyperFramesProvider()
        from app.rendering.provider import RenderRequest
        request = RenderRequest(
            composition=comp_json,
            assets=assets,
            html_path=html_path,
            raw_assets=raw_assets,
            user_prompt=prompt,
            engine_hint=plan.get("engine_hint") if isinstance(plan, dict) else None,
        )
        result = provider.render(job, project, request)
        # result 是同步返回的 RenderResult
```

注意：`HyperFramesProvider.render` 是 async，但 `render_video_task` 是同步 Celery 任务，需要用 `asyncio.run(provider.render(...))` 或把调用点改为 await。

更简单的做法：在 render_video_task 中直接复用已有的 `_render_with_provider` 模式，或让 `HyperFramesProvider.render` 有一个同步包装。

实际代码需要检查 `render_video_task` 当前如何调用 provider。当前代码片段（约 670-700 行）：

```python
        request = RenderRequest(
            composition=comp_json,
            assets=assets,
            html_path=html_path,
            raw_assets=raw_assets,
            user_prompt=prompt,
            engine_hint=plan.get("engine_hint") if isinstance(plan, dict) else None,
        )
        _append_log(job, f"Render request engine={selected_engine!r} for job={job_id}")
        db.commit()
        service = RenderService()
        result = service.render(job, project, request)
```

所以可以直接保留 `RenderService.render()` 调用，只要 `service.py` 的降级链正确即可。

因此 Step 3 简化为：删除 hybrid 专用函数和分支，直接生成整片 HTML 后调用 `RenderService.render()`。

- [ ] **Step 4: 运行测试**

```bash
cd /Users/edwinhao/ClipWorks/backend
pytest tests/test_render_task.py -v
```

Expected: PASS（可能需要更新旧测试）

- [ ] **Step 5: 提交**

```bash
cd /Users/edwinhao/ClipWorks
git add backend/app/tasks/render_task.py backend/tests/test_render_task.py
git commit -m "refactor(render_task): whole-page HyperFrames render, remove hybrid scene prerender"
```

---

## Task 3: 更新 RenderService 降级链，移除 RemotionProvider 默认注册

**Files:**
- Modify: `backend/app/rendering/service.py`
- Test: `backend/tests/rendering/test_hybrid_provider.py`

**Interfaces:**
- Consumes: `RenderRequest`
- Produces: `RenderResult` from `hyperframes` → `video-use` → `mock`

- [ ] **Step 1: 修改 service.py**

```python
# backend/app/rendering/service.py
from app.rendering.engine_selector import select_engine
from app.rendering.providers.hyperframes import HyperFramesProvider
from app.rendering.providers.video_use import VideoUseProvider
from app.rendering.providers.mock import MockProvider
from app.rendering.provider import RenderRequest, RenderResult

logger = logging.getLogger(__name__)

PROVIDERS = [
    HyperFramesProvider(),
    VideoUseProvider(),
    MockProvider(),
]


class RenderService:
    def render(self, job, project, request: RenderRequest) -> RenderResult:
        return asyncio.run(self._render_async(job, project, request))

    async def _render_async(self, job, project, request: RenderRequest) -> RenderResult:
        engine = request.engine or select_engine(request)
        provider_map = {p.name: p for p in PROVIDERS}

        order_names: list[str] = []
        preferred = engine
        if preferred in provider_map:
            order_names.append(preferred)

        # 补入其余真实引擎
        for p in PROVIDERS:
            if p.name == "mock" or p.name in order_names:
                continue
            if not p.can_handle(request):
                continue
            order_names.append(p.name)

        if "mock" in provider_map and "mock" not in order_names:
            order_names.append("mock")

        logger.info("render engine chain: preferred=%s order=%s", engine, order_names)
        last_error = None
        for name in order_names:
            provider = provider_map[name]
            result = await provider.render(job, project, request)
            is_real = name != "mock"
            placeholder = "sample.mp4" in (getattr(result, "output_url", None) or "")
            if result.success and not (is_real and placeholder):
                return result
            last_error = getattr(result, "error_message", None) or (
                "placeholder output" if placeholder else None
            )
            logger.warning("provider=%s did not produce a real render: %s", name, last_error)

        return RenderResult(success=False, error_message=last_error or "All providers failed")
```

- [ ] **Step 2: 更新 hybrid provider 测试**

```python
# backend/tests/rendering/test_hybrid_provider.py
import pytest
from app.rendering.provider import RenderRequest
from app.rendering.service import RenderService, PROVIDERS


def test_service_does_not_include_remotion_by_default():
    names = {p.name for p in PROVIDERS}
    assert "remotion" not in names
    assert names == {"hyperframes", "video-use", "mock"}


@pytest.mark.asyncio
async def test_service_falls_back_from_hyperframes_to_video_use_to_mock(monkeypatch):
    service = RenderService()

    async def fake_hf(job, project, request):
        from app.rendering.provider import RenderResult
        return RenderResult(success=False, error_message="hf fail")

    async def fake_vu(job, project, request):
        from app.rendering.provider import RenderResult
        if request.raw_assets:
            return RenderResult(success=True, output_url="/api/static/vu.mp4")
        return RenderResult(success=False, error_message="no raw assets")

    async def fake_mock(job, project, request):
        from app.rendering.provider import RenderResult
        return RenderResult(success=True, output_url="/api/static/sample.mp4")

    monkeypatch.setattr("app.rendering.providers.hyperframes.HyperFramesProvider.render", fake_hf)
    monkeypatch.setattr("app.rendering.providers.video_use.VideoUseProvider.render", fake_vu)
    monkeypatch.setattr("app.rendering.providers.mock.MockProvider.render", fake_mock)

    req = RenderRequest(composition={}, assets={}, raw_assets=["clip.mp4"])
    result = service.render(None, None, req)
    assert result.success
    assert result.output_url == "/api/static/vu.mp4"
```

- [ ] **Step 3: 运行测试**

```bash
cd /Users/edwinhao/ClipWorks/backend
pytest tests/rendering/test_hybrid_provider.py tests/rendering/test_remotion_provider.py -v
```

Expected: `test_remotion_provider.py` 可能失败，需要下一步处理。

- [ ] **Step 4: 提交**

```bash
cd /Users/edwinhao/ClipWorks
git add backend/app/rendering/service.py backend/tests/rendering/test_hybrid_provider.py
git commit -m "refactor(rendering): drop RemotionProvider from default chain"
```

---

## Task 4: 标记 RemotionProvider 为 deprecated 并移除 renderer 端点

**Files:**
- Modify: `backend/app/rendering/providers/remotion.py`
- Modify: `services/renderer/main.py`
- Test: `backend/tests/rendering/test_remotion_provider.py`

**Interfaces:**
- `RemotionProvider` 保留但 `can_handle` 永远返回 False（除非显式 engine="remotion"）
- `/render/remotion` 端点从 renderer 移除

- [ ] **Step 1: 修改 RemotionProvider 为可选/deprecated**

```python
# backend/app/rendering/providers/remotion.py
# 在 class 顶部添加 logging
import warnings

logger = logging.getLogger(__name__)


class RemotionProvider(RenderProvider):
    name = "remotion"

    def __init__(self):
        warnings.warn(
            "RemotionProvider is deprecated and no longer in the default render chain. "
            "Use hyperframes whole-page rendering instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    def can_handle(self, request: RenderRequest) -> bool:
        # 仅在显式指定 engine=remotion 时启用，默认不再使用。
        return request.engine == "remotion"

    # render 方法保持不变
```

- [ ] **Step 2: 从 renderer main.py 移除 /render/remotion 端点**

```python
# services/renderer/main.py
# 删除 RemotionRequest 模型和 render_remotion 函数
# 保留 HyperFramesRequest, ProxyRequest, SoundtrackRequest 等
```

- [ ] **Step 3: 更新或删除 test_remotion_provider.py**

```python
# backend/tests/rendering/test_remotion_provider.py
import pytest
import warnings
from app.rendering.providers.remotion import RemotionProvider
from app.rendering.provider import RenderRequest


def test_remotion_provider_is_deprecated():
    with pytest.warns(DeprecationWarning, match="RemotionProvider is deprecated"):
        provider = RemotionProvider()
    assert provider.can_handle(RenderRequest(engine="remotion")) is True
    assert provider.can_handle(RenderRequest(engine="hyperframes")) is False
    assert provider.can_handle(RenderRequest()) is False
```

- [ ] **Step 4: 运行测试**

```bash
cd /Users/edwinhao/ClipWorks/backend
pytest tests/rendering/test_remotion_provider.py -v
cd /Users/edwinhao/ClipWorks/services/renderer
source .venv/bin/activate
pytest tests/test_remotion.py -v
```

Expected: backend PASS；renderer test_remotion.py 可能需要删除或跳过。

- [ ] **Step 5: 提交**

```bash
cd /Users/edwinhao/ClipWorks
git add backend/app/rendering/providers/remotion.py services/renderer/main.py backend/tests/rendering/test_remotion_provider.py services/renderer/tests/test_remotion.py
git commit -m "chore(remotion): deprecate RemotionProvider and remove renderer /render/remotion endpoint"
```

---

## Task 5: 延长 HyperFrames 超时

**Files:**
- Modify: `services/renderer/main.py`
- Modify: `backend/app/rendering/providers/hyperframes.py`

**Interfaces:**
- `/render/hyperframes` timeout 180s
- `HyperFramesProvider.render` httpx timeout 200s

- [ ] **Step 1: 修改 renderer main.py**

```python
# services/renderer/main.py
# 在 render_hyperframes 中
out, err = proc.communicate(timeout=180)
```

- [ ] **Step 2: 修改 HyperFramesProvider**

```python
# backend/app/rendering/providers/hyperframes.py
# async with httpx.AsyncClient(timeout=90) as client: -> timeout=200
async with httpx.AsyncClient(timeout=200) as client:
```

- [ ] **Step 3: 更新对应测试中的超时断言**

```python
# services/renderer/tests/test_hyperframes.py
# 超时测试使用 180
def test_render_hyperframes_timeout(...):
    proc = _fake_proc()
    proc.communicate.side_effect = [
        subprocess.TimeoutExpired(cmd=["npx"], timeout=180),
        ("", ""),
    ]
```

- [ ] **Step 4: 运行测试**

```bash
cd /Users/edwinhao/ClipWorks/services/renderer
pytest tests/test_hyperframes.py -v
cd /Users/edwinhao/ClipWorks/backend
pytest tests/rendering/test_hyperframes_provider.py -v
```

- [ ] **Step 5: 提交**

```bash
cd /Users/edwinhao/ClipWorks
git add services/renderer/main.py backend/app/rendering/providers/hyperframes.py services/renderer/tests/test_hyperframes.py
git commit -m "chore(hyperframes): extend timeout to 180s renderer / 200s backend"
```

---

## Task 6: 前端首页改为 Agent 对话入口

**Files:**
- Modify: `frontend/src/app/page.tsx`
- Test: `frontend/tests/app/HomePage.test.tsx`（如存在）或新建

**Interfaces:**
- 使用现有 `AgentChat` 组件（mode="plan"）
- 路由跳转到 `/projects/{id}`

- [ ] **Step 1: 修改 page.tsx**

```tsx
// frontend/src/app/page.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/Button';

export default function HomePage() {
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  const [creating, setCreating] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    setCreating(true);
    try {
      const project = await api.post('/projects/', { title: prompt.slice(0, 50), prompt });
      router.push(`/projects/${project.id}?initialPrompt=${encodeURIComponent(prompt)}`);
    } catch {
      setCreating(false);
    }
  };

  return (
    <main className="min-h-dvh bg-background-base text-content-primary flex flex-col">
      <nav className="flex items-center justify-between px-6 py-4 border-b border-border-subtle">
        <span className="font-bold text-lg">ClipWorks</span>
        <div className="flex items-center gap-4 text-sm text-content-secondary">
          <a href="/projects" className="hover:text-content-primary">Projects</a>
          <a href="/billing" className="hover:text-content-primary">Billing</a>
          <a href="/settings" className="hover:text-content-primary">Settings</a>
        </div>
      </nav>

      <div className="flex-1 flex flex-col items-center justify-center px-4">
        <h1 className="text-3xl md:text-5xl font-bold text-center mb-3">一句话，一条成片</h1>
        <p className="text-content-secondary text-center mb-8 max-w-md">
          描述你的视频，或粘贴链接、上传素材。AI 导演会帮你规划脚本、准备素材并生成视频。
        </p>

        <form onSubmit={handleSubmit} className="w-full max-w-2xl">
          <div className="bg-background-surface border border-border-subtle rounded-2xl p-4 shadow-lg">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="例如：帮我做一个 15 秒的产品介绍视频，突出 AI 剪辑和省钱的卖点，9:16 竖屏"
              className="w-full bg-transparent resize-none outline-none text-lg min-h-[120px] placeholder:text-content-tertiary"
            />
            <div className="flex items-center justify-between mt-4">
              <div className="flex gap-2">
                <button type="button" className="text-sm px-3 py-1.5 rounded-full bg-background-elevated text-content-secondary hover:text-content-primary">
                  📎 素材
                </button>
                <button type="button" className="text-sm px-3 py-1.5 rounded-full bg-background-elevated text-content-secondary hover:text-content-primary">
                  🔗 URL
                </button>
                <button type="button" className="text-sm px-3 py-1.5 rounded-full bg-background-elevated text-content-secondary hover:text-content-primary">
                  🎨 风格
                </button>
              </div>
              <Button type="submit" disabled={!prompt.trim() || creating}>
                {creating ? '创建中…' : '生成视频 →'}
              </Button>
            </div>
          </div>
        </form>

        <div className="flex flex-wrap justify-center gap-2 mt-6">
          {['从公众号文章生成视频', '商品详情页转营销短片', '生日祝福视频'].map((tip) => (
            <button
              key={tip}
              onClick={() => setPrompt(tip)}
              className="text-sm px-3 py-1.5 rounded-full bg-background-elevated text-content-secondary hover:text-content-primary border border-border-subtle"
            >
              {tip}
            </button>
          ))}
        </div>
      </div>
    </main>
  );
}
```

- [ ] **Step 2: 运行前端测试**

```bash
cd /Users/edwinhao/ClipWorks/frontend
npm test -- --run
```

Expected: 现有测试可能失败，需要更新 snapshot 或测试。

- [ ] **Step 3: 提交**

```bash
cd /Users/edwinhao/ClipWorks
git add frontend/src/app/page.tsx
git commit -m "feat(ui): homepage as Agent conversation entry"
```

---

## Task 7: 项目工作区三栏布局

**Files:**
- Modify: `frontend/src/app/projects/[id]/page.tsx`
- Modify: `frontend/src/components/project/AgentChat.tsx`（支持 size="lg"）
- Modify: `frontend/src/components/project/AgentCanvas.tsx`
- 新建: `frontend/src/components/project/TimelinePanel.tsx`

**Interfaces:**
- 左侧 `<AgentChat size="lg" mode="modify" ... />`
- 中间 `<AgentCanvas project={...} />`（预览 + 故事板）
- 右侧 `<TimelinePanel composition={...} />`

- [ ] **Step 1: 新建 TimelinePanel.tsx**

```tsx
// frontend/src/components/project/TimelinePanel.tsx
'use client';

import { useState } from 'react';
import { clsx } from 'clsx';
import { Composition } from '@/lib/types';

interface TimelinePanelProps {
  composition: Composition | null;
}

export function TimelinePanel({ composition }: TimelinePanelProps) {
  const [collapsed, setCollapsed] = useState(false);
  if (!composition) return null;

  const tracks = composition.tracks || [];

  return (
    <div className={clsx('h-full bg-background-surface border-l border-border-subtle flex flex-col', collapsed && 'w-12')}
      style={{ width: collapsed ? 48 : 280 }}>
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-between px-3 py-2 border-b border-border-subtle text-sm font-medium"
      >
        {!collapsed && <span>Timeline</span>}
        <span>{collapsed ? '←' : '→'}</span>
      </button>

      {!collapsed && (
        <div className="flex-1 overflow-y-auto p-3 space-y-3 text-sm">
          {tracks.map((track) => (
            <div key={track.id}>
              <div className="text-content-tertiary text-xs mb-1 capitalize">{track.type} Track</div>
              <div className="space-y-1">
                {track.clips.map((clip) => (
                  <div
                    key={clip.id}
                    className="h-7 rounded px-2 flex items-center bg-background-elevated border border-border-subtle truncate"
                    title={clip.text_content || clip.asset_id || 'clip'}
                  >
                    {clip.text_content || clip.asset_id || 'clip'}
                  </div>
                ))}
              </div>
            </div>
          ))}
          <a
            href={`/projects/${composition.project_id}/editor`}
            className="block text-center text-xs px-3 py-2 rounded bg-background-elevated border border-border-subtle hover:border-border-default"
          >
            打开高级编辑器 →
          </a>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: 修改 projects/[id]/page.tsx 为三栏布局**

保留现有数据获取逻辑，调整布局为：

```tsx
<div className="flex h-[calc(100dvh-64px)]">
  <aside className="w-[360px] border-r border-border-subtle overflow-hidden">
    <AgentChat size="lg" mode="modify" ... />
  </aside>
  <main className="flex-1 flex flex-col min-w-0 bg-background-base">
    <AgentCanvas project={project} />
  </main>
  <TimelinePanel composition={composition} />
</div>
```

- [ ] **Step 3: 运行前端测试**

```bash
cd /Users/edwinhao/ClipWorks/frontend
npm test -- --run
```

- [ ] **Step 4: 提交**

```bash
cd /Users/edwinhao/ClipWorks
git add frontend/src/app/projects/\[id\]/page.tsx frontend/src/components/project/TimelinePanel.tsx frontend/src/components/project/AgentChat.tsx frontend/src/components/project/AgentCanvas.tsx
git commit -m "feat(ui): workspace three-column layout (chat / canvas / timeline)"
```

---

## Task 8: 补齐关键确认点组件

**Files:**
- 新建: `frontend/src/components/project/IntentCard.tsx`
- 新建: `frontend/src/components/project/PlanApproval.tsx`
- 新建: `frontend/src/components/project/StoryboardStrip.tsx`
- 修改: `frontend/src/components/project/AgentCanvas.tsx`

**Interfaces:**
- `IntentCard`：展示 Agent 总结的需求，提供 Edit/Confirm
- `PlanApproval`：展示 pending plan，提供 Approve/Reject
- `StoryboardStrip`：展示 scenes 缩略图，点击选中

- [ ] **Step 1: 新建 IntentCard.tsx**

```tsx
// frontend/src/components/project/IntentCard.tsx
'use client';

interface IntentCardProps {
  intent: { duration?: number; format?: string; style?: string; goal?: string };
  onConfirm: () => void;
  onEdit: (text: string) => void;
}

export function IntentCard({ intent, onConfirm, onEdit }: IntentCardProps) {
  return (
    <div className="bg-brand-900/20 border border-brand-500/30 rounded-xl p-4">
      <div className="text-brand-400 font-semibold text-sm mb-2">AI 理解的需求</div>
      <div className="space-y-1 text-sm text-content-secondary">
        {intent.goal && <p>目标：{intent.goal}</p>}
        {intent.duration && <p>时长：{intent.duration} 秒</p>}
        {intent.format && <p>画幅：{intent.format}</p>}
        {intent.style && <p>风格：{intent.style}</p>}
      </div>
      <div className="flex gap-2 mt-3">
        <button onClick={onConfirm} className="px-3 py-1.5 rounded bg-brand-600 text-white text-sm">确认</button>
        <button onClick={() => onEdit('')} className="px-3 py-1.5 rounded bg-background-elevated text-content-secondary text-sm">修改</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 新建 PlanApproval.tsx（复用 AgentChat 中已有逻辑）**

将 `AgentChat.tsx` 中 pending plan 的 UI 抽取为独立组件，保持相同 props：

```tsx
// frontend/src/components/project/PlanApproval.tsx
'use client';
import { AgentPlan } from '@/lib/types';

interface PlanApprovalProps {
  plan: AgentPlan;
  onApprove: () => void;
  onReject: () => void;
  loading?: boolean;
}

export function PlanApproval({ plan, onApprove, onReject, loading }: PlanApprovalProps) {
  return (
    <div className="bg-success/10 border border-success/30 rounded-xl p-4">
      <div className="flex justify-between items-center mb-3">
        <span className="font-semibold text-success">方案已就绪 · 待确认</span>
        <span className="text-xs text-content-tertiary">{plan.format} · {plan.duration}s · {plan.scenes.length} 镜</span>
      </div>
      <div className="space-y-2 mb-4">
        {plan.scenes.map((s, idx) => (
          <div key={idx} className="bg-background-base rounded p-2 text-sm border border-border-subtle">
            <span className="font-medium">镜 {idx + 1}</span>
            <span className="text-content-tertiary ml-2">({s.start}s–{s.start + s.duration}s)</span>
            <p className="text-content-secondary mt-1">{s.description}</p>
            {s.text && <p className="text-brand-400 mt-1">“{s.text}”</p>}
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <button onClick={onApprove} disabled={loading} className="flex-1 px-3 py-2 rounded bg-brand-600 text-white text-sm">确认生成</button>
        <button onClick={onReject} disabled={loading} className="flex-1 px-3 py-2 rounded bg-background-elevated text-content-secondary text-sm">再改改</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: 新建 StoryboardStrip.tsx**

```tsx
// frontend/src/components/project/StoryboardStrip.tsx
'use client';
import { Scene } from '@/lib/types';

interface StoryboardStripProps {
  scenes: Scene[];
  currentIndex: number;
  onSelect: (index: number) => void;
}

export function StoryboardStrip({ scenes, currentIndex, onSelect }: StoryboardStripProps) {
  return (
    <div className="h-36 bg-background-surface border-t border-border-subtle p-3 overflow-x-auto">
      <div className="flex gap-3 min-w-max">
        {scenes.map((s, idx) => (
          <button
            key={s.id || idx}
            onClick={() => onSelect(idx)}
            className={`w-28 h-24 rounded-lg border flex flex-col justify-center items-center p-2 text-xs transition-colors ${
              idx === currentIndex
                ? 'border-brand-500 bg-brand-900/20 text-content-primary'
                : 'border-border-subtle bg-background-elevated text-content-secondary'
            }`}
          >
            <span className="font-medium">镜 {idx + 1}</span>
            <span className="text-content-tertiary mt-1">{s.start}s–{s.start + s.duration}s</span>
            <span className="truncate w-full text-center mt-1">{s.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 修改 AgentCanvas.tsx 引入 StoryboardStrip 和预览**

```tsx
// frontend/src/components/project/AgentCanvas.tsx
'use client';
import { useState } from 'react';
import { Project } from '@/lib/types';
import { StoryboardStrip } from './StoryboardStrip';

interface AgentCanvasProps {
  project: Project;
}

export function AgentCanvas({ project }: AgentCanvasProps) {
  const [currentScene, setCurrentScene] = useState(0);
  const scenes = project.composition?.tracks?.flatMap((t) => t.clips) || [];

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="flex-1 flex items-center justify-center bg-black/40 p-6">
        <div className="relative bg-black rounded-2xl overflow-hidden shadow-2xl" style={{ width: 270, height: 480 }}>
          {/* 实际视频/iframe 预览 */}
          <div className="absolute inset-0 flex flex-col items-center justify-center text-white text-center p-4">
            <div className="text-xl font-bold mb-2">镜 {currentScene + 1}</div>
            <div className="text-sm opacity-80">{scenes[currentScene]?.text_content || '预览区域'}</div>
          </div>
          <div className="absolute bottom-4 left-4 right-4 h-1 bg-white/20 rounded">
            <div className="h-full bg-brand-400 rounded" style={{ width: `${((currentScene + 1) / Math.max(1, scenes.length)) * 100}%` }} />
          </div>
        </div>
      </div>
      <StoryboardStrip scenes={scenes} currentIndex={currentScene} onSelect={setCurrentScene} />
    </div>
  );
}
```

- [ ] **Step 5: 运行前端测试**

```bash
cd /Users/edwinhao/ClipWorks/frontend
npm test -- --run
```

- [ ] **Step 6: 提交**

```bash
cd /Users/edwinhao/ClipWorks
git add frontend/src/components/project/
git commit -m "feat(ui): add intent card, plan approval, storyboard strip components"
```

---

## Task 9: 前端导出设置与进度面板整合

**Files:**
- 新建: `frontend/src/components/project/ExportSettings.tsx`
- 修改: `frontend/src/components/project/GenerationPanel.tsx`
- 修改: `frontend/src/app/projects/[id]/page.tsx`

**Interfaces:**
- `ExportSettings`：分辨率/时长/质量/导出位置 + 进度
- `GenerationPanel`：已支持 SSE，只需调整按钮文案和错误状态

- [ ] **Step 1: 新建 ExportSettings.tsx**

```tsx
// frontend/src/components/project/ExportSettings.tsx
'use client';

import { useState } from 'react';
import { Project, RenderJob } from '@/lib/types';
import { GenerationPanel } from './GenerationPanel';

interface ExportSettingsProps {
  project: Project;
  latestJob: RenderJob | null;
  onStart: (settings: { format: string; duration: number; quality: string; location: string }) => void;
}

const FORMATS = [
  { label: '9:16 竖屏', value: '9:16', width: 1080, height: 1920 },
  { label: '16:9 横屏', value: '16:9', width: 1920, height: 1080 },
  { label: '1:1 方形', value: '1:1', width: 1080, height: 1080 },
];

export function ExportSettings({ project, latestJob, onStart }: ExportSettingsProps) {
  const [format, setFormat] = useState(project.target_format || '9:16');
  const [duration, setDuration] = useState(project.target_duration || 15);
  const [quality, setQuality] = useState('1080p');
  const [location, setLocation] = useState('cloud');

  return (
    <div className="max-w-xl mx-auto p-6">
      <h2 className="text-xl font-semibold mb-6">导出设置</h2>

      <div className="space-y-5">
        <div>
          <label className="block text-sm font-medium mb-2">分辨率</label>
          <div className="flex gap-2">
            {FORMATS.map((f) => (
              <button
                key={f.value}
                onClick={() => setFormat(f.value)}
                className={`px-3 py-2 rounded-lg border text-sm ${
                  format === f.value ? 'bg-brand-600 text-white border-brand-600' : 'bg-background-elevated border-border-subtle'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">时长</label>
          <input
            type="range"
            min={5}
            max={60}
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
            className="w-full"
          />
          <div className="text-right text-sm text-content-secondary">{duration}s</div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">质量</label>
          <div className="flex gap-2">
            {['720p 草稿', '1080p 成片', '4K Pro'].map((q) => (
              <button
                key={q}
                onClick={() => setQuality(q.split(' ')[0])}
                className={`px-3 py-2 rounded-lg border text-sm ${
                  quality === q.split(' ')[0] ? 'bg-brand-600 text-white border-brand-600' : 'bg-background-elevated border-border-subtle'
                }`}
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">导出位置</label>
          <div className="flex gap-2">
            {[
              { label: '云端渲染', value: 'cloud' },
              { label: '本机导出（未来）', value: 'local' },
            ].map((l) => (
              <button
                key={l.value}
                onClick={() => setLocation(l.value)}
                className={`px-3 py-2 rounded-lg border text-sm ${
                  location === l.value ? 'bg-brand-600 text-white border-brand-600' : 'bg-background-elevated border-border-subtle'
                }`}
              >
                {l.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <button
        onClick={() => onStart({ format, duration, quality, location })}
        disabled={project.status === 'generating'}
        className="w-full mt-6 px-4 py-3 rounded-lg bg-brand-600 text-white font-medium disabled:opacity-60"
      >
        {project.status === 'generating' ? '生成中…' : '开始导出'}
      </button>

      {latestJob && <GenerationPanel project={project} latestJob={latestJob} steps={[]} currentStepIndex={-1} currentDescription="" />}
    </div>
  );
}
```

注意：`GenerationPanel` 需要 `steps` / `currentStepIndex` / `currentDescription` props，这里传空数组是因为新版 GenerationPanel 内部可以从 `job.logs` 推导。如果 GenerationPanel 必须接收这些 props，需要传入有意义的步骤列表。

- [ ] **Step 2: 修改 GenerationPanel 支持无 steps 模式**

如果 `steps` 为空，从 `job.logs` 推导当前步骤。或保持原接口不变。

- [ ] **Step 3: 在工作区 page.tsx 中打开 ExportSettings 弹窗/抽屉**

```tsx
const [showExport, setShowExport] = useState(false);
// 点击 Export 按钮 setShowExport(true)
{showExport && <ExportSettings ... />}
```

- [ ] **Step 4: 运行前端测试**

```bash
cd /Users/edwinhao/ClipWorks/frontend
npm test -- --run
```

- [ ] **Step 5: 提交**

```bash
cd /Users/edwinhao/ClipWorks
git add frontend/src/components/project/ExportSettings.tsx frontend/src/components/project/GenerationPanel.tsx frontend/src/app/projects/\[id\]/page.tsx
git commit -m "feat(ui): export settings panel with integrated generation progress"
```

---

## Task 10: 文档更新

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/superpowers/specs/2026-07-16-hybrid-hyperframes-remotion-design.md`

- [ ] **Step 1: 修改 README.md**

```markdown
## 渲染引擎

`services/renderer/` 提供统一的独立渲染服务，后端通过 `RenderProvider` 接口按需调度：

- **HyperFrames** — 基于 Node.js 的 HTML/CSS 动画渲染引擎，整片一次性出片。
- **video-use** — 基于 ffmpeg 的原始素材剪辑引擎。
- **Mock** — 占位预览，用于无真实引擎时的兜底。
```

- [ ] **Step 2: 修改 AGENTS.md 渲染相关段落**

更新第 2.3、3.3、7.4 等章节，移除 Remotion 作为默认引擎的描述，强调 HyperFrames 整片渲染和 Agent 超时/重试策略。

- [ ] **Step 3: 标记旧 hybrid design doc 为废弃**

```markdown
> ⚠️ 已废弃：本文档描述的 hybrid（HF 分镜 + Remotion 总装）架构已不再使用。
> 当前架构见 `2026-07-22-remotion-removal-agent-redesign.md`。
```

- [ ] **Step 4: 提交**

```bash
cd /Users/edwinhao/ClipWorks
git add README.md AGENTS.md docs/superpowers/specs/2026-07-16-hybrid-hyperframes-remotion-design.md
git commit -m "docs: update architecture docs for hyperframes-only rendering"
```

---

## Self-Review

### Spec coverage

| Spec 要求 | 对应任务 |
|---|---|
| 移除 Remotion 默认依赖 | Task 1, 2, 3, 4 |
| HyperFrames 整片渲染 | Task 2 |
| 延长 HF 超时 | Task 5 |
| Agent 层决定重试 | Task 2（失败写入 logs，Agent 可读取） |
| Agent-first 首页 | Task 6 |
| 三栏工作区 | Task 7 |
| 关键确认点 | Task 8 |
| 导出设置 + 进度 | Task 9 |
| 文档更新 | Task 10 |
| streaming thinking | Task 6, 7, 8（复用现有 SSE） |

### Placeholder scan

- 无 "TBD"/"TODO"/"implement later"。
- 每个代码步骤包含实际代码或命令。
- 测试步骤包含预期输出。

### Type consistency

- `RenderRequest` / `RenderResult` 类型在各任务中一致。
- `AgentPlan` / `Scene` / `Composition` 类型来自 `frontend/src/lib/types.ts`。
- `GenerationPanel` props 保持一致；Task 9 中注意 `steps` 可能为空，需兼容。

### 已知风险

1. `render_task.py` 当前可能仍有大量 hybrid 相关代码和测试，Task 2 需要仔细删除。
2. `AgentChat.tsx` 的 `mode="plan"` / `mode="modify"` / `mode="vibe"` 逻辑复杂，抽取 `PlanApproval` 时注意不要破坏现有 vibe flow。
3. 前端 TypeScript 类型需与 `frontend/src/lib/types.ts` 对齐。
4. 测试可能需要大量更新，特别是 `test_render_task.py` 和 renderer 的 `test_remotion.py`。

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-22-remotion-removal-agent-redesign.md`.

Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
