import json
import logging
from typing import Optional

from .llm import KimiClient
from .prompts import MODIFY_VIDEO

logger = logging.getLogger(__name__)


def _apply_simple_modification(composition: dict, instruction: str) -> dict:
    """Simple rule-based fallback modifications."""
    modified = json.loads(json.dumps(composition))
    lowered = instruction.lower()

    for track in modified.get("tracks", []):
        for clip in track.get("clips", []):
            style = clip.get("style", {})
            text = clip.get("text_content", "") or ""

            if "red" in lowered or "红色" in lowered:
                style["color"] = "#ff3333"
            if "blue" in lowered or "蓝色" in lowered:
                style["color"] = "#3333ff"
            if "big" in lowered or "bigger" in lowered or "大" in lowered:
                style["fontSize"] = (style.get("fontSize", 48) or 48) * 1.3
            if "small" in lowered or "smaller" in lowered or "小" in lowered:
                style["fontSize"] = (style.get("fontSize", 48) or 48) * 0.8
            if "shorten" in lowered or "缩短" in lowered:
                clip["duration"] = max(1, clip.get("duration", 5) * 0.7)
            if "lengthen" in lowered or "延长" in lowered:
                clip["duration"] = clip.get("duration", 5) * 1.3

            clip["style"] = style

    return modified


def modify_composition(composition: dict, instruction: str) -> dict:
    """Call Kimi to modify a composition. Falls back to simple rule-based edits."""
    prompt = f"Instruction: {instruction}\n\nCurrent composition:\n{json.dumps(composition, ensure_ascii=False, indent=2)}"
    try:
        client = KimiClient()
        result = client.chat_completion_json(
            system_prompt=MODIFY_VIDEO,
            user_prompt=prompt,
        )
        if result and "composition" in result:
            logger.info("Composition modified via Kimi: %s", result.get("reply", ""))
            return {
                "reply": result.get("reply", "Updated the video based on your request."),
                "composition": result["composition"],
            }
    except Exception as exc:
        logger.error("modify_composition failed, using fallback: %s", exc)

    modified = _apply_simple_modification(composition, instruction)
    return {
        "reply": "I applied a quick local adjustment. Connect Kimi for smarter edits.",
        "composition": modified,
    }
