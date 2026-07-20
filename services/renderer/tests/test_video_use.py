import json
import os
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

from main import app
from video_use.edit_video import VideoUseError, render

client = TestClient(app)

_FFMPEG_AVAILABLE = shutil.which("ffmpeg") and shutil.which("ffprobe")
pytestmark = pytest.mark.skipif(not _FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe 不可用")


def _make_clip(path: str, duration: float, size: str = "320x240", freq: int = 440) -> str:
    """用 testsrc + sine 生成一个带音轨的临时小视频。"""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"testsrc=size={size}:duration={duration}:rate=15",
        "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        path,
    ]
    subprocess.run(cmd, capture_output=True, check=True, timeout=120)
    return path


def _make_bgm(path: str, duration: float = 5.0) -> str:
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency=220:duration={duration}",
        "-c:a", "pcm_s16le",
        path,
    ]
    subprocess.run(cmd, capture_output=True, check=True, timeout=120)
    return path


def _probe(path: str) -> dict:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-show_entries", "stream=codec_type,codec_name,width,height",
        "-of", "json", path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
    return json.loads(result.stdout)


def _stream(info: dict, codec_type: str) -> dict:
    return next(s for s in info["streams"] if s["codec_type"] == codec_type)


def test_render_concat_two_clips(tmp_path):
    clip1 = _make_clip(str(tmp_path / "a.mp4"), 1.5)
    clip2 = _make_clip(str(tmp_path / "b.mp4"), 1.5, freq=880)
    output = str(tmp_path / "out.mp4")

    render({
        "width": 320, "height": 240, "fps": 15,
        "clips": [
            {"path": clip1, "trim_start": 0, "trim_duration": 1.5},
            {"path": clip2, "trim_start": 0, "trim_duration": 1.5},
        ],
        "output": output,
    })

    assert os.path.exists(output)
    info = _probe(output)
    assert abs(float(info["format"]["duration"]) - 3.0) < 0.6
    video = _stream(info, "video")
    assert video["codec_name"] == "h264"
    assert (video["width"], video["height"]) == (320, 240)


def test_render_scales_and_pads_to_target_size(tmp_path):
    # 输入画幅与目标不同：按比例缩放 + 居中 pad，输出必须严格等于目标尺寸。
    clip = _make_clip(str(tmp_path / "wide.mp4"), 1.0, size="640x240")
    output = str(tmp_path / "out.mp4")

    render({
        "width": 320, "height": 240, "fps": 15,
        "clips": [{"path": clip, "trim_start": 0, "trim_duration": 1.0}],
        "output": output,
    })

    video = _stream(_probe(output), "video")
    assert (video["width"], video["height"]) == (320, 240)


def test_render_with_bgm(tmp_path):
    clip1 = _make_clip(str(tmp_path / "a.mp4"), 1.0)
    clip2 = _make_clip(str(tmp_path / "b.mp4"), 1.0, freq=880)
    bgm = _make_bgm(str(tmp_path / "bgm.wav"))
    output = str(tmp_path / "out.mp4")

    render({
        "width": 320, "height": 240, "fps": 15,
        "clips": [
            {"path": clip1, "trim_start": 0, "trim_duration": 1.0},
            {"path": clip2, "trim_start": 0, "trim_duration": 1.0},
        ],
        "bgm_path": bgm,
        "bgm_volume": 0.2,
        "output": output,
    })

    info = _probe(output)
    assert abs(float(info["format"]["duration"]) - 2.0) < 0.6
    assert _stream(info, "audio")["codec_name"] == "aac"


def test_render_empty_clips_raises(tmp_path):
    with pytest.raises(VideoUseError, match="clips"):
        render({"width": 320, "height": 240, "clips": [], "output": str(tmp_path / "out.mp4")})


def test_render_missing_input_raises(tmp_path):
    with pytest.raises(VideoUseError, match="不存在"):
        render({
            "width": 320, "height": 240,
            "clips": [{"path": str(tmp_path / "nope.mp4"), "trim_start": 0, "trim_duration": 1}],
            "output": str(tmp_path / "out.mp4"),
        })


def test_endpoint_video_use(assets_dir):
    clip1 = _make_clip(os.path.join(assets_dir, "a.mp4"), 1.0)
    clip2 = _make_clip(os.path.join(assets_dir, "b.mp4"), 1.0, freq=880)
    output = os.path.join(assets_dir, "final.mp4")

    response = client.post("/render/video-use", json={
        "width": 320, "height": 240, "fps": 15,
        "clips": [
            {"path": clip1, "trim_start": 0, "trim_duration": 1.0},
            {"path": clip2, "trim_start": 0, "trim_duration": 1.0},
        ],
        "output": output,
    })

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["output_url"] == "/api/static/final.mp4"
    assert abs(float(_probe(output)["format"]["duration"]) - 2.0) < 0.6


def test_endpoint_rejects_path_outside_assets(assets_dir):
    response = client.post("/render/video-use", json={
        "width": 320, "height": 240,
        "clips": [{"path": "/etc/passwd", "trim_start": 0, "trim_duration": 1.0}],
        "output": os.path.join(assets_dir, "out.mp4"),
    })
    assert response.status_code == 400


def test_endpoint_rejects_empty_clips(assets_dir):
    response = client.post("/render/video-use", json={
        "width": 320, "height": 240, "clips": [],
        "output": os.path.join(assets_dir, "out.mp4"),
    })
    assert response.status_code == 400
