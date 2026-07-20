import json
import logging
import re
from typing import Optional

from app.agent.llm import KimiClient, LLMUnavailableError
from app.agent.planner import DEFAULT_PLAN
from app.config import KIMI_PLANNING_MODEL
from app.services.scraper import scrape_url

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"https?://\S+")

PLANNING_SYSTEM_PROMPT = """You are ClipWorks, an expert AI video director. Your goal is to have a short, focused conversation with the user, then propose a concrete, executable video plan.

Engines available:
- HyperFrames: best for animated text / marketing / product explainers (HTML/CSS animations).
- Remotion: best for React-template based stories with structured data.
- video-use: best when the user provides raw footage or a URL that should be clipped / narrated.

You must respond using EXACTLY ONE of the two JSON formats below. Do not add conversational text outside the JSON block.

Format 1 — when you need more information:
```json
{
  "needs_more_info": true,
  "question": "ONE focused clarifying question in the user's language",
  "why": "Briefly explain why this detail matters for the video"
}
```

Format 2 — when you have enough information and the user has confirmed or asked to generate:
```json
{
  "final_plan": true,
  "title": "string",
  "hook": "string",
  "format": "16:9|9:16|1:1",
  "duration": 30,
  "scenes": [
    {"start": 0, "duration": 5, "description": "what happens visually", "visual": "image/animation description", "text": "on-screen text"}
  ],
  "assets_needed": ["description of needed images/music"],
  "engine_hint": "hyperframes|remotion|video-use"
}
```

Rules for a smart, Codex-like experience:
- Be proactive. If the user gives a URL, read the provided webpage title/description and infer the product, audience, and key selling points. Use those inferences directly in the plan; do NOT ask the user to confirm them.
- Ask only ONE question per turn. Keep it concise (under 60 words).
- Ask about the most impactful missing detail first: duration, aspect ratio, target audience/platform, or core message.
- If the user already stated duration/format/audience/style, trust them. Do NOT ask for confirmation of things they already said.
- If the user says generate/ok/开始生成/就这样/直接做/直接生成 or any synonym meaning "just make it", immediately produce Format 2 using reasonable defaults for anything unclear.
- If the user has provided a topic/URL plus duration and format, that is enough information: produce Format 2 immediately. Do not ask for more details.
- Default to hyperframes for animated marketing videos without raw footage. Prefer video-use when a source URL or raw clip should be narrated/remixed.
- Make the plan specific: include concrete scene descriptions, visual style, and on-screen text. Avoid generic filler like "intro scene".
- Always respond in the same language as the user (Chinese if they write Chinese).

Example of a good clarifying question:
{
  "needs_more_info": true,
  "question": "这个视频主要投放在哪个平台？（B站/抖音/YouTube/Product Hunt）不同平台决定画幅和节奏。",
  "why": "9:16 适合抖音/B站竖屏，16:9 适合 YouTube/Product Hunt；平台决定 hook 写法。"
}
"""


def _append_scraped_content(urls: list[str], lines: list[str]) -> None:
    """Fetch and summarize any webpages referenced in the conversation."""
    seen = set()
    for url in urls:
        if url in seen or not url.startswith(("http://", "https://")):
            continue
        seen.add(url)
        try:
            data = scrape_url(url)
        except Exception as exc:
            logger.warning("Failed to scrape %s for agent context: %s", url, exc)
            continue
        if not (data.get("title") or data.get("description")):
            continue
        lines.append(f"\n--- Webpage content for {url} ---")
        if data.get("title"):
            lines.append(f"Title: {data['title']}")
        if data.get("description"):
            lines.append(f"Description: {data['description'][:600]}")
        if data.get("images"):
            lines.append(f"Images: {', '.join(data['images'][:3])}")


def _build_user_context(project, user_message: str, history: list[dict]) -> str:
    lines = []
    lines.append(f"Project title: {project.title}")
    if project.source_url:
        lines.append(f"Source URL: {project.source_url}")
    if project.target_format:
        lines.append(f"Target format: {project.target_format}")
    if project.target_duration:
        lines.append(f"Target duration: {project.target_duration}s")

    urls = []
    if project.source_url:
        urls.append(project.source_url)
    urls.extend(_URL_RE.findall(user_message))
    _append_scraped_content(urls, lines)

    if history:
        lines.append("\nConversation so far:")
        for m in history[-6:]:
            role = m.get("role", "user")
            content = m.get("content", "")
            lines.append(f"{role}: {content[:300]}")
    lines.append(f"\nUser message: {user_message}")
    return "\n".join(lines)


def _extract_json_block(text: str) -> Optional[str]:
    """Extract the first JSON block from assistant text."""
    if "```json" in text:
        return text.split("```json")[1].split("```")[0].strip()
    if "```" in text:
        return text.split("```")[1].split("```")[0].strip()
    return text.strip()


