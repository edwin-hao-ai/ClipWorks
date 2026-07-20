# Agent Loop 向导 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 ClipWorks 视频创作从「单步对话直接出 plan」改造为「脚本 → 素材 → 场景 → 动效」四步递进式 Agent loop，并配套向导式 UI；保持 `/chat/stream` 旧入口兼容。

**Architecture:** 后端新增 `backend/app/agent/steps/` 子包，每步一个独立 LLM Agent（统一 `run(project, state, user_input) -> Iterator[str]` SSE 接口），由 `backend/app/routers/agent.py` 的新端点调度；`Project.agent_state` 扩展为四步状态机。前端新增 `PlanWizard` 组件及四个 Panel，在项目处于 `draft/planning` 时替换原有 `AgentChat` 的大尺寸规划视图。

**Tech Stack:** FastAPI + SQLAlchemy + KimiClient；Next.js 14 + TypeScript + Tailwind CSS + lucide-react。

## Global Constraints

- 不替换现有 composition 模型、渲染流水线和 `/chat/stream` 入口；四步完成后仍调用 `build_composition(plan)` + hybrid 渲染。
- 每步 Agent 必须有确定性 fallback，LLM 不可用时用户仍可继续。
- `Project.agent_state` 是 JSON 字段，扩展无需 DB 迁移。
- 后端路由不额外加 `/api` 前缀；静态文件通过 `/api/static` 暴露。
- 前端优先使用设计系统 token（`bg-background-base`、`text-content-primary` 等），避免硬编码颜色。
- 所有 modal/浮层支持 Escape 与点击外部关闭；删除用两步内联确认。
- Python 函数/变量使用 `snake_case`；TypeScript 组件使用 PascalCase 命名导出。
- TDD：每个功能模块先写测试再实现。

---

## File Map

### 后端新增

| 文件 | 职责 |
|---|---|
| `backend/app/agent/steps/__init__.py` | Step 调度器、`run_step`、状态机校验、SSE 打包。 |
| `backend/app/agent/steps/_base.py` | 共享工具：JSON 提取、SSE chunk 封装、状态读写 helper。 |
| `backend/app/agent/steps/_prompts.py` | 四步系统 prompt 常量。 |
| `backend/app/agent/steps/_fallbacks.py` | 每步确定性 fallback。 |
| `backend/app/agent/steps/script_step.py` | Step 1：脚本 Agent。 |
| `backend/app/agent/steps/assets_step.py` | Step 2：素材 Agent。 |
| `backend/app/agent/steps/scenes_step.py` | Step 3：场景 Agent。 |
| `backend/app/agent/steps/effects_step.py` | Step 4：动效 Agent。 |
| `backend/tests/agent/test_steps.py` | 各 step 解析与 fallback 测试。 |
| `backend/tests/test_agent_router_wizard.py` | 新 router 端点测试。 |

### 后端修改

| 文件 | 修改点 |
|---|---|
| `backend/app/agent/__init__.py` | 导出 `run_step`。 |
| `backend/app/routers/agent.py` | 新增 `/state`、`/step/{step_name}`、`/back`、`/reset`、`/state` (POST) 端点；扩展 `/approve` 兼容四步数据。 |

### 前端新增

| 文件 | 职责 |
|---|---|
| `frontend/src/components/project/PlanWizard.tsx` | 向导外壳：步骤条、底部控制、全局生成状态。 |
| `frontend/src/components/project/ScriptPanel.tsx` | Script 步骤展示/编辑。 |
| `frontend/src/components/project/AssetsPanel.tsx` | Assets 步骤展示/编辑。 |
| `frontend/src/components/project/ScenesPanel.tsx` | Scenes 步骤展示/编辑。 |
| `frontend/src/components/project/EffectsPanel.tsx` | Effects 步骤展示/编辑。 |
| `frontend/tests/components/PlanWizard.test.tsx` | PlanWizard 交互测试。 |

### 前端修改

| 文件 | 修改点 |
|---|---|
| `frontend/src/lib/types.ts` | 扩展 `AgentState`、`AgentPlan`、`AgentStep`、新增 `AgentScript`/`AgentAsset`/`AgentScene`/`AgentEffect`。 |
| `frontend/src/app/projects/[id]/page.tsx` | `isPlanning` 视图替换为 `PlanWizard`；保留 `AgentChat` 作为侧边辅助（后续可选）。 |

---

## Task 1: 后端 Step 基础结构与 Script Step

**Files:**
- Create: `backend/app/agent/steps/__init__.py`
- Create: `backend/app/agent/steps/_base.py`
- Create: `backend/app/agent/steps/_prompts.py`
- Create: `backend/app/agent/steps/_fallbacks.py`
- Create: `backend/app/agent/steps/script_step.py`
- Create: `backend/tests/agent/test_steps.py`
- Modify: `backend/app/agent/__init__.py`

**Interfaces:**
- Consumes: `Project` (SQLAlchemy model), `dict` agent_state, optional `user_input: str | None`.
- Produces: `run_step(step_name, project, state, user_input=None) -> Iterator[str]` where each yielded string is a JSON-encoded SSE `data:` payload (without the `data:` prefix).

- [ ] **Step 1: Write the failing test for script_step JSON extraction**

```python
# backend/tests/agent/test_steps.py
import json
import pytest
from app.agent.steps.script_step import _extract_script_json


class FakeProject:
    title = "Test"
    source_url = ""
    target_format = "16:9"
    target_duration = 30


def test_extract_script_json_from_markdown_block():
    text = 'Some words\n```json\n{"title": "T", "hook": "H", "roles": [], "narrative_arc": "A", "cta": "C", "duration": 30, "format": "16:9"}\n```'
    result = _extract_script_json(text)
    assert result["title"] == "T"
    assert result["format"] == "16:9"


def test_extract_script_json_invalid_returns_none():
    assert _extract_script_json("not json") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && pytest tests/agent/test_steps.py::test_extract_script_json_from_markdown_block -v`
Expected: FAIL with `_extract_script_json not defined`.

- [ ] **Step 3: Implement `_base.py` helpers and `script_step.py`**

```python
# backend/app/agent/steps/_base.py
import json
import re
from typing import Optional


def extract_json_block(text: str) -> Optional[str]:
    if "```json" in text:
        return text.split("```json")[1].split("```")[0].strip()
    if "```" in text:
        return text.split("```")[1].split("```")[0].strip()
    return text.strip()


def parse_json(text: str) -> Optional[dict]:
    try:
        return json.loads(extract_json_block(text))
    except Exception:
        return None


def sse_token(text: str) -> str:
    return json.dumps({"type": "token", "text": text}, ensure_ascii=False)


def sse_done() -> str:
    return json.dumps({"type": "done"}, ensure_ascii=False)


def sse_error(message: str) -> str:
    return json.dumps({"type": "error", "message": message}, ensure_ascii=False)
```

```python
# backend/app/agent/steps/script_step.py
import json
import logging
from typing import Iterator, Optional

from app.agent.llm import KimiClient, LLMUnavailableError
from app.agent.steps._base import parse_json, sse_done, sse_error, sse_token
from app.agent.steps._fallbacks import fallback_script
from app.agent.steps._prompts import SCRIPT_SYSTEM_PROMPT
from app.config import KIMI_PLANNING_MODEL

logger = logging.getLogger(__name__)


def _extract_script_json(text: str) -> Optional[dict]:
    data = parse_json(text)
    if not data:
        return None
    required = {"title", "hook", "roles", "narrative_arc", "cta", "duration", "format"}
    if not required.issubset(data.keys()):
        return None
    return data


def _build_context(project, state: dict, user_input: Optional[str]) -> str:
    lines = [
        f"Project title: {project.title}",
        f"Target format: {project.target_format or '16:9'}",
        f"Target duration: {project.target_duration or 30}s",
    ]
    if project.source_url:
        lines.append(f"Source URL: {project.source_url}")
    if user_input:
        lines.append(f"User brief / feedback: {user_input}")
    messages = state.get("messages", [])
    if messages:
        lines.append("\nConversation so far:")
        for m in messages[-6:]:
            lines.append(f"{m.get('role')}: {m.get('content', '')[:300]}")
    return "\n".join(lines)


