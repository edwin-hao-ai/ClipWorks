import json
import logging
import os
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

ASSETS_DIR = os.path.abspath(os.getenv("ASSETS_DIR", "/app/data/assets"))
app = FastAPI(title="ClipWorks Renderer")


def _has_command(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _reap_process_group(proc: subprocess.Popen) -> None:
    """Best-effort 收割子进程所在的整个进程组。

    渲染 CLI（remotion/hyperframes）失败退出时，它拉起的 Chromium 孙进程常常残留成
    僵尸；在内存紧张的部署环境（如 4GB Docker VM）里，几个僵尸浏览器就足以让后续
    所有浏览器启动超时、形成死亡螺旋。因此所有失败路径（超时/非零退出）都必须收割。
    """
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:  # noqa: BLE001 - 收割是 best-effort，任何异常都不许外泄
        pass


def _has_node_module_bin(name: str) -> bool:
    # 同时兼容 Docker 路径（/app/node_modules）与宿主机开发路径（renderer 根目录 / remotion 子目录）
    candidates = [
        os.path.join("/app", "node_modules", ".bin", name),
        os.path.join(os.path.dirname(__file__), "node_modules", ".bin", name),
        os.path.join(os.path.dirname(__file__), "remotion", "node_modules", ".bin", name),
    ]
    return any(os.path.exists(p) for p in candidates)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "engines": {
            "hyperframes": _has_node_module_bin("hyperframes"),
            "remotion": _has_node_module_bin("remotion"),
            "video_use": _has_command("ffmpeg"),
        },
    }


class HyperFramesRequest(BaseModel):
    html_path: str
    output_path: str


class RemotionRequest(BaseModel):
    composition_path: str
    output_path: str


class ProxyRequest(BaseModel):
    input_path: str
    output_path: str
    asset_type: str  # video | audio


class NarrationSegment(BaseModel):
    path: str
    start: float = 0.0  # seconds from composition start


class SoundtrackRequest(BaseModel):
    output_path: str
    duration: float  # seconds
    narration: list[NarrationSegment] = []
    bgm_style: str = "ambient"  # ambient | none
    seed: int = 0  # deterministic variation per project


class MuxAudioRequest(BaseModel):
    video_path: str
    audio_path: str
    output_path: str


class QARequest(BaseModel):
    video_path: str
    samples: int = 6
    black_threshold: int = 8  # mean luminance (0-255) below which a frame counts as black


class VideoUseClip(BaseModel):
    path: str
    trim_start: float = 0.0  # seconds into the source footage
    trim_duration: float  # seconds to keep


class VideoUseRequest(BaseModel):
    width: int
    height: int
    fps: int = 30
    clips: list[VideoUseClip]
    bgm_path: Optional[str] = None
    bgm_volume: float = 0.25
    output: str


def _relative_url(abs_path: str) -> str:
    abs_path = os.path.abspath(abs_path)
    if os.path.commonpath([abs_path, ASSETS_DIR]) != ASSETS_DIR:
        raise ValueError(f"Path {abs_path!r} is not under ASSETS_DIR {ASSETS_DIR!r}")
    rel = os.path.relpath(abs_path, ASSETS_DIR)
    return f"/api/static/{rel}"


def _is_under_assets(path: str) -> bool:
    abs_path = os.path.abspath(path)
    return os.path.commonpath([abs_path, ASSETS_DIR]) == ASSETS_DIR


_HYPERFRAMES_UNAVAILABLE = False


