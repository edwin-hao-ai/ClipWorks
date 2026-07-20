"""为项目合成生成「配乐+旁白」音轨并落库，供 Remotion 混进最终 MP4。

输出产物：一个浏览器安全的 WAV（PCM 48k stereo），持久化为 MediaAsset(type=audio)。
- 旁白：从文本轨抽取文案，调用可插拔 TTS（无密钥时全部跳过）。
- 配乐：渲染服务用 ffmpeg 程序化生成确定性氛围铺底（永远存在）。
- 闪避：旁白存在时由渲染服务做 sidechain 压缩把 BGM 压低（广播级混音）。

任何一步失败都只记录 warning 并返回 None，绝不让渲染主流程因音频失败而中断。
"""
from __future__ import annotations

import hashlib
import logging
import os
from typing import Optional

import httpx

from app.config import ASSETS_DIR, RENDERER_URL
from app.services.tts import synthesize_narration

logger = logging.getLogger(__name__)

MAX_NARRATION_SEGMENTS = 6


def _composition_duration(comp_json: dict) -> float:
    duration = float(comp_json.get("duration") or 0)
    max_end = 0.0
    for track in comp_json.get("tracks", []) or []:
        for clip in track.get("clips", []) or []:
            start = float(clip.get("start_time", 0) or 0)
            dur = float(clip.get("duration", 0) or 0)
            max_end = max(max_end, start + dur)
    return max(duration, max_end, 1.0)


def _narration_scripts(comp_json: dict) -> list[dict]:
    """从文本轨按时间顺序抽取旁白文案（每镜一条、全局去重、限条数）。

    每个场景（同一 start_time）只保留一条：优先 clip.style.narration（富方案的
    口语化旁白），没有时退回屏上文案。先按场景归并、再按时间截断——之前的实现
    先全量收集再按 start 取前 N 条，早场景的重复条目（主文案 + lower-third 各一条）
    会挤掉晚场景，导致旁白只覆盖前半段、混音随 sidechain 被截短、视频被 mux 裁短。
    """
    by_start: dict[float, dict] = {}
    seen_texts: set[str] = set()
    for track in comp_json.get("tracks", []) or []:
        if track.get("type") != "text":
            continue
        for clip in track.get("clips", []) or []:
            style = clip.get("style") or {}
            narration = (style.get("narration") or "").strip()
            text = narration or (clip.get("text_content") or "").strip()
            if not text or text == "ClipWorks" or text in seen_texts:
                continue
            start = float(clip.get("start_time", 0) or 0)
            existing = by_start.get(start)
            if existing is None:
                by_start[start] = {"text": text, "start": start, "explicit": bool(narration)}
                seen_texts.add(text)
            elif narration and not existing["explicit"]:
                # 同一场景的显式旁白覆盖先遇到的屏上文案兜底
                seen_texts.discard(existing["text"])
                by_start[start] = {"text": text, "start": start, "explicit": True}
                seen_texts.add(text)
    scripts = sorted(by_start.values(), key=lambda s: s["start"])
    return [{"text": s["text"], "start": s["start"]} for s in scripts[:MAX_NARRATION_SEGMENTS]]


def build_soundtrack(project, comp_json: dict, db) -> Optional[str]:
    """生成并落库音轨，返回 MediaAsset.id；失败返回 None。"""
    from app.models import MediaAsset

    project_dir = os.path.join(ASSETS_DIR, project.id)
    narr_dir = os.path.join(project_dir, "narration")
    os.makedirs(narr_dir, exist_ok=True)

    duration = _composition_duration(comp_json)
    scripts = _narration_scripts(comp_json)

    narration_payload: list[dict] = []
    for i, script in enumerate(scripts):
        seg_path = os.path.join(narr_dir, f"seg_{i}.wav")
        if synthesize_narration(script["text"], seg_path):
            narration_payload.append({"path": seg_path, "start": script["start"]})

    if scripts and not narration_payload:
        logger.info("TTS unavailable for project=%s; falling back to BGM-only bed", project.id)

    seed = int(hashlib.sha1(project.id.encode()).hexdigest(), 16) % 100
    output_path = os.path.join(project_dir, "soundtrack.wav")

    try:
        resp = httpx.post(
            f"{RENDERER_URL}/render/soundtrack",
            json={
                "output_path": output_path,
                "duration": duration,
                "narration": narration_payload,
                "bgm_style": "ambient",
                "seed": seed,
            },
            timeout=320,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001 - 音频失败不阻断渲染
        logger.warning("soundtrack request failed for project=%s: %s", project.id, exc)
        return None

    if not data.get("success"):
        logger.warning("soundtrack mix failed for project=%s: %s", project.id, data.get("error"))
        return None

    metadata = {
        "has_narration": bool(narration_payload),
        "narration_segments": len(narration_payload),
        "bgm_style": "ambient",
        "duration": duration,
    }
    # 音轨文件名固定（soundtrack.wav），重复渲染会覆盖同一文件；
    # 资产行必须复用，否则素材库里每次渲染都多出一条同名重复记录。
    existing = (
        db.query(MediaAsset)
        .filter(MediaAsset.project_id == project.id, MediaAsset.local_path == output_path)
        .first()
    )
    if existing:
        existing.metadata_ = metadata
        db.commit()
        return existing.id

    asset = MediaAsset(
        project_id=project.id,
        type="audio",
        source="generated",
        local_path=output_path,
        metadata_=metadata,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset.id


def attach_audio_track(comp_json: dict, asset_id: str) -> None:
    """在 comp_json 里挂载/替换一条贯穿全片的 audio 轨（不改动其它轨道）。"""
    duration = _composition_duration(comp_json)
    tracks = comp_json.setdefault("tracks", [])
    # 去掉旧的 audio 轨，避免重复叠加。
    tracks = [t for t in tracks if t.get("type") != "audio"]
    max_index = max((int(t.get("index", 0)) for t in tracks), default=-1)
    tracks.append(
        {
            "type": "audio",
            "index": max_index + 1,
            "name": "soundtrack",
            "clips": [
                {
                    "asset_id": asset_id,
                    "start_time": 0,
                    "duration": duration,
                    "position": {},
                    "style": {},
                }
            ],
        }
    )
    comp_json["tracks"] = tracks
