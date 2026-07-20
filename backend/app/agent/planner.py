import json
import logging
from typing import Optional

from .llm import KimiClient
from .prompts import PLAN_VIDEO

logger = logging.getLogger(__name__)

DEFAULT_PLAN = {
    "title": "ClipWorks Video",
    "hook": "Discover something amazing with ClipWorks.",
    "style": "现代动感",
    "mood": "热血、向上",
    "rhythm": "快切",
    "scenes": [
        {
            "start": 0,
            "duration": 5,
            "description": "Opening title card with brand name",
            "visual": "gradient background",
            "text": "ClipWorks",
            "narration": "一句话，一段素材，一条成片。",
            "visual_type": "text",
            "shot": "logo 定格",
            "transition": "fade",
            "lower_third": "ClipWorks · AI 成片工厂",
        },
        {
            "start": 5,
            "duration": 10,
            "description": "Feature highlight scene",
            "visual": "abstract shapes",
            "text": "AI-powered video creation",
            "narration": "AI 自动规划脚本与分镜，真实素材直接进画面。",
            "visual_type": "metaphor",
            "shot": "缓慢推镜",
            "transition": "slide",
            "lower_third": "AI 规划 · 自动分镜",
        },
        {
            "start": 15,
            "duration": 5,
            "description": "Call to action",
            "visual": "brand background",
            "text": "Try it now",
            "narration": "立即开始你的第一条片子。",
            "visual_type": "text",
            "shot": "正面定格",
            "transition": "zoom",
            "lower_third": "免费体验",
        },
    ],
    "format": "16:9",
    "duration": 20,
    "assets_needed": ["gradient background", "brand logo placeholder"],
}


def _normalize_plan(plan: dict) -> dict:
    """把 LLM 规划的镜头时长归一化：各镜 duration 按原比例缩放，使总和精确等于
    plan.duration，并把 start 重排为从 0 开始的连续时间轴。

    LLM 偶尔会产出「总时长 30s 但镜头只排到 22s」（或超出）的方案，直接交给
    渲染会出现黑帧尾/截断，成片时长与用户 brief 不符；这里在规划出口统一收口。
    """
    scenes = plan.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return plan
    target = plan.get("duration")
    if not isinstance(target, (int, float)) or target <= 0:
        target = max(((s.get("start") or 0) + (s.get("duration") or 0)) for s in scenes)
    target = float(target)
    if target <= 0:
        return plan
    durs = [max(float(s.get("duration") or 0), 0.0) for s in scenes]
    total = sum(durs)
    if total <= 0:
        durs = [1.0] * len(scenes)
        total = float(len(scenes))
    scale = target / total
    cursor = 0.0
    last = len(scenes) - 1
    for i, scene in enumerate(scenes):
        scene["start"] = round(cursor, 1)
        if i == last:
            # 尾镜吃满剩余时长，消除四舍五入漂移，保证总时长精确命中 target
            remain = round(target - cursor, 1)
            scene["duration"] = remain if remain > 0 else (round(durs[i] * scale, 1) or 0.5)
        else:
            dur = round(durs[i] * scale, 1)
            scene["duration"] = dur
            cursor = round(cursor + dur, 1)
    plan["duration"] = int(target) if target.is_integer() else round(target, 1)
    return plan


def plan_video(
    source_url: Optional[str],
    user_prompt: Optional[str],
    target_format: Optional[str] = None,
) -> dict:
    """Call Kimi to plan a video. Falls back to DEFAULT_PLAN on failure.

    target_format（如 "9:16"）来自项目设置：既写进规划输入让 LLM 按竖屏排镜，
    也在出口强制覆盖 plan.format——LLM 或 DEFAULT_PLAN 默认 16:9 时不得违逆用户画幅。
    非白名单取值（含 None）视为未指定。
    """
    if target_format not in {"16:9", "9:16", "1:1"}:
        target_format = None
    user_input = ""
    if source_url:
        user_input += f"Source URL: {source_url}\n"
    if user_prompt:
        user_input += f"User request: {user_prompt}\n"
    if target_format:
        user_input += f"Target format: {target_format}\n"
    if not user_input:
        user_input = "Create a short generic marketing video for ClipWorks."

    try:
        # Short timeout + no retries: planning is an enhancement with a
        # deterministic fallback, so a slow model must not freeze the pipeline.
        client = KimiClient(timeout=90, max_retries=0)
        result = client.chat_completion_json(
            system_prompt=PLAN_VIDEO,
            user_prompt=user_input,
            max_retries=0,
        )
        if result and "title" in result and "scenes" in result:
            logger.info("Video plan generated: %s", result.get("title"))
            if target_format:
                result["format"] = target_format
            return _normalize_plan(result)
    except Exception as exc:
        logger.error("plan_video failed, using fallback plan: %s", exc)

    plan = DEFAULT_PLAN.copy()
    if target_format:
        plan["format"] = target_format
    return plan
