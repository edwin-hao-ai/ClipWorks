import json
import os
import httpx
import logging
from app.config import ASSETS_DIR, RENDERER_URL
from app.rendering.provider import RenderProvider, RenderRequest, RenderResult

logger = logging.getLogger(__name__)


class RemotionProvider(RenderProvider):
    name = "remotion"

    def can_handle(self, request: RenderRequest) -> bool:
        return request.engine in (None, "remotion")

    async def render(self, job, project, request: RenderRequest) -> RenderResult:
        project_dir = os.path.join(ASSETS_DIR, project.id)
        os.makedirs(project_dir, exist_ok=True)
        comp_path = os.path.join(project_dir, "composition.json")
        output_path = os.path.join(project_dir, "output.mp4")

        with open(comp_path, "w", encoding="utf-8") as f:
            json.dump({"composition": request.composition}, f, ensure_ascii=False)

        try:
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(
                    f"{RENDERER_URL}/render/remotion",
                    json={"composition_path": comp_path, "output_path": output_path},
                )
                resp.raise_for_status()
                data = resp.json()
                return RenderResult(
                    success=data.get("success", False),
                    output_url=data.get("output_url"),
                    error_message=data.get("error"),
                )
        except Exception as exc:
            logger.exception("Remotion provider failed")
            return RenderResult(success=False, error_message=str(exc))
