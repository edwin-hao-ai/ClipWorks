from app.rendering.provider import RenderRequest


def select_engine(request: RenderRequest) -> str:
    if request.raw_assets:
        return "video-use"
    prompt = (request.user_prompt or "").lower()
    if any(k in prompt for k in ["remotion", "模板", "批量", "react"]):
        return "remotion"
    return "hyperframes"
