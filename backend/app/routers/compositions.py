from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Composition, Track, Clip, User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/compositions", tags=["compositions"])


def build_composition_json(comp: Composition) -> dict:
    tracks = []
    for t in comp.tracks:
        clips = []
        for c in t.clips:
            clip = {
                "id": c.id,
                "asset_id": c.asset_id,
                "start_time": c.start_time,
                "duration": c.duration,
                "position": c.position,
                "style": c.style,
                "text_content": c.text_content,
            }
            clips.append(clip)
        tracks.append({
            "id": t.id,
            "type": t.type,
            "index": t.index,
            "name": t.name,
            "clips": clips,
        })
    return {
        "id": comp.id,
        "width": comp.width,
        "height": comp.height,
        "duration": comp.duration,
        "fps": comp.fps,
        "metadata": comp.metadata_,
        "tracks": tracks,
    }


def _require_composition(project_id: str, user: User, db: Session) -> Composition:
    comp = db.query(Composition).filter(Composition.project_id == project_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Composition not found")
    if comp.project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this project")
    return comp


@router.get("/{project_id}")
def get_composition(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    comp = _require_composition(project_id, user, db)
    return build_composition_json(comp)


@router.put("/{project_id}")
def update_composition(project_id: str, data: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    comp = _require_composition(project_id, user, db)
    # Clear existing tracks and recreate from payload. Use ORM deletes so the
    # cascade="all, delete-orphan" on Track.clips is honored.
    for track in comp.tracks:
        db.delete(track)
    db.flush()
    for t_data in data.get("tracks", []):
        track = Track(
            composition_id=comp.id,
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
    return build_composition_json(comp)
