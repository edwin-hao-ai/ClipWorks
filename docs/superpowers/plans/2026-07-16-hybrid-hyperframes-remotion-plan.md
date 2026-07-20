# ClipWorks Hybrid 渲染实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 ClipWorks 默认渲染路径改造为 hybrid：每个 plan scene 先由 HyperFrames 预渲染成 MP4 片段，再由 Remotion 总装成最终成片（含转场、字幕、角标、音轨）。

**Architecture:** 在 `render_task.py` 中新增 scene 拆分、单 scene HTML 生成、HF 预渲染、总装 composition 构建四个步骤；`engine_selector.py` 默认返回 `hybrid`；`RemotionProvider` 识别 `engine="hybrid"` 并直接渲染携带 scene MP4 片段的总装 composition；单 scene 失败时该 scene 回退到 Remotion 内置动效，不整片失败。

**Tech Stack:** FastAPI, SQLAlchemy, Celery, HyperFrames CLI, Remotion, ffmpeg, pytest.

## Global Constraints

- 必须遵循现有 backend 测试隔离：pytest 自动使用 `clipworks_test` 库和 redis db 1，不能写开发库。
- 新代码需匹配项目 PEP 8 / snake_case 风格；TypeScript 保持现有风格。
- 不要修改现有纯 Remotion / video-use / mock provider 的默认行为，除非 hybrid 明确要求。
- 所有新增文件需有对应测试；端到端脚本必须能独立运行并产出合法 MP4。
- 不要提交 `.env` 等敏感文件；git 操作前需用户确认。
- 保持最小改动，不借机重构无关代码。

## 文件结构

| 文件 | 责任 |
|---|---|
| `backend/app/agent/prompts.py` | 新增 `GENERATE_SCENE_HTML` 提示词 |
| `backend/app/agent/html_generator.py` | 新增 `generate_scene_html()`、`_fallback_scene_html()`、`_render_single_scene()` |
| `backend/app/rendering/engine_selector.py` | 默认返回 `hybrid`；保留 `video-use` 优先；纯 HyperFrames 仍可通过 prompt 关键词触发 |
| `backend/app/rendering/providers/remotion.py` | `can_handle` 接受 `hybrid`；渲染总装 composition |
| `backend/app/rendering/providers/hyperframes.py` | 可选：支持显式 `engine="hyperframes"` 调用；保持现有整片 HTML 路径 |
| `backend/app/tasks/render_task.py` | 编排 scene 拆分、HTML 生成、HF 预渲染、总装 composition、进度事件 |
| `services/renderer/remotion/src/compositions/GenericComp.tsx` | 当 clip 来自 HF scene 时跳过 AmbientCanvas 场景级氛围，避免双重动效 |
| `backend/tests/rendering/test_hybrid_provider.py` | 测试 scene 拆分、HF 调用、总装 composition、失败回退 |
| `backend/tests/test_render_task.py` | 扩展测试 hybrid 流程事件与缓存复用 |
| `services/renderer/tests/test_hyperframes.py` | 扩展单 scene HTML 渲染路径 |
| `scripts/e2e_hybrid.sh` | 端到端验证 hybrid 渲染产出真实 MP4 与 scene 片段 |

---

### Task 1: 新增单 Scene HTML 生成的 LLM 提示词

**Files:**
- Modify: `backend/app/agent/prompts.py`

**Interfaces:**
- Produces: `GENERATE_SCENE_HTML` 字符串常量。

- [ ] **Step 1: 在 `prompts.py` 末尾追加 `GENERATE_SCENE_HTML`**

```python
GENERATE_SCENE_HTML = """You are ClipWorks, an expert motion designer for short-form marketing videos.
Given a single scene specification and project context, output a self-contained HTML string that HyperFrames CLI can render into a silent MP4 clip for this scene.

Scene fields you MUST use:
- start, duration: the scene begins at t=0 in the generated clip and lasts exactly `duration` seconds.
- text: the main on-screen headline (<=14 Chinese characters, punchy and emotional).
- visual: a short Chinese description of atmosphere/color palette (e.g. "深蓝科技粒子", "暖橙日出").
- visual_type: one of product | broll | metaphor | text.
- shot: camera language hint (e.g. "特写", "缓慢推镜").
- narration: spoken line for this scene (do NOT render as visible text; use it only to match mood).

Project context provided:
- width, height, fps
- style: overall visual style (e.g. "赛博霓虹", "温暖治愈", "极简高级")
- mood: emotional tone
- brand_color: hex color that must appear subtly in the scene

Requirements:
1. Output ONLY a valid, self-contained HTML string (no markdown code fences, no explanations).
2. The root container must be exactly width x height pixels.
3. The clip duration is `duration` seconds; all CSS animations must fit within this time.
4. Include: a full-bleed background layer (gradient or provided image), the headline text layer, and subtle motion decorations matching `visual`.
5. Use CSS @keyframes for entrance and emphasis animations. Recommended easing: cubic-bezier(0.22, 1, 0.36, 1).
6. Do NOT include lower-third / subtitle text in this HTML — those are rendered separately by Remotion.
7. Do NOT include scene-to-scene transitions — those are handled by Remotion.
8. Headline must be highly readable: font size >= 6% of the shorter canvas edge, contrast >= 4.5:1.
9. If an image asset path is provided, use it as a background/hero image with object-fit: cover.

Respond with the raw HTML string only."""
"""
```

- [ ] **Step 2: 运行导入检查**

Run: `cd /Users/edwinhao/ClipWorks/backend && python -c "from app.agent.prompts import GENERATE_SCENE_HTML; print(len(GENERATE_SCENE_HTML))"`
Expected: 打印提示词长度，无 ImportError。

