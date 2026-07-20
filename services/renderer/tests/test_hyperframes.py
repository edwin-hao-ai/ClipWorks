import os
import signal
import subprocess
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@pytest.fixture
def assets_dir(monkeypatch, tmp_path):
    monkeypatch.setattr("main.ASSETS_DIR", str(tmp_path))
    # 每个用例都复位「HyperFrames 不可用」的进程级记忆，避免互相污染。
    monkeypatch.setattr("main._HYPERFRAMES_UNAVAILABLE", False)
    return str(tmp_path)


@pytest.fixture
def sample_html(assets_dir):
    html_path = os.path.join(assets_dir, "test.html")
    with open(html_path, "w") as f:
        f.write("<html><body>hi</body></html>")
    return html_path


def _fake_proc(returncode=0, out="", err="", pid=43210):
    proc = MagicMock()
    proc.pid = pid
    proc.returncode = returncode
    proc.communicate.return_value = (out, err)
    return proc


def test_render_hyperframes_writes_output(sample_html, assets_dir):
    output_path = os.path.join(assets_dir, "test.mp4")

    with patch("main.subprocess.Popen", return_value=_fake_proc()) as mock_popen:
        response = client.post(
            "/render/hyperframes",
            json={"html_path": sample_html, "output_path": output_path},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["output_url"] == "/api/static/test.mp4"
    assert data["html_output_url"] == "/api/static/test.html"
    mock_popen.assert_called_once()
    args, kwargs = mock_popen.call_args
    cmd = args[0]
    assert cmd[:3] == ["npx", "hyperframes", "render"]
    assert os.path.dirname(sample_html) in cmd  # HyperFrames 接收目录而非文件
    assert output_path in cmd
    assert kwargs.get("start_new_session") is True  # 必须新会话，killpg 才收得干净


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
    proc = _fake_proc()
    proc.communicate.side_effect = [
        subprocess.TimeoutExpired(cmd=["npx"], timeout=75),  # 首次 communicate 超时
        ("", ""),                                            # 收割后的 reap communicate
    ]

    with patch("main.subprocess.Popen", return_value=proc), \
            patch("main.os.getpgid", return_value=43210), \
            patch("main.os.killpg") as mock_kill:
        response = client.post(
            "/render/hyperframes",
            json={"html_path": sample_html, "output_path": output_path},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["output_url"] is None
    assert data["error"] == "HyperFrames render timed out (engine likely unavailable on this platform)"
    mock_kill.assert_called_once_with(43210, signal.SIGKILL)  # 超时必须收割整个进程组


def test_render_hyperframes_missing_cli(sample_html, assets_dir):
    output_path = os.path.join(assets_dir, "test.mp4")

    with patch("main.subprocess.Popen", side_effect=FileNotFoundError()):
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

    with patch("main.subprocess.Popen", return_value=_fake_proc(returncode=1, err="render failed")), \
            patch("main.os.getpgid", return_value=43210), \
            patch("main.os.killpg") as mock_kill:
        response = client.post(
            "/render/hyperframes",
            json={"html_path": sample_html, "output_path": output_path},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["output_url"] is None
    assert data["error"] == "render failed"
    mock_kill.assert_called_once_with(43210, signal.SIGKILL)  # 非零退出同样收割 Chromium 孙进程
