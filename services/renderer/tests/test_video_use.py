import os
import pytest
from fastapi.testclient import TestClient
from main import app, ASSETS_DIR

client = TestClient(app)


@pytest.fixture
def assets_dir(monkeypatch, tmp_path):
    monkeypatch.setattr("main.ASSETS_DIR", str(tmp_path))
    return str(tmp_path)


def test_render_video_use_copies_asset(assets_dir):
    os.makedirs(assets_dir, exist_ok=True)
    asset = os.path.join(assets_dir, "input.mp4")
    output = os.path.join(assets_dir, "output.mp4")
    with open(asset, "wb") as f:
        f.write(b"fake-video")

    response = client.post(
        "/render/video-use",
        json={"asset_paths": [asset], "instruction": "cut first 10s", "output_path": output},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["output_url"] == "/api/static/output.mp4"