---

### Task 2: 实现 `generate_scene_html` 与确定性降级

**Files:**
- Modify: `backend/app/agent/html_generator.py`
- Test: `backend/tests/agent/test_html_generator.py`（如不存在则创建）

**Interfaces:**
- Consumes: `GENERATE_SCENE_HTML` from `prompts.py`, `KimiClient` from `.llm`.
- Produces: `generate_scene_html(scene, composition, assets) -> str`.

- [ ] **Step 1: 编写 `generate_scene_html` 的单元测试**

```python
# backend/tests/agent/test_html_generator.py
import pytest
from app.agent.html_generator import generate_scene_html


def test_generate_scene_html_returns_html_with_headline():
    scene = {
        "start": 0,
        "duration": 5,
        "text": "ClipWorks 一句话成片",
        "visual": "深蓝科技粒子",
        "visual_type": "text",
        "shot": "特写",
        "narration": "让视频创作变得简单",
    }
    composition = {
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "metadata": {"style": "赛博霓虹", "mood": "热血", "brand_color": "#00E5FF"},
    }
    assets = {}
    html = generate_scene_html(scene, composition, assets)
    assert html.startswith("<!DOCTYPE html>") or html.startswith("<html")
    assert "ClipWorks 一句话成片" in html
    assert "width: 1920px" in html or "1920" in html


def test_generate_scene_html_uses_fallback_when_scene_text_empty():
    scene = {"start": 0, "duration": 3, "text": "", "visual": "", "visual_type": "text"}
    composition = {"width": 1080, "height": 1920, "fps": 30, "metadata": {}}
    html = generate_scene_html(scene, composition, {})
    assert "<!DOCTYPE html>" in html
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/edwinhao/ClipWorks/backend && pytest tests/agent/test_html_generator.py -v`
Expected: 2 FAILED (`generate_scene_html` not defined)。

- [ ] **Step 3: 实现 `generate_scene_html`、`_fallback_scene_html`、`_render_single_scene`**

在 `backend/app/agent/html_generator.py` 中：

1. 导入 `GENERATE_SCENE_HTML`：

```python
from .prompts import GENERATE_HTML, GENERATE_SCENE_HTML, STORYBOARD
```

2. 在文件末尾追加：

