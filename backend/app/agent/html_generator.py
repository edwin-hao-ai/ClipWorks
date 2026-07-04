import json
import logging
from typing import Optional

from .llm import KimiClient
from .prompts import GENERATE_HTML

logger = logging.getLogger(__name__)


def _escape_html(text: Optional[str]) -> str:
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _fallback_html(composition: dict, assets: dict) -> str:
    """Generate a deterministic HyperFrames-compatible HTML composition."""
    width = composition.get("width", 1920)
    height = composition.get("height", 1080)
    duration = composition.get("duration", 20)
    fps = composition.get("fps", 30)
    tracks = composition.get("tracks", [])
    title = composition.get("metadata", {}).get("title", "ClipWorks Video")

    bg_image = assets.get("background_image")
    logo_image = assets.get("logo")

    scenes_html = []
    styles_html = []
    scene_index = 0

    for track in tracks:
        for clip in track.get("clips", []):
            start = clip.get("start_time", 0)
            dur = clip.get("duration", 5)
            end = start + dur
            pos = clip.get("position", {})
            x = pos.get("x", 0)
            y = pos.get("y", 0)
            w = pos.get("width", width)
            h = pos.get("height", height)
            style = clip.get("style", {})
            text = clip.get("text_content", "")

            cls = f"scene scene-{scene_index}"
            styles_html.append(
                f"""
                .scene-{scene_index} {{
                    left: {x}px;
                    top: {y}px;
                    width: {w}px;
                    height: {h}px;
                    animation: sceneFade {duration}s linear {start}s forwards;
                    opacity: 0;
                    z-index: {scene_index};
                }}
                """
            )

            inner = ""
            if track.get("type") == "text" and text:
                font_size = style.get("fontSize", height * 0.06)
                color = style.get("color", "#ffffff")
                bg = style.get("background", "transparent")
                inner = f'<div class="text-box" style="font-size:{font_size}px;color:{color};background:{bg};text-align:center;">{_escape_html(text)}</div>'
            elif track.get("type") in {"video", "image"}:
                bg = style.get("background", "linear-gradient(135deg, #1a1a2e, #16213e)")
                img_tag = ""
                if bg_image:
                    img_tag = f'<img src="{bg_image}" class="bg-image" alt="background" />'
                elif logo_image:
                    img_tag = f'<img src="{logo_image}" class="logo-image" alt="logo" />'
                inner = f'<div class="visual-box" style="background:{bg};">{img_tag}</div>'

            if inner:
                scenes_html.append(f'<div class="{cls}">{inner}</div>')
                scene_index += 1

    scenes = "\n".join(scenes_html)
    keyframes = "\n".join(styles_html)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_escape_html(title)}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #000; overflow: hidden; }}
  #stage {{
    position: relative;
    width: {width}px;
    height: {height}px;
    background: #0f0f1a;
    overflow: hidden;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }}
  .scene {{
    position: absolute;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }}
  .text-box {{
    width: 100%;
    padding: 20px;
    font-weight: 700;
    text-shadow: 0 2px 10px rgba(0,0,0,0.5);
    line-height: 1.2;
  }}
  .visual-box {{
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .bg-image, .logo-image {{
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
  }}
  @keyframes sceneFade {{
    0% {{ opacity: 0; transform: scale(0.98); }}
    5% {{ opacity: 1; transform: scale(1); }}
    95% {{ opacity: 1; transform: scale(1); }}
    100% {{ opacity: 0; transform: scale(1.02); }}
  }}
  {keyframes}
</style>
</head>
<body>
<div id="stage">
  {scenes}
</div>
<script>
  // HyperFrames rendering hint: total duration and FPS
  window.hyperframesDuration = {duration};
  window.hyperframesFps = {fps};
</script>
</body>
</html>"""


def generate_html(composition: dict, assets: Optional[dict] = None) -> str:
    """Call Kimi to generate HyperFrames HTML. Falls back to deterministic HTML."""
    assets = assets or {}
    prompt = f"Composition:\n{json.dumps(composition, ensure_ascii=False, indent=2)}\n\nAssets:\n{json.dumps(assets, ensure_ascii=False, indent=2)}"
    try:
        client = KimiClient()
        result = client.chat_completion(
            system_prompt=GENERATE_HTML,
            user_prompt=prompt,
            json_mode=False,
        )
        if result and "<html" in result:
            logger.info("HTML generated via Kimi (%d chars)", len(result))
            return result.strip()
    except Exception as exc:
        logger.error("generate_html failed, using fallback: %s", exc)

    return _fallback_html(composition, assets)
