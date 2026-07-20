import asyncio
import json
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project, RenderJob, User
from app.routers.auth import get_current_user
from app.tasks.render_task import render_video_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects/{project_id}/renders", tags=["renders"])


def _require_project(project_id: str, user: User, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this project")
    return project


def _check_credits(user: User) -> None:
    """Hard gate: refuse to queue a new render when the user has no credits left.

    Returns HTTP 402 so the frontend can render an inline upgrade prompt instead
    of silently falling back to a placeholder or blowing up the workspace.
    """
    if (user.credits or 0) <= 0:
        raise HTTPException(status_code=402, detail="额度不足，请前往计费页升级套餐")


def _is_placeholder(job: RenderJob) -> bool:
    """True when the render fell back to the MockProvider sample output.

    Derived from output_url so the UI can label placeholder results without
    needing a schema migration.
    """
    return "sample.mp4" in (job.output_url or "")


def _queue_position(job: RenderJob, db: Session) -> int:
    """Return how many jobs are ahead of this one in the worker queue.

    0 means the job is currently being processed. A positive number means
    there are that many jobs ahead of it (including the one currently running).
    """
    if job.status == "running":
        return 0
    if job.status != "queued":
        return 0
    has_running = (
        db.query(RenderJob)
        .filter(RenderJob.status == "running")
        .first()
        is not None
    )
    ahead = (
        db.query(RenderJob)
        .filter(
            RenderJob.status == "queued",
            RenderJob.created_at < job.created_at,
        )
        .count()
    )
    return (1 if has_running else 0) + ahead


@router.post("/generate", status_code=202)
def generate_video(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _require_project(project_id, user, db)
    _check_credits(user)
    project.status = "generating"
    db.commit()

    composition_id = project.composition.id if project.composition else None
    job = RenderJob(project_id=project_id, composition_id=composition_id, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        render_video_task.delay(job.id, project_id)
    except Exception as exc:
        logger.exception("Failed to enqueue render task for project %s", project_id)
        job.status = "failed"
        job.error_message = f"任务入队失败：{exc}"
        project.status = "failed"
        db.commit()
        raise HTTPException(status_code=503, detail="生成队列不可用，请稍后重试")
    return {"job_id": job.id, "status": "queued"}


@router.post("/agent-generate", status_code=202)
def agent_generate_video(
    project_id: str,
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Regenerate video using the Agent, optionally guided by a user prompt and engine choice."""
    project = _require_project(project_id, user, db)
    _check_credits(user)
    prompt = data.get("prompt") if isinstance(data, dict) else None
    engine = data.get("engine") if isinstance(data, dict) else None

    project.status = "generating"
    db.commit()

    composition_id = project.composition.id if project.composition else None
    job = RenderJob(project_id=project_id, composition_id=composition_id, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        render_video_task.delay(job.id, project_id, prompt, engine)
    except Exception as exc:
        logger.exception("Failed to enqueue agent render task for project %s", project_id)
        job.status = "failed"
        job.error_message = f"任务入队失败：{exc}"
        project.status = "failed"
        db.commit()
        raise HTTPException(status_code=503, detail="生成队列不可用，请稍后重试")
    return {"job_id": job.id, "status": "queued"}


@router.get("/", response_model=list[dict])
def list_renders(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _require_project(project_id, user, db)
    jobs = (
        db.query(RenderJob)
        .filter(RenderJob.project_id == project.id)
        .order_by(RenderJob.created_at.desc())
        .all()
    )
    return [
        {
            "id": job.id,
            "status": job.status,
            "progress": job.progress,
            "logs": job.logs or [],
            "output_url": job.output_url,
            "html_output_url": job.html_output_url,
            "error_message": job.error_message,
            "is_placeholder": _is_placeholder(job),
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "queue_position": _queue_position(job, db),
        }
        for job in jobs
    ]


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
        "logs": job.logs or [],
        "output_url": job.output_url,
        "html_output_url": job.html_output_url,
        "error_message": job.error_message,
        "is_placeholder": _is_placeholder(job),
        "queue_position": _queue_position(job, db),
    }


def _has_completed_output(project_id: str, db: Session) -> bool:
    return (
        db.query(RenderJob)
        .filter(
            RenderJob.project_id == project_id,
            RenderJob.status == "completed",
            RenderJob.output_url.isnot(None),
        )
        .first()
        is not None
    )


def _reset_project_status_after_cancel(project: Project, db: Session) -> None:
    """When a render is cancelled, move the project out of 'generating'.

    Falls back to 'ready' if a previous completed render exists, otherwise
    'draft', so the workspace returns to a usable state instead of spinning.
    """
    if project.status == "generating":
        project.status = "ready" if _has_completed_output(project.id, db) else "draft"


@router.post("/{job_id}/cancel")
def cancel_render(
    project_id: str,
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel a queued/running render. Idempotent for already-terminal jobs."""
    project = _require_project(project_id, user, db)
    job = db.query(RenderJob).filter(RenderJob.id == job_id).first()
    if not job or job.project_id != project.id:
        raise HTTPException(status_code=404, detail="Render job not found")
    if job.status in ("queued", "running"):
        job.status = "cancelled"
        job.completed_at = datetime.now(timezone.utc)
        job.error_message = job.error_message or "已取消生成"
        entry = {"time": datetime.now(timezone.utc).isoformat(), "message": "用户取消了生成"}
        job.logs = (job.logs or []) + [entry]
        _reset_project_status_after_cancel(project, db)
        db.commit()
        db.refresh(job)
    return _job_to_dict(job, db)


def _job_to_dict(job: RenderJob, db: Session) -> dict:
    return {
        "id": job.id,
        "status": job.status,
        "progress": job.progress,
        "logs": job.logs or [],
        "output_url": job.output_url,
        "html_output_url": job.html_output_url,
        "error_message": job.error_message,
        "is_placeholder": _is_placeholder(job),
        "queue_position": _queue_position(job, db),
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


@router.get("/stream")
def stream_renders(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Server-sent events stream of the latest render job for a project.

    The frontend connects to this endpoint during generation and receives
    job state updates (logs, progress, status) as they are written by the worker.
    """
    project = _require_project(project_id, user, db)

    async def event_generator():
        last_log_count = -1
        last_status = None
        last_progress = -1
        last_change_ts = time.time()
        waiting_since = None
        # If a job stays queued/running with no new log/progress for this long,
        # surface a "stalled" state instead of letting the UI spin forever.
        STALL_SECONDS = 240
        # If the project is "generating" but no job appears (task lost / queue
        # down), tell the UI quickly rather than waiting indefinitely.
        NO_JOB_SECONDS = 20
        # Re-create a DB session for each poll so we always read fresh state.
        poll_db = next(get_db())
        try:
            while True:
                # Read the latest project status too, so we notice if it moved
                # out of "generating" via another path.
                proj_status = (
                    poll_db.query(Project.status).filter(Project.id == project.id).scalar()
                )
                job = (
                    poll_db.query(RenderJob)
                    .filter(RenderJob.project_id == project.id)
                    .order_by(RenderJob.created_at.desc())
                    .first()
                )
                now = time.time()
                if job:
                    waiting_since = None
                    logs = job.logs or []
                    log_count = len(logs)
                    changed = (
                        log_count != last_log_count
                        or job.status != last_status
                        or job.progress != last_progress
                    )
                    if changed:
                        payload = _job_to_dict(job, poll_db)
                        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                        last_log_count = log_count
                        last_status = job.status
                        last_progress = job.progress
                        last_change_ts = now
                    # Stop streaming once the job reaches a terminal state.
                    if job.status in ("completed", "failed", "cancelled"):
                        break
                    if (
                        job.status in ("queued", "running")
                        and (now - last_change_ts) > STALL_SECONDS
                    ):
                        payload = _job_to_dict(job, poll_db)
                        payload["status"] = "stalled"
                        payload["stalled_reason"] = "no_progress"
                        payload["error_message"] = (
                            job.error_message
                            or "生成任务长时间没有新的进展，可能渲染引擎繁忙或卡住。"
                        )
                        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                        break
                else:
                    if waiting_since is None:
                        waiting_since = now
                    if proj_status == "generating" and (now - waiting_since) > NO_JOB_SECONDS:
                        yield (
                            "data: "
                            + json.dumps(
                                {
                                    "status": "stalled",
                                    "stalled_reason": "no_job",
                                    "logs": [],
                                    "progress": 0,
                                    "error_message": "生成任务未能启动（队列未响应）。请重试生成。",
                                },
                                ensure_ascii=False,
                            )
                            + "\n\n"
                        )
                        break
                    yield f"data: {json.dumps({'status': 'waiting', 'logs': []}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(1)
        finally:
            poll_db.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
