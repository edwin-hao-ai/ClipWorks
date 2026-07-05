import os
import httpx
import logging
from app.config import ASSETS_DIR, RENDERER_URL
from app.rendering.provider import RenderProvider, RenderRequest, RenderResult

logger = logging.getLogger(__name__)


class VideoUseProvider(RenderProvider):
    name = "video-use"

    def can_handle(self, request: RenderRequest) -> bool:
        return request.engine in (None, "video-use") and bool(request.raw_assets)

    async def render(self, job, project, request: RenderRequest) -> RenderResult:
        output_path = os.path.join(ASSETS_DIR, project.id, "output.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        try:
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(
                    f"{RENDERER_URL}/render/video-use",
                    json={
                        "asset_paths": request.raw_assets,
                        "instruction": request.user_prompt or "Edit the video",
                        "output_path": output_path,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return RenderResult(
                    success=data.get("success", False),
                    output_url=data.get("output_url"),
                    error_message=data.get("error"),
                )
        except Exception as exc:
            logger.exception("VideoUse provider failed")
            return RenderResult(success=False, error_message=str(exc))
