import json
import logging
from typing import Optional

from .llm import KimiClient
from .prompts import MODIFY_VIDEO

logger = logging.getLogger(__name__)


def _fallback_modify(composition: dict, user_message: str, scene_id: Optional[str] = None) -> dict:
    """Deterministic fallback when LLM is unavailable."""
    modified = json.loads(json.dumps(composition))
    message_lower = user_message.lower()

    if scene_id:
        # Apply a targeted change to the scene if it exists
        for track in modified.get("tracks", []):
            for clip in track.get("clips", []):
                if clip.get("scene_id") == scene_id or clip.get("id") == scene_id:
                    if "红" in user_message or "red" in message_lower:
                        clip.setdefault("style", {})["color"] = "#ef4444"
                    if "大" in user_message or "big" in message_lower:
                        clip.setdefault("style", {})["fontSize"] = 96
                    if "短" in user_message or "short" in message_lower:
                        clip["duration"] = max(1, clip.get("duration", 5) - 2)
                    return modified

    # Global changes
    if "短" in user_message or "short" in message_lower:
        modified["duration"] = max(5, modified.get("duration", 30) // 2)
    if "红" in user_message or "red" in message_lower:
        for track in modified.get("tracks", []):
            for clip in track.get("clips", []):
                clip.setdefault("style", {})["color"] = "#ef4444"
    return modified


def modify_video(composition: dict, user_message: str, scene_id: Optional[str] = None) -> dict:
    """Modify composition based on natural language instruction."""
    prompt = json.dumps({
        "composition": composition,
        "user_message": user_message,
        "scene_id": scene_id,
    }, ensure_ascii=False, indent=2)

    try:
        client = KimiClient()
        result = client.chat_completion_json(
            system_prompt=MODIFY_VIDEO,
            user_prompt=prompt,
        )
        if result:
            # The current MODIFY_VIDEO prompt asks for {"reply", "composition"}.
            # Also accept a bare composition JSON for forward compatibility.
            if "composition" in result:
                logger.info("Composition modified via LLM")
                return result["composition"]
            if "tracks" in result:
                logger.info("Composition modified via LLM")
                return result
    except Exception as exc:
        logger.error("modify_video LLM failed, using fallback: %s", exc)

    return _fallback_modify(composition, user_message, scene_id)