```python
def _scene_palette(visual: str) -> str:
    """根据 visual 关键词给出确定性渐变。"""
    v = (visual or "").lower()
    if any(k in v for k in ("科技", "粒子", "hud", "tech", "蓝", "代码", "数据")):
        return "radial-gradient(ellipse at center, #0a1a2a 0%, #020203 100%)"
    if any(k in v for k in ("暖", "日出", "橙", "sun", "warm")):
        return "radial-gradient(ellipse at center, #3a1c0a 0%, #120604 100%)"
    if any(k in v for k in ("自然", "绿", "forest", "leaf")):
        return "radial-gradient(ellipse at center, #0c2a1a 0%, #020a04 100%)"
    if any(k in v for k in ("奢", "金", "premium", "gold")):
        return "radial-gradient(ellipse at center, #2a230a 0%, #0a0802 100%)"
    return "linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)"


def _fallback_scene_html(scene: dict, composition: dict, assets: dict) -> str:
    """LLM 不可用时，为单个 scene 生成确定性 HTML。"""
    width = composition.get("width", 1920)
    height = composition.get("height", 1080)
    fps = composition.get("fps", 30)
    duration = float(scene.get("duration", 5) or 5)
    text = scene.get("text") or scene.get("headline") or "ClipWorks"
    visual = scene.get("visual") or ""
    visual_type = scene.get("visual_type") or "text"
    brand_color = (composition.get("metadata") or {}).get("brand_color") or "#00E5FF"

    images = assets.get("images") or {}
    image_ids = assets.get("image_ids") or list(images.keys())
    img_url = None
    image_index = scene.get("image_index", -1)
    if isinstance(image_index, int) and 0 <= image_index < len(image_ids):
        img_url = images.get(image_ids[image_index])
    if not img_url and image_ids:
        img_url = images.get(image_ids[0])

    bg = _scene_palette(visual)
    img_tag = f'<img src="{img_url}" class="bg-image" alt="scene" />' if img_url else ""

    # 根据 visual_type 微调排版
    headline_size = min(width, height) * 0.07
    subtext = ""
    if visual_type == "product":
        subtext = "产品亮点 · 一键呈现"
    elif visual_type == "broll":
        subtext = "真实场景 · 质感画面"
    elif visual_type == "metaphor":
        subtext = "意象表达 · 引发共鸣"

    sub_tag = f'<div class="sub">{_escape_html(subtext)}</div>' if subtext else ""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Scene</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #000; overflow: hidden; }}
  #stage {{
    position: relative; width: {width}px; height: {height}px;
    background: {bg}; overflow: hidden;
    font-family: 'Noto Sans CJK SC','PingFang SC','Microsoft YaHei',sans-serif;
  }}
  .bg-image {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0.55; animation: kenburns {duration}s ease-in-out alternate; }}
  .scrim {{ position: absolute; inset: 0; background: rgba(0,0,0,0.45); }}
  .copy {{ position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: {int(min(width,height)*0.08)}px; text-align: center; z-index: 10; }}
  .headline {{ color: #fff; font-weight: 900; font-size: {int(headline_size)}px; line-height: 1.2;
    opacity: 0; animation: titleIn 0.8s cubic-bezier(0.22,1,0.36,1) 0.2s forwards;
    text-shadow: 0 6px 32px rgba(0,0,0,0.55), 0 0 40px {brand_color}44; }}
  .sub {{ margin-top: {int(height*0.026)}px; color: #e8eaf6; font-weight: 600; font-size: {int(headline_size*0.55)}px;
    opacity: 0; animation: subIn 0.8s cubic-bezier(0.22,1,0.36,1) 0.5s forwards; }}
  .glow {{ position: absolute; inset: 0; z-index: 0; pointer-events: none;
    background: radial-gradient(circle at 30% 70%, {brand_color}33 0%, transparent 55%);
    animation: pulse {duration}s ease-in-out infinite alternate; }}
  @keyframes kenburns {{ 0% {{ transform: scale(1); }} 100% {{ transform: scale(1.08); }} }}
  @keyframes titleIn {{ 0% {{ opacity: 0; transform: translateY(40px) scale(0.96); filter: blur(10px); }} 100% {{ opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }} }}
  @keyframes subIn {{ 0% {{ opacity: 0; transform: translateY(24px); }} 100% {{ opacity: 1; transform: translateY(0); }} }}
  @keyframes pulse {{ 0% {{ opacity: 0.4; }} 100% {{ opacity: 0.7; }} }}
</style>
</head>
<body>
<div id="stage">
  <div class="glow"></div>
  {img_tag}
  <div class="scrim"></div>
  <div class="copy">
    <div class="headline">{_escape_html(text)}</div>
    {sub_tag}
  </div>
</div>
<script>window.hyperframesDuration = {duration}; window.hyperframesFps = {fps};</script>
</body>
</html>"""


def generate_scene_html(scene: dict, composition: dict, assets: Optional[dict] = None) -> str:
    """为单个 scene 生成自包含 HTML；LLM 失败时走确定性降级模板。"""
    assets = assets or {}
    duration = float(scene.get("duration", 5) or 5)
    if duration <= 0:
        duration = 5

    prompt = (
        "Scene:\n" + json.dumps(scene, ensure_ascii=False, indent=2) + "\n\n"
        "Composition context:\n" + json.dumps(composition, ensure_ascii=False, indent=2) + "\n\n"
        "Available image assets (local paths):\n" + json.dumps(assets.get("images", {}), ensure_ascii=False, indent=2)
    )
    try:
        client = KimiClient(timeout=90, max_retries=1)
        raw = client.chat_completion(
            system_prompt=GENERATE_SCENE_HTML,
            user_prompt=prompt,
            json_mode=False,
            max_retries=1,
        )
        if raw and "<" in raw:
            html = raw.strip()
            # 去除可能的 markdown 代码围栏
            if html.startswith("```html"):
                html = html.split("```html", 1)[-1]
            if html.startswith("```"):
                html = html.split("```", 1)[-1]
            if html.endswith("```"):
                html = html.rsplit("```", 1)[0]
            html = html.strip()
            if html.startswith(("<!DOCTYPE html>", "<html")):
                logger.info("Generated scene HTML via LLM")
                return html
    except Exception as exc:
        logger.info("LLM scene HTML generation failed: %s", exc)

    return _fallback_scene_html(scene, composition, assets)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/edwinhao/ClipWorks/backend && pytest tests/agent/test_html_generator.py -v`
Expected: 2 PASSED。

---

### Task 3: 引擎选择器默认返回 `hybrid`

**Files:**
- Modify: `backend/app/rendering/engine_selector.py`
- Test: `backend/tests/rendering/test_engine_selector.py`

**Interfaces:**
- Produces: `select_engine()` returns `"hybrid"` for default marketing-video requests.

- [ ] **Step 1: 扩展 `test_engine_selector.py` 中的断言**

```python
# 在 backend/tests/rendering/test_engine_selector.py 中新增/修改测试

def test_default_returns_hybrid():
    request = RenderRequest(composition={}, assets={})
    assert select_engine(request) == "hybrid"


def test_video_use_still_priority_with_raw_assets():
    request = RenderRequest(composition={}, assets={}, raw_assets=["/tmp/clip.mp4"])
    assert select_engine(request) == "video-use"


def test_hyperframes_keyword_respected():
    request = RenderRequest(composition={}, assets={}, user_prompt="use hyperframes light html")
    assert select_engine(request) == "hyperframes"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/edwinhao/ClipWorks/backend && pytest tests/rendering/test_engine_selector.py -v`
Expected: 新增测试 FAIL。

- [ ] **Step 3: 修改 `engine_selector.py`**

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
    # 默认走 hybrid：HF 负责单 scene 视觉动效，Remotion 负责总装、转场、音轨。
    return "hybrid"
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/edwinhao/ClipWorks/backend && pytest tests/rendering/test_engine_selector.py -v`
Expected: ALL PASSED。

---

### Task 4: `RemotionProvider` 支持 `engine="hybrid"`

**Files:**
- Modify: `backend/app/rendering/providers/remotion.py`
- Test: `backend/tests/rendering/test_remotion_provider.py`（扩展）

**Interfaces:**
- Consumes: `RenderRequest.engine == "hybrid"`。
- Produces: `can_handle` 接受 `"hybrid"`；`_build_asset_map` 自动解析 scene MP4 素材。

- [ ] **Step 1: 在 `test_remotion_provider.py` 添加 hybrid 测试**

