import os
import subprocess
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@pytest.fixture
def assets_dir(monkeypatch, tmp_path):
    monkeypatch.setattr("main.ASSETS_DIR", str(tmp_path))
    return str(tmp_path)


@pytest.fixture
def sample_html(assets_dir):
    html_path = os.path.join(assets_dir, "test.html")
    with open(html_path, "w") as f:
        f.write("<html><body>hi</body></html>")
    return html_path


def test_render_hyperframes_writes_output(sample_html, assets_dir):
    output_path = os.path.join(assets_dir, "test.mp4")

    with patch("main.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        response = client.post(
            "/render/hyperframes",
            json={"html_path": sample_html, "output_path": output_path, "duration": 5, "fps": 30},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["output_url"] == "/api/static/test.mp4"
    assert data["html_output_url"] == "/api/static/test.html"
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    assert "--duration" in args[0]
    assert "5" in args[0]
    assert "--fps" in args[0]
    assert "30" in args[0]


def test_render_hyperframes_rejects_paths_outside_assets(sample_html, assets_dir):
    output_path = os.path.join(assets_dir, "test.mp4")
    outside_path = "/tmp/outside.html"

    response = client.post(
        "/render/hyperframes",
        json={"html_path": outside_path, "output_path": output_path},
    )

    assert response.status_code == 400
    assert "Paths must be under ASSETS_DIR" in response.json()["detail"]


def test_render_hyperframes_timeout(sample_html, assets_dir):
    output_path = os.path.join(assets_dir, "test.mp4")

    with patch("main.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["npx"], timeout=300)
        response = client.post(
            "/render/hyperframes",
            json={"html_path": sample_html, "output_path": output_path},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["output_url"] is None
    assert data["error"] == "Render timed out"


def test_render_hyperframes_missing_cli(sample_html, assets_dir):
    output_path = os.path.join(assets_dir, "test.mp4")

    with patch("main.subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError()
        response = client.post(
            "/render/hyperframes",
            json={"html_path": sample_html, "output_path": output_path},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["output_url"] is None
    assert data["error"] == "HyperFrames CLI not found"


def test_render_hyperframes_nonzero_exit(sample_html, assets_dir):
    output_path = os.path.join(assets_dir, "test.mp4")

    with patch("main.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "render failed"
        mock_run.return_value.stdout = ""
        response = client.post(
            "/render/hyperframes",
            json={"html_path": sample_html, "output_path": output_path},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["output_url"] is None
    assert data["error"] == "render failed"
