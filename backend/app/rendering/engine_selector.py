from app.rendering.provider import RenderRequest


def select_engine(request: RenderRequest) -> str:
    if request.raw_assets:
        return "video-use"
    prompt = (request.user_prompt or "").lower()
    if any(k in prompt for k in ["hyperframes", "html", "轻量"]):
        return "hyperframes"
    # Honor the Agent-recommended engine from the approved plan unless the user
    # explicitly chose another engine in their prompt.
    hint = (request.engine_hint or "").lower()
    if hint and hint in ("hyperframes", "remotion", "video-use"):
        return hint
    # 默认走 Remotion：真 <Img>/<Video>/<Audio>、spring 动效、CJK 字体、H.264 输出，
    # 失败时 RenderService 会自动降级到其它引擎。
    return "remotion"
