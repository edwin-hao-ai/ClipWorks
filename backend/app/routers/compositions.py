from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Composition, Track, Clip, MediaAsset
from app.schemas import CompositionOut

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


@router.get("/{project_id}")
def get_composition(project_id: str, db: Session = Depends(get_db)):
    comp = db.query(Composition).filter(Composition.project_id == project_id).first()
    if not comp:
        return {"error": "not found"}
    return build_composition_json(comp)


@router.put("/{project_id}")
def update_composition(project_id: str, data: dict, db: Session = Depends(get_db)):
    comp = db.query(Composition).filter(Composition.project_id == project_id).first()
    if not comp:
        return {"error": "not found"}
    # Clear existing tracks and recreate from payload
    db.query(Track).filter(Track.composition_id == comp.id).delete()
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
