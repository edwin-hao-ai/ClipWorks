import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from app.agent import plan_video, build_composition
from app.database import get_db, SessionLocal
from app.models import Project, RenderJob, User, Track, Clip
from app.rendering.provider import RenderRequest
from app.rendering.service import RenderService
from app.routers.auth import get_current_user
from app.routers.compositions import build_composition_json
from app.services.assets import resolve_image_asset, persist_asset
from app.services.scraper import scrape_url

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects/{project_id}/renders", tags=["renders"])


def _require_project(project_id: str, user: User, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this project")
    return project


def _is_default_seeded_composition(comp: dict) -> bool:
    """Detect whether the composition is still the seeded default placeholder."""
    tracks = comp.get("tracks", [])
    if not tracks:
        return True
    if len(tracks) != 2:
        return False
    types = {t.get("type") for t in tracks}
    if types != {"video", "text"}:
        return False
    for t in tracks:
        if t.get("type") == "text":
            for c in t.get("clips", []):
                if c.get("text_content") == "ClipWorks":
                    return True
    return False


def _persist_composition_tracks(project: Project, comp_json: dict, db: Session) -> None:
    """Replace the project's composition tracks with the provided composition JSON."""
    if project.composition is None:
        return
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


def _maybe_plan_and_persist(project: Project, prompt: Optional[str], db: Session) -> dict:
    """If the composition is still the default placeholder, plan and persist a new one."""
    comp_json = build_composition_json(project.composition) if project.composition else {"tracks": []}

    if _is_default_seeded_composition(comp_json):
        plan = plan_video(source_url=project.source_url, user_prompt=prompt)
        comp_json = build_composition(plan)
        _persist_composition_tracks(project, comp_json, db)
        comp_json = build_composition_json(project.composition)

    return comp_json


def _build_assets(project: Project, db: Session) -> dict:
    """Scrape the project's source URL and resolve the first image asset."""
    from app.config import ASSETS_DIR

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
    """Collect absolute paths of uploaded video assets for the video-use engine."""
    paths = []
    for asset in project.assets:
        if asset.type == "video" and asset.local_path:
            abs_path = os.path.abspath(asset.local_path)
            paths.append(abs_path)
    return paths


async def _render_video_task(job_id: str, project_id: str, prompt: Optional[str], engine: Optional[str]):
    db = SessionLocal()
    try:
        job = db.query(RenderJob).filter(RenderJob.id == job_id).first()
        project = db.query(Project).filter(Project.id == project_id).first()
        if not job or not project:
            return

        comp_json = _maybe_plan_and_persist(project, prompt, db)
        assets = _build_assets(project, db)
        raw_assets = _collect_raw_assets(project)

        request = RenderRequest(
            engine=engine,
            composition=comp_json,
            assets=assets,
            raw_assets=raw_assets,
            user_prompt=prompt,
            source_url=project.source_url,
        )
        result = await RenderService().render(job, project, request)
        if result.success:
            job.status = "completed"
            job.progress = 100
            job.output_url = result.output_url
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
    finally:
        db.close()


def render_video_task(job_id: str, project_id: str, prompt: Optional[str] = None, engine: Optional[str] = None):
    asyncio.run(_render_video_task(job_id, project_id, prompt, engine))


@router.post("/generate", status_code=202)
def generate_video(
    project_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _require_project(project_id, user, db)
    project.status = "generating"
    db.commit()

    composition_id = project.composition.id if project.composition else None
    job = RenderJob(project_id=project_id, composition_id=composition_id, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(render_video_task, job.id, project_id)
    return {"job_id": job.id, "status": "queued"}


@router.post("/agent-generate", status_code=202)
def agent_generate_video(
    project_id: str,
    data: dict,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Regenerate video using the Agent, optionally guided by a user prompt and engine choice."""
    project = _require_project(project_id, user, db)
    prompt = data.get("prompt") if isinstance(data, dict) else None
    engine = data.get("engine") if isinstance(data, dict) else None

    project.status = "generating"
    db.commit()

    composition_id = project.composition.id if project.composition else None
    job = RenderJob(project_id=project_id, composition_id=composition_id, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(render_video_task, job.id, project_id, prompt, engine)
    return {"job_id": job.id, "status": "queued"}


@router.get("/{job_id}")
def get_render(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(RenderJob).filter(RenderJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Render job not found")
    if job.project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this project")
    return {
        "id": job.id,
        "status": job.status,
        "progress": job.progress,
        "output_url": job.output_url,
        "html_output_url": job.html_output_url,
        "error_message": job.error_message,
    }