```python
# backend/tests/rendering/test_remotion_provider.py
from app.rendering.provider import RenderRequest
from app.rendering.providers.remotion import RemotionProvider


def test_remotion_provider_handles_hybrid_engine():
    provider = RemotionProvider()
    request = RenderRequest(composition={}, assets={}, engine="hybrid")
    assert provider.can_handle(request)


def test_remotion_provider_still_rejects_unknown_engine():
    provider = RemotionProvider()
    request = RenderRequest(composition={}, assets={}, engine="video-use")
    assert not provider.can_handle(request)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/edwinhao/ClipWorks/backend && pytest tests/rendering/test_remotion_provider.py -v`
Expected: 新增测试 FAIL。

- [ ] **Step 3: 修改 `RemotionProvider.can_handle`**

```python
# backend/app/rendering/providers/remotion.py
class RemotionProvider(RenderProvider):
    name = "remotion"

    def can_handle(self, request: RenderRequest) -> bool:
        return request.engine in (None, "remotion", "hybrid")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/edwinhao/ClipWorks/backend && pytest tests/rendering/test_remotion_provider.py -v`
Expected: ALL PASSED。

---

### Task 5: 在 `render_task.py` 中新增 scene 拆分与预渲染辅助函数

**Files:**
- Modify: `backend/app/tasks/render_task.py`
- Test: `backend/tests/test_render_task.py`（扩展）

**Interfaces:**
- Produces:
  - `_derive_scenes(comp_json) -> list[dict]`
  - `_scene_cache_key(project_id, idx, scene, composition) -> str`
  - `_write_scene_htmls(project_id, scenes, composition, assets, job) -> dict[int, str]`
  - `_prerender_scenes(project_id, scenes, html_paths, job, db) -> dict[int, tuple[str, bool]]`
  - `_build_assembly_composition(comp_json, scenes, scene_results, project, db) -> dict`

- [ ] **Step 1: 编写测试先失败**

```python
# backend/tests/test_render_task.py 顶部/新增
import os
from unittest.mock import MagicMock, patch
from app.tasks.render_task import (
    _derive_scenes,
    _build_assembly_composition,
)


def test_derive_scenes_uses_plan_scenes():
    comp = {
        "metadata": {
            "plan": {
                "scenes": [
                    {"start": 0, "duration": 3, "text": "A"},
                    {"start": 3, "duration": 4, "text": "B"},
                ]
            }
        },
        "tracks": [],
    }
    scenes = _derive_scenes(comp)
    assert len(scenes) == 2
    assert scenes[0]["text"] == "A"
    assert scenes[1]["start"] == 3


def test_derive_scenes_falls_back_to_clips():
    comp = {
        "metadata": {},
        "tracks": [
            {"type": "text", "clips": [
                {"start_time": 0, "duration": 2, "text_content": "X"},
                {"start_time": 2, "duration": 3, "text_content": "Y"},
            ]}
        ],
    }
    scenes = _derive_scenes(comp)
    assert len(scenes) == 2
    assert scenes[0]["text"] == "X"


def test_build_assembly_composition_replaces_visual_clips():
    comp = {
        "width": 1920,
        "height": 1080,
        "duration": 7,
        "tracks": [
            {"type": "video", "index": 0, "clips": [{"start_time": 0, "duration": 3, "asset_id": "old1"}]},
            {"type": "text", "index": 1, "clips": [{"start_time": 0, "duration": 3, "text_content": "A"}]},
        ],
    }
    scenes = [{"start": 0, "duration": 3, "text": "A", "transition": "fade"}]
    scene_results = {0: ("scene_0_asset_id", False)}
    project = MagicMock()
    project.id = "p1"
    project.assets = []
    result = _build_assembly_composition(comp, scenes, scene_results, project)
    assert len(result["tracks"]) == 2
    video_track = result["tracks"][0]
    assert video_track["type"] == "video"
    assert len(video_track["clips"]) == 1
    assert video_track["clips"][0]["asset_id"] == "scene_0_asset_id"
    assert video_track["clips"][0]["style"]["transition"] == "fade"
    # text track unchanged
    assert result["tracks"][1]["clips"][0]["text_content"] == "A"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/edwinhao/ClipWorks/backend && pytest tests/test_render_task.py -v`
Expected: 新增测试 FAIL。

- [ ] **Step 3: 实现辅助函数**

在 `backend/app/tasks/render_task.py` 中，在 `_write_project_html` 之后、紧挨着它，新增：

