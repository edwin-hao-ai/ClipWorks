import asyncio
import logging
import os
import shutil
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from app.agent import plan_video, build_composition, generate_html
from app.config import ASSETS_DIR
from app.database import get_db, SessionLocal
from app.models import Project, RenderJob, User
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


def _write_project_files(project_id: str, html: str) -> tuple[str, str]:
    project_dir = os.path.join(ASSETS_DIR, project_id)
    os.makedirs(project_dir, exist_ok=True)
    html_path = os.path.join(project_dir, "index.html")
    output_path = os.path.join(project_dir, "output.mp4")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    return html_path, output_path


def _mock_render(job: RenderJob, project: Project, db: Session):
    """Simulate a render for demo/fallback purposes."""
    job.status = "running"
    db.commit()
    try:
        for i in range(1, 6):
            time.sleep(1)
            job.progress = i * 20
            db.commit()
        job.status = "completed"
        job.progress = 100
        job.completed_at = datetime.utcnow()
        job.output_url = "/api/static/sample.mp4"
        job.html_output_url = "/api/static/index.html"
        project.status = "ready"
        db.commit()
    except Exception as exc:
        db.rollback()
        job.status = "failed"
        job.error_message = str(exc)
        project.status = "failed"
        db.commit()


async def _agent_render(job: RenderJob, project: Project, db: Session, prompt: Optional[str] = None):
    """Run the real AI pipeline: plan -> compose -> HTML -> HyperFrames (with fallback)."""
    job.status = "running"
    db.commit()

    try:
        comp_json = build_composition_json(project.composition) if project.composition else {"tracks": []}

        if _is_default_seeded_composition(comp_json) or not comp_json.get("tracks"):
            # Build plan from source URL / user prompt
            plan = plan_video(source_url=project.source_url, user_prompt=prompt)
            comp_json = build_composition(plan)
            # Persist the new composition by clearing tracks and recreating them
            from app.models import Track, Clip
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

        # Gather assets: try to use scraped images from source URL
        assets = {}
        if project.source_url:
            scraped = scrape_url(project.source_url)
            if scraped.get("images"):
                first_image = scraped["images"][0]
                asset_data = resolve_image_asset(first_image, project.id, db)
                if asset_data.get("local_path"):
                    persist_asset(project.id, asset_data, db)
                    assets["background_image"] = "/" + asset_data["local_path"]
                assets["scraped"] = scraped

        html = generate_html(comp_json, assets)
        html_path, output_path = _write_project_files(project.id, html)

        # Update job with HTML output immediately so the user can preview it
        relative_html = f"/api/static/{project.id}/index.html"
        job.html_output_url = relative_html
        job.html_output_path = html_path
        db.commit()

        request = RenderRequest(
            composition=comp_json,
            assets=assets,
            user_prompt=prompt,
            source_url=project.source_url,
        )
        result = await RenderService().render(job, project, request)
        if result.success:
            job.output_url = result.output_url
            job.html_output_url = result.html_output_url
            job.output_path = output_path
            job.status = "completed"
            job.progress = 100
            job.completed_at = datetime.utcnow()
            project.status = "ready"
        else:
            # Fallback: keep HTML preview and use sample MP4 so UI stays usable
            _mock_render(job, project, db)
            job.error_message = result.error_message or "Render failed"
        db.commit()
    except Exception as exc:
        logger.exception("Agent render failed")
        db.rollback()
        _mock_render(job, project, db)


async def _render_video_task(job_id: str, project_id: str, prompt: Optional[str] = None):
    db = SessionLocal()
    try:
        job = db.query(RenderJob).filter(RenderJob.id == job_id).first()
        project = db.query(Project).filter(Project.id == project_id).first()
        if not job or not project:
            return
        # Without a source URL or user prompt, run the mock render so tests and
        # bare projects stay fast and deterministic.
        if not project.source_url and not prompt:
            _mock_render(job, project, db)
        else:
            await _agent_render(job, project, db, prompt=prompt)
    finally:
        db.close()


def render_video_task(job_id: str, project_id: str, prompt: Optional[str] = None):
    asyncio.run(_render_video_task(job_id, project_id, prompt))


def mock_render_task(job_id: str, project_id: str):
    """Kept for compatibility / explicit fallback endpoints."""
    db = SessionLocal()
    try:
        job = db.query(RenderJob).filter(RenderJob.id == job_id).first()
        project = db.query(Project).filter(Project.id == project_id).first()
        if not job or not project:
            return
        _mock_render(job, project, db)
    finally:
        db.close()


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
    """Regenerate video using the Agent, optionally guided by a user prompt."""
    project = _require_project(project_id, user, db)
    prompt = data.get("prompt") if isinstance(data, dict) else None

    project.status = "generating"
    db.commit()

    composition_id = project.composition.id if project.composition else None
    job = RenderJob(project_id=project_id, composition_id=composition_id, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(render_video_task, job.id, project_id, prompt)
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
