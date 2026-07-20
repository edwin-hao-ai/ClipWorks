import os
import subprocess
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@pytest.fixture
def assets_dir(monkeypatch, tmp_path):
    monkeypatch.setattr("main.ASSETS_DIR", str(tmp_path))
    return str(tmp_path)


@pytest.mark.skipif(subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0, reason="ffmpeg not available")
def test_render_proxy_video(assets_dir):
    input_path = os.path.join(assets_dir, "input.mp4")
    output_path = os.path.join(assets_dir, "input.remotion.webm")
    # Create a tiny valid H.264 MP4.
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=1:size=320x240:rate=30",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            input_path,
        ],
        check=True,
        capture_output=True,
    )

    response = client.post(
        "/render/proxy",
        json={
            "input_path": input_path,
            "output_path": output_path,
            "asset_type": "video",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["output_path"] == output_path
    assert os.path.exists(output_path)


@pytest.mark.skipif(subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0, reason="ffmpeg not available")
def test_render_proxy_audio(assets_dir):
    input_path = os.path.join(assets_dir, "input.mp3")
    output_path = os.path.join(assets_dir, "input.remotion.ogg")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=1000:duration=1",
            "-c:a",
            "libmp3lame",
            input_path,
        ],
        check=True,
        capture_output=True,
    )

    response = client.post(
        "/render/proxy",
        json={
            "input_path": input_path,
            "output_path": output_path,
            "asset_type": "audio",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["output_path"] == output_path
    assert os.path.exists(output_path)


def test_render_proxy_rejects_paths_outside_assets(assets_dir):
    response = client.post(
        "/render/proxy",
        json={
            "input_path": "/etc/passwd",
            "output_path": os.path.join(assets_dir, "out.webm"),
            "asset_type": "video",
        },
    )
    assert response.status_code == 400


def test_render_proxy_rejects_invalid_asset_type(assets_dir):
    response = client.post(
        "/render/proxy",
        json={
            "input_path": os.path.join(assets_dir, "input.mp4"),
            "output_path": os.path.join(assets_dir, "out.webm"),
            "asset_type": "image",
        },
    )
    assert response.status_code == 400
