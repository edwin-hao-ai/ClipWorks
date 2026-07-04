import json
import logging
from typing import Optional

from .llm import KimiClient
from .prompts import BUILD_COMPOSITION

logger = logging.getLogger(__name__)


def _format_from_plan(plan: dict) -> str:
    fmt = plan.get("format", "16:9")
    return fmt if fmt in {"16:9", "9:16", "1:1"} else "16:9"


def _dimensions(format_str: str) -> tuple[int, int]:
    return {
        "16:9": (1920, 1080),
        "9:16": (1080, 1920),
        "1:1": (1080, 1080),
    }.get(format_str, (1920, 1080))


def _fallback_composition(plan: dict) -> dict:
    width, height = _dimensions(_format_from_plan(plan))
    duration = plan.get("duration", 20)
    scenes = plan.get("scenes", [])
    if not scenes:
        scenes = [
            {"start": 0, "duration": duration, "description": "Full video", "text": plan.get("title", "ClipWorks")}
        ]

    text_clips = []
    visual_clips = []
    for scene in scenes:
        start = scene.get("start", 0)
        dur = scene.get("duration", 5)
        text = scene.get("text", "")
        visual = scene.get("visual", "")

        visual_clips.append({
            "start_time": start,
            "duration": dur,
            "position": {"x": 0, "y": 0, "width": width, "height": height},
            "style": {"background": "linear-gradient(135deg, #1a1a2e, #16213e)"},
            "text_content": visual,
        })
        if text:
            text_clips.append({
                "start_time": start,
                "duration": dur,
                "position": {"x": width * 0.1, "y": height * 0.4, "width": width * 0.8, "height": height * 0.2},
                "style": {"fontSize": height * 0.08, "color": "#ffffff", "textAlign": "center"},
                "text_content": text,
            })

    return {
        "width": width,
        "height": height,
        "duration": duration,
        "fps": 30,
        "metadata": {"title": plan.get("title", "ClipWorks Video"), "hook": plan.get("hook", ""), "plan": plan},
        "tracks": [
            {"type": "video", "index": 0, "name": "画面", "clips": visual_clips},
            {"type": "text", "index": 1, "name": "字幕", "clips": text_clips},
        ],
    }


def build_composition(video_plan: dict) -> dict:
    """Call Kimi to build a Composition JSON. Falls back to a deterministic composition."""
    prompt = json.dumps(video_plan, ensure_ascii=False, indent=2)
    try:
        client = KimiClient()
        result = client.chat_completion_json(
            system_prompt=BUILD_COMPOSITION,
            user_prompt=prompt,
        )
        if result and "tracks" in result and "width" in result:
            logger.info("Composition generated with %d tracks", len(result.get("tracks", [])))
            return result
    except Exception as exc:
        logger.error("build_composition failed, using fallback: %s", exc)

    return _fallback_composition(video_plan)