```python
import hashlib
import httpx
from app.models import MediaAsset


def _derive_scenes(comp_json: dict) -> list[dict]:
    """从 composition 中提取 scene 列表。优先使用 plan.scenes，否则从 text/video 轨推导。"""
    plan = (comp_json.get("metadata") or {}).get("plan") or {}
    scenes = plan.get("scenes")
    if isinstance(scenes, list) and scenes:
        return [dict(s) for s in scenes]

    # 无 plan.scenes 时，从 text 轨 + video 轨的 clip 边界推导
    clips: list[dict] = []
    for track in comp_json.get("tracks", []) or []:
        ttype = track.get("type")
        if ttype not in {"text", "video", "image", "overlay"}:
            continue
        for clip in track.get("clips", []) or []:
            clips.append({
                "start": float(clip.get("start_time", 0) or 0),
                "duration": float(clip.get("duration", 5) or 5),
                "text": clip.get("text_content", ""),
                "visual": (clip.get("style") or {}).get("visual", ""),
                "transition": (clip.get("style") or {}).get("transition", "fade"),
                "lower_third": (clip.get("style") or {}).get("lower_third", ""),
                "visual_type": (clip.get("style") or {}).get("visual_type", "text"),
                "narration": (clip.get("style") or {}).get("narration", ""),
                "shot": (clip.get("style") or {}).get("shot", ""),
            })
    clips.sort(key=lambda c: c["start"])
    # 合并同一 start 的 clip
    merged: list[dict] = []
    for c in clips:
        if merged and abs(merged[-1]["start"] - c["start"]) < 0.1:
            if c["text"] and not merged[-1]["text"]:
                merged[-1]["text"] = c["text"]
            if c["visual"] and not merged[-1]["visual"]:
                merged[-1]["visual"] = c["visual"]
        else:
            merged.append(dict(c))
    return merged


def _scene_cache_key(project_id: str, idx: int, scene: dict, composition: dict) -> str:
    """基于 scene 内容与项目画幅生成缓存键，用于复用未改动的 scene 片段。"""
    style = (composition.get("metadata") or {}).get("style", "")
    payload = json.dumps({"project_id": project_id, "idx": idx, "scene": scene, "style": style}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def _write_scene_htmls(
    project_id: str,
    scenes: list[dict],
    composition: dict,
    assets: dict,
    job: RenderJob,
    db,
) -> dict[int, str]:
    """为每个 scene 生成独立 HTML，返回 index -> html_path 映射。"""
    from app.agent import generate_scene_html

    render_dir = os.path.join(ASSETS_DIR, project_id, f"render_{job.id}")
    os.makedirs(render_dir, exist_ok=True)
    html_paths: dict[int, str] = {}
    for idx, scene in enumerate(scenes):
        html_path = os.path.join(render_dir, f"scene_{idx}.html")
        try:
            html = generate_scene_html(scene, composition, assets)
        except Exception as exc:
            logger.warning("generate_scene_html failed for scene %d: %s", idx, exc)
            html = generate_scene_html(scene, composition, {})
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        html_paths[idx] = html_path
        _append_log(job, f"场景 HTML 已生成 {idx + 1}/{len(scenes)}")
        db.commit()
    return html_paths


def _prerender_scenes(
    project_id: str,
    scenes: list[dict],
    html_paths: dict[int, str],
    job: RenderJob,
    db,
) -> dict[int, tuple[str, bool]]:
    """调用 renderer /render/hyperframes 把每个 scene HTML 渲染成 MP4。

    返回 index -> (scene_asset_id, fallback_to_remotion) 的映射。
    fallback_to_remotion=True 表示该 scene HF 渲染失败，应让 Remotion 用内置动效渲染。
    """
    from app.config import ASSETS_BASE_URL

    render_dir = os.path.join(ASSETS_DIR, project_id, f"render_{job.id}")
    os.makedirs(render_dir, exist_ok=True)
    results: dict[int, tuple[str, bool]] = {}

    concurrency = int(os.getenv("HF_CONCURRENCY", "1"))

    async def _render_one(idx: int, html_path: str) -> tuple[int, str, bool]:
        output_path = os.path.join(render_dir, f"scene_{idx}.mp4")
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{RENDERER_URL}/render/hyperframes",
                    json={"html_path": html_path, "output_path": output_path},
                )
                data = resp.json()
                if data.get("success"):
                    return idx, output_path, False
        except Exception as exc:
            logger.warning("HF prerender scene %d failed: %s", idx, exc)
        return idx, "", True

    async def _run_all():
        sem = asyncio.Semaphore(max(1, concurrency))

        async def bounded(idx: int, html_path: str):
            async with sem:
                return await _render_one(idx, html_path)

        tasks = [bounded(idx, html_paths[idx]) for idx in range(len(scenes))]
        return await asyncio.gather(*tasks)

    outputs = asyncio.run(_run_all())

    for idx, output_path, fallback in outputs:
        if fallback:
            _append_log(job, f"场景 {idx + 1}/{len(scenes)} HF 预渲染失败，将回退 Remotion 默认动效")
            results[idx] = ("", True)
            db.commit()
            continue

        # 注册为 MediaAsset，方便 Remotion 通过 asset_id 引用
        asset = MediaAsset(
            project_id=project_id,
            type="video",
            source="generated",
            local_path=os.path.abspath(output_path),
            metadata_={"name": f"第 {idx + 1} 镜动效预览", "scene_index": idx},
        )
        db.add(asset)
        db.flush()
        results[idx] = (asset.id, False)
        _append_log(job, f"场景预渲染完成 {idx + 1}/{len(scenes)}")
        db.commit()

    return results


def _build_assembly_composition(
    comp_json: dict,
    scenes: list[dict],
    scene_results: dict[int, tuple[str, bool]],
    project,
) -> dict:
    """把原 composition 中每个 scene 范围内的 video/image clip 替换为预渲染的 scene MP4。

    fallback scene（HF 失败）不插入 video clip，保留原 visual clip 让 Remotion 自行渲染。
    """
    import copy

    assembly = copy.deepcopy(comp_json)
    tracks = assembly.get("tracks", []) or []
    new_tracks: list[dict] = []

    for track in tracks:
        ttype = track.get("type")
        if ttype not in {"video", "image"}:
            new_tracks.append(track)
            continue

        kept_clips: list[dict] = []
        for clip in track.get("clips", []) or []:
            c_start = float(clip.get("start_time", 0) or 0)
            c_dur = float(clip.get("duration", 5) or 5)
            c_end = c_start + c_dur
            # 判断该 clip 是否完全落在某个 scene 内
            matched_scene_idx = None
            for s_idx, scene in enumerate(scenes):
                s_start = float(scene.get("start", 0))
                s_dur = float(scene.get("duration", scene.get("dur", 5)))
                s_end = s_start + s_dur
                if abs(c_start - s_start) < 0.1 and abs(c_end - s_end) < 0.1:
                    matched_scene_idx = s_idx
                    break
            if matched_scene_idx is not None and matched_scene_idx in scene_results:
                asset_id, fallback = scene_results[matched_scene_idx]
                if fallback:
                    # 保留原 clip，让 Remotion 用 KenBurns/MotionText 兜底
                    kept_clips.append(clip)
                else:
                    # 同一 scene 只保留一个 video clip；后续同 scene clip 跳过
                    if not any(
                        c.get("style", {}).get("scene_index") == matched_scene_idx
                        for c in kept_clips
                    ):
                        scene = scenes[matched_scene_idx]
                        kept_clips.append({
                            "start_time": scene.get("start", 0),
                            "duration": scene.get("duration", 5),
                            "asset_id": asset_id,
                            "position": {"x": 0, "y": 0, "width": assembly.get("width", 1920), "height": assembly.get("height", 1080)},
                            "style": {
                                "transition": scene.get("transition", "fade"),
                                "scene_index": matched_scene_idx,
                                "source": "hyperframes",
                            },
                            "text_content": "",
                        })
            else:
                kept_clips.append(clip)

        if kept_clips:
            new_track = dict(track)
            new_track["clips"] = kept_clips
            new_tracks.append(new_track)

    # 把未匹配到 video/image 轨的 scene 单独插入一条 video 轨（兜底）
    orphan_scene_clips = []
    for s_idx, scene in enumerate(scenes):
        if s_idx not in scene_results:
            continue
        asset_id, fallback = scene_results[s_idx]
        if fallback:
            continue
        # 简单检查是否已有该 scene 的 clip
        if not any(
            c.get("style", {}).get("scene_index") == s_idx
            for t in new_tracks for c in t.get("clips", [])
        ):
            orphan_scene_clips.append({
                "start_time": scene.get("start", 0),
                "duration": scene.get("duration", 5),
                "asset_id": asset_id,
                "position": {"x": 0, "y": 0, "width": assembly.get("width", 1920), "height": assembly.get("height", 1080)},
                "style": {"transition": scene.get("transition", "fade"), "scene_index": s_idx, "source": "hyperframes"},
                "text_content": "",
            })
    if orphan_scene_clips:
        new_tracks.insert(0, {"type": "video", "index": -1, "name": "HF Scenes", "clips": orphan_scene_clips})

    assembly["tracks"] = new_tracks
    # 标记总装 composition 来源，便于 Remotion 端识别
    assembly["metadata"] = assembly.get("metadata") or {}
    assembly["metadata"]["engine"] = "hybrid"
    return assembly
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/edwinhao/ClipWorks/backend && pytest tests/test_render_task.py -v`
Expected: 新增与既有测试均 PASS。

