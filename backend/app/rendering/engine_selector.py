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
