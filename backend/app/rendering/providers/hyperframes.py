import os
import logging
from typing import Optional
import httpx

from app.agent import generate_html
from app.config import ASSETS_DIR, RENDERER_URL
from app.rendering.provider import RenderProvider, RenderRequest, RenderResult

logger = logging.getLogger(__name__)


class HyperFramesProvider(RenderProvider):
    name = "hyperframes"

    def can_handle(self, request: RenderRequest) -> bool:
        return request.engine in (None, "hyperframes")

    async def render(self, job, project, request: RenderRequest) -> RenderResult:
        project_dir = os.path.join(ASSETS_DIR, project.id)
        os.makedirs(project_dir, exist_ok=True)
        output_path = os.path.join(project_dir, "output.mp4")

        # Reuse the HTML the render task already produced. Generating it again
        # here would mean a second slow LLM call (which frequently times out)
        # with no visible progress to the user.
        html_path = request.html_path or os.path.join(project_dir, "index.html")
        if not (request.html_path and os.path.exists(html_path)):
            html = generate_html(request.composition, request.assets)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)

        payload = {
            "html_path": html_path,
            "output_path": output_path,
        }

        try:
            # Fail fast if the renderer hangs (e.g. Chromium unavailable on
            # ARM64). Letting this sit for 300s makes the UI look frozen.
            async with httpx.AsyncClient(timeout=200) as client:
                resp = await client.post(f"{RENDERER_URL}/render/hyperframes", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return RenderResult(
                    success=data.get("success", False),
                    output_url=data.get("output_url"),
                    html_output_url=data.get("html_output_url"),
                    error_message=data.get("error"),
                )
        except Exception as exc:
            logger.exception("HyperFrames provider failed")
            return RenderResult(success=False, error_message=str(exc))
