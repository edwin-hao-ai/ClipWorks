import logging
from typing import Optional

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agent import modify_video
from app.agent.conversation import stream_planning_response, build_fallback_plan
from app.database import get_db
from app.models import Project, User, RenderJob
from app.routers.auth import get_current_user
from app.routers.compositions import build_composition_json
from app.routers.renders import render_video_task, _check_credits

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects/{project_id}/agent", tags=["agent"])


class AgentChatPayload(BaseModel):
    message: str
    scene_id: Optional[str] = None
    render: bool = True
    engine: Optional[str] = None


class AgentPlanPayload(BaseModel):
    message: str


class AgentApprovePayload(BaseModel):
    engine: Optional[str] = None


def _require_project(project_id: str, user: User, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this project")
    return project


def _persist_composition(project, comp_json, db):
    from app.models import Track as TrackModel, Clip as ClipModel
    tracks = comp_json.get("tracks")
    if not isinstance(tracks, list) or len(tracks) == 0:
        raise HTTPException(status_code=422, detail="Agent returned composition without valid tracks")
    for track in project.composition.tracks:
        db.delete(track)
    db.flush()
    max_end = 0
    for t_data in tracks:
        track = TrackModel(
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
            end = start + duration
            if end > max_end:
                max_end = end
            clip = ClipModel(
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


@router.post("/chat")
def chat_with_agent(
    project_id: str,
    payload: AgentChatPayload,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Chat with the Agent to modify the current composition. Optionally triggers re-render."""
    project = _require_project(project_id, user, db)

    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    if not project.composition:
        raise HTTPException(status_code=404, detail="Composition not found")

    scene_id = payload.scene_id
    should_render = payload.render
    if should_render:
        _check_credits(user)
    current_composition = build_composition_json(project.composition)

    try:
        result = modify_video(current_composition, message, scene_id=scene_id)
    except Exception as exc:
        logger.exception("Agent chat modification failed")
        raise HTTPException(status_code=500, detail=f"Agent failed: {exc}")

    updated = result.get("composition")
    if not updated or not isinstance(updated, dict):
        raise HTTPException(status_code=500, detail="Agent returned invalid composition")

    # 画幅指令（确定性路径会回传 target_format）：同步到项目设置，后续渲染沿用。
    new_format = result.get("target_format")
    if new_format and new_format != project.target_format:
        project.target_format = new_format

    _persist_composition(project, updated, db)

    default_reply = f"已针对场景调整：{message}" if scene_id else f"已应用修改：{message}"
    reply = result.get("reply") or default_reply

    # Optionally trigger re-render via Celery so the HTTP response returns immediately.
    # 未做任何修改时（指令超出能力边界）不入队渲染、不扣额度，
    # 避免「说了没改却照样出片」的假成功。
    job = None
    if should_render and result.get("changed", True):
        project.status = "generating"
        db.commit()
        job = RenderJob(project_id=project_id, composition_id=project.composition.id, status="queued")
        db.add(job)
        db.commit()
        db.refresh(job)
        render_video_task.delay(job.id, project_id, None, payload.engine)

    return {
        "reply": reply,
        "composition": build_composition_json(project.composition),
        "job_id": job.id if job else None,
    }


@router.post("/chat/stream")
def chat_with_agent_stream(
    project_id: str,
    payload: AgentPlanPayload,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stream a planning conversation with the Agent. The agent asks clarifying questions
    until it has enough info, then produces a final plan marked with [PLAN_READY]."""
    project = _require_project(project_id, user, db)
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    # Work on a fresh dict copy so SQLAlchemy detects the JSON mutation.
    state = dict(project.agent_state or {"messages": [], "pending_plan": None, "step": "idle"})
    history = list(state.get("messages", []))

    def event_stream():
        full_reply = ""
        pending_plan = None
        for chunk in stream_planning_response(project, message, history):
            if chunk.startswith("\n\n[PLAN_READY]"):
                plan_json = chunk.replace("\n\n[PLAN_READY]", "").strip()
                try:
                    pending_plan = json.loads(plan_json)
                except Exception as exc:
                    logger.warning("Failed to parse extracted plan: %s", exc)
            else:
                full_reply += chunk
                yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"

        # Persist conversation state.
        state["messages"] = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": full_reply},
        ]
        if pending_plan:
            state["pending_plan"] = pending_plan
            state["step"] = "pending_approval"
            project.status = "planning"
        else:
            state["pending_plan"] = None
            state["step"] = "chatting"
        project.agent_state = state
        db.commit()

        if pending_plan:
            yield f"data: {json.dumps({'type': 'plan', 'plan': pending_plan})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'pending_plan': bool(pending_plan)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/approve")
def approve_agent_plan(
    project_id: str,
    payload: AgentApprovePayload,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approve the pending plan and queue video generation.

    The actual composition build, HTML generation and rendering happen
    asynchronously in the worker so the HTTP response returns immediately
    and the UI can switch to the generation screen.
    """
    project = _require_project(project_id, user, db)
    _check_credits(user)
    state = project.agent_state or {}
    plan = state.get("pending_plan")
    if not plan:
        raise HTTPException(status_code=400, detail="No pending plan to approve")

    # Update project settings from the plan.
    if plan.get("format"):
        project.target_format = plan["format"]
    if plan.get("duration"):
        project.target_duration = plan["duration"]
    if plan.get("title"):
        project.title = plan["title"]

    # Persist the plan as a script for reference.
    from app.models import Script
    script = Script(
        project_id=project.id,
        title=plan.get("title", project.title),
        hook=plan.get("hook", ""),
        scenes=plan.get("scenes", []),
    )
    db.add(script)

    state["step"] = "generating"
    state["pending_plan"] = None
    project.agent_state = state
    project.status = "generating"
    db.commit()

    job = RenderJob(project_id=project_id, status="queued", logs=[])
    db.add(job)
    db.commit()
    db.refresh(job)

    engine = payload.engine or plan.get("engine_hint")
    render_video_task.delay(job.id, project_id, None, engine, plan)

    return {
        "job_id": job.id,
        "status": "queued",
    }


@router.post("/reject")
def reject_agent_plan(
    project_id: str,
    payload: AgentPlanPayload,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reject the pending plan and continue the conversation."""
    project = _require_project(project_id, user, db)
    state = project.agent_state or {}
    if not state.get("pending_plan"):
        raise HTTPException(status_code=400, detail="No pending plan to reject")

    state["pending_plan"] = None
    state["step"] = "chatting"
    project.agent_state = state
    project.status = "draft"
    db.commit()

    # Treat the rejection message as the next user input in the planning chat.
    return chat_with_agent_stream(project_id, payload, user, db)