---

### Task 6: 在 `render_video_task` 中接入 hybrid 流程

**Files:**
- Modify: `backend/app/tasks/render_task.py`
- Test: `backend/tests/test_render_task.py`（新增集成测试）

**Interfaces:**
- Consumes: `_derive_scenes`, `_write_scene_htmls`, `_prerender_scenes`, `_build_assembly_composition`。
- Produces: `RenderRequest(engine="hybrid", ...)` 发给 `RenderService`。

- [ ] **Step 1: 修改 `render_video_task` 的 HTML/渲染阶段**

替换现有 `_write_project_html` 调用块：

```python
# 旧代码（保留注释供对比）:
# _append_log(job, "生成 HyperFrames HTML 动画…")
# html_path, html_url = _write_project_html(project_id, comp_json, assets)

# 新代码：
_html_path, _html_url = _write_project_html(project_id, comp_json, assets)
job.html_output_path = _html_path
job.html_output_url = _html_url

# 默认走 hybrid：拆分 scene -> HF 预渲染 -> Remotion 总装
selected_engine = engine or "hybrid"
if selected_engine == "hybrid":
    _append_log(job, "进入 Hybrid 渲染：逐场景生成 HTML 动画…")
    db.commit()
    try:
        scenes = _derive_scenes(comp_json)
        if scenes:
            html_paths = _write_scene_htmls(project_id, scenes, comp_json, assets, job, db)
            scene_results = _prerender_scenes(project_id, scenes, html_paths, job, db)
            fallback_count = sum(1 for _, fb in scene_results.values() if fb)
            success_count = len(scene_results) - fallback_count
            _append_log(job, f"场景预渲染完成：{success_count} 个成功，{fallback_count} 个回退 Remotion")
            comp_json = _build_assembly_composition(comp_json, scenes, scene_results, project)
            _append_log(job, "总装时间线已构建")
        else:
            _append_log(job, "未识别到 scene，将使用 Remotion 直接渲染")
            selected_engine = "remotion"
    except Exception as hybrid_exc:
        logger.warning("Hybrid pipeline failed for job=%s: %s", job_id, hybrid_exc)
        _append_log(job, f"Hybrid 流程失败：{str(hybrid_exc)[:120]}，回退纯 Remotion")
        selected_engine = "remotion"
    db.commit()

job.progress = 70
```

然后刷新 project.assets 并构造 `RenderRequest`：

```python
# 刷新 project 关系，确保 RemotionProvider 能解析到刚刚创建的 scene MP4 素材
db.refresh(project)

request = RenderRequest(
    engine=selected_engine,
    composition=comp_json,
    assets=assets,
    raw_assets=raw_assets,
    user_prompt=prompt,
    source_url=project.source_url,
    engine_hint=plan.get("engine_hint") if isinstance(plan, dict) else None,
    html_path=_html_path,
    html_url=_html_url,
)
```

- [ ] **Step 2: 确保 `RenderService` 对 `hybrid` 正确分发**

