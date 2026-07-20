import json
import logging
from typing import Optional

from .llm import KimiClient
from .prompts import GENERATE_HTML, STORYBOARD

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
    per_clip_images = assets.get("images") or {}

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
                # 优先使用逐镜绑定的素材图（assets["images"][asset_id]），
                # 其次才是全局背景/Logo，再不行才退回渐变——保证真实素材进画面。
                clip_img = per_clip_images.get(clip.get("asset_id")) if clip.get("asset_id") else None
                img_tag = ""
                if clip_img:
                    img_tag = f'<img src="{clip_img}" class="bg-image kb" alt="scene" />'
                elif bg_image:
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
    width: 100%;
    height: 100%;
    max-width: 100%;
    max-height: 100%;
    object-fit: cover;
  }}
  .logo-image {{ object-fit: contain; }}
  /* Ken Burns 缓慢推镜，让静态素材图也有电影感动效 */
  .kb {{ animation: kenburns 12s ease-in-out infinite alternate; transform-origin: center; }}
  @keyframes kenburns {{
    0% {{ transform: scale(1); }}
    100% {{ transform: scale(1.08); }}
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


def _palette_from_visual(visual: str) -> str:
    """根据中文视觉词给一个确定的深色渐变（无图时的氛围底色）。"""
    v = (visual or "").lower()
    if any(k in v for k in ("科技", "粒子", "hud", "tech", "蓝")):
        return "radial-gradient(ellipse at center, #0a1a2a 0%, #020203 100%)"
    if any(k in v for k in ("暖", "日出", "橙", "sun", "warm")):
        return "radial-gradient(ellipse at center, #3a1c0a 0%, #120604 100%)"
    if any(k in v for k in ("自然", "绿", "forest", "leaf")):
        return "radial-gradient(ellipse at center, #0c2a1a 0%, #020a04 100%)"
    if any(k in v for k in ("奢", "金", "premium", "gold")):
        return "radial-gradient(ellipse at center, #2a230a 0%, #0a0802 100%)"
    return "linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)"


def _validate_storyboard(data, duration: float) -> Optional[list]:
    """Schema 校验 AI 分镜。返回清洗后的 scenes 列表；不合法返回 None。"""
    if not isinstance(data, dict):
        return None
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return None
    cleaned = []
    for s in scenes:
        if not isinstance(s, dict):
            return None
        try:
            start = float(s.get("start", 0))
            dur = float(s.get("duration", 0))
        except (TypeError, ValueError):
            return None
        if dur <= 0 or start < 0:
            return None
        headline = str(s.get("headline") or "").strip()
        try:
            image_index = int(s.get("image_index", -1))
        except (TypeError, ValueError):
            image_index = -1
        cleaned.append(
            {
                "start": max(0.0, start),
                "duration": min(dur, max(0.5, duration - start) if duration else dur),
                "headline": headline,
                "subtext": str(s.get("subtext") or "").strip(),
                "visual": str(s.get("visual") or ""),
                "image_index": image_index,
                # 富方案字段（旁白/转场/角标/镜头类型），缺省给安全默认
                "narration": str(s.get("narration") or "").strip(),
                "visual_type": str(s.get("visual_type") or "text").strip(),
                "transition": str(s.get("transition") or "fade").strip(),
                "lower_third": str(s.get("lower_third") or "").strip(),
            }
        )
    cleaned.sort(key=lambda x: x["start"])
    return cleaned or None


def _storyboard_from_composition(composition: dict, image_ids: list) -> list:
    """无 AI 时，从现有时间线确定性地构造分镜（与 AI 分镜共用同一套渲染模板）。"""
    scenes: list = []
    # 先收集视觉轨（按时间）拿到每段 visual/图，再叠上文本轨文案。
    visual_clips: list = []
    text_clips: list = []
    for track in composition.get("tracks", []) or []:
        ttype = track.get("type")
        for clip in track.get("clips", []) or []:
            style = clip.get("style") or {}
            item = {
                "start": float(clip.get("start_time", 0) or 0),
                "duration": float(clip.get("duration", 5) or 5),
                "text": (clip.get("text_content") or "").strip(),
                "visual": style.get("visual", "") or (clip.get("text_content") or ""),
                # 富方案字段沿时间线透传到分镜
                "transition": style.get("transition", "fade"),
                "lower_third": style.get("lower_third", ""),
                "narration": style.get("narration", ""),
                "visual_type": style.get("visual_type", "text"),
            }
            if ttype == "text":
                text_clips.append(item)
            elif ttype in {"video", "image", "overlay"}:
                visual_clips.append(item)
    # 以文本轨为主时间线（卖点文案），找不到文本时退到视觉轨。
    anchors = text_clips or visual_clips
    anchors.sort(key=lambda x: x["start"])
    for i, a in enumerate(anchors[:8]):
        img_idx = (i % len(image_ids)) if image_ids else -1
        # 找同时间段最近的视觉描述
        visual = a["visual"]
        for v in visual_clips:
            if abs(v["start"] - a["start"]) < 0.5 and v["visual"]:
                visual = v["visual"]
                break
        scenes.append(
            {
                "start": a["start"],
                "duration": a["duration"],
                "headline": a["text"] or (visual[:14] if visual else "ClipWorks"),
                "subtext": "",
                "visual": visual,
                "image_index": img_idx,
                "transition": a.get("transition", "fade"),
                "lower_third": a.get("lower_third", ""),
                "narration": a.get("narration", ""),
                "visual_type": a.get("visual_type", "text"),
            }
        )
    return scenes


def _scene_theme(visual: str) -> str:
    """根据视觉描述返回场景主题类名，用于定制 CSS 变量和动画。"""
    v = (visual or "").lower()
    if any(k in v for k in ("代码", "数据", "git", "tech", "hud", "科技", "编程", "markdown", "编辑器", "搜索", "ai", "问答", "对话", "chat", "智能")):
        return "theme-tech"
    if any(k in v for k in ("火箭", "起飞", "发布", "速度", "rocket", "launch", "fast")):
        return "theme-speed"
    if any(k in v for k in ("混乱", "文档", "文件", "堆叠", "chaos", "files", "mess")):
        return "theme-chaos"
    if any(k in v for k in ("粒子", "光", "glow", "neon", "闪耀", "星空", "宇宙", "premium", "奢华", "金")):
        return "theme-glow"
    if any(k in v for k in ("暖", "日出", "橙", "sun", "warm", "自然", "绿", "forest")):
        return "theme-warm"
    return "theme-default"


def _decor_for_visual(visual: str, brand_color: str, width: int, height: int, scene_index: int) -> str:
    """根据 visual 描述生成丰富的场景装饰 HTML（CSS 动画，性能友好）。"""
    v = (visual or "").lower()
    seed = scene_index * 997
    theme = _scene_theme(visual)
    parts = [f'<div class="ambient-glow" style="--brand:{brand_color}"></div>']

    if theme == "theme-tech" or any(k in v for k in ("代码", "数据", "tech", "科技", "编辑器", "markdown")):
        # 网格 + 代码雨 + 浮动终端窗口
        cells = ""
        for r in range(24):
            for c in range(48):
                if ((r * 48 + c + seed) % 5) == 0:
                    cells += f"<span style='left:{c*2.08}%;top:{r*4.16}%;animation-delay:{(r+c)*0.04}s'></span>"
        parts.append(f'<div class="matrix" style="--brand:{brand_color}">{cells}</div>')
        parts.append(f'<div class="hud-ring" style="--brand:{brand_color}"></div>')
        parts.append('<div class="scanline"></div>')
        # 浮动小终端窗口
        terminals = ""
        for i in range(5):
            x = 6 + ((i * 73 + seed) % 60)
            y = 10 + ((i * 47 + seed) % 50)
            delay = i * 0.4
            terminals += f"<div class='term-float' style='left:{x}%;top:{y}%;animation-delay:{delay}s'><div class='term-bar'></div><div class='term-line'></div><div class='term-line short'></div></div>"
        parts.append(f'<div class="terminals">{terminals}</div>')

    elif theme == "theme-speed" or any(k in v for k in ("火箭", "发布", "速度", "launch")):
        # 速度线 + 中心冲击环
        streaks = ""
        for i in range(20):
            x = ((i * 31 + seed) % 100)
            delay = (i * 0.06) % 0.8
            streaks += f"<span style='left:{x}%;animation-delay:{delay}s'></span>"
        parts.append(f'<div class="speed-lines">{streaks}</div>')
        parts.append(f'<div class="shockwave" style="--brand:{brand_color}"></div>')

    elif theme == "theme-chaos" or any(k in v for k in ("混乱", "文档", "文件", "堆叠", "chaos")):
        docs = ""
        for i in range(22):
            x = 5 + ((i * 37 + seed) % 85)
            y = 5 + ((i * 29 + seed) % 75)
            rot = -15 + (i % 9) * 4
            delay = (i * 0.07) % 1.5
            docs += f"<span style='left:{x}%;top:{y}%;--rot:{rot}deg;animation-delay:{delay}s'></span>"
        parts.append(f'<div class="floating-docs">{docs}</div>')

    elif theme == "theme-glow":
        particles = ""
        for i in range(50):
            x = ((i * 113 + seed) % 100)
            y = ((i * 89 + seed) % 100)
            delay = (i * 0.1) % 3
            size = 2 + (i % 6)
            particles += f"<span style='left:{x}%;top:{y}%;width:{size}px;height:{size}px;animation-delay:{delay}s'></span>"
        parts.append(f'<div class="particles" style="--brand:{brand_color}">{particles}</div>')
        parts.append(f'<div class="lens-flare" style="--brand:{brand_color}"></div>')

    elif theme == "theme-warm":
        # 柔和漂浮光斑
        orbs = ""
        for i in range(16):
            x = ((i * 67 + seed) % 100)
            y = ((i * 43 + seed) % 100)
            delay = (i * 0.2) % 4
            size = 40 + (i % 60)
            orbs += f"<span style='left:{x}%;top:{y}%;width:{size}px;height:{size}px;animation-delay:{delay}s'></span>"
        parts.append(f'<div class="warm-orbs">{orbs}</div>')

    else:
        # 默认：极简漂浮粒子 +  subtle 光晕
        particles = ""
        for i in range(24):
            x = ((i * 131 + seed) % 100)
            y = ((i * 97 + seed) % 100)
            delay = (i * 0.12) % 3
            size = 2 + (i % 4)
            particles += f"<span style='left:{x}%;top:{y}%;width:{size}px;height:{size}px;animation-delay:{delay}s'></span>"
        parts.append(f'<div class="particles" style="--brand:{brand_color}">{particles}</div>')

    return "".join(parts)


def _transition_anim(transition: str, duration: float, start: float) -> str:
    """把 transition 字段映射成更丰富的 CSS 入场动画。"""
    t = (transition or "fade").lower()
    anims = {
        "fade": "sceneFade",
        "slide": "sceneSlide",
        "zoom": "sceneZoom",
        "glitch": "sceneGlitch",
        "wipe": "sceneWipe",
        "ripple": "sceneRipple",
        "mask": "sceneMask",
    }
    return anims.get(t, "sceneFade")


def _render_storyboard(scenes: list, composition: dict, assets: dict) -> str:
    """把分镜渲染成自包含、高视觉冲击力的 HTML。"""
    width = composition.get("width", 1920)
    height = composition.get("height", 1080)
    duration = composition.get("duration", 20) or 20
    fps = composition.get("fps", 30) or 30
    title = (composition.get("metadata") or {}).get("title", "ClipWorks Video")
    brand_color = (composition.get("metadata") or {}).get("brand_color") or "#00E5FF"

    images: dict = assets.get("images") or {}
    image_ids: list = assets.get("image_ids") or list(images.keys())
    bg_image = assets.get("background_image")

    scenes_html: list = []
    styles_html: list = []
    for i, s in enumerate(scenes):
        start = s["start"]
        img_url = None
        if 0 <= s["image_index"] < len(image_ids):
            img_url = images.get(image_ids[s["image_index"]])
        if not img_url:
            img_url = bg_image
        bg_css = _palette_from_visual(s["visual"])
        img_tag = f'<img src="{img_url}" class="bg-image kb" alt="scene" />' if img_url else ""
        sub = f'<div class="sub">{_escape_html(s["subtext"])}</div>' if s["subtext"] else ""
        anim = _transition_anim(s.get("transition"), duration, start)
        lt = s.get("lower_third") or ""
        lt_html = (
            f'<div class="lower-third" style="--brand:{brand_color};">'
            f'<span class="lt-pill"></span>{_escape_html(lt)}</div>'
            if lt
            else ""
        )
        decor = _decor_for_visual(s.get("visual") or s.get("headline") or "", brand_color, width, height, i)
        theme = _scene_theme(s.get("visual") or "")
        visual_text = _escape_html(s.get("visual") or "")[:60]
        visual_hint_html = f'<div class="visual-hint">{visual_text}</div>' if visual_text else ""

        scenes_html.append(
            f'<div class="scene scene-{i} {theme}" style="background:{bg_css};" data-anim="{anim}">'
            f'{decor}'
            f'{img_tag}'
            f'<div class="scrim"></div>'
            f'<div class="copy">'
            f'<div class="headline" data-text="{_escape_html(s["headline"])}">{_escape_html(s["headline"])}</div>'
            f'{sub}'
            f'{visual_hint_html}'
            f'</div>'
            f'{lt_html}'
            f'</div>'
        )
        styles_html.append(
            f".scene-{i} {{ animation: {anim} {duration}s cubic-bezier(0.22,0.61,0.36,1) {start}s forwards; z-index: {i}; }}"
        )

    scenes_block = "\n  ".join(scenes_html)
    styles_block = "\n  ".join(styles_html)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_escape_html(title)}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #000; overflow: hidden; }}
  :root {{
    --brand: {brand_color};
    --brand-dim: {brand_color}44;
    --bg-dark: #050510;
  }}
  #stage {{
    position: relative; width: {width}px; height: {height}px;
    overflow: hidden; background: var(--bg-dark);
    font-family: 'Noto Sans CJK SC','PingFang SC','Microsoft YaHei',sans-serif;
  }}

  /* 场景基础 */
  .scene {{ position: absolute; inset: 0; overflow: hidden; opacity: 0; }}
  .bg-image {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
  .kb {{ animation: kenburns 10s ease-in-out infinite alternate; transform-origin: center; }}
  .scrim {{ position: absolute; inset: 0;
    background: radial-gradient(ellipse at center, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0.65) 100%);
    mix-blend-mode: multiply; }}

  /* 文案层 */
  .copy {{ position: absolute; inset: 0; display: flex; flex-direction: column;
    align-items: center; justify-content: center; padding: {int(height*0.08)}px; text-align: center; z-index: 20; }}
  .headline {{ color: #fff; font-weight: 900; line-height: 1.15;
    font-size: {int(height*0.082)}px;
    opacity: 0; animation: titleReveal 1s cubic-bezier(0.22,0.61,0.36,1) 0.2s forwards;
    text-shadow: 0 6px 32px rgba(0,0,0,0.55), 0 0 60px var(--brand-dim); }}
  .headline::after {{
    content: attr(data-text);
    position: absolute; left: 0; top: 0; width: 100%; height: 100%;
    color: transparent; -webkit-text-stroke: 1.5px rgba(255,255,255,0.18);
    z-index: -1; animation: titleStroke 3s ease-in-out infinite alternate; }}
  .sub {{ margin-top: {int(height*0.026)}px; color: #e8eaf6; font-weight: 600;
    font-size: {int(height*0.042)}px;
    opacity: 0; animation: subReveal 0.9s cubic-bezier(0.22,0.61,0.36,1) 0.55s forwards;
    text-shadow: 0 3px 18px rgba(0,0,0,0.5); }}
  .visual-hint {{ margin-top: {int(height*0.018)}px; color: rgba(255,255,255,0.55);
    font-size: {int(height*0.022)}px; font-weight: 500; letter-spacing: 0.05em;
    opacity: 0; animation: subReveal 0.8s ease-out 0.9s forwards; }}

  /* Lower third */
  .lower-third {{ position: absolute; left: {int(width*0.04)}px; bottom: {int(height*0.07)}px;
    display: flex; align-items: center; gap: {int(width*0.012)}px;
    padding: {int(height*0.014)}px {int(width*0.022)}px;
    background: rgba(0,0,0,0.35); backdrop-filter: blur(8px);
    border: 1px solid rgba(255,255,255,0.12); border-radius: 999px;
    color: #fff; font-weight: 700; font-size: {int(height*0.026)}px; z-index: 50;
    opacity: 0; animation: ltReveal 0.7s cubic-bezier(0.22,0.61,0.36,1) 0.85s forwards; }}
  .lt-pill {{ width: {max(6, int(width*0.006))}px; height: {int(height*0.026)}px; border-radius: 999px; background: var(--brand); box-shadow: 0 0 12px var(--brand); }}

  /* 全局品牌点缀 */
  .brand-bar {{ position: absolute; left: 0; right: 0; bottom: 0; height: {int(height*0.012)}px;
    background: var(--brand); box-shadow: 0 0 32px var(--brand); z-index: 9999; }}
  .brand-chip {{ position: absolute; left: {int(width*0.04)}px; top: {int(height*0.04)}px;
    width: {int(width*0.10)}px; height: {int(height*0.008)}px; border-radius: 999px;
    background: var(--brand); opacity: 0.92; z-index: 9999; box-shadow: 0 0 16px var(--brand); }}

  /* Keyframes */
  @keyframes kenburns {{ 0% {{ transform: scale(1) translate(0,0); }} 100% {{ transform: scale(1.1) translate(-1%,-1%); }} }}
  @keyframes titleReveal {{
    0% {{ opacity: 0; transform: translateY(45px) scale(0.96); filter: blur(12px); letter-spacing: 0.08em; }}
    100% {{ opacity: 1; transform: translateY(0) scale(1); filter: blur(0); letter-spacing: normal; }}
  }}
  @keyframes titleStroke {{ 0% {{ opacity: 0.3; transform: translate(-2px,-2px); }} 100% {{ opacity: 0.7; transform: translate(2px,2px); }} }}
  @keyframes subReveal {{ 0% {{ opacity: 0; transform: translateY(24px); filter: blur(6px); }} 100% {{ opacity: 1; transform: translateY(0); filter: blur(0); }} }}
  @keyframes ltReveal {{ 0% {{ opacity: 0; transform: translateX(-30px); }} 100% {{ opacity: 1; transform: translateX(0); }} }}

  /* 场景转场 */
  @keyframes sceneFade {{ 0% {{ opacity: 0; }} 3% {{ opacity: 1; }} 97% {{ opacity: 1; }} 100% {{ opacity: 0; }} }}
  @keyframes sceneSlide {{ 0% {{ opacity: 0; transform: translateX(10%) scale(1.02); }} 4% {{ opacity: 1; transform: translateX(0) scale(1); }} 96% {{ opacity: 1; transform: translateX(0) scale(1); }} 100% {{ opacity: 0; transform: translateX(-8%) scale(1.02); }} }}
  @keyframes sceneZoom {{ 0% {{ opacity: 0; transform: scale(1.18); }} 5% {{ opacity: 1; transform: scale(1); }} 95% {{ opacity: 1; transform: scale(1); }} 100% {{ opacity: 0; transform: scale(0.92); }} }}
  @keyframes sceneGlitch {{ 0% {{ opacity: 0; clip-path: inset(0 100% 0 0); }} 3% {{ opacity: 1; clip-path: inset(0 0 0 0); }} 97% {{ opacity: 1; clip-path: inset(0 0 0 0); }} 100% {{ opacity: 0; clip-path: inset(0 0 0 100%); }} }}
  @keyframes sceneWipe {{ 0% {{ opacity: 1; clip-path: polygon(0 0, 0 0, 0 100%, 0 100%); }} 6% {{ clip-path: polygon(0 0, 100% 0, 100% 100%, 0 100%); }} 97% {{ clip-path: polygon(0 0, 100% 0, 100% 100%, 0 100%); }} 100% {{ opacity: 0; clip-path: polygon(100% 0, 100% 0, 100% 100%, 100% 100%); }} }}
  @keyframes sceneRipple {{ 0% {{ opacity: 0; transform: scale(1.1); filter: blur(20px); }} 5% {{ opacity: 1; transform: scale(1); filter: blur(0); }} 95% {{ opacity: 1; }} 100% {{ opacity: 0; transform: scale(0.95); filter: blur(12px); }} }}
  @keyframes sceneMask {{ 0% {{ opacity: 1; clip-path: circle(0% at 50% 50%); }} 6% {{ clip-path: circle(150% at 50% 50%); }} 97% {{ clip-path: circle(150% at 50% 50%); }} 100% {{ opacity: 0; clip-path: circle(0% at 50% 50%); }} }}

  /* 装饰元素通用 */
  .ambient-glow {{ position: absolute; inset: 0; z-index: 0; pointer-events: none;
    background: radial-gradient(circle at 30% 70%, var(--brand-dim) 0%, transparent 55%);
    opacity: 0.6; animation: ambientPulse 6s ease-in-out infinite alternate; }}
  @keyframes ambientPulse {{ 0% {{ opacity: 0.4; transform: scale(1); }} 100% {{ opacity: 0.7; transform: scale(1.08); }} }}

  /* Tech: matrix + hud */
  .matrix {{ position: absolute; inset: 0; z-index: 1; overflow: hidden; opacity: 0.35; pointer-events: none; }}
  .matrix span {{ position: absolute; width: 2.08%; height: 4.16%;
    background: linear-gradient(180deg, transparent, var(--brand), transparent);
    opacity: 0; animation: matrixDrop 2.2s linear infinite; }}
  @keyframes matrixDrop {{ 0% {{ opacity: 0; transform: translateY(-40px); }} 15% {{ opacity: 0.7; }} 100% {{ opacity: 0; transform: translateY(60px); }} }}

  .hud-ring {{ position: absolute; left: 50%; top: 50%; width: {int(width*1.3)}px; height: {int(width*1.3)}px;
    transform: translate(-50%,-50%); border: 1px solid rgba(255,255,255,0.08); border-radius: 50%;
    z-index: 1; opacity: 0; animation: hudPulse 2.5s ease-in-out 0.2s forwards; pointer-events: none; }}
  .hud-ring::before {{ content: ''; position: absolute; inset: 10%; border: 1px dashed rgba(255,255,255,0.14); border-radius: 50%; animation: hudSpin 16s linear infinite; }}
  .hud-ring::after {{ content: ''; position: absolute; inset: 22%; border: 1px solid rgba(255,255,255,0.06); border-radius: 50%; animation: hudSpin 24s linear infinite reverse; }}
  @keyframes hudPulse {{ 0% {{ opacity: 0; transform: translate(-50%,-50%) scale(0.85); }} 100% {{ opacity: 1; transform: translate(-50%,-50%) scale(1); }} }}
  @keyframes hudSpin {{ 100% {{ transform: rotate(360deg); }} }}

  .scanline {{ position: absolute; inset: 0; z-index: 2; pointer-events: none;
    background: repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,0,0,0.18) 4px);
    opacity: 0.4; animation: scanMove 5s linear infinite; mix-blend-mode: overlay; }}
  @keyframes scanMove {{ 0% {{ background-position: 0 0; }} 100% {{ background-position: 0 48px; }} }}

  .terminals {{ position: absolute; inset: 0; z-index: 3; pointer-events: none; }}
  .term-float {{ position: absolute; width: {int(width*0.12)}px; padding: {int(height*0.012)}px;
    background: rgba(0,0,0,0.35); border: 1px solid rgba(255,255,255,0.12); border-radius: 6px;
    backdrop-filter: blur(4px); opacity: 0; animation: termFloat 4s ease-in-out infinite alternate; }}
  .term-bar {{ height: {int(height*0.008)}px; background: rgba(255,255,255,0.15); border-radius: 999px; margin-bottom: {int(height*0.008)}px; }}
  .term-line {{ height: {int(height*0.005)}px; background: var(--brand); border-radius: 999px; margin-bottom: {int(height*0.005)}px; opacity: 0.7; }}
  .term-line.short {{ width: 60%; }}
  @keyframes termFloat {{ 0% {{ opacity: 0; transform: translateY(15px); }} 20% {{ opacity: 0.8; }} 100% {{ opacity: 0.5; transform: translateY(-10px); }} }}

  /* Speed */
  .speed-lines {{ position: absolute; inset: 0; z-index: 1; overflow: hidden; pointer-events: none; }}
  .speed-lines span {{ position: absolute; top: -20%; width: 2px; height: 140%;
    background: linear-gradient(180deg, transparent, rgba(255,255,255,0.2), transparent);
    animation: speedLine 0.8s linear infinite; }}
  @keyframes speedLine {{ 0% {{ transform: translateY(-100%); }} 100% {{ transform: translateY(100%); }} }}

  .shockwave {{ position: absolute; left: 50%; top: 50%; width: 200px; height: 200px;
    transform: translate(-50%,-50%); border: 2px solid var(--brand); border-radius: 50%;
    z-index: 1; opacity: 0.6; animation: shockwave 2.5s ease-out infinite; pointer-events: none; }}
  @keyframes shockwave {{ 0% {{ transform: translate(-50%,-50%) scale(0.4); opacity: 0.7; }} 100% {{ transform: translate(-50%,-50%) scale(3.5); opacity: 0; }} }}

  /* Chaos */
  .floating-docs {{ position: absolute; inset: 0; z-index: 1; overflow: hidden; pointer-events: none; }}
  .floating-docs span {{ position: absolute; width: {int(width*0.04)}px; height: {int(width*0.055)}px; border-radius: 4px;
    background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.16);
    animation: docFloat 3.5s ease-in-out infinite alternate; }}
  @keyframes docFloat {{ 0% {{ opacity: 0.35; transform: translateY(0) rotate(var(--rot,0deg)); }} 50% {{ opacity: 0.8; }} 100% {{ opacity: 0.45; transform: translateY(-22px) rotate(calc(var(--rot,0deg) + 5deg)); }} }}

  /* Glow / Particles */
  .particles {{ position: absolute; inset: 0; z-index: 1; overflow: hidden; pointer-events: none; }}
  .particles span {{ position: absolute; background: var(--brand); border-radius: 50%;
    opacity: 0; box-shadow: 0 0 10px var(--brand); animation: particleFloat 3.5s ease-in-out infinite; }}
  @keyframes particleFloat {{ 0%,100% {{ opacity: 0; transform: translateY(0) scale(0.5); }} 50% {{ opacity: 0.75; transform: translateY(-40px) scale(1.1); }} }}

  .lens-flare {{ position: absolute; left: 70%; top: 30%; width: {int(width*0.25)}px; height: {int(width*0.25)}px;
    background: radial-gradient(circle, var(--brand-dim) 0%, transparent 65%); border-radius: 50%;
    filter: blur(40px); z-index: 0; opacity: 0.5; animation: flareMove 8s ease-in-out infinite alternate; pointer-events: none; }}
  @keyframes flareMove {{ 0% {{ transform: translate(0,0); }} 100% {{ transform: translate(-80px,60px); }} }}

  /* Warm */
  .warm-orbs {{ position: absolute; inset: 0; z-index: 1; overflow: hidden; pointer-events: none; }}
  .warm-orbs span {{ position: absolute; background: radial-gradient(circle, rgba(255,160,80,0.35) 0%, transparent 70%); border-radius: 50%;
    filter: blur(20px); animation: orbFloat 7s ease-in-out infinite alternate; }}
  @keyframes orbFloat {{ 0% {{ opacity: 0.3; transform: translateY(0) scale(1); }} 100% {{ opacity: 0.65; transform: translateY(-50px) scale(1.2); }} }}

  {styles_block}
