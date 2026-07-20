import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.celery_app import celery_app
from app.config import ASSETS_DIR, RENDERER_URL
from app.database import SessionLocal
from app.models import MediaAsset, Project, RenderJob, User
from app.rendering.provider import RenderRequest
from app.rendering.service import RenderService

logger = logging.getLogger(__name__)


def _append_log(job: RenderJob, message: str):
    """Append a human-readable step log to the render job.

    Builds a NEW list on every call instead of appending in place: SQLAlchemy
    cannot detect in-place mutations of a JSON column, so the old code only ever
    flushed the very first entry and the SSE stream looked frozen.
    """
    entry = {"time": datetime.now(timezone.utc).isoformat(), "message": message}
    job.logs = (job.logs or []) + [entry]


def _project_has_output(db, project: Project) -> bool:
    return (
        db.query(RenderJob)
        .filter(
            RenderJob.project_id == project.id,
            RenderJob.status == "completed",
            RenderJob.output_url.isnot(None),
        )
        .first()
        is not None
    )


def _guard_cancel(db, job: RenderJob, project: Project) -> bool:
    """Re-read job status and finalize if the user cancelled.

    Returns True when the job was cancelled (already finalized: status left as
    'cancelled', project moved out of 'generating', a log line appended) so the
    caller should stop immediately without retrying or overwriting the result.
    """
    db.refresh(job)
    if job.status != "cancelled":
        return False
    if project and project.status == "generating":
        project.status = "ready" if _project_has_output(db, project) else "draft"
    _append_log(job, "已停止：任务被取消")
    db.commit()
    return True


def _persist_composition_json(project: Project, comp_json: dict, db) -> dict:
    """Persist a composition JSON onto the project's Composition model."""
    from app.models import Track, Clip
    from app.routers.compositions import build_composition_json

    if project.composition is None:
        return comp_json

    for track in project.composition.tracks:
        db.delete(track)
    db.flush()

    max_end = 0.0
    for t_data in comp_json.get("tracks", []):
        track = Track(
            composition_id=project.composition.id,
            type=t_data["type"],
            index=t_data["index"],
            name=t_data.get("name"),
        )
        db.add(track)
        db.flush()
        for c_data in t_data.get("clips", []):
            start = float(c_data.get("start_time", 0) or 0)
            duration = float(c_data.get("duration", 5) or 5)
            max_end = max(max_end, start + duration)
            clip = Clip(
                track_id=track.id,
                asset_id=c_data.get("asset_id"),
                start_time=start,
                duration=duration,
                position=c_data.get("position", {}),
                style=c_data.get("style", {}),
                text_content=c_data.get("text_content"),
            )
            db.add(clip)

    if max_end > 0:
        project.composition.duration = max(1, int(max_end))
    if "width" in comp_json:
        project.composition.width = int(comp_json["width"])
    if "height" in comp_json:
        project.composition.height = int(comp_json["height"])

    db.commit()
    db.refresh(project)
    return build_composition_json(project.composition)


def _maybe_plan(project: Project, prompt: Optional[str], db) -> dict:
    """若当前时间线仍是默认空壳，则调用 AI 规划并构建时间线（不落库，由调用方绑定素材后统一持久化）。"""
    from app.agent import plan_video, build_composition
    from app.routers.compositions import build_composition_json

    comp_json = build_composition_json(project.composition) if project.composition else {"tracks": []}

    tracks = comp_json.get("tracks", [])
    is_default = False
    if not tracks:
        is_default = True
    elif len(tracks) == 2 and {t.get("type") for t in tracks} == {"video", "text"}:
        # 只有合成仍完全是默认占位（无真实文案、无绑定素材）时才自动重新规划，
        # 避免用户编辑后因残留占位文字而被覆盖。
        all_clips = []
        for t in tracks:
            all_clips.extend(t.get("clips", []))
        if all_clips and all(
            (c.get("text_content") or "") in ("", "ClipWorks")
            and not c.get("asset_id")
            and not (c.get("style") or {}).get("visual")
            for c in all_clips
        ):
            is_default = True

    if is_default:
        plan = plan_video(
            source_url=project.source_url,
            user_prompt=prompt,
            target_format=getattr(project, "target_format", None),
        )
        comp_json = build_composition(plan)

    return comp_json