@app.post("/render/hyperframes")
def render_hyperframes(req: HyperFramesRequest):
    global _HYPERFRAMES_UNAVAILABLE
    if not _is_under_assets(req.html_path) or not _is_under_assets(req.output_path):
        raise HTTPException(status_code=400, detail="Paths must be under ASSETS_DIR")

    os.makedirs(os.path.dirname(os.path.abspath(req.output_path)), exist_ok=True)

    # Once HyperFrames has hung/failed in this process (e.g. Chromium cannot
    # render on ARM64 Linux), stop trying so every subsequent request does not
    # hang for the full timeout and make the UI look frozen.
    if _HYPERFRAMES_UNAVAILABLE:
        return {
            "success": False,
            "output_url": None,
            "html_output_url": _relative_url(req.html_path),
            "error": "HyperFrames is unavailable in this environment (Chromium cannot render on this platform)",
        }

    # HyperFrames expects the directory containing index.html, not the file itself.
    html_dir = os.path.dirname(os.path.abspath(req.html_path))
    cmd = [
        "npx",
        "hyperframes",
        "render",
        html_dir,
        req.output_path,
    ]
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True
        )
    except FileNotFoundError:
        _HYPERFRAMES_UNAVAILABLE = True
        return {"success": False, "output_url": None, "html_output_url": _relative_url(req.html_path), "error": "HyperFrames CLI not found"}
    try:
        out, err = proc.communicate(timeout=75)
    except subprocess.TimeoutExpired:
        _reap_process_group(proc)  # 连 Chromium 孙进程一起收割，避免僵尸累积
        try:
            proc.communicate(timeout=5)
        except Exception:
            pass
        _HYPERFRAMES_UNAVAILABLE = True
        return {
            "success": False,
            "output_url": None,
            "html_output_url": _relative_url(req.html_path),
            "error": "HyperFrames render timed out (engine likely unavailable on this platform)",
        }

    if proc.returncode != 0:
        _reap_process_group(proc)  # 失败退出也可能残留 Chromium
        return {
            "success": False,
            "output_url": None,
            "html_output_url": _relative_url(req.html_path),
            "error": err or out or "HyperFrames render failed",
        }
    return {
        "success": True,
        "output_url": _relative_url(req.output_path),
        "html_output_url": _relative_url(req.html_path),
        "error": None,
    }


@app.post("/render/remotion")
def render_remotion(req: RemotionRequest):
    if not _is_under_assets(req.composition_path) or not _is_under_assets(req.output_path):
        raise HTTPException(status_code=400, detail="Paths must be under ASSETS_DIR")

    os.makedirs(os.path.dirname(os.path.abspath(req.output_path)), exist_ok=True)
    remotion_dir = os.path.join(os.path.dirname(__file__), "remotion")

    # Ensure the props file is fully written and valid JSON before handing it to Remotion.
    props_path = os.path.abspath(req.composition_path)
    for attempt in range(10):
        try:
            with open(props_path, "r", encoding="utf-8") as f:
                json.load(f)
            break
        except Exception:
            if attempt == 9:
                logger.error("Props file is not valid JSON: %s", props_path)
                return {"success": False, "output_url": None, "error": f"Props file is not valid JSON: {props_path}"}
            time.sleep(0.2)

    output_path = os.path.abspath(req.output_path)
    cmd = [
        "npx", "remotion", "render", "Generic", output_path,
        "--props", props_path,
        "--concurrency", "1",
    ]
    log_path = output_path + ".render.log"
    try:
        with open(log_path, "w", encoding="utf-8") as log_file:
            proc = subprocess.Popen(
                cmd,
                cwd=remotion_dir,
                stdout=subprocess.DEVNULL,
                stderr=log_file,
                start_new_session=True,
            )
            try:
                returncode = proc.wait(timeout=600)
            except subprocess.TimeoutExpired:
                logger.warning("Remotion render timed out, killing process group")
                try:
                    os.killpg(os.getpgid(proc.pid), 9)
                except ProcessLookupError:
                    pass
                proc.wait(timeout=5)
                return {
                    "success": False,
                    "output_url": None,
                    "error": "Remotion render timed out after 600 seconds",
                }

        if returncode != 0:
            _reap_process_group(proc)  # CLI 非零退出时 Chromium 孙进程可能还活着
            error_detail = "Remotion render failed"
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    error_detail = f.read().strip() or error_detail
            except Exception:
                pass
            logger.error("Remotion render failed: %s", error_detail[:500])
            return {"success": False, "output_url": None, "error": error_detail}

        if not os.path.exists(output_path) or os.path.getsize(output_path) < 1024:
            return {
                "success": False,
                "output_url": None,
                "error": "Remotion finished but output MP4 is missing or too small",
            }

        return {"success": True, "output_url": _relative_url(req.output_path), "error": None}
    except Exception as exc:
        logger.exception("Remotion render raised exception")
        return {"success": False, "output_url": None, "error": str(exc)}


