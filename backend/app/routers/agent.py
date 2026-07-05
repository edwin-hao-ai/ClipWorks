import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.agent import modify_video
from app.database import get_db
from app.models import Project, User, RenderJob
from app.routers.auth import get_current_user
from app.routers.compositions import build_composition_json
from app.routers.renders import render_video_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects/{project_id}/agent", tags=["agent"])


def _require_project(project_id: str, user: User, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this project")
    return project


def _persist_composition(project, comp_json, db):
    from app.models import Track as TrackModel, Clip as ClipModel
    for track in project.composition.tracks:
        db.delete(track)
    db.flush()
    for t_data in comp_json.get("tracks", []):
        track = TrackModel(
            composition_id=project.composition.id,
            type=t_data["type"],
            index=t_data["index"],
            name=t_data.get("name"),
        )
        db.add(track)
        db.flush()
        for c_data in t_data.get("clips", []):
            clip = ClipModel(
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


@router.post("/chat")
def chat_with_agent(
    project_id: str,
    payload: dict,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Chat with the Agent to modify the current composition. Optionally triggers re-render."""
    project = _require_project(project_id, user, db)

    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    if not project.composition:
        raise HTTPException(status_code=404, detail="Composition not found")

    scene_id = payload.get("scene_id")
    should_render = payload.get("render", True)
    current_composition = build_composition_json(project.composition)

    try:
        updated = modify_video(current_composition, message, scene_id=scene_id)
    except Exception as exc:
        logger.exception("Agent chat modification failed")
        raise HTTPException(status_code=500, detail=f"Agent failed: {exc}")

    if not updated or not isinstance(updated, dict):
        raise HTTPException(status_code=500, detail="Agent returned invalid composition")

    _persist_composition(project, updated, db)

    reply = f"已应用修改：{message}"
    if scene_id:
        reply = f"已针对场景调整：{message}"

    # Optionally trigger re-render in the background
    job = None
    if should_render:
        project.status = "generating"
        db.commit()
        job = RenderJob(project_id=project_id, composition_id=project.composition.id, status="queued")
        db.add(job)
        db.commit()
        db.refresh(job)
        background_tasks.add_task(render_video_task, job.id, project_id)

    return {
        "reply": reply,
        "composition": build_composition_json(project.composition),
        "job_id": job.id if job else None,
    }