def _stock_queries(plan: Optional[dict], prompt: Optional[str]) -> Optional[list[str]]:
    """从已确认方案或用户一句话中提取配图检索词，供自动配图兜底使用。"""
    if isinstance(plan, dict):
        needed = plan.get("assets_needed")
        if isinstance(needed, list):
            qs = [str(x).strip() for x in needed if isinstance(x, str) and x.strip()][:5]
            if qs:
                return qs
    if prompt and prompt.strip():
        return [prompt.strip()]
    return None


_FORMAT_DIMS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}


def _apply_target_format(comp_json: dict, target_format: Optional[str]) -> dict:
    """强制成片画幅与项目 target_format 一致，作为 LLM/方案忽略画幅时的安全网。

    画幅变化时按轴比例缩放所有 clip 的 position；字号按纵向比例缩放
    （本仓库字号语义相对画布高度，如 composer 的 height*0.08）。
    """
    dims = _FORMAT_DIMS.get(target_format or "")
    if not dims:
        return comp_json
    w, h = dims
    old_w, old_h = comp_json.get("width"), comp_json.get("height")
    if not old_w or not old_h or (old_w, old_h) == (w, h):
        comp_json["width"], comp_json["height"] = w, h
        return comp_json
    sx, sy = w / old_w, h / old_h
    for track in comp_json.get("tracks", []):
        for clip in track.get("clips", []):
            pos = clip.get("position")
            if isinstance(pos, dict):
                pos["x"] = round(pos.get("x", 0) * sx)
                pos["width"] = round(pos.get("width", old_w) * sx)
                pos["y"] = round(pos.get("y", 0) * sy)
                pos["height"] = round(pos.get("height", old_h) * sy)
            style = clip.get("style")
            if isinstance(style, dict) and isinstance(style.get("fontSize"), (int, float)):
                style["fontSize"] = max(12, round(style["fontSize"] * sy))
    comp_json["width"], comp_json["height"] = w, h
    return comp_json


def _build_assets(project: Project, db, stock_queries: Optional[list[str]] = None) -> dict:
    """收集项目可用图片素材：既有上传 + 网页抓取 + 自动配图，全部落库并返回 id/url 池。

    返回字段：
      background_image: 首张图 url（兼容旧 HTML 兜底）
      image_ids:        素材 id 列表（用于绑定到 visual clip）
      images:           {asset_id: /api/static url}（HyperFrames 预览用）
      scraped:          原始抓取结果（标题/描述等供 AI 参考）
    """
    from app.config import ASSETS_BASE_URL, ASSETS_DIR
    from app.services.assets import resolve_image_asset, persist_asset
    from app.services.scraper import scrape_url
    import os

    def _static_url(local_path: str) -> str:
        rel = os.path.relpath(local_path, ASSETS_DIR).replace(os.path.sep, "/")
        return f"/api/static/{rel}"

    assets: dict = {"image_ids": [], "images": {}}
    seen = set()

    def _add(asset_id: str, local_path: str):
        if not asset_id or asset_id in seen or not local_path:
            return
        seen.add(asset_id)
        assets["image_ids"].append(asset_id)
        assets["images"][asset_id] = _static_url(local_path)

    # 1) 用户已上传到项目的图片（upload/pexels），优先使用。
    for a in getattr(project, "assets", []) or []:
        if a.type == "image" and a.local_path:
            _add(a.id, a.local_path)

    # 2) 抓取 source_url 的图片并落库（最多凑到 6 张）。
    scraped = {}
    if project.source_url:
        scraped = scrape_url(project.source_url) or {}
        for img_url in scraped.get("images", []) or []:
            if len(assets["image_ids"]) >= 6:
                break
            try:
                asset_data = resolve_image_asset(img_url, project.id, db)
                local_path = asset_data.get("local_path")
                if not local_path:
                    continue
                media = persist_asset(project.id, asset_data, db)
                _add(media.id, local_path)
            except Exception as exc:
                logger.warning("collect scraped image failed %s: %s", img_url, exc)

    # 3) 素材仍不足 3 张时按主题自动配图：有 PEXELS_API_KEY 走 Pexels 主题搜索，
    # 无密钥用 Lorem Picsum 确定性真实照片兜底——「一句话成片」不再只剩渐变文字卡。
    if len(assets["image_ids"]) < 3:
        try:
            from app.services.stock_images import fetch_stock_images
            queries = stock_queries or [project.title or "product marketing"]
            for media in fetch_stock_images(project, queries, db, limit=5 - len(assets["image_ids"])):
                if media is not None and getattr(media, "local_path", None):
                    _add(media.id, media.local_path)
        except Exception as exc:  # noqa: BLE001 - 配图失败不阻断渲染
            logger.warning("stock image top-up failed: %s", exc)

    if assets["image_ids"]:
        first_id = assets["image_ids"][0]
        assets["background_image"] = assets["images"][first_id]
    assets["scraped"] = scraped
    return assets