@app.post("/render/proxy")
def render_proxy(req: ProxyRequest):
    """Transcode a media file into a Chromium-safe open codec for Remotion."""
    if not _is_under_assets(req.input_path) or not _is_under_assets(req.output_path):
        raise HTTPException(status_code=400, detail="Paths must be under ASSETS_DIR")

    os.makedirs(os.path.dirname(os.path.abspath(req.output_path)), exist_ok=True)

    if req.asset_type == "video":
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            req.input_path,
            "-c:v",
            "libvpx",
            "-b:v",
            "2M",
            "-auto-alt-ref",
            "0",
            "-pix_fmt",
            "yuv420p",
            "-an",
            req.output_path,
        ]
    elif req.asset_type == "audio":
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            req.input_path,
            "-c:a",
            "libvorbis",
            "-q:a",
            "4",
            "-vn",
            req.output_path,
        ]
    else:
        raise HTTPException(status_code=400, detail="asset_type must be video or audio")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
        if result.returncode != 0:
            logger.error("Proxy transcode failed: %s", result.stderr[:500])
            return {"success": False, "output_path": None, "error": result.stderr or "Transcode failed"}
        return {"success": True, "output_path": req.output_path, "error": None}
    except subprocess.TimeoutExpired:
        return {"success": False, "output_path": None, "error": "Transcode timed out"}
    except FileNotFoundError:
        return {"success": False, "output_path": None, "error": "ffmpeg not found"}


def _bgm_input_expr(duration: float, seed: int) -> str:
    """Build a deterministic, royalty-free ambient pad via ffmpeg aevalsrc.

    No external files or keys required: a soft three-part sine pad with slow
    tremolo. The seed nudges the base frequencies so different projects don't
    all sound identical, while staying fully deterministic per seed.
    """
    base = 220.0 + (seed % 7) * 5.0  # 220..250 Hz
    p2 = base * 1.25
    p3 = base * 1.5
    expr = (
        f"0.05*sin(2*PI*{base:.2f}*t)*(0.6+0.4*sin(2*PI*0.25*t))"
        f"+0.035*sin(2*PI*{p2:.2f}*t)"
        f"+0.025*sin(2*PI*{p3:.2f}*t)"
    )
    return f"aevalsrc={expr}:s=48000:c=2:d={max(0.5, duration):.3f}"


