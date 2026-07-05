import time
from datetime import datetime
from app.rendering.provider import RenderProvider, RenderRequest, RenderResult


class MockProvider(RenderProvider):
    name = "mock"

    def can_handle(self, request: RenderRequest) -> bool:
        return True

    async def render(self, job, project, request: RenderRequest) -> RenderResult:
        job.status = "running"
        for i in range(1, 6):
            time.sleep(1)
            job.progress = i * 20
        job.status = "completed"
        job.progress = 100
        job.completed_at = datetime.utcnow()
        project.status = "ready"
        return RenderResult(
            success=True,
            output_url="/api/static/sample.mp4",
            html_output_url="/api/static/index.html",
        )