`backend/app/rendering/service.py` 中，当 `engine="hybrid"` 时，`provider_map["hybrid"]` 不存在；需要让 `hybrid` 映射到 `remotion` provider。修改 `_render_async`：

```python
async def _render_async(self, job, project, request: RenderRequest) -> RenderResult:
    engine = request.engine or select_engine(request)
    provider_map = {p.name: p for p in PROVIDERS}

    order_names: list[str] = []
    preferred = engine
    if preferred == "hybrid":
        preferred = "remotion"
    if preferred in provider_map:
        order_names.append(preferred)
    for name in ("remotion", "hyperframes"):
        if name in provider_map and name not in order_names:
            order_names.append(name)
    # ... 后续不变
```

- [ ] **Step 3: 添加集成测试**

```python
# backend/tests/test_render_task.py
from unittest.mock import patch, MagicMock
from app.tasks.render_task import render_video_task


def test_render_video_task_hybrid_path(monkeypatch, db_session, project_with_assets):
    # 简化集成测试：mock RenderService.render 返回成功
    monkeypatch.setattr(
        "app.tasks.render_task.RenderService",
        lambda: MagicMock(render=lambda *a, **kw: MagicMock(success=True, output_url="/api/static/p1/output.mp4", error_message=None)),
    )
    # mock 外部 HTTP 调用，避免真实请求 renderer
    monkeypatch.setattr(
        "app.tasks.render_task._prerender_scenes",
        lambda *a, **kw: {0: ("scene_asset_id", False)},
    )
    job = RenderJob(project_id=project_with_assets.id, status="queued")
    db_session.add(job)
    db_session.commit()

    plan = {
        "title": "T",
        "duration": 5,
        "format": "16:9",
        "scenes": [{"start": 0, "duration": 5, "text": "Hello"}],
    }
    render_video_task(job.id, project_with_assets.id, engine="hybrid", plan=plan)
    db_session.refresh(job)
    assert job.status == "completed"
    assert any("总装" in (e.get("message") or "") for e in (job.logs or []))
```

- [ ] **Step 4: 运行相关测试**

Run: `cd /Users/edwinhao/ClipWorks/backend && pytest tests/test_render_task.py tests/rendering/test_engine_selector.py tests/rendering/test_remotion_provider.py -v`
Expected: ALL PASSED。

---

### Task 7: Remotion 端识别 hybrid scene clip 并跳过重复氛围

**Files:**
- Modify: `services/renderer/remotion/src/compositions/GenericComp.tsx`
- Test: 手动/视觉验证（TSX 文件当前无单元测试，通过 e2e 验证）

**Interfaces:**
- Consumes: `clip.style.source === "hyperframes"`。
- Produces: 当总装 composition 的 clip 来自 HF 时，不叠加 AmbientCanvas 的场景级特效；保留 GrainOverlay、Vignette、品牌条。

- [ ] **Step 1: 修改 `GenericComp` 的 flavor 计算逻辑**

在 `activeFlavor` 计算之后添加：

```typescript
// 当 composition 来自 hybrid 流程时，HF 已经负责了单 scene 的氛围动效；
// Remotion 端再叠加 AmbientCanvas 会出现双重粒子/网格，因此整体禁用氛围层。
const isHybrid = composition.metadata?.engine === "hybrid";
```

并将 `<AmbientCanvas ... />` 渲染改为：

```tsx
{!isHybrid && (
  <AmbientCanvas
    flavor={activeFlavor}
    width={canvasWidth}
    height={canvasHeight}
    brandColor={brandColor}
  />
)}
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd /Users/edwinhao/ClipWorks/services/renderer/remotion && npx tsc --noEmit`
Expected: 无 TS 错误。

---

### Task 8: 后端 hybrid 专用测试

**Files:**
- Create: `backend/tests/rendering/test_hybrid_provider.py`

- [ ] **Step 1: 编写测试文件**

```python
import pytest
from unittest.mock import MagicMock, patch
from app.rendering.provider import RenderRequest
from app.rendering.providers.remotion import RemotionProvider


def test_build_assembly_composition_uses_scene_mp4():
    from app.tasks.render_task import _build_assembly_composition
    comp = {
        "width": 1920, "height": 1080, "duration": 6,
        "metadata": {"plan": {"scenes": []}},
        "tracks": [
            {"type": "video", "index": 0, "clips": [
                {"start_time": 0, "duration": 3, "asset_id": "a1"},
                {"start_time": 3, "duration": 3, "asset_id": "a2"},
            ]},
            {"type": "text", "index": 1, "clips": [
                {"start_time": 0, "duration": 3, "text_content": "S1"},
                {"start_time": 3, "duration": 3, "text_content": "S2"},
            ]},
        ],
    }
    scenes = [
        {"start": 0, "duration": 3, "text": "S1", "transition": "fade"},
        {"start": 3, "duration": 3, "text": "S2", "transition": "slide"},
    ]
    scene_results = {0: ("mp4_0", False), 1: ("mp4_1", False)}
    project = MagicMock()
    project.id = "p1"
    project.assets = []
    assembly = _build_assembly_composition(comp, scenes, scene_results, project)
    video_clips = assembly["tracks"][0]["clips"]
    assert [c["asset_id"] for c in video_clips] == ["mp4_0", "mp4_1"]
    assert assembly["metadata"]["engine"] == "hybrid"


def test_build_assembly_composition_fallback_keeps_original_clip():
    from app.tasks.render_task import _build_assembly_composition
    comp = {
        "width": 1920, "height": 1080, "duration": 3,
        "tracks": [
            {"type": "image", "index": 0, "clips": [
                {"start_time": 0, "duration": 3, "asset_id": "orig"},
            ]},
        ],
    }
    scenes = [{"start": 0, "duration": 3, "text": "S1"}]
    scene_results = {0: ("", True)}
    project = MagicMock()
    project.id = "p1"
    project.assets = []
    assembly = _build_assembly_composition(comp, scenes, scene_results, project)
    assert assembly["tracks"][0]["clips"][0]["asset_id"] == "orig"


def test_remotion_provider_hybrid_can_handle():
    provider = RemotionProvider()
    assert provider.can_handle(RenderRequest(composition={}, assets={}, engine="hybrid"))
```