def _extract_plan(text: str) -> Optional[dict]:
    """Try to extract a final plan from assistant text."""
    try:
        block = _extract_json_block(text)
        data = json.loads(block)
        if data.get("final_plan"):
            return data
    except Exception:
        pass
    return None


def _extract_question(text: str) -> Optional[dict]:
    """Try to extract a clarifying question from assistant text."""
    try:
        block = _extract_json_block(text)
        data = json.loads(block)
        if data.get("needs_more_info"):
            return data
    except Exception:
        pass
    return None


# 当模型没有严格输出 JSON（而是把方案写成了 Markdown 闲聊）时，用这些信号兜底，
# 仍然给出一个可“确认生成”的结构化方案，避免主链路卡在无限对话。
_GENERATE_HINTS = (
    "直接生成", "开始生成", "生成吧", "就这样", "直接做", "开始",
    "可以", "确定", "ok", "生成", "做吧", "出片",
)


def _user_wants_generate(message: str) -> bool:
    m = (message or "").lower()
    return any(h in m for h in _GENERATE_HINTS)


def _looks_like_plan(text: str) -> bool:
    # 形如 “场景 1 (0s-2s) …” 的中文分镜，且带有时长标记。
    return "场景" in text and ("秒" in text or "duration" in text or "s-" in text or "s)" in text)


def _should_offer_plan(user_message: str, full_text: str) -> bool:
    # 还在追问（needs_more_info）时不兜底出方案。
    if _extract_question(full_text):
        return False
    return _user_wants_generate(user_message) or _looks_like_plan(full_text)


def _synthesize_plan(project, full_text: str) -> dict:
    """从闲聊式回复里尽量提炼一个结构化方案；提不动就用确定性默认方案。"""
    plan = build_fallback_plan(project)
    m = re.search(r"\*\*([^*]{2,40})\*\*", full_text)
    if m:
        plan["title"] = m.group(1).strip()
    return plan


FALLBACK_NOTE = "（AI 暂不可用，已为你生成一个可编辑的默认分镜）"


def stream_planning_response(project, user_message: str, history: list[dict]):
    """Yield text chunks from the planning agent and return the final plan if one was produced.

    When the LLM is unavailable (missing key or API error) we degrade
    gracefully: stream a short Chinese note and emit a deterministic
    ``[PLAN_READY]`` plan so the user can still reach “确认生成”.
    """
    client = KimiClient(model=KIMI_PLANNING_MODEL)
    messages = history + [{"role": "user", "content": _build_user_context(project, user_message, history)}]

    full_text = ""
    try:
        for chunk in client.chat_completion_stream(PLANNING_SYSTEM_PROMPT, messages, temperature=1.0):
            full_text += chunk
            yield chunk
    except LLMUnavailableError as exc:
        logger.warning("Planning LLM unavailable, emitting fallback plan: %s", exc)
        fallback = build_fallback_plan(project)
        yield f"\n\n{FALLBACK_NOTE}"
        yield "\n\n[PLAN_READY]" + json.dumps(fallback, ensure_ascii=False)
        return

    plan = _extract_plan(full_text)
    if plan and plan.get("final_plan"):
        yield "\n\n[PLAN_READY]" + json.dumps(plan, ensure_ascii=False)
    elif _should_offer_plan(user_message, full_text):
        # 模型把方案写成了 Markdown 闲聊而非 JSON：兜底产出可确认的结构化方案，
        # 保证用户始终能走到“确认生成”，而不是无限对话。
        logger.info("Planner emitted non-JSON plan; synthesizing approvable plan.")
        yield "\n\n[PLAN_READY]" + json.dumps(_synthesize_plan(project, full_text), ensure_ascii=False)


def build_fallback_plan(project) -> dict:
    """Return a deterministic plan when no LLM is available.

    分镜按目标时长等比缩放，使三段首尾相接且总时长精确等于 duration。
    否则只改 duration 数字、不缩放分镜会导致：target_duration≠20 时
    plan.duration 与分镜总长不一致（_persist_composition 还会按片段末端
    把 composition.duration 重算成分镜总长），出片时长与声称不符。
    """
    d = max(3, int(project.target_duration or 20))
    a = max(1, d // 5)          # 开场 ~20%
    b = max(1, (d * 3) // 5)    # 主体 ~60%
    c = d - a - b               # 收尾 = 余量，保证 a + b + c == d
    if c < 1:                   # 极小 d 的兜底（d>=3 时不会触发）
        c = 1
    src = DEFAULT_PLAN["scenes"]
    # 重建 scenes，复用文案但覆盖 start/duration；绝不改写 DEFAULT_PLAN 本身。
    scenes = [
        {**src[0], "start": 0, "duration": a},
        {**src[1], "start": a, "duration": b},
        {**src[2], "start": a + b, "duration": c},
    ]
    plan = {**DEFAULT_PLAN, "scenes": scenes}
    plan["format"] = project.target_format or "16:9"
    plan["duration"] = d
    plan["engine_hint"] = "hyperframes"
    return plan
