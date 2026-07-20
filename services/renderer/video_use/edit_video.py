"""video-use 引擎：按结构化 spec 用 ffmpeg 一次性完成真实剪辑合成。

与 hyperframes（HTML 动画）/remotion（React 模板）不同，本引擎面向「原始素材剪辑」：
把若干段真实视频按 trim 区间截取、统一画幅后顺序拼接，可选混入一条压低音量的
背景音乐，输出通用 H.264 + AAC MP4。

spec 格式（JSON）::

    {
      "width": 1920, "height": 1080, "fps": 30,
      "clips": [
        {"path": "/abs/a.mp4", "trim_start": 0.0, "trim_duration": 5.0},
        {"path": "/abs/b.mp4", "trim_start": 2.0, "trim_duration": 3.0}
      ],
      "bgm_path": "/abs/bgm.mp3",   // 可选
      "bgm_volume": 0.25,           // 可选，默认 0.25
      "output": "/abs/out.mp4"
    }

用法：
    python edit_video.py spec.json          # 命令行
    from video_use.edit_video import render # import 复用（端点/测试）
    render(spec)
"""

import json
import logging
import os
import shutil
import subprocess
import sys

logger = logging.getLogger(__name__)

# 单次剪辑的 ffmpeg 超时：拼接是逐帧重编码，给足余量但必须有上限，
# 避免异常输入把渲染服务卡死。
_FFMPEG_TIMEOUT = 300


class VideoUseError(Exception):
    """video-use 剪辑失败（输入非法 / ffmpeg 不可用 / ffmpeg 执行失败）。"""


def _has_audio(path: str) -> bool:
    """用 ffprobe 判断素材是否带音频流。

    concat 滤镜要求所有输入片段都有音频流；无声片段需要用 anullsrc 补静音，
    否则 ffmpeg 直接报错退出。探测失败时保守地当作有声处理——若实际无声，
    ffmpeg 会给出清晰错误（VideoUseError），而不是悄悄丢掉有声片段的音轨。
    """
    if not shutil.which("ffprobe"):
        return True
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_type",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
        return result.returncode == 0 and "audio" in result.stdout
    except Exception as exc:  # noqa: BLE001 - 探测失败按有声处理
        logger.warning("ffprobe audio check failed for %s: %s", path, exc)
        return True


def _fmt(value: float) -> str:
    """格式化秒数，避免 5.0 之外的浮点长尾（ffmpeg 接受小数）。"""
    return f"{float(value):.3f}".rstrip("0").rstrip(".") or "0"


def _build_command(spec: dict, audio_flags: list[bool]) -> list[str]:
    width = int(spec["width"])
    height = int(spec["height"])
    fps = int(spec.get("fps", 30))
    clips = spec["clips"]
    bgm_path = spec.get("bgm_path")
    n = len(clips)

    cmd = ["ffmpeg", "-y"]
    for clip in clips:
        cmd += ["-i", os.path.abspath(clip["path"])]
    if bgm_path:
        cmd += ["-i", os.path.abspath(bgm_path)]

    filters: list[str] = []
    for i, clip in enumerate(clips):
        start = _fmt(clip.get("trim_start", 0))
        dur = _fmt(clip["trim_duration"])
        # 统一画幅：按比例缩放后居中 pad 到目标尺寸，setsar=1 消除像素比差异，
        # fps 归一化避免不同帧率片段 concat 后时间轴错乱。
        filters.append(
            f"[{i}:v]trim=start={start}:duration={dur},setpts=PTS-STARTPTS,"
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}[v{i}]"
        )
        if audio_flags[i]:
            filters.append(
                f"[{i}:a]atrim=start={start}:duration={dur},asetpts=PTS-STARTPTS,"
                f"aresample=44100[a{i}]"
            )
        else:
            # 无声片段补等长静音，保证 concat 的 a=1 所有输入齐备。
            filters.append(f"anullsrc=r=44100:cl=stereo,atrim=start=0:duration={dur}[a{i}]")

    concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(n))
    if bgm_path:
        volume = _fmt(spec.get("bgm_volume", 0.25))
        filters.append(f"{concat_inputs}concat=n={n}:v=1:a=1[outv][voice]")
        # duration=first：成片时长由拼接后的画面音轨决定，bgm 用尽后自然淡出
        # （dropout_transition=0 不做交叉淡化）。
        filters.append(f"[{n}:a]volume={volume}[bgm]")
        filters.append("[voice][bgm]amix=inputs=2:duration=first:dropout_transition=0[outa]")
    else:
        filters.append(f"{concat_inputs}concat=n={n}:v=1:a=1[outv][outa]")

    cmd += [
        "-filter_complex", ";".join(filters),
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-movflags", "+faststart",
        os.path.abspath(spec["output"]),
    ]
    return cmd


def _validate(spec: dict) -> None:
    if not isinstance(spec, dict):
        raise VideoUseError("spec must be a JSON object")
    clips = spec.get("clips") or []
    if not clips:
        raise VideoUseError("clips 为空：至少需要一个视频片段")
    for key in ("width", "height", "output"):
        if not spec.get(key):
            raise VideoUseError(f"spec 缺少必填字段: {key}")
    for clip in clips:
        path = clip.get("path")
        if not path:
            raise VideoUseError("clip 缺少 path 字段")
        if not os.path.exists(path):
            raise VideoUseError(f"片段文件不存在: {path}")
        if float(clip.get("trim_duration", 0) or 0) <= 0:
            raise VideoUseError(f"clip trim_duration 必须 > 0: {path}")
    bgm_path = spec.get("bgm_path")
    if bgm_path and not os.path.exists(bgm_path):
        raise VideoUseError(f"背景音乐文件不存在: {bgm_path}")
    if not shutil.which("ffmpeg"):
        raise VideoUseError("ffmpeg 不可用：渲染容器内未安装 ffmpeg")


def render(spec: dict) -> None:
    """按 spec 执行剪辑，失败抛 VideoUseError。"""
    _validate(spec)
    output = os.path.abspath(spec["output"])
    os.makedirs(os.path.dirname(output), exist_ok=True)

    audio_flags = [_has_audio(clip["path"]) for clip in spec["clips"]]
    cmd = _build_command(spec, audio_flags)
    logger.info("video-use ffmpeg: %s", " ".join(cmd))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=_FFMPEG_TIMEOUT, check=False)
    except subprocess.TimeoutExpired as exc:
        raise VideoUseError(f"ffmpeg 剪辑超时（{_FFMPEG_TIMEOUT}s）") from exc
    except FileNotFoundError as exc:
        raise VideoUseError("ffmpeg 不可用：渲染容器内未安装 ffmpeg") from exc

    if result.returncode != 0:
        raise VideoUseError(f"ffmpeg 剪辑失败: {(result.stderr or '')[-1000:]}")
    if not os.path.exists(output) or os.path.getsize(output) < 1024:
        raise VideoUseError("ffmpeg 完成但输出文件缺失或过小")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python edit_video.py spec.json", file=sys.stderr)
        return 2
    try:
        with open(argv[1], "r", encoding="utf-8") as f:
            spec = json.load(f)
        render(spec)
    except (VideoUseError, OSError, json.JSONDecodeError) as exc:
        print(f"video-use error: {exc}", file=sys.stderr)
        return 1
    print(f"ok: {spec['output']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