def _collect_raw_assets(project: Project) -> list[str]:
    import os
    paths = []
    for asset in project.assets:
        if asset.type == "video" and asset.local_path:
            paths.append(os.path.abspath(asset.local_path))
    return paths


def _write_project_html(project_id: str, composition: dict, assets: dict) -> tuple[str, str]:
    import os
    from app.agent import generate_html
    project_dir = os.path.join(ASSETS_DIR, project_id)
    os.makedirs(project_dir, exist_ok=True)
    html_path = os.path.join(project_dir, "index.html")
    html = generate_html(composition, assets)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    rel = os.path.relpath(html_path, ASSETS_DIR).replace(os.path.sep, "/")
    return html_path, f"/api/static/{rel}"


def _derive_scenes(comp_json: dict) -> list[dict]:
    """从 composition 中提取 scene 列表。优先使用 plan.scenes，否则从 text/video 轨推导。"""
    plan = (comp_json.get("metadata") or {}).get("plan") or {}
    scenes = plan.get("scenes")
    if isinstance(scenes, list) and scenes:
        return [dict(s) for s in scenes]

    # 无 plan.scenes 时，从 text 轨 + video 轨的 clip 边界推导
    clips: list[dict] = []
    for track in comp_json.get("tracks", []) or []:
        ttype = track.get("type")
        if ttype not in {"text", "video", "image", "overlay"}:
            continue
        for clip in track.get("clips", []) or []:
            clips.append({
                "start": float(clip.get("start_time", 0) or 0),
                "duration": float(clip.get("duration", 5) or 5),
                "text": clip.get("text_content", ""),
                "visual": (clip.get("style") or {}).get("visual", ""),
                "transition": (clip.get("style") or {}).get("transition", "fade"),
                "lower_third": (clip.get("style") or {}).get("lower_third", ""),
                "visual_type": (clip.get("style") or {}).get("visual_type", "text"),
                "narration": (clip.get("style") or {}).get("narration", ""),
                "shot": (clip.get("style") or {}).get("shot", ""),
            })
    clips.sort(key=lambda c: c["start"])
    # 合并同一 start 的 clip
    merged: list[dict] = []
    for c in clips:
        if merged and abs(merged[-1]["start"] - c["start"]) < 0.1:
            if c["text"] and not merged[-1]["text"]:
                merged[-1]["text"] = c["text"]
            if c["visual"] and not merged[-1]["visual"]:
                merged[-1]["visual"] = c["visual"]
        else:
            merged.append(dict(c))
    return merged


