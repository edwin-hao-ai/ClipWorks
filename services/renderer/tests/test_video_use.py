import os
from fastapi.testclient import TestClient
from main import app, ASSETS_DIR

client = TestClient(app)


def test_render_video_use_copies_asset(tmp_path):
    os.makedirs(ASSETS_DIR, exist_ok=True)
    asset = os.path.join(ASSETS_DIR, "input.mp4")
    output = os.path.join(ASSETS_DIR, "output.mp4")
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
