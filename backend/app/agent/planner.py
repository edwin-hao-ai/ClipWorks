import json
import logging
from typing import Optional

from .llm import KimiClient
from .prompts import PLAN_VIDEO

logger = logging.getLogger(__name__)

DEFAULT_PLAN = {
    "title": "ClipWorks Video",
    "hook": "Discover something amazing with ClipWorks.",
    "scenes": [
        {
            "start": 0,
            "duration": 5,
            "description": "Opening title card with brand name",
            "visual": "gradient background",
            "text": "ClipWorks",
        },
        {
            "start": 5,
            "duration": 10,
            "description": "Feature highlight scene",
            "visual": "abstract shapes",
            "text": "AI-powered video creation",
        },
        {
            "start": 15,
            "duration": 5,
            "description": "Call to action",
            "visual": "brand background",
            "text": "Try it now",
        },
    ],
    "format": "16:9",
    "duration": 20,
    "assets_needed": ["gradient background", "brand logo placeholder"],
}


def plan_video(source_url: Optional[str], user_prompt: Optional[str]) -> dict:
    """Call Kimi to plan a video. Falls back to DEFAULT_PLAN on failure."""
    user_input = ""
    if source_url:
        user_input += f"Source URL: {source_url}\n"
    if user_prompt:
        user_input += f"User request: {user_prompt}\n"
    if not user_input:
        user_input = "Create a short generic marketing video for ClipWorks."

    try:
        client = KimiClient()
        result = client.chat_completion_json(
            system_prompt=PLAN_VIDEO,
            user_prompt=user_input,
        )
        if result and "title" in result and "scenes" in result:
            logger.info("Video plan generated: %s", result.get("title"))
            return result
    except Exception as exc:
        logger.error("plan_video failed, using fallback plan: %s", exc)

    return DEFAULT_PLAN.copy()
