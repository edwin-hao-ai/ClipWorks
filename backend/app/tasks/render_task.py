import logging
from datetime import datetime, timezone
from typing import Optional

from app.agent import generate_html
from app.celery_app import celery_app
from app.config import ASSETS_DIR
from app.database import SessionLocal
from app.models import Project, RenderJob
from app.rendering.provider import RenderRequest
from app.rendering.service import RenderService

logger = logging.getLogger(__name__)


def _maybe_plan_and_persist(project: Project, prompt: Optional[str], db) -> dict:
    from app.agent import plan_video, build_composition
    from app.routers.compositions import build_composition_json
    from app.models import Track, Clip

    comp_json = build_composition_json(project.composition) if project.composition else {"tracks": []}

    tracks = comp_json.get("tracks", [])
    is_default = False
    if not tracks:
        is_default = True
    elif len(tracks) == 2 and {t.get("type") for t in tracks} == {"video", "text"}:
        for t in tracks:
            if t.get("type") == "text":
                for c in t.get("clips", []):
                    if c.get("text_content") == "ClipWorks":
                        is_default = True

    if is_default:
        plan = plan_video(source_url=project.source_url, user_prompt=prompt)
        comp_json = build_composition(plan)
        # persist
        if project.composition is not None:
            for track in project.composition.tracks:
                db.delete(track)
            db.flush()
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
                    clip = Clip(
                        track_id=track.id,
                        asset_id=c_data.get("asset_id"),
                        start_time=c_data.get("start_time", 0),
                        duration=c_data.get("duration", 5),
                        position=c_data.get("position", {}),
                        style=c_data.get("style", {}),
                        text_content=c_data.get("text_content"),
                    )
                    db.add(clip)
            db.commit()
            db.refresh(project)
            comp_json = build_composition_json(project.composition)

    return comp_json


def _build_assets(project: Project, db) -> dict:
    from app.config import ASSETS_DIR
    from app.services.assets import resolve_image_asset, persist_asset
    from app.services.scraper import scrape_url
    import os

    assets = {}
    if not project.source_url:
        return assets

    scraped = scrape_url(project.source_url)
    if scraped.get("images"):
        first_image = scraped["images"][0]
        asset_data = resolve_image_asset(first_image, project.id, db)
        local_path = asset_data.get("local_path")
        if local_path:
            persist_asset(project.id, asset_data, db)
            rel = os.path.relpath(local_path, ASSETS_DIR).replace(os.path.sep, "/")
            assets["background_image"] = f"/api/static/{rel}"
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
    project_dir = os.path.join(ASSETS_DIR, project_id)
    os.makedirs(project_dir, exist_ok=True)
    html_path = os.path.join(project_dir, "index.html")
    html = generate_html(composition, assets)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    rel = os.path.relpath(html_path, ASSETS_DIR).replace(os.path.sep, "/")
    return html_path, f"/api/static/{rel}"


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def render_video_task(self, job_id: str, project_id: str, prompt: Optional[str] = None, engine: Optional[str] = None):
    job = None
    project = None
    db = SessionLocal()
    try:
        job = db.query(RenderJob).filter(RenderJob.id == job_id).first()
        project = db.query(Project).filter(Project.id == project_id).first()
        if not job or not project:
            return

        job.status = "running"
        db.commit()

        comp_json = _maybe_plan_and_persist(project, prompt, db)
        assets = _build_assets(project, db)
        raw_assets = _collect_raw_assets(project)

        html_path, html_url = _write_project_html(project_id, comp_json, assets)
        job.html_output_path = html_path
        job.html_output_url = html_url
        db.commit()

        request = RenderRequest(
            engine=engine,
            composition=comp_json,
            assets=assets,
            raw_assets=raw_assets,
            user_prompt=prompt,
            source_url=project.source_url,
        )
        result = RenderService().render(job, project, request)
        if result.success:
            job.status = "completed"
            job.progress = 100
            job.output_url = result.output_url
            if result.html_output_url:
                job.html_output_url = result.html_output_url
            job.completed_at = datetime.now(timezone.utc)
            project.status = "ready"
        else:
            job.status = "failed"
            job.error_message = result.error_message
            project.status = "failed"
        db.commit()
    except Exception as exc:
        logger.exception("Render task failed")
        db.rollback()
        if job:
            job.status = "failed"
            job.error_message = str(exc)
        if project:
            project.status = "failed"
        db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()