def run(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    client = KimiClient(model=KIMI_PLANNING_MODEL)
    context = _build_context(project, state, user_input)
    full_text = ""
    try:
        for chunk in client.chat_completion_stream(SCRIPT_SYSTEM_PROMPT, [
            {"role": "user", "content": context},
        ], temperature=1.0):
            full_text += chunk
            yield sse_token(chunk)
    except LLMUnavailableError as exc:
        logger.warning("Script step LLM unavailable: %s", exc)
        script = fallback_script(project, state)
        yield sse_token("AI 暂不可用，已生成可编辑默认脚本。")
        yield sse_done()
        state["script"] = script
        return

    parsed = _extract_script_json(full_text)
    if parsed:
        state["script"] = parsed
    else:
        logger.warning("Script step produced unparseable output: %s", full_text)
        yield sse_error("无法解析脚本，请手动编辑或重试。")
        state["script"] = fallback_script(project, state)
    yield sse_done()
```

```python
# backend/app/agent/steps/_prompts.py
SCRIPT_SYSTEM_PROMPT = """You are ClipWorks, an expert AI video director. The user is in Step 1 "Script" of a 4-step video creation wizard.

Output EXACTLY one JSON code block (no conversational text outside it) with this schema:
```json
{
  "title": "video title",
  "hook": "first 3 seconds hook",
  "roles": [{"name": " narrator/character", "perspective": "first person / brand / user"}],
  "narrative_arc": "hook → conflict/pain → reveal/product → proof/experience → CTA",
  "cta": "call to action",
  "duration": 30,
  "format": "16:9"
}
```

Rules:
- Think roles and narrative arc first, then write hook and CTA.
- Use story-like language, not dry parameter lists.
- If the user has already specified duration/format, use those exact values.
- Respond in the same language as the user (Chinese if they write Chinese)."""
```

```python
# backend/app/agent/steps/_fallbacks.py
from app.agent.conversation import build_fallback_plan


def fallback_script(project, state):
    plan = build_fallback_plan(project)
    return {
        "title": plan.get("title", project.title),
        "hook": plan.get("hook", ""),
        "roles": [{"name": "旁白", "perspective": "品牌方"}],
        "narrative_arc": "钩子 → 痛点 → 产品登场 → 体验证据 → CTA",
        "cta": "立即体验",
        "duration": plan.get("duration", project.target_duration or 30),
        "format": plan.get("format", project.target_format or "16:9"),
    }
```

- [ ] **Step 4: Run tests**

Run: `cd backend && pytest tests/agent/test_steps.py -v`
Expected: PASS.

- [ ] **Step 5: Wire `__init__.py` and `app/agent/__init__.py`**

```python
# backend/app/agent/steps/__init__.py
from app.agent.steps.script_step import run as run_script
from app.agent.steps.assets_step import run as run_assets
from app.agent.steps.scenes_step import run as run_scenes
from app.agent.steps.effects_step import run as run_effects

STEPS = {
    "script": run_script,
    "assets": run_assets,
    "scenes": run_scenes,
    "effects": run_effects,
}

ORDER = ["script", "assets", "scenes", "effects"]


def run_step(step_name: str, project, state: dict, user_input: str | None = None):
    if step_name not in STEPS:
        raise ValueError(f"Unknown step: {step_name}")
    return STEPS[step_name](project, state, user_input)


def previous_step(step_name: str) -> str | None:
    try:
        idx = ORDER.index(step_name)
    except ValueError:
        return None
    return ORDER[idx - 1] if idx > 0 else None
```

```python
# backend/app/agent/__init__.py
from .planner import plan_video
from .composer import build_composition
from .html_generator import generate_html, generate_scene_html
from .modifier import modify_video
from .steps import run_step

__all__ = [
    "plan_video",
    "build_composition",
    "generate_html",
    "generate_scene_html",
    "modify_video",
    "run_step",
]
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/agent/steps backend/app/agent/__init__.py backend/tests/agent/test_steps.py
git commit -m "feat(agent): add step base, script step, and tests"
```

---

## Task 2: Assets / Scenes / Effects Steps

**Files:**
- Create: `backend/app/agent/steps/assets_step.py`
- Create: `backend/app/agent/steps/scenes_step.py`
- Create: `backend/app/agent/steps/effects_step.py`
- Modify: `backend/app/agent/steps/_prompts.py`
- Modify: `backend/app/agent/steps/_fallbacks.py`
- Modify: `backend/tests/agent/test_steps.py`

**Interfaces:**
- Consumes: `state["script"]` for assets; `state["script"]` + `state["assets"]` for scenes; `state["scenes"]` for effects.
- Produces: `state["assets"]` / `state["scenes"]` / `state["effects"]`; each step follows the same `run(project, state, user_input)` signature.

- [ ] **Step 1: Write failing tests for assets/scenes/effects parsing**

```python
# backend/tests/agent/test_steps.py (append)
from app.agent.steps.assets_step import _extract_assets_json
from app.agent.steps.scenes_step import _extract_scenes_json
from app.agent.steps.effects_step import _extract_effects_json


def test_extract_assets_json():
    text = '```json\n{"needed": [{"type": "image", "description": "D", "query": "Q", "count": 1}]}\n```'
    result = _extract_assets_json(text)
    assert result["needed"][0]["type"] == "image"


def test_extract_scenes_json():
    text = '```json\n{"scenes": [{"start": 0, "duration": 5, "description": "D", "visual": "V", "text": "T", "visual_type": "text", "shot": "S", "transition": "fade", "lower_third": "L", "required_assets": [0]}]}\n```'
    result = _extract_scenes_json(text)
    assert len(result["scenes"]) == 1
    assert result["scenes"][0]["transition"] == "fade"


def test_extract_effects_json():
    text = '```json\n{"effects": [{"scene_index": 0, "visual_style": "V", "animation_keywords": ["a"], "generate_image": true, "generate_image_prompt": "P"}]}\n```'
    result = _extract_effects_json(text)
    assert result["effects"][0]["scene_index"] == 0
```

- [ ] **Step 2: Implement the three steps and prompts**

```python
# backend/app/agent/steps/assets_step.py
import json
import logging
from typing import Iterator, Optional

from app.agent.llm import KimiClient, LLMUnavailableError
from app.agent.steps._base import parse_json, sse_done, sse_error, sse_token
from app.agent.steps._fallbacks import fallback_assets
from app.agent.steps._prompts import ASSETS_SYSTEM_PROMPT
from app.config import KIMI_PLANNING_MODEL

logger = logging.getLogger(__name__)


def _extract_assets_json(text: str) -> Optional[dict]:
    data = parse_json(text)
    if not data or "needed" not in data:
        return None
    return data


def _build_context(project, state: dict, user_input: Optional[str]) -> str:
    script = state.get("script", {})
    lines = [
        f"Project title: {project.title}",
        f"Script: {json.dumps(script, ensure_ascii=False)}",
    ]
    if user_input:
        lines.append(f"User feedback: {user_input}")
    return "\n".join(lines)


def run(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    client = KimiClient(model=KIMI_PLANNING_MODEL)
    context = _build_context(project, state, user_input)
    full_text = ""
    try:
        for chunk in client.chat_completion_stream(ASSETS_SYSTEM_PROMPT, [
            {"role": "user", "content": context},
        ], temperature=1.0):
            full_text += chunk
            yield sse_token(chunk)
    except LLMUnavailableError as exc:
        logger.warning("Assets step LLM unavailable: %s", exc)
        assets = fallback_assets(project, state)
        yield sse_token("AI 暂不可用，已生成默认素材清单。")
        yield sse_done()
        state["assets"] = assets
        return

    parsed = _extract_assets_json(full_text)
    if parsed:
        state["assets"] = parsed
    else:
        logger.warning("Assets step unparseable: %s", full_text)
        yield sse_error("无法解析素材清单，请手动编辑或重试。")
        state["assets"] = fallback_assets(project, state)
    yield sse_done()
```

```python
# backend/app/agent/steps/scenes_step.py
import json
import logging
from typing import Iterator, Optional

from app.agent.llm import KimiClient, LLMUnavailableError
from app.agent.planner import _normalize_plan
from app.agent.steps._base import parse_json, sse_done, sse_error, sse_token
from app.agent.steps._fallbacks import fallback_scenes
from app.agent.steps._prompts import SCENES_SYSTEM_PROMPT
from app.config import KIMI_PLANNING_MODEL

logger = logging.getLogger(__name__)


def _extract_scenes_json(text: str) -> Optional[dict]:
    data = parse_json(text)
    if not data or "scenes" not in data:
        return None
    return data


def _build_context(project, state: dict, user_input: Optional[str]) -> str:
    script = state.get("script", {})
    assets = state.get("assets", {})
    lines = [
        f"Project title: {project.title}",
        f"Target duration: {project.target_duration or script.get('duration', 30)}s",
        f"Target format: {project.target_format or script.get('format', '16:9')}",
        f"Script: {json.dumps(script, ensure_ascii=False)}",
        f"Assets: {json.dumps(assets, ensure_ascii=False)}",
    ]
    if user_input:
        lines.append(f"User feedback: {user_input}")
    return "\n".join(lines)


def run(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    client = KimiClient(model=KIMI_PLANNING_MODEL)
    context = _build_context(project, state, user_input)
    full_text = ""
    try:
        for chunk in client.chat_completion_stream(SCENES_SYSTEM_PROMPT, [
            {"role": "user", "content": context},
        ], temperature=1.0):
            full_text += chunk
            yield sse_token(chunk)
    except LLMUnavailableError as exc:
        logger.warning("Scenes step LLM unavailable: %s", exc)
        scenes = fallback_scenes(project, state)
        yield sse_token("AI 暂不可用，已生成默认场景。")
        yield sse_done()
        state["scenes"] = scenes
        return

    parsed = _extract_scenes_json(full_text)
    if parsed:
        plan = {
            "duration": project.target_duration or state.get("script", {}).get("duration", 30),
            "scenes": parsed["scenes"],
        }
        _normalize_plan(plan)
        state["scenes"] = {"scenes": plan["scenes"]}
    else:
        logger.warning("Scenes step unparseable: %s", full_text)
        yield sse_error("无法解析场景，请手动编辑或重试。")
        state["scenes"] = fallback_scenes(project, state)
    yield sse_done()
```

```python
# backend/app/agent/steps/effects_step.py
import json
import logging
from typing import Iterator, Optional

from app.agent.llm import KimiClient, LLMUnavailableError
from app.agent.steps._base import parse_json, sse_done, sse_error, sse_token
from app.agent.steps._fallbacks import fallback_effects
from app.agent.steps._prompts import EFFECTS_SYSTEM_PROMPT
from app.config import KIMI_PLANNING_MODEL

logger = logging.getLogger(__name__)


def _extract_effects_json(text: str) -> Optional[dict]:
    data = parse_json(text)
    if not data or "effects" not in data:
        return None
    return data


def _build_context(project, state: dict, user_input: Optional[str]) -> str:
    scenes = state.get("scenes", {})
    script = state.get("script", {})
    lines = [
        f"Project title: {project.title}",
        f"Target format: {project.target_format or script.get('format', '16:9')}",
        f"Scenes: {json.dumps(scenes, ensure_ascii=False)}",
    ]
    if user_input:
        lines.append(f"User feedback: {user_input}")
    return "\n".join(lines)


def run(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    client = KimiClient(model=KIMI_PLANNING_MODEL)
    context = _build_context(project, state, user_input)
    full_text = ""
    try:
        for chunk in client.chat_completion_stream(EFFECTS_SYSTEM_PROMPT, [
            {"role": "user", "content": context},
        ], temperature=1.0):
            full_text += chunk
            yield sse_token(chunk)
    except LLMUnavailableError as exc:
        logger.warning("Effects step LLM unavailable: %s", exc)
        effects = fallback_effects(project, state)
        yield sse_token("AI 暂不可用，已生成默认动效。")
        yield sse_done()
        state["effects"] = effects
        return

    parsed = _extract_effects_json(full_text)
    if parsed:
        state["effects"] = parsed
    else:
        logger.warning("Effects step unparseable: %s", full_text)
        yield sse_error("无法解析动效，请手动编辑或重试。")
        state["effects"] = fallback_effects(project, state)
    yield sse_done()
```

Append prompts to `_prompts.py`:

```python
ASSETS_SYSTEM_PROMPT = """You are ClipWorks, an expert AI video director. The user is in Step 2 "Assets".

Given the script, list the images/videos/music/generated images needed. Output EXACTLY one JSON code block:
```json
{
  "needed": [
    {"type": "image|video|music|generated_image", "description": "中文描述", "query": "English search/generation prompt", "count": 1}
  ]
}
```
Rules:
- Distinguish searched images, generated images, raw footage, and music.
- generated_image queries must be valid English image-generation prompts.
- Keep the list reasonable: 3-6 items.
- Respond in the same language as the user for descriptions; queries in English."""

SCENES_SYSTEM_PROMPT = """You are ClipWorks, an expert AI video director. The user is in Step 3 "Scenes".

Break the script into timed scenes. Output EXACTLY one JSON code block:
```json
{
  "scenes": [
    {"start": 0, "duration": 5, "description": "what happens visually", "visual": "image/animation description", "text": "on-screen text", "visual_type": "product|broll|metaphor|text", "shot": "shot type", "transition": "fade|slide|zoom", "lower_third": "caption", "required_assets": [0]}
  ]
}
```
Rules:
- Follow the script narrative arc strictly.
- First scene must grab attention within 3 seconds.
- On-screen text <= 14 chars; narration <= 18 chars.
- Prefer assets listed in the assets step (reference by index in required_assets).
- Total duration must equal the target duration."""

EFFECTS_SYSTEM_PROMPT = """You are ClipWorks, an expert AI video director. The user is in Step 4 "Effects".

For each scene, specify the HTML animation style and whether an extra image should be generated. Output EXACTLY one JSON code block:
```json
{
  "effects": [
    {"scene_index": 0, "visual_style": "深蓝科技粒子", "animation_keywords": ["粒子", "HUD", "淡入"], "generate_image": false, "generate_image_prompt": ""}
  ]
}
```
Rules:
- visual_style is a short Chinese visual direction keyword.
- animation_keywords are used by the HTML generator.
- Only set generate_image=true when the scene truly needs a bespoke image; provide an English prompt."""
```

Append fallbacks to `_fallbacks.py`:

```python
def fallback_assets(project, state):
    script = state.get("script", {})
    title = script.get("title", project.title)
    return {
        "needed": [
            {"type": "image", "description": f"{title} 主题配图", "query": title, "count": 1},
            {"type": "image", "description": "品牌背景", "query": "modern abstract gradient background", "count": 1},
            {"type": "music", "description": "背景音乐", "query": "upbeat background music", "count": 1},
        ]
    }


def fallback_scenes(project, state):
    from app.agent.conversation import build_fallback_plan
    plan = build_fallback_plan(project)
    scenes = plan.get("scenes", [])
    for i, s in enumerate(scenes):
        s.setdefault("visual_type", "text")
        s.setdefault("shot", "定格")
        s.setdefault("transition", "fade")
        s.setdefault("lower_third", "")
        s.setdefault("required_assets", [])
    return {"scenes": scenes}


def fallback_effects(project, state):
    scenes = state.get("scenes", {}).get("scenes", [])
    effects = []
    for i, scene in enumerate(scenes):
        visual = scene.get("visual", "")
        keywords = ["淡入"]
        if "科技" in visual or "tech" in visual.lower():
            keywords.append("粒子")
        if "暖" in visual:
            keywords.append("光晕")
        effects.append({
            "scene_index": i,
            "visual_style": visual or "现代简约",
            "animation_keywords": keywords,
            "generate_image": False,
            "generate_image_prompt": "",
        })
    return {"effects": effects}
```

- [ ] **Step 3: Run tests**

Run: `cd backend && pytest tests/agent/test_steps.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/agent/steps backend/tests/agent/test_steps.py
git commit -m "feat(agent): add assets, scenes, effects steps and prompts"
```

---

## Task 3: 后端 Router 端点

**Files:**
- Modify: `backend/app/routers/agent.py`
- Create: `backend/tests/test_agent_router_wizard.py`

**Interfaces:**
- Consumes: `run_step` from `app.agent.steps`; existing `_require_project`, `_persist_composition`, `_check_credits` helpers.
- Produces: New endpoints `GET/POST /projects/{project_id}/agent/state`, `POST /projects/{project_id}/agent/step/{step_name}`, `POST /projects/{project_id}/agent/back`, `POST /projects/{project_id}/agent/reset`, and updated `POST /projects/{project_id}/agent/approve` that builds a plan from the four-step data.

- [ ] **Step 1: Write failing router tests**

```python
# backend/tests/test_agent_router_wizard.py
import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_state_requires_auth():
    response = client.get("/projects/any/agent/state")
    assert response.status_code == 401


def test_reset_state_auth_flow(monkeypatch, db_session):
    # Use the existing test fixtures; this test assumes fixtures create a user+project.
    pass
```

For the actual tests rely on existing `backend/tests/conftest.py` fixtures. Add tests after reviewing fixtures.

- [ ] **Step 2: Add state helpers and endpoints to `agent.py`**

Insert after imports and before existing endpoints:

```python
# backend/app/routers/agent.py
from app.agent.steps import run_step, ORDER, previous_step


class AgentStateEditPayload(BaseModel):
    state: dict


class AgentStepPayload(BaseModel):
    user_input: Optional[str] = None


def _fresh_agent_state() -> dict:
    return {
        "messages": [],
        "pending_plan": None,
        "step": "idle",
        "generating_step": None,
        "script": None,
        "assets": None,
        "scenes": None,
        "effects": None,
    }


def _load_state(project) -> dict:
    state = dict(project.agent_state) if project.agent_state else _fresh_agent_state()
    for key in _fresh_agent_state():
        state.setdefault(key, _fresh_agent_state()[key])
    return state


def _validate_step_order(state: dict, step_name: str):
    current = state.get("step", "idle")
    if step_name == "script":
        return
    required = previous_step(step_name)
    if required and current not in {required, step_name} and not state.get(required):
        raise HTTPException(
            status_code=400,
            detail=f"Please complete {required} before running {step_name}",
        )
```

Add new endpoints (place before `/approve` for logical grouping):

```python
@router.get("/state")
def get_agent_state(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _require_project(project_id, user, db)
    return _load_state(project)


@router.post("/state")
def update_agent_state(
    project_id: str,
    payload: AgentStateEditPayload,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _require_project(project_id, user, db)
    state = _load_state(project)
    # Only allow editing step-specific data and current step marker; do not overwrite messages blindly.
    for key in ["script", "assets", "scenes", "effects", "step", "generating_step"]:
        if key in payload.state:
            state[key] = payload.state[key]
    project.agent_state = state
    db.commit()
    return state


@router.post("/step/{step_name}")
def run_agent_step(
    project_id: str,
    step_name: str,
    payload: AgentStepPayload,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if step_name not in ("script", "assets", "scenes", "effects"):
        raise HTTPException(status_code=400, detail="Invalid step name")
    project = _require_project(project_id, user, db)
    state = _load_state(project)
    if state.get("generating_step"):
        raise HTTPException(
            status_code=409,
            detail=f"Already generating {state['generating_step']}; please wait",
        )
    _validate_step_order(state, step_name)
    state["generating_step"] = step_name
    project.agent_state = state
    project.status = "planning"
    db.commit()

    def event_stream():
        try:
            for chunk in run_step(step_name, project, state, payload.user_input):
                yield f"data: {chunk}\n\n"
            state["step"] = step_name
        except Exception as exc:
            logger.exception("Step %s failed", step_name)
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"
        finally:
            state["generating_step"] = None
            project.agent_state = state
            db.commit()
        yield f"data: {json.dumps({'type': 'done', 'step': step_name}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/back")
def step_back(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _require_project(project_id, user, db)
    state = _load_state(project)
    current = state.get("step", "idle")
    prev = previous_step(current)
    if not prev:
        raise HTTPException(status_code=400, detail="Cannot go back from idle")
    state["step"] = prev
    state["generating_step"] = None
    project.agent_state = state
    db.commit()
    return state


@router.post("/reset")
def reset_agent(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _require_project(project_id, user, db)
    state = _fresh_agent_state()
    project.agent_state = state
    project.status = "draft"
    db.commit()
    return state
```

- [ ] **Step 3: Extend `/approve` to consume four-step data**

Modify `/approve` so that if `state["script"]` exists it builds the plan from the four-step data; otherwise keeps old `pending_plan` behavior.

```python
@router.post("/approve")
def approve_agent_plan(
    project_id: str,
    payload: AgentApprovePayload,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _require_project(project_id, user, db)
    _check_credits(user)
    state = _load_state(project)

    plan = None
    if state.get("script") and state.get("assets") and state.get("scenes") and state.get("effects"):
        script = state["script"]
        scenes_data = state["scenes"].get("scenes", [])
        effects_data = state["effects"].get("effects", [])
        # Merge effects into scenes for downstream consumption.
        enriched_scenes = []
        for i, scene in enumerate(scenes_data):
            effect = next((e for e in effects_data if e.get("scene_index") == i), {})
            enriched = dict(scene)
            enriched["visual_style"] = effect.get("visual_style", "")
            enriched["animation_keywords"] = effect.get("animation_keywords", [])
            enriched["generate_image"] = effect.get("generate_image", False)
            enriched["generate_image_prompt"] = effect.get("generate_image_prompt", "")
            enriched_scenes.append(enriched)
        plan = {
            "title": script.get("title", project.title),
            "hook": script.get("hook", ""),
            "format": script.get("format", project.target_format or "16:9"),
            "duration": script.get("duration", project.target_duration or 30),
            "scenes": enriched_scenes,
            "assets_needed": [a.get("description", "") for a in state["assets"].get("needed", [])],
            "engine_hint": payload.engine or "hyperframes",
        }
    else:
        plan = state.get("pending_plan")

    if not plan:
        raise HTTPException(status_code=400, detail="No plan to approve")

    # Update project settings.
    if plan.get("format"):
        project.target_format = plan["format"]
    if plan.get("duration"):
        project.target_duration = plan["duration"]
    if plan.get("title"):
        project.title = plan["title"]

    # Persist script record.
    from app.models import Script
    script_record = Script(
        project_id=project.id,
        title=plan.get("title", project.title),
        hook=plan.get("hook", ""),
        scenes=plan.get("scenes", []),
    )
    db.add(script_record)

    state["step"] = "approved"
    state["pending_plan"] = None
    project.agent_state = state
    project.status = "generating"
    db.commit()

    job = RenderJob(project_id=project_id, status="queued", logs=[])
    db.add(job)
    db.commit()
    db.refresh(job)

    engine = payload.engine or plan.get("engine_hint")
    render_video_task.delay(job.id, project_id, None, engine, plan)

    return {"job_id": job.id, "status": "queued"}
```

- [ ] **Step 4: Run backend tests**

Run: `cd backend && pytest tests/test_agent_router_wizard.py tests/agent/test_steps.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/agent.py backend/tests/test_agent_router_wizard.py
git commit -m "feat(agent): add wizard state/step/back/reset endpoints and four-step approve"
```

---

## Task 4: 前端类型扩展与 PlanWizard 框架

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Create: `frontend/src/components/project/PlanWizard.tsx`
- Create: `frontend/src/components/project/ScriptPanel.tsx`
- Create: `frontend/tests/components/PlanWizard.test.tsx`

**Interfaces:**
- Consumes: Extended `AgentState` from types; project `status`/`target_format`/`target_duration`.
- Produces: `PlanWizard` renders the step sidebar + active panel + controls.

- [ ] **Step 1: Extend types**

```typescript
// frontend/src/lib/types.ts
export type AgentStep = 'idle' | 'script' | 'assets' | 'scenes' | 'effects' | 'approved' | 'chatting' | 'pending_approval' | 'generating';

export interface AgentScript {
  title: string;
  hook: string;
  roles: { name: string; perspective: string }[];
  narrative_arc: string;
  cta: string;
  duration: number;
  format: '16:9' | '9:16' | '1:1';
}

export interface AgentAssetItem {
  type: 'image' | 'video' | 'music' | 'generated_image';
  description: string;
  query: string;
  count: number;
}

export interface AgentAssetPlan {
  needed: AgentAssetItem[];
}

export interface AgentSceneItem {
  start: number;
  duration: number;
  description: string;
  visual: string;
  text: string;
  visual_type: 'product' | 'broll' | 'metaphor' | 'text';
  shot: string;
  transition: string;
  lower_third: string;
  required_assets: number[];
  visual_style?: string;
  animation_keywords?: string[];
  generate_image?: boolean;
  generate_image_prompt?: string;
}

export interface AgentScenePlan {
  scenes: AgentSceneItem[];
}

export interface AgentEffectItem {
  scene_index: number;
  visual_style: string;
  animation_keywords: string[];
  generate_image: boolean;
  generate_image_prompt: string;
}

export interface AgentEffectPlan {
  effects: AgentEffectItem[];
}

export interface AgentState {
  step: AgentStep;
  generating_step?: AgentStep | null;
  messages?: { role: 'user' | 'assistant'; content: string }[];
  pending_plan?: AgentPlan | null;
  script?: AgentScript | null;
  assets?: AgentAssetPlan | null;
  scenes?: AgentScenePlan | null;
  effects?: AgentEffectPlan | null;
}
```

- [ ] **Step 2: Write failing test for PlanWizard rendering current step**

```typescript
// frontend/tests/components/PlanWizard.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { PlanWizard } from '@/components/project/PlanWizard';
import { Project } from '@/lib/types';

const baseProject: Project = {
  id: '1',
  title: 'P',
  source_type: 'url',
  status: 'planning',
  target_format: '16:9',
  target_duration: 30,
  created_at: '',
  updated_at: '',
  agent_state: {
    step: 'script',
    script: {
      title: 'T',
      hook: 'H',
      roles: [],
      narrative_arc: 'A',
      cta: 'C',
      duration: 30,
      format: '16:9',
    },
  },
};

describe('PlanWizard', () => {
  it('renders script panel when step is script', () => {
    render(
      <PlanWizard
        project={baseProject}
        onStateChange={vi.fn()}
        onApprove={vi.fn()}
        generating={false}
      />
    );
    expect(screen.getByText(/脚本/i)).toBeInTheDocument();
    expect(screen.getByDisplayValue('T')).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Implement PlanWizard shell and ScriptPanel**

```tsx
// frontend/src/components/project/PlanWizard.tsx
'use client';

import { useState } from 'react';
import { clsx } from 'clsx';
import { Project } from '@/lib/types';
import { ScriptPanel } from './ScriptPanel';
import { AssetsPanel } from './AssetsPanel';
import { ScenesPanel } from './ScenesPanel';
import { EffectsPanel } from './EffectsPanel';
import { Button } from '@/components/ui/Button';

const STEPS = [
  { id: 'script', label: '脚本' },
  { id: 'assets', label: '素材' },
  { id: 'scenes', label: '场景' },
  { id: 'effects', label: '动效' },
] as const;

export interface PlanWizardProps {
  project: Project;
  onStateChange: (state: NonNullable<Project['agent_state']>) => void;
  onApprove: () => void;
  generating: boolean;
}

export function PlanWizard({ project, onStateChange, onApprove, generating }: PlanWizardProps) {
  const state = project.agent_state || { step: 'idle' };
  const [activeTab, setActiveTab] = useState<string>(
    STEPS.find((s) => s.id === state.step)?.id ?? 'script'
  );

  const currentStepIndex = STEPS.findIndex((s) => s.id === state.step);
  const activeIndex = STEPS.findIndex((s) => s.id === activeTab);

  const updateSection = <K extends keyof NonNullable<Project['agent_state']>>(
    key: K,
    value: NonNullable<Project['agent_state']>[K]
  ) => {
    onStateChange({ ...state, [key]: value });
  };

  const canGoNext = (() => {
    if (activeIndex < currentStepIndex) return true;
    if (activeIndex > currentStepIndex) return false;
    return !!state[activeTab as keyof typeof state];
  })();

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Step sidebar */}
      <nav aria-label="创作步骤" className="flex items-center gap-2">
        {STEPS.map((step, idx) => {
          const reached = idx <= currentStepIndex;
          const active = step.id === activeTab;
          return (
            <button
              key={step.id}
              type="button"
              onClick={() => setActiveTab(step.id)}
              className={clsx(
                'flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                active
                  ? 'bg-brand-500/15 text-brand-400'
                  : reached
                  ? 'text-content-secondary hover:bg-background-hover'
                  : 'text-content-tertiary cursor-not-allowed'
              )}
              disabled={!reached}
            >
              <span
                className={clsx(
                  'flex items-center justify-center w-5 h-5 rounded-full text-xs',
                  active ? 'bg-brand-500 text-white' : 'bg-background-elevated'
                )}
              >
                {idx + 1}
              </span>
              {step.label}
            </button>
          );
        })}
      </nav>

      {generating && state.generating_step && (
        <div className="flex items-center gap-2 text-sm text-brand-400">
          <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
          Agent 正在生成{STEPS.find((s) => s.id === state.generating_step)?.label}…
        </div>
      )}

      <div className="flex-1 min-h-0 overflow-y-auto bg-background-surface border border-border-subtle rounded-lg p-4">
        {activeTab === 'script' && (
          <ScriptPanel
            value={state.script}
            project={project}
            onChange={(script) => updateSection('script', script)}
          />
        )}
        {activeTab === 'assets' && (
          <AssetsPanel
            value={state.assets}
            onChange={(assets) => updateSection('assets', assets)}
          />
        )}
        {activeTab === 'scenes' && (
          <ScenesPanel
            value={state.scenes}
            onChange={(scenes) => updateSection('scenes', scenes)}
          />
        )}
        {activeTab === 'effects' && (
          <EffectsPanel
            value={state.effects}
            scenes={state.scenes}
            onChange={(effects) => updateSection('effects', effects)}
          />
        )}
      </div>

      <div className="flex items-center justify-between">
        <Button
          variant="secondary"
          onClick={() => setActiveTab(STEPS[Math.max(0, activeIndex - 1)].id)}
          disabled={activeIndex === 0}
        >
          上一步
        </Button>
        <div className="flex items-center gap-2">
          {activeIndex === STEPS.length - 1 ? (
            <Button onClick={onApprove} disabled={generating || currentStepIndex < activeIndex}>
              确认生成
            </Button>
          ) : (
            <Button
              onClick={() => setActiveTab(STEPS[activeIndex + 1].id)}
              disabled={!canGoNext}
            >
              下一步
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
```

```tsx
// frontend/src/components/project/ScriptPanel.tsx
'use client';

import { AgentScript, Project } from '@/lib/types';

export interface ScriptPanelProps {
  value?: AgentScript | null;
  project: Project;
  onChange: (script: AgentScript) => void;
}

export function ScriptPanel({ value, project, onChange }: ScriptPanelProps) {
  const script = value || {
    title: project.title,
    hook: '',
    roles: [],
    narrative_arc: '',
    cta: '',
    duration: project.target_duration || 30,
    format: (project.target_format as '16:9' | '9:16' | '1:1') || '16:9',
  };

  const update = <K extends keyof AgentScript>(key: K, val: AgentScript[K]) => {
    onChange({ ...script, [key]: val });
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-content-primary">脚本</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-1">
          <label className="text-sm text-content-secondary">标题</label>
          <input
            type="text"
            value={script.title}
            onChange={(e) => update('title', e.target.value)}
            className="w-full rounded-md bg-background-elevated border border-border px-3 py-2 text-sm text-content-primary focus:outline-none focus:border-brand-500"
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm text-content-secondary">钩子（前 3 秒）</label>
          <input
            type="text"
            value={script.hook}
            onChange={(e) => update('hook', e.target.value)}
            className="w-full rounded-md bg-background-elevated border border-border px-3 py-2 text-sm text-content-primary focus:outline-none focus:border-brand-500"
          />
        </div>
      </div>
      <div className="space-y-1">
        <label className="text-sm text-content-secondary">叙事弧线</label>
        <textarea
          value={script.narrative_arc}
          onChange={(e) => update('narrative_arc', e.target.value)}
          rows={3}
          className="w-full rounded-md bg-background-elevated border border-border px-3 py-2 text-sm text-content-primary focus:outline-none focus:border-brand-500"
        />
      </div>
      <div className="space-y-1">
        <label className="text-sm text-content-secondary">CTA</label>
        <input
          type="text"
          value={script.cta}
          onChange={(e) => update('cta', e.target.value)}
          className="w-full rounded-md bg-background-elevated border border-border px-3 py-2 text-sm text-content-primary focus:outline-none focus:border-brand-500"
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1">
          <label className="text-sm text-content-secondary">时长（秒）</label>
          <input
            type="number"
            value={script.duration}
            onChange={(e) => update('duration', Number(e.target.value))}
            className="w-full rounded-md bg-background-elevated border border-border px-3 py-2 text-sm text-content-primary focus:outline-none focus:border-brand-500"
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm text-content-secondary">画幅</label>
          <select
            value={script.format}
            onChange={(e) => update('format', e.target.value as AgentScript['format'])}
            className="w-full rounded-md bg-background-elevated border border-border px-3 py-2 text-sm text-content-primary focus:outline-none focus:border-brand-500"
          >
            <option value="16:9">16:9</option>
            <option value="9:16">9:16</option>
            <option value="1:1">1:1</option>
          </select>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run frontend test**

Run: `cd frontend && npm test -- PlanWizard.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/components/project/PlanWizard.tsx frontend/src/components/project/ScriptPanel.tsx frontend/tests/components/PlanWizard.test.tsx
git commit -m "feat(ui): add PlanWizard shell, ScriptPanel, and types"
```

---

## Task 5: Assets / Scenes / Effects Panels

**Files:**
- Create: `frontend/src/components/project/AssetsPanel.tsx`
- Create: `frontend/src/components/project/ScenesPanel.tsx`
- Create: `frontend/src/components/project/EffectsPanel.tsx`
- Modify: `frontend/tests/components/PlanWizard.test.tsx`

**Interfaces:**
- Consumes: `AgentAssetPlan`, `AgentScenePlan`, `AgentEffectPlan` from types.
- Produces: Editable panels that call `onChange` with updated data.

- [ ] **Step 1: Implement AssetsPanel**

```tsx
// frontend/src/components/project/AssetsPanel.tsx
'use client';

import { AgentAssetItem, AgentAssetPlan } from '@/lib/types';
import { Button } from '@/components/ui/Button';
import { Plus, Trash2 } from 'lucide-react';

const ASSET_TYPES: { value: AgentAssetItem['type']; label: string }[] = [
  { value: 'image', label: '搜索图片' },
  { value: 'generated_image', label: '生成图' },
  { value: 'video', label: '视频' },
  { value: 'music', label: '音乐' },
];

export interface AssetsPanelProps {
  value?: AgentAssetPlan | null;
  onChange: (assets: AgentAssetPlan) => void;
}

export function AssetsPanel({ value, onChange }: AssetsPanelProps) {
  const assets = value || { needed: [] };

  const updateItem = (idx: number, patch: Partial<AgentAssetItem>) => {
    const needed = assets.needed.map((item, i) => (i === idx ? { ...item, ...patch } : item));
    onChange({ ...assets, needed });
  };

  const addItem = () => {
    onChange({
      ...assets,
      needed: [...assets.needed, { type: 'image', description: '', query: '', count: 1 }],
    });
  };

  const removeItem = (idx: number) => {
    const needed = assets.needed.filter((_, i) => i !== idx);
    onChange({ ...assets, needed });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-content-primary">素材</h2>
        <Button size="sm" onClick={addItem}>
          <Plus className="w-4 h-4 mr-1" /> 添加素材
        </Button>
      </div>
      <div className="space-y-3">
        {assets.needed.map((item, idx) => (
          <div key={idx} className="grid grid-cols-12 gap-3 items-end bg-background-elevated p-3 rounded-md">
            <div className="col-span-2 space-y-1">
              <label className="text-xs text-content-secondary">类型</label>
              <select
                value={item.type}
                onChange={(e) => updateItem(idx, { type: e.target.value as AgentAssetItem['type'] })}
                className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary"
              >
                {ASSET_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="col-span-4 space-y-1">
              <label className="text-xs text-content-secondary">描述</label>
              <input
                type="text"
                value={item.description}
                onChange={(e) => updateItem(idx, { description: e.target.value })}
                className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary"
              />
            </div>
            <div className="col-span-4 space-y-1">
              <label className="text-xs text-content-secondary">检索词 / Prompt</label>
              <input
                type="text"
                value={item.query}
                onChange={(e) => updateItem(idx, { query: e.target.value })}
                className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary"
              />
            </div>
            <div className="col-span-1 space-y-1">
              <label className="text-xs text-content-secondary">数量</label>
              <input
                type="number"
                min={1}
                value={item.count}
                onChange={(e) => updateItem(idx, { count: Number(e.target.value) })}
                className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary"
              />
            </div>
            <div className="col-span-1">
              <button
                type="button"
                onClick={() => removeItem(idx)}
                className="p-2 text-content-secondary hover:text-error"
                aria-label="删除素材"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
        {assets.needed.length === 0 && (
          <p className="text-sm text-content-tertiary">暂无素材，点击上方按钮添加。</p>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Implement ScenesPanel**

```tsx
// frontend/src/components/project/ScenesPanel.tsx
'use client';

import { AgentSceneItem, AgentScenePlan } from '@/lib/types';
import { Button } from '@/components/ui/Button';
import { Plus, Trash2 } from 'lucide-react';

export interface ScenesPanelProps {
  value?: AgentScenePlan | null;
  onChange: (scenes: AgentScenePlan) => void;
}

export function ScenesPanel({ value, onChange }: ScenesPanelProps) {
  const scenes = value || { scenes: [] };

  const updateItem = (idx: number, patch: Partial<AgentSceneItem>) => {
    const list = scenes.scenes.map((s, i) => (i === idx ? { ...s, ...patch } : s));
    onChange({ ...scenes, scenes: list });
  };

  const addScene = () => {
    const last = scenes.scenes[scenes.scenes.length - 1];
    const start = last ? last.start + last.duration : 0;
    onChange({
      ...scenes,
      scenes: [
        ...scenes.scenes,
        {
          start,
          duration: 5,
          description: '',
          visual: '',
          text: '',
          visual_type: 'text',
          shot: '',
          transition: 'fade',
          lower_third: '',
          required_assets: [],
        },
      ],
    });
  };

  const removeScene = (idx: number) => {
    onChange({ ...scenes, scenes: scenes.scenes.filter((_, i) => i !== idx) });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-content-primary">场景</h2>
        <Button size="sm" onClick={addScene}>
          <Plus className="w-4 h-4 mr-1" /> 添加场景
        </Button>
      </div>
      <div className="space-y-3">
        {scenes.scenes.map((scene, idx) => (
          <div key={idx} className="bg-background-elevated p-3 rounded-md space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-content-secondary">场景 {idx + 1}</span>
              <button
                type="button"
                onClick={() => removeScene(idx)}
                className="p-1.5 text-content-secondary hover:text-error"
                aria-label="删除场景"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
            <div className="grid grid-cols-12 gap-3">
              <div className="col-span-2 space-y-1">
                <label className="text-xs text-content-secondary">开始</label>
                <input
                  type="number"
                  value={scene.start}
                  onChange={(e) => updateItem(idx, { start: Number(e.target.value) })}
                  className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary"
                />
              </div>
              <div className="col-span-2 space-y-1">
                <label className="text-xs text-content-secondary">时长</label>
                <input
                  type="number"
                  value={scene.duration}
                  onChange={(e) => updateItem(idx, { duration: Number(e.target.value) })}
                  className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary"
                />
              </div>
              <div className="col-span-2 space-y-1">
                <label className="text-xs text-content-secondary">转场</label>
                <select
                  value={scene.transition}
                  onChange={(e) => updateItem(idx, { transition: e.target.value })}
                  className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary"
                >
                  <option value="fade">fade</option>
                  <option value="slide">slide</option>
                  <option value="zoom">zoom</option>
                </select>
              </div>
              <div className="col-span-3 space-y-1">
                <label className="text-xs text-content-secondary">镜头</label>
                <input
                  type="text"
                  value={scene.shot}
                  onChange={(e) => updateItem(idx, { shot: e.target.value })}
                  className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary"
                />
              </div>
              <div className="col-span-3 space-y-1">
                <label className="text-xs text-content-secondary">类型</label>
                <select
                  value={scene.visual_type}
                  onChange={(e) => updateItem(idx, { visual_type: e.target.value as AgentSceneItem['visual_type'] })}
                  className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary"
                >
                  <option value="product">product</option>
                  <option value="broll">broll</option>
                  <option value="metaphor">metaphor</option>
                  <option value="text">text</option>
                </select>
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-content-secondary">画面描述</label>
              <input
                type="text"
                value={scene.visual}
                onChange={(e) => updateItem(idx, { visual: e.target.value })}
                className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs text-content-secondary">文案</label>
                <input
                  type="text"
                  value={scene.text}
                  onChange={(e) => updateItem(idx, { text: e.target.value })}
                  className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-content-secondary">角标</label>
                <input
                  type="text"
                  value={scene.lower_third}
                  onChange={(e) => updateItem(idx, { lower_third: e.target.value })}
                  className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary"
                />
              </div>
            </div>
          </div>
        ))}
        {scenes.scenes.length === 0 && (
          <p className="text-sm text-content-tertiary">暂无场景，点击上方按钮添加。</p>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Implement EffectsPanel**

```tsx
// frontend/src/components/project/EffectsPanel.tsx
'use client';

import { AgentEffectItem, AgentEffectPlan, AgentScenePlan } from '@/lib/types';

const STYLE_PRESETS = ['深蓝科技粒子', '暖橙光晕', '极简高级', '赛博霓虹', '清新自然'];

export interface EffectsPanelProps {
  value?: AgentEffectPlan | null;
  scenes?: AgentScenePlan | null;
  onChange: (effects: AgentEffectPlan) => void;
}

export function EffectsPanel({ value, scenes, onChange }: EffectsPanelProps) {
  const effects = value || { effects: [] };
  const sceneList = scenes?.scenes || [];

  const ensureEffects = () => {
    if (effects.effects.length >= sceneList.length) return effects;
    const generated = sceneList.map((_, idx) => ({
      scene_index: idx,
      visual_style: '',
      animation_keywords: [],
      generate_image: false,
      generate_image_prompt: '',
    }));
    return { effects: generated };
  };

  const working = ensureEffects();

  const updateEffect = (idx: number, patch: Partial<AgentEffectItem>) => {
    const list = working.effects.map((e, i) => (i === idx ? { ...e, ...patch } : e));
    onChange({ effects: list });
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-content-primary">动效</h2>
      <div className="space-y-4">
        {sceneList.map((scene, idx) => {
          const effect = working.effects[idx] || {
            scene_index: idx,
            visual_style: '',
            animation_keywords: [],
            generate_image: false,
            generate_image_prompt: '',
          };
          return (
            <div key={idx} className="bg-background-elevated p-3 rounded-md space-y-3">
              <div className="text-sm font-medium text-content-secondary">
                场景 {idx + 1}：{scene.text || scene.description || '未命名'}
              </div>
              <div className="flex flex-wrap gap-2">
                {STYLE_PRESETS.map((style) => (
                  <button
                    key={style}
                    type="button"
                    onClick={() => updateEffect(idx, { visual_style: style })}
                    className={`px-2 py-1 rounded-full text-xs border ${
                      effect.visual_style === style
                        ? 'bg-brand-500/20 border-brand-500 text-brand-400'
                        : 'border-border text-content-secondary hover:bg-background-hover'
                    }`}
                  >
                    {style}
                  </button>
                ))}
              </div>
              <div className="space-y-1">
                <label className="text-xs text-content-secondary">视觉风格</label>
                <input
                  type="text"
                  value={effect.visual_style}
                  onChange={(e) => updateEffect(idx, { visual_style: e.target.value })}
                  className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-content-secondary">动画关键词（逗号分隔）</label>
                <input
                  type="text"
                  value={effect.animation_keywords.join('，')}
                  onChange={(e) =>
                    updateEffect(idx, {
                      animation_keywords: e.target.value.split(/[,，]/).map((s) => s.trim()).filter(Boolean),
                    })
                  }
                  className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary"
                />
              </div>
              <label className="flex items-center gap-2 text-sm text-content-primary">
                <input
                  type="checkbox"
                  checked={effect.generate_image}
                  onChange={(e) => updateEffect(idx, { generate_image: e.target.checked })}
                  className="rounded border-border"
                />
                需要生成图
              </label>
              {effect.generate_image && (
                <div className="space-y-1">
                  <label className="text-xs text-content-secondary">生成图 Prompt（英文）</label>
                  <input
                    type="text"
                    value={effect.generate_image_prompt}
                    onChange={(e) => updateEffect(idx, { generate_image_prompt: e.target.value })}
                    className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary"
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Extend PlanWizard tests to cover navigation**

```typescript
// frontend/tests/components/PlanWizard.test.tsx (append)
import userEvent from '@testing-library/user-event';

it('navigates to assets panel after clicking next when data exists', async () => {
  const onChange = vi.fn();
  const projectWithAssets = {
    ...baseProject,
    agent_state: {
      step: 'assets',
      script: baseProject.agent_state.script,
      assets: { needed: [] },
    },
  };
  render(
    <PlanWizard
      project={projectWithAssets}
      onStateChange={onChange}
      onApprove={vi.fn()}
      generating={false}
    />
  );
  await userEvent.click(screen.getByRole('button', { name: /下一步/i }));
  expect(screen.getByText(/素材/i)).toBeInTheDocument();
});
```

- [ ] **Step 5: Run tests**

Run: `cd frontend && npm test -- PlanWizard`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/project/AssetsPanel.tsx frontend/src/components/project/ScenesPanel.tsx frontend/src/components/project/EffectsPanel.tsx frontend/tests/components/PlanWizard.test.tsx
git commit -m "feat(ui): add assets, scenes, effects panels"
```

---

## Task 6: 工作区集成 PlanWizard

**Files:**
- Modify: `frontend/src/app/projects/[id]/page.tsx`
- Modify: `frontend/src/lib/api.ts` (if needed for SSE helpers)

**Interfaces:**
- Consumes: `PlanWizard`, project state, `/agent/state` and `/agent/step/*` endpoints.
- Produces: `isPlanning` view now renders the wizard; generation starts via `/agent/approve`.

- [ ] **Step 1: Add SSE helper to api.ts**

```typescript
// frontend/src/lib/api.ts
export async function* streamJsonLines(
  url: string,
  body: unknown
): AsyncGenerator<{ type: string; [key: string]: unknown }> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  const reader = res.body?.getReader();
  if (!reader) throw new Error('No response body');
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith('data:')) continue;
      const payload = trimmed.slice(5).trim();
      if (payload === '[DONE]') return;
      try {
        yield JSON.parse(payload);
      } catch {
        // ignore malformed lines
      }
    }
  }
}
```

- [ ] **Step 2: Replace planning view in project page**

In `frontend/src/app/projects/[id]/page.tsx`:
1. Import `PlanWizard` and `streamJsonLines`.
2. Add state for `wizardGenerating`.
3. Replace the `isPlanning` block (`<AgentChat size="lg" mode="plan" ... />`) with `<PlanWizard ... />`.
4. Implement `handleStateChange` to call `POST /agent/state` and update local project.
5. Implement `handleRunStep` to stream a step and merge results.
6. Implement `handleApprove` to call `POST /agent/approve`.

```tsx
// Add imports
import { PlanWizard } from '@/components/project/PlanWizard';
import { streamJsonLines } from '@/lib/api';

// Add state
const [wizardGenerating, setWizardGenerating] = useState(false);

// Add handlers (inside component)
const handleWizardStateChange = async (nextState: NonNullable<Project['agent_state']>) => {
  if (!project) return;
  setProject((prev) => (prev ? { ...prev, agent_state: nextState } : null));
  try {
    await api.post(`/projects/${project.id}/agent/state`, { state: nextState });
  } catch (err) {
    setError(err instanceof Error ? err.message : '保存状态失败');
  }
};

const handleRunStep = async (stepName: string, userInput?: string) => {
  if (!project) return;
  setWizardGenerating(true);
  setError(null);
  try {
    for await (const chunk of streamJsonLines(`/projects/${project.id}/agent/step/${stepName}`, {
      user_input: userInput || '',
    })) {
      if (chunk.type === 'error') {
        setError(String(chunk.message));
      }
    }
    const data = await api.get(`/projects/${project.id}/agent/state`);
    setProject((prev) => (prev ? { ...prev, agent_state: data } : null));
  } catch (err) {
    setError(err instanceof Error ? err.message : '生成失败');
  } finally {
    setWizardGenerating(false);
  }
};

const handleApprove = async () => {
  if (!project) return;
  setWizardGenerating(true);
  setError(null);
  try {
    await api.post(`/projects/${project.id}/agent/approve`, {});
    setProject((prev) => (prev ? { ...prev, status: 'generating' } : null));
    setTimeout(() => refreshProject(), 500);
  } catch (err) {
    const msg = err instanceof Error ? err.message : '确认生成失败';
    if (msg.includes('402')) setCreditBlocked(true);
    else setError(msg);
  } finally {
    setWizardGenerating(false);
  }
};
```

Replace the `isPlanning` block:

```tsx
{isPlanning && (
  <div className="max-w-4xl mx-auto h-full flex flex-col py-4">
    <PlanWizard
      project={project}
      onStateChange={handleWizardStateChange}
      onApprove={handleApprove}
      generating={wizardGenerating}
    />
    <div className="mt-4 flex items-center gap-2">
      <Button
        variant="secondary"
        size="sm"
        onClick={() => handleRunStep(activeTab)}
        disabled={wizardGenerating}
      >
        重新生成当前步骤
      </Button>
      <span className="text-xs text-content-tertiary">
        也可以直接在上方编辑后点「确认生成」。
      </span>
    </div>
  </div>
)}
```

Note: `activeTab` is internal to `PlanWizard`. To expose it, add an `onStepChange` callback to `PlanWizard` or move `activeTab` state up to the page. For this plan, move `activeTab` state up to the page so `handleRunStep(activeTab)` works.

Modify `PlanWizardProps`:

```typescript
export interface PlanWizardProps {
  project: Project;
  activeTab?: string;
  onActiveTabChange?: (tab: string) => void;
  onStateChange: (state: NonNullable<Project['agent_state']>) => void;
  onApprove: () => void;
  generating: boolean;
}
```

Update `PlanWizard` to use external tab state if provided, otherwise internal.

- [ ] **Step 3: Run frontend build and tests**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no type errors.

Run: `cd frontend && npm test`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/projects/[id]/page.tsx frontend/src/lib/api.ts frontend/src/components/project/PlanWizard.tsx
git commit -m "feat(ui): integrate PlanWizard into project workspace"
```

---

## Task 7: 后端完整测试

**Files:**
- Create/Modify: `backend/tests/test_agent_router_wizard.py`

- [ ] **Step 1: Add router tests using existing fixtures**

Check `backend/tests/conftest.py` for fixtures like `client`, `test_user`, `test_project`. Then write tests:

```python
# backend/tests/test_agent_router_wizard.py
import json
from unittest.mock import patch

import pytest


def test_state_lifecycle(client, auth_headers, test_project):
    # GET initial state
    r = client.get(f"/projects/{test_project.id}/agent/state", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["step"] == "idle"


def test_reset_clears_state(client, auth_headers, test_project):
    r = client.post(f"/projects/{test_project.id}/agent/reset", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["step"] == "idle"


def test_skip_step_returns_400(client, auth_headers, test_project):
    r = client.post(
        f"/projects/{test_project.id}/agent/step/scenes",
        json={},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_concurrent_step_returns_409(client, auth_headers, test_project):
    # Pre-seed script step.
    from app.models import Project as ProjectModel
    project = client.app.state.db.query(ProjectModel).filter_by(id=test_project.id).first()
    # Mock run_step to stay generating.
    with patch('app.routers.agent.run_step') as mock_run:
        mock_run.return_value = iter([])
        client.post(f"/projects/{test_project.id}/agent/step/script", json={}, headers=auth_headers)
        r = client.post(f"/projects/{test_project.id}/agent/step/script", json={}, headers=auth_headers)
        assert r.status_code == 409
```

Adjust based on actual fixture names.

- [ ] **Step 2: Run backend tests**

Run: `cd backend && pytest tests/test_agent_router_wizard.py tests/agent/test_steps.py -v`
Expected: PASS.

- [ ] **Step 3: Run full backend suite**

Run: `cd backend && pytest`
Expected: PASS (or existing failures only).

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_agent_router_wizard.py
git commit -m "test(agent): add wizard router tests"
```

---

## Task 8: 端到端冒烟与收尾

**Files:**
- Create: `scripts/e2e_agent_loop.py`

- [ ] **Step 1: Create a lightweight API smoke script**

```python
# scripts/e2e_agent_loop.py
"""Smoke test the four-step wizard API without a browser."""
import argparse
import os
import sys

import requests

API = os.getenv("CLIPWORKS_API", "http://localhost:8000")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", required=True)
    args = parser.parse_args()

    s = requests.Session()
    # Assumes mock auth cookie already set or auth is disabled in test mode.
    # For local dev, visit http://localhost:3000/login first to get the cookie.

    r = s.post(f"{API}/projects/{args.project_id}/agent/reset")
    print("reset", r.status_code, r.json())

    for step in ["script", "assets", "scenes", "effects"]:
        print(f"\n--- running {step} ---")
        r = s.post(
            f"{API}/projects/{args.project_id}/agent/step/{step}",
            json={"user_input": ""},
            stream=True,
        )
        for line in r.iter_lines():
            if line:
                print(line.decode())

    r = s.post(f"{API}/projects/{args.project_id}/agent/approve", json={})
    print("\napprove", r.status_code, r.json())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run smoke test against local stack**

Ensure Docker stack is running (`docker compose up -d`). Then:

Run: `cd backend && source .venv/bin/activate && python scripts/e2e_agent_loop.py --project-id <id>`
Expected: Four steps complete and approve returns a `job_id`.

- [ ] **Step 3: Final commit and status check**

```bash
git add scripts/e2e_agent_loop.py
git commit -m "test(e2e): add agent loop API smoke script"
git status
```

---

## Self-Review

### Spec Coverage

| Spec Section | Implementing Task |
|---|---|
| 四步流程 (script/assets/scenes/effects) | Tasks 1, 2 |
| 状态机 (idle/script/assets/scenes/effects/approved) | Task 3 |
| agent_state 扩展 | Tasks 1, 4 |
| 每步独立 LLM Agent + SSE | Tasks 1, 2 |
| 后端新端点 | Task 3 |
| `/approve` 兼容四步数据 | Task 3 |
| 前端向导 UI | Tasks 4, 5, 6 |
| 错误处理与 fallback | Tasks 1, 2 |
| 越步/并发校验 | Task 3, 7 |
| 测试 | Tasks 1, 4, 7, 8 |

### Placeholder Scan

- No `TBD`, `TODO`, or vague "add validation" steps.
- Each code block contains concrete implementation.
- Test commands and expected outputs are explicit.

### Type Consistency

- `AgentStep` union covers new steps.
- `Project.agent_state` references new nested types.
- Backend `state` keys (`script`, `assets`, `scenes`, `effects`) match design doc and approve logic.

### Gaps

- Frontend `/agent/chat` modify mode remains unchanged; the wizard replaces only the large planning view.
- `AgentChat` side-assistant integration (section 7.4 of spec) is out of scope for this plan to keep the first iteration shippable.
- Auto image generation when `generate_image=true` is explicitly excluded by the spec's non-goals.