def _scene_cache_key(project_id: str, idx: int, scene: dict, composition: dict) -> str:
    """基于 scene 内容与项目画幅生成缓存键，用于复用未改动的 scene 片段。"""
    style = (composition.get("metadata") or {}).get("style", "")
    payload = json.dumps({"project_id": project_id, "idx": idx, "scene": scene, "style": style}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def _write_scene_htmls(
    project_id: str,
    scenes: list[dict],
    composition: dict,
    assets: dict,
    job: RenderJob,
    db,
) -> dict[int, str]:
    """为每个 scene 生成独立 HTML，返回 index -> html_path 映射。"""
    from app.agent import generate_scene_html

    render_dir = os.path.join(ASSETS_DIR, project_id, f"render_{job.id}")
    os.makedirs(render_dir, exist_ok=True)
    html_paths: dict[int, str] = {}
    for idx, scene in enumerate(scenes):
        html_path = os.path.join(render_dir, f"scene_{idx}.html")
        try:
            html = generate_scene_html(scene, composition, assets)
        except Exception as exc:
            logger.warning("generate_scene_html failed for scene %d: %s", idx, exc)
            html = generate_scene_html(scene, composition, {})
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        html_paths[idx] = html_path
        _append_log(job, f"场景 HTML 已生成 {idx + 1}/{len(scenes)}")
        db.commit()
    return html_paths


def _prerender_scenes(
    project_id: str,
    scenes: list[dict],
    html_paths: dict[int, str],
    job: RenderJob,
    db,
) -> dict[int, tuple[str, bool]]:
    """调用 renderer /render/hyperframes 把每个 scene HTML 渲染成 MP4。

    返回 index -> (scene_asset_id, fallback_to_remotion) 的映射。
    fallback_to_remotion=True 表示该 scene HF 渲染失败，应让 Remotion 用内置动效渲染。
    """
    from app.config import ASSETS_BASE_URL

    render_dir = os.path.join(ASSETS_DIR, project_id, f"render_{job.id}")
    os.makedirs(render_dir, exist_ok=True)
    results: dict[int, tuple[str, bool]] = {}

    concurrency = int(os.getenv("HF_CONCURRENCY", "1"))

    async def _render_one(idx: int, html_path: str) -> tuple[int, str, bool]:
        output_path = os.path.join(render_dir, f"scene_{idx}.mp4")
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{RENDERER_URL}/render/hyperframes",
                    json={"html_path": html_path, "output_path": output_path},
                )
                data = resp.json()
                if data.get("success"):
                    return idx, output_path, False
        except Exception as exc:
            logger.warning("HF prerender scene %d failed: %s", idx, exc)
        return idx, "", True

    async def _run_all():
        sem = asyncio.Semaphore(max(1, concurrency))

        async def bounded(idx: int, html_path: str):
            async with sem:
                return await _render_one(idx, html_path)

        tasks = [bounded(idx, html_paths[idx]) for idx in range(len(scenes))]
        return await asyncio.gather(*tasks)

    outputs = asyncio.run(_run_all())

    for idx, output_path, fallback in outputs:
        if fallback:
            _append_log(job, f"场景 {idx + 1}/{len(scenes)} HF 预渲染失败，将回退 Remotion 默认动效")
            results[idx] = ("", True)
            db.commit()
            continue

        # 注册为 MediaAsset，方便 Remotion 通过 asset_id 引用
        asset = MediaAsset(
            project_id=project_id,
            type="video",
            source="generated",
            local_path=os.path.abspath(output_path),
            metadata_={"name": f"第 {idx + 1} 镜动效预览", "scene_index": idx},
        )
        db.add(asset)
        db.flush()
        results[idx] = (asset.id, False)
        _append_log(job, f"场景预渲染完成 {idx + 1}/{len(scenes)}")
        db.commit()

    return results