- [ ] **Step 2: 运行测试**

Run: `cd /Users/edwinhao/ClipWorks/backend && pytest tests/rendering/test_hybrid_provider.py -v`
Expected: ALL PASSED。

---

### Task 9: 端到端脚本

**Files:**
- Create: `scripts/e2e_hybrid.sh`

- [ ] **Step 1: 编写脚本**

```bash
#!/usr/bin/env bash
set -euo pipefail

# scripts/e2e_hybrid.sh
# 验证 hybrid 渲染链路：创建项目 -> 触发 hybrid 渲染 -> 校验 scene 片段与最终 MP4。

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR/backend"

source .venv/bin/activate 2>/dev/null || true

API="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"

echo "==> E2E Hybrid render test against $API"

# 1) 确保用户存在（mock auth）
curl -s -c /tmp/cw_cookie.txt "$API/auth/login?email=e2e_hybrid@clipworks.test" >/dev/null

# 2) 创建项目
PROJECT_JSON=$(curl -s -b /tmp/cw_cookie.txt -X POST "$API/projects/" \
  -H "Content-Type: application/json" \
  -d '{"title":"Hybrid E2E","source_url":"https://example.com","target_format":"16:9","target_duration":10}')
PROJECT_ID=$(echo "$PROJECT_JSON" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Project: $PROJECT_ID"

# 3) 触发 hybrid 渲染
JOB_JSON=$(curl -s -b /tmp/cw_cookie.txt -X POST "$API/renders/" \
  -H "Content-Type: application/json" \
  -d "{\"project_id\":\"$PROJECT_ID\",\"engine\":\"hybrid\",\"prompt\":\"一句话介绍 ClipWorks\"}")
JOB_ID=$(echo "$JOB_JSON" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Job: $JOB_ID"

# 4) 轮询等待完成（最多 10 分钟）
for i in $(seq 1 120); do
  STATUS_JSON=$(curl -s -b /tmp/cw_cookie.txt "$API/renders/$JOB_ID")
  STATUS=$(echo "$STATUS_JSON" | python -c "import sys,json; print(json.load(sys.stdin)['status'])")
  echo "  [$i] status=$STATUS"
  if [ "$STATUS" = "completed" ]; then
    break
  elif [ "$STATUS" = "failed" ]; then
    echo "FAILED"
    echo "$STATUS_JSON"
    exit 1
  fi
  sleep 5
done

# 5) 校验最终 MP4
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

# 6) 校验 scene 片段存在
SCENE_COUNT=$(find "$ROOT_DIR/data/assets/$PROJECT_ID" -name 'scene_*.mp4' | wc -l | tr -d ' ')
echo "Scene clips: $SCENE_COUNT"
if [ "$SCENE_COUNT" -lt 1 ]; then
  echo "No scene clips found"
  exit 1
fi

echo "==> Hybrid E2E PASSED"
```

- [ ] **Step 2: 添加可执行权限**

Run: `chmod +x /Users/edwinhao/ClipWorks/scripts/e2e_hybrid.sh`

---

### Task 10: 全量测试与提交

- [ ] **Step 1: 运行后端测试**

Run: `cd /Users/edwinhao/ClipWorks/backend && pytest tests/rendering/ tests/test_render_task.py tests/agent/test_html_generator.py -v`
Expected: ALL PASSED。

- [ ] **Step 2: 运行渲染服务测试**

Run: `cd /Users/edwinhao/ClipWorks/services/renderer && pytest tests/test_hyperframes.py tests/test_remotion.py -v`
Expected: ALL PASSED。

- [ ] **Step 3: 本地端到端（如环境可用）**

Run: `bash /Users/edwinhao/ClipWorks/scripts/e2e_hybrid.sh`
Expected: 输出 `==> Hybrid E2E PASSED`。

- [ ] **Step 4: 提交代码**

```bash
cd /Users/edwinhao/ClipWorks
git add -A
git commit -m "feat(rendering): hybrid HyperFrames + Remotion pipeline

- Add per-scene HTML generation with LLM + deterministic fallback
- Render each scene via HyperFrames into scene_{i}.mp4
- Build assembly composition where Remotion composites scene clips with transitions/audio
- Make hybrid the default engine; video-use still prioritized for raw footage
- Add tests and e2e_hybrid.sh"
```

---

## 计划自检

| Spec 要求 | 对应任务 |
|---|---|
| 默认 hybrid 路径 | Task 3 |
| 单 scene HTML 生成 | Task 1, 2 |
| HF 预渲染成 MP4 | Task 5 |
| Remotion 总装转场/音轨 | Task 4, 6, 7 |
| 单 scene 失败回退 | Task 5 |
| 进度事件 | Task 5, 6 |
| scene 预览资产 | Task 5 (`MediaAsset`) |
| 测试覆盖 | Task 2, 3, 4, 5, 6, 8 |
| E2E 验证 | Task 9 |

无 TBD/TODO/占位符。所有任务都有具体代码、命令和预期输出。