@app.post("/render/soundtrack")
def render_soundtrack(req: SoundtrackRequest):
    """Mix narration (optional) over a deterministic BGM bed into a browser-safe WAV.

    Real-when-available: callers pass narration wav paths (e.g. from a TTS
    provider). Deterministic fallback: with no narration, returns a BGM-only bed,
    so every render still ships a mixed audio track (→ AAC in the final MP4).
    """
    if not _is_under_assets(req.output_path):
        raise HTTPException(status_code=400, detail="output_path must be under ASSETS_DIR")
    for seg in req.narration:
        if not _is_under_assets(seg.path):
            raise HTTPException(status_code=400, detail=f"narration path must be under ASSETS_DIR: {seg.path}")
        if not os.path.exists(seg.path):
            return {"success": False, "output_path": None, "error": f"narration file missing: {seg.path}"}

    os.makedirs(os.path.dirname(os.path.abspath(req.output_path)), exist_ok=True)

    duration = max(0.5, float(req.duration))
    cmd = ["ffmpeg", "-y"]

    if req.bgm_style != "none":
        cmd += ["-f", "lavfi", "-i", _bgm_input_expr(duration, req.seed)]
        bgm_index = 0
    else:
        bgm_index = None

    for seg in req.narration:
        cmd += ["-i", os.path.abspath(seg.path)]

    # Recompute input indices: bgm (if any) is input 0, narration inputs follow.
    narr_start_idx = 1 if bgm_index is not None else 0
    filters: list[str] = []
    mix_inputs: list[str] = []

    if bgm_index is not None:
        filters.append(f"[{bgm_index}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,volume=0.5[bgm]")
        mix_inputs.append("[bgm]")

    delayed_labels: list[str] = []
    for i, seg in enumerate(req.narration):
        idx = narr_start_idx + i
        delay_ms = max(0, int(round(float(seg.start) * 1000)))
        lbl = f"[v{i}]"
        filters.append(
            f"[{idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
            f"adelay={delay_ms}|{delay_ms},volume=1.0{lbl}"
        )
        delayed_labels.append(lbl)

    if delayed_labels:
        # 旁白总线先 pad 到全片时长再分发：sidechaincompress 的输出会随较短输入终止，
        # 旁白比 BGM 短时整段混音会被截短（下游 mux -shortest 还会把视频一并裁短）。
        filters.append(
            f"{''.join(delayed_labels)}amix=inputs={len(delayed_labels)}:duration=longest:dropout_transition=0,"
            f"apad,atrim=0:{duration:.3f}[voice]"
        )
        if bgm_index is not None:
            # [voice] 要被 sidechain 的 key 输入和最终 amix 各消费一次——ffmpeg 滤镜标签
            # 只能被消费一次，先 asplit 拆成两路，否则报 "matches no streams"。
            filters.append("[voice]asplit=2[voiceA][voiceB]")
            # Duck the BGM under the narration for a broadcast-style mix.
            filters.append(
                "[bgm][voiceA]sidechaincompress=threshold=0.02:ratio=8:attack=60:release=500:makeup=1[bgmduck]"
            )
            filters.append("[bgmduck][voiceB]amix=inputs=2:duration=longest:dropout_transition=0,loudnorm=I=-16:TP=-1.5:LRA=11[mix]")
        else:
            filters.append("[voice]loudnorm=I=-16:TP=-1.5:LRA=11[mix]")
    elif bgm_index is not None:
        filters.append("[bgm]loudnorm=I=-18:TP=-2:LRA=11[mix]")
    else:
        return {"success": False, "output_path": None, "error": "no audio sources (bgm_style=none and no narration)"}

    cmd += [
        "-filter_complex", ";".join(filters),
        "-map", "[mix]",
        "-t", f"{duration:.3f}",
        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2",
        os.path.abspath(req.output_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
        if result.returncode != 0:
            logger.error("Soundtrack mix failed: %s", result.stderr[:800])
            return {"success": False, "output_path": None, "error": result.stderr[-1200:] or "soundtrack mix failed"}
        if not os.path.exists(req.output_path) or os.path.getsize(req.output_path) < 1024:
            return {"success": False, "output_path": None, "error": "soundtrack output missing or too small"}
        return {"success": True, "output_path": req.output_path, "error": None}
    except subprocess.TimeoutExpired:
        return {"success": False, "output_path": None, "error": "soundtrack mix timed out"}
    except FileNotFoundError:
        return {"success": False, "output_path": None, "error": "ffmpeg not found"}


@app.post("/render/mux-audio")
def render_mux_audio(req: MuxAudioRequest):
    """把已生成的 WAV/音轨用 ffmpeg 混进视频 MP4（copy 视频流 + AAC 编码音频）。

    为什么不在 Remotion 里用 <Audio> 直接出片：Chromium 逐帧渲染时再解码远端音轨，
    在 ARM64/单并发下会把 1 分钟的出片拖到 5-10 分钟甚至超时。让 Remotion 只负责它
    擅长的视频帧（≈1 分钟），音频由 ffmpeg 一次封装（≈2 秒），既快又稳，产物仍是
    通用 H.264 + AAC。
    """
    for p in (req.video_path, req.audio_path, req.output_path):
        if not _is_under_assets(p):
            raise HTTPException(status_code=400, detail=f"path must be under ASSETS_DIR: {p}")
    if not os.path.exists(req.video_path):
        return {"success": False, "output_path": None, "error": f"video missing: {req.video_path}"}
    if not os.path.exists(req.audio_path):
        return {"success": False, "output_path": None, "error": f"audio missing: {req.audio_path}"}

    os.makedirs(os.path.dirname(os.path.abspath(req.output_path)), exist_ok=True)
    # 同路径复用时写到临时文件再原子替换，避免覆盖输入导致读一半被截断。
    out_abs = os.path.abspath(req.output_path)
    same_as_video = os.path.abspath(req.video_path) == out_abs
    tmp_out = out_abs + ".muxtmp.mp4" if same_as_video else out_abs
    cmd = [
        "ffmpeg", "-y",
        "-i", os.path.abspath(req.video_path),
        "-i", os.path.abspath(req.audio_path),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-shortest",
        "-movflags", "+faststart",
        tmp_out,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=False)
        if result.returncode != 0:
            logger.error("mux-audio failed: %s", result.stderr[:800])
            return {"success": False, "output_path": None, "error": result.stderr[-1200:] or "mux-audio failed"}
        if not os.path.exists(tmp_out) or os.path.getsize(tmp_out) < 1024:
            return {"success": False, "output_path": None, "error": "mux output missing or too small"}
        if same_as_video:
            os.replace(tmp_out, out_abs)
        return {"success": True, "output_url": _relative_url(out_abs), "output_path": out_abs, "error": None}
    except subprocess.TimeoutExpired:
        return {"success": False, "output_url": None, "output_path": None, "error": "mux-audio timed out"}
    except FileNotFoundError:
        return {"success": False, "output_url": None, "output_path": None, "error": "ffmpeg not found"}


def _probe_duration(video_path: str) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return float(r.stdout.strip() or 0)
    except Exception:
        return 0.0


@app.post("/render/qa")
def render_qa(req: QARequest):
    """出片质量闸门：抽 N 帧算平均亮度，全部近黑（解码失败/空舞台）判不合格。

    低误报设计：只看「是否全黑」，不评判纯色/渐变背景（营销片常见红绿蓝纯色+文案
    亮度远高于阈值，不会误判）。真正的灾难性失败（黑屏、素材解码失败）才会触发。
    """
    if not _is_under_assets(req.video_path):
        raise HTTPException(status_code=400, detail="video_path must be under ASSETS_DIR")
    if not os.path.exists(req.video_path):
        return {"ok": False, "samples": [], "reason": f"video missing: {req.video_path}"}

    duration = _probe_duration(req.video_path)
    if duration <= 0:
        return {"ok": False, "samples": [], "reason": "cannot probe duration"}

    n = max(1, min(int(req.samples), 12))
    means: list[int] = []
    for i in range(n):
        t = duration * (i + 1) / (n + 1)
        cmd = [
            "ffmpeg", "-ss", f"{t:.3f}", "-i", os.path.abspath(req.video_path),
            "-frames:v", "1", "-vf", "scale=1:1:force_original_aspect_ratio=disable,format=gray",
            "-f", "rawvideo", "-v", "quiet", "-",
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=30, check=False)
            if r.stdout:
                means.append(r.stdout[0])
        except Exception:
            continue

    if not means:
        return {"ok": False, "samples": [], "duration": duration, "reason": "no frames sampled"}

    peak = max(means)
    if peak < req.black_threshold:
        return {
            "ok": False,
            "samples": means,
            "duration": duration,
            "reason": f"all sampled frames near-black (peak luminance {peak} < {req.black_threshold})",
        }
    return {"ok": True, "samples": means, "duration": duration, "reason": None}


@app.post("/render/video-use")
def render_video_use(req: VideoUseRequest):
    """原始素材剪辑：按结构化 spec（trim + 统一画幅 + concat + 可选 bgm）输出 H.264/AAC MP4。

    剪辑进程以独立进程组启动（start_new_session=True），失败/超时后收割整个进程组，
    与 remotion/hyperframes 端点同一安全模式；实际 ffmpeg 逻辑在 video_use/edit_video.py，
    这里通过 CLI 子进程调用，避免重编码阻塞主进程内存。
    """
    if not _is_under_assets(req.output):
        raise HTTPException(status_code=400, detail="Output path must be under ASSETS_DIR")
    if not req.clips:
        raise HTTPException(status_code=400, detail="clips must not be empty")
    for clip in req.clips:
        if not _is_under_assets(clip.path):
            raise HTTPException(status_code=400, detail=f"Clip path must be under ASSETS_DIR: {clip.path}")
        if not os.path.exists(clip.path):
            return {"success": False, "output_url": None, "error": f"clip file missing: {clip.path}"}
    if req.bgm_path:
        if not _is_under_assets(req.bgm_path):
            raise HTTPException(status_code=400, detail=f"bgm_path must be under ASSETS_DIR: {req.bgm_path}")
        if not os.path.exists(req.bgm_path):
            return {"success": False, "output_url": None, "error": f"bgm file missing: {req.bgm_path}"}

    os.makedirs(os.path.dirname(os.path.abspath(req.output)), exist_ok=True)

    spec = {
        "width": req.width,
        "height": req.height,
        "fps": req.fps,
        "clips": [c.model_dump() for c in req.clips],
        "bgm_path": req.bgm_path,
        "bgm_volume": req.bgm_volume,
        "output": req.output,
    }
    spec_path = None
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "video_use", "edit_video.py")
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".spec.json", dir=os.path.dirname(os.path.abspath(req.output)), delete=False
        ) as f:
            json.dump(spec, f)
            spec_path = f.name

        proc = subprocess.Popen(
            [sys.executable, script, spec_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True,
        )
        try:
            out, err = proc.communicate(timeout=300)
        except subprocess.TimeoutExpired:
            _reap_process_group(proc)
            try:
                proc.communicate(timeout=5)
            except Exception:
                pass
            return {"success": False, "output_url": None, "error": "video-use render timed out after 300 seconds"}

        if proc.returncode != 0:
            _reap_process_group(proc)
            logger.error("video-use render failed: %s", (err or out)[:500])
            return {"success": False, "output_url": None, "error": (err or out or "video-use render failed").strip()}

        if not os.path.exists(req.output) or os.path.getsize(req.output) < 1024:
            return {"success": False, "output_url": None, "error": "video-use finished but output MP4 is missing or too small"}
        return {"success": True, "output_url": _relative_url(req.output), "error": None}
    except FileNotFoundError:
        return {"success": False, "output_url": None, "error": "python interpreter not found for video-use CLI"}
    finally:
        if spec_path and os.path.exists(spec_path):
            try:
                os.remove(spec_path)
            except OSError:
                pass
