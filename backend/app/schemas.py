from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Any


class UserOut(BaseModel):
    id: str
    email: str
    name: Optional[str]
    avatar_url: Optional[str]

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    title: str
    source_url: Optional[str] = None
    source_type: str = "url"


class ProjectOut(BaseModel):
    id: str
    title: str
    source_url: Optional[str]
    source_type: str
    status: str
    target_format: str
    target_duration: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompositionOut(BaseModel):
    id: str
    width: int
    height: int
    duration: int
    fps: int
    metadata: dict

    class Config:
        from_attributes = True


class RenderJobOut(BaseModel):
    id: str
    status: str
    progress: int
    output_url: Optional[str]
    html_output_url: Optional[str]
    error_message: Optional[str]

    class Config:
        from_attributes = True