</style>
</head>
<body>
<div id="stage">
  {scenes_block}
  <div class="brand-bar"></div>
  <div class="brand-chip"></div>
</div>
<script>window.hyperframesDuration = {duration}; window.hyperframesFps = {fps};</script>
</body>
</html>"""


def generate_html(composition: dict, assets: Optional[dict] = None) -> str:
    """结构化分镜 → 模板渲染。

    1) 让 AI 输出紧凑的 storyboard JSON（schema 校验 + 1 次重试），比直接吐整页
       HTML 更快、更稳，显著降低超时回退率。
    2) 校验通过后与本地确定性分镜共用同一套渲染模板，因此无论 AI 是否出场，
       预览 HTML 的质量与结构都一致——AI 不可用只是「分镜来源不同」，不是降级。
    3) 仅当模板渲染本身抛错时才落到最朴素的 _fallback_html（极少触发）。
    """
    assets = assets or {}
    image_ids: list = assets.get("image_ids") or list((assets.get("images") or {}).keys())
    duration = float(composition.get("duration", 0) or 0)

    prompt = (
        "Composition:\n"
        + json.dumps(composition, ensure_ascii=False)
        + "\n\nImage asset ids (image_index 指向下标):\n"
        + json.dumps(image_ids, ensure_ascii=False)
    )
    try:
        # 结构化 JSON 比整页 HTML 短很多，90s 通常足够；保留 1 次重试兜住偶发超时/截断。
        client = KimiClient(timeout=90, max_retries=1)
        raw = client.chat_completion(
            system_prompt=STORYBOARD,
            user_prompt=prompt,
            json_mode=True,
            max_retries=1,
        )
        data = json.loads(raw) if raw else None
        scenes = _validate_storyboard(data, duration)
        if scenes:
            logger.info("HTML storyboard via AI (%d scenes)", len(scenes))
            return _render_storyboard(scenes, composition, assets)
        logger.info("AI storyboard invalid/empty; building storyboard from composition")
    except Exception as exc:
        logger.info("AI storyboard unavailable (%s); building storyboard from composition", exc)

    scenes = _storyboard_from_composition(composition, image_ids)
    if scenes:
        try:
            return _render_storyboard(scenes, composition, assets)
        except Exception as exc:  # noqa: BLE001 - 模板异常才走最朴素兜底
            logger.warning("storyboard render failed, using minimal fallback: %s", exc)

    return _fallback_html(composition, assets)
