"""音轨混音测试：旁白段 + BGM 闪避路径。

回归目标：[voice] 标签被 sidechaincompress 与最终 amix 各消费一次导致 ffmpeg
报 "matches no streams"——此路在无 TTS 密钥的年代从未被真实执行，espeak 兜底
让旁白首次成真才暴露。测试用 ffmpeg 合成两段确定性旁白 wav 走完整混音。
"""
import subprocess

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _tone(path: str, freq: int, dur: float = 1.5) -> None:
    """用 ffmpeg 生成一段确定性正弦波 wav（模拟旁白段，22050Hz mono 对齐 espeak 产物）。"""
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={dur}",
            "-ar", "22050", "-ac", "1", "-c:a", "pcm_s16le", path,
        ],
        check=True,
    )


def test_soundtrack_bgm_only(assets_dir):
    out = f"{assets_dir}/bgm_only.wav"
    resp = client.post(
        "/render/soundtrack",
        json={"output_path": out, "duration": 4, "narration": [], "bgm_style": "ambient", "seed": 7},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True, data.get("error")
    import os
    assert os.path.getsize(out) > 1024


def test_soundtrack_with_narration_and_ducking(assets_dir):
    seg0 = f"{assets_dir}/seg_0.wav"
    seg1 = f"{assets_dir}/seg_1.wav"
    _tone(seg0, 440)
    _tone(seg1, 660)
    out = f"{assets_dir}/mixed.wav"
    resp = client.post(
        "/render/soundtrack",
        json={
            "output_path": out,
            "duration": 6,
            "narration": [
                {"path": seg0, "start": 0.5},
                {"path": seg1, "start": 3.0},
            ],
            "bgm_style": "ambient",
            "seed": 3,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True, data.get("error")
    import os
    assert os.path.getsize(out) > 1024


def test_soundtrack_keeps_full_duration_when_narration_short(assets_dir):
    """旁白比 BGM 短时混音也必须是全片时长。

    回归目标：sidechaincompress 输出随较短输入终止，曾导致 15s 的片子混音只有
    8s、下游 mux -shortest 把视频一并裁短。修复后旁白总线先 pad 到全片时长。
    """
    seg = f"{assets_dir}/seg_short.wav"
    _tone(seg, 520, dur=1.0)  # 1 秒旁白放在第 1 秒，远短于 6 秒全片
    out = f"{assets_dir}/mixed_full.wav"
    resp = client.post(
        "/render/soundtrack",
        json={
            "output_path": out,
            "duration": 6,
            "narration": [{"path": seg, "start": 1.0}],
            "bgm_style": "ambient",
            "seed": 5,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True, data.get("error")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1", out],
        capture_output=True, text=True, check=True,
    )
    dur = float(probe.stdout.strip().split("=")[1])
    assert dur >= 5.9, f"混音被截短到 {dur}s（应为 6s）"


def test_soundtrack_rejects_path_outside_assets(assets_dir):
    resp = client.post(
        "/render/soundtrack",
        json={"output_path": "/tmp/evil.wav", "duration": 2, "narration": [], "bgm_style": "ambient", "seed": 1},
    )
    assert resp.status_code == 400
