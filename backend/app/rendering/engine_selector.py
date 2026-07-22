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
    # 默认整片 HyperFrames 渲染；Remotion 不再作为默认路径。
    return "hyperframes"