def _build_assembly_composition(
    comp_json: dict,
    scenes: list[dict],
    scene_results: dict[int, tuple[str, bool]],
    project,
) -> dict:
    """把原 composition 中每个 scene 范围内的 video/image clip 替换为预渲染的 scene MP4。

    fallback scene（HF 失败）不插入 video clip，保留原 visual clip 让 Remotion 自行渲染。
    """
    import copy

    assembly = copy.deepcopy(comp_json)
    tracks = assembly.get("tracks", []) or []
    new_tracks: list[dict] = []

    for track in tracks:
        ttype = track.get("type")
        if ttype not in {"video", "image"}:
            new_tracks.append(track)
            continue

        kept_clips: list[dict] = []
        for clip in track.get("clips", []) or []:
            c_start = float(clip.get("start_time", 0) or 0)
            c_dur = float(clip.get("duration", 5) or 5)
            c_end = c_start + c_dur
            # 判断该 clip 是否完全落在某个 scene 内
            matched_scene_idx = None
            for s_idx, scene in enumerate(scenes):
                s_start = float(scene.get("start", 0))
                s_dur = float(scene.get("duration", scene.get("dur", 5)))
                s_end = s_start + s_dur
                if abs(c_start - s_start) < 0.1 and abs(c_end - s_end) < 0.1:
                    matched_scene_idx = s_idx
                    break
            if matched_scene_idx is not None and matched_scene_idx in scene_results:
                asset_id, fallback = scene_results[matched_scene_idx]
                if fallback:
                    # 保留原 clip，让 Remotion 用 KenBurns/MotionText 兜底
                    kept_clips.append(clip)
                else:
                    # 同一 scene 只保留一个 video clip；后续同 scene clip 跳过
                    if not any(
                        c.get("style", {}).get("scene_index") == matched_scene_idx
                        for c in kept_clips
                    ):
                        scene = scenes[matched_scene_idx]
                        kept_clips.append({
                            "start_time": scene.get("start", 0),
                            "duration": scene.get("duration", 5),
                            "asset_id": asset_id,
                            "position": {"x": 0, "y": 0, "width": assembly.get("width", 1920), "height": assembly.get("height", 1080)},
                            "style": {
                                "transition": scene.get("transition", "fade"),
                                "scene_index": matched_scene_idx,
                                "source": "hyperframes",
                            },
                            "text_content": "",
                        })
            else:
                kept_clips.append(clip)

        if kept_clips:
            new_track = dict(track)
            new_track["clips"] = kept_clips
            new_tracks.append(new_track)

    # 把未匹配到 video/image 轨的 scene 单独插入一条 video 轨（兜底）
    orphan_scene_clips = []
    for s_idx, scene in enumerate(scenes):
        if s_idx not in scene_results:
            continue
        asset_id, fallback = scene_results[s_idx]
        if fallback:
            continue
        # 简单检查是否已有该 scene 的 clip
        if not any(
            c.get("style", {}).get("scene_index") == s_idx
            for t in new_tracks for c in t.get("clips", [])
        ):
            orphan_scene_clips.append({
                "start_time": scene.get("start", 0),
                "duration": scene.get("duration", 5),
                "asset_id": asset_id,
                "position": {"x": 0, "y": 0, "width": assembly.get("width", 1920), "height": assembly.get("height", 1080)},
                "style": {"transition": scene.get("transition", "fade"), "scene_index": s_idx, "source": "hyperframes"},
                "text_content": "",
            })
    if orphan_scene_clips:
        new_tracks.insert(0, {"type": "video", "index": -1, "name": "HF Scenes", "clips": orphan_scene_clips})

    assembly["tracks"] = new_tracks
    # 标记总装 composition 来源，便于 Remotion 端识别
    assembly["metadata"] = assembly.get("metadata") or {}
    assembly["metadata"]["engine"] = "hybrid"
    return assembly


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30, time_limit=900, soft_time_limit=840)
def render_video_task(
    self,
    job_id: str,
    project_id: str,
    prompt: Optional[str] = None,
    engine: Optional[str] = None,
    plan: Optional[dict] = None,
):
    job = None
    project = None
    db = SessionLocal()
    try:
        job = db.query(RenderJob).filter(RenderJob.id == job_id).first()
        project = db.query(Project).filter(Project.id == project_id).first()
        if not job or not project:
            return
        # Honour a cancellation that landed before the worker picked this job up:
        # leave it as-is and never move it to running/completed.
        if job.status in ("cancelled", "completed", "failed"):
            return

        job.status = "running"
        job.progress = 10
        job.composition_id = project.composition.id if project.composition else None
        _append_log(job, "已加入生成队列，开始执行")
        db.commit()

        if _guard_cancel(db, job, project):
            return

        # 先收集素材（既有上传图 + 网页抓取图落库），再绑定到 visual clip，
        # 这是「真实素材进画面」的关键——否则 AI 时间线再漂亮也只能画渐变块。
        _append_log(job, "抓取网页图片与品牌素材…")
        assets = _build_assets(project, db, stock_queries=_stock_queries(plan, prompt))
        raw_assets = _collect_raw_assets(project)
        job.progress = 20
        _append_log(job, f"原始视频素材清点完成，共 {len(raw_assets)} 条可剪辑片段")
        db.commit()
        _append_log(job, f"素材收集完成，可用图片 {len(assets.get('image_ids', []))} 张")
        job.progress = 30
        db.commit()

        if _guard_cancel(db, job, project):
            return

        # If a plan is provided (Agent approval flow), build the composition now.
        if plan:
            from app.agent import build_composition
            _append_log(job, "AI 导演根据已确认方案构建时间线…")
            db.commit()  # flush heartbeat so the SSE stream shows it during the slow build
            comp_json = build_composition(plan)
        else:
            _append_log(job, "分析现有素材并规划成片，AI 规划可能需要 30-60 秒…")
            db.commit()  # flush heartbeat so the SSE stream shows it during planning
            comp_json = _maybe_plan(project, prompt, db)

        # 画幅安全网：LLM/已确认方案偶尔忽略项目 target_format（如 9:16 项目出 16:9），
        # 在绑定素材前统一收口，避免竖屏项目被渲染成横屏、位置错位。
        comp_json = _apply_target_format(comp_json, getattr(project, "target_format", None))

        # 先把上传的视频素材绑定到 video 轨 clip（「上传素材→AI 剪辑」链路），
        # 再把图片绑定到剩余缺失 asset_id 的 visual clip（不覆盖 AI 已指定的），
        # 顺序不能反：图片绑定会把 video 轨矫正为 image 轨，抢占后视频就进不了画面。
        from app.agent.asset_bind import bind_images_to_composition, bind_videos_to_composition
        video_ids = [a.id for a in project.assets if a.type == "video" and a.local_path]
        bind_videos_to_composition(comp_json, video_ids)
        bind_images_to_composition(comp_json, assets.get("image_ids", []))
        job.progress = 40
        _append_log(job, "时间线草稿已生成，图片素材已绑定到镜头")
        db.commit()

        # 生成「配乐+旁白」音轨并挂载为一条贯穿全片的 audio 轨：TTS 旁白 real-when-available，
        # 无密钥时退到程序化 BGM 兜底，确保最终 MP4 一定混入一条音轨（Remotion 封装为 AAC）。
        _append_log(job, "合成旁白与配乐音轨（无 TTS 密钥时使用确定性配乐兜底）…")
        try:
            from app.services.audio_track import attach_audio_track, build_soundtrack
            audio_asset_id = build_soundtrack(project, comp_json, db)
            if audio_asset_id:
                attach_audio_track(comp_json, audio_asset_id)
                _append_log(job, "音轨已合成（旁白/配乐已混入时间线）")
            else:
                _append_log(job, "音轨合成被跳过：渲染服务不可用，成片将不含音轨")
        except Exception as audio_exc:  # noqa: BLE001 - 音频失败不阻断渲染
            logger.warning("audio track build failed for job=%s: %s", job_id, audio_exc)
            _append_log(job, f"音轨合成失败（已跳过）：{str(audio_exc)[:120]}")
        db.commit()

        comp_json = _persist_composition_json(project, comp_json, db)
        _append_log(job, f"时间线构建完成，共 {len(comp_json.get('tracks', []))} 条轨道")
        job.progress = 50
        db.commit()

        if _guard_cancel(db, job, project):
            return

        job.progress = 60
        _append_log(job, "时间线已落库，进入动画合成阶段")
        db.commit()

        _append_log(job, "生成 HyperFrames HTML 动画…")
        try:
            html_path, html_url = _write_project_html(project_id, comp_json, assets)
            job.html_output_path = html_path
            job.html_output_url = html_url
            _append_log(job, "HTML 预览已生成")
        except Exception as html_exc:
            logger.warning("HTML generation failed for job=%s: %s", job_id, html_exc)
            _append_log(job, f"HTML 生成失败：{str(html_exc)[:120]}，将使用兜底 HTML")
            # Try once more with a minimal fallback HTML so rendering can still proceed.
            html_path, html_url = _write_project_html(project_id, comp_json, {})
            job.html_output_path = html_path
            job.html_output_url = html_url
        job.progress = 70
        db.commit()

        logger.info(f"Render request engine={engine!r} for job={job_id}")
        _append_log(
            job,
            f"调用渲染引擎 {engine or 'auto'} 合成视频，引擎较慢时这一步可能需要 1-2 分钟…",
        )
        # Flush the heartbeat immediately so the SSE stream shows it; otherwise
        # the user stares at the previous log line until the renderer returns.
        db.commit()

        if _guard_cancel(db, job, project):
            return

        request = RenderRequest(
            engine=engine,
            composition=comp_json,
            assets=assets,
            raw_assets=raw_assets,
            user_prompt=prompt,
            source_url=project.source_url,
            engine_hint=plan.get("engine_hint") if isinstance(plan, dict) else None,
            html_path=html_path,
            html_url=html_url,
        )
        job.progress = 80
        _append_log(job, "渲染请求已发送，引擎正在出片（Remotion 约需 1-3 分钟）…")
        db.commit()
        result = RenderService().render(job, project, request)
        logger.info(f"Render result success={result.success} output_url={result.output_url} error={result.error_message}")

        # A cancellation may have landed while the (blocking) engine call ran.
        # Honour it now and never overwrite the cancelled state with a result.
        if _guard_cancel(db, job, project):
            return

        if result.success:
            job.output_url = result.output_url
            if result.html_output_url:
                job.html_output_url = result.html_output_url
            is_placeholder = bool(result.output_url and "/sample.mp4" in result.output_url)
            job.progress = 90
            _append_log(job, "引擎出片完成，进入成片质量检测")
            db.commit()

            # 抽帧质量闸门：仅对真实成片（非占位）检测黑屏/解码失败；纯色+文案亮度高、不误判。
            qa_failed_reason: Optional[str] = None
            if not is_placeholder:
                from app.rendering.qa import check_render_quality
                output_path = os.path.join(ASSETS_DIR, project.id, "output.mp4")
                qa_ok, qa_reason = check_render_quality(output_path)
                if not qa_ok:
                    _append_log(job, f"质量检测未通过（{qa_reason}），自动重生成一次…")
                    db.commit()
                    retry = RenderService().render(job, project, request)
                    if retry.success and not (retry.output_url and "/sample.mp4" in retry.output_url):
                        qa2_ok, qa2_reason = check_render_quality(output_path)
                        if qa2_ok:
                            result = retry
                            job.output_url = retry.output_url
                            _append_log(job, "质量检测通过（已重生成）")
                        else:
                            qa_failed_reason = qa2_reason
                    else:
                        qa_failed_reason = qa_reason
                else:
                    _append_log(job, "质量检测通过（画面非全黑、解码正常）")

            if qa_failed_reason:
                job.status = "failed"
                project.status = "failed"
                job.error_message = f"出片质量检测未通过：{qa_failed_reason}"
                _append_log(job, f"❌ {job.error_message}，已重试一次仍不合格，不计扣额度")
            else:
                job.status = "completed"
                job.progress = 100
                job.completed_at = datetime.now(timezone.utc)
                project.status = "ready"
                if is_placeholder:
                    _append_log(job, "⚠️ 渲染引擎返回了占位视频，真实渲染可能因环境/浏览器不可用而失败")
                    job.error_message = "渲染引擎返回了占位视频（sample.mp4），请检查 renderer 的 Chromium/Chrome 配置。"
                else:
                    _append_log(job, "视频渲染完成")
                # Deduct one credit per successfully rendered (and QA-passed) video.
                user = db.query(User).filter(User.id == project.user_id).first()
                if user and user.credits > 0:
                    user.credits -= 1
        else:
            job.status = "failed"
            job.error_message = result.error_message
            project.status = "failed"
            _append_log(job, f"渲染失败：{result.error_message}")
        db.commit()
    except Exception as exc:
        logger.exception("Render task failed")
        db.rollback()
        if job:
            job.status = "failed"
            job.error_message = str(exc)
            _append_log(job, f"执行出错：{str(exc)[:200]}")
        if project:
            project.status = "failed"
        db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()
