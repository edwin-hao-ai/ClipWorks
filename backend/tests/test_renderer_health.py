import httpx
import pytest
from app.config import RENDERER_URL


@pytest.mark.integration
@pytest.mark.asyncio
async def test_renderer_health():
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{RENDERER_URL}/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
