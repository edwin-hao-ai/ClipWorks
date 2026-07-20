from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Literal


class UserOut(BaseModel):
    id: str
    email: str
    name: Optional[str]
    avatar_url: Optional[str]
    provider: Optional[str]
    credits: int = 10
    plan: str = 'free'

    class Config:
        from_attributes = True


class UserUpdateIn(BaseModel):
    # 仅允许更新展示用昵称与套餐（mock 计费）；邮箱/登录方式等身份字段不允许在此修改。
    name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    plan: Optional[Literal['free', 'pro', 'enterprise']] = None


class UserStatsOut(BaseModel):
    videos_generated: int
    remaining_credits: int
    current_plan: str

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    title: str
    source_url: Optional[str] = None
    source_type: str = "url"
    target_format: Optional[str] = "16:9"
    target_duration: Optional[int] = 30


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    source_url: Optional[str] = None
    target_format: Optional[str] = None
    target_duration: Optional[int] = None


class ClipOut(BaseModel):
    id: str
    asset_id: Optional[str]
    start_time: float
    duration: float
    position: dict
    style: dict
    text_content: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class TrackOut(BaseModel):
    id: str
    type: str
    index: int
    name: Optional[str]
    clips: list[ClipOut]

    model_config = ConfigDict(from_attributes=True)


class CompositionOut(BaseModel):
    id: str
    width: int
    height: int
    duration: int
    fps: int
    metadata: dict = Field(alias="metadata_")
    tracks: list[TrackOut] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ProjectOut(BaseModel):
    id: str
    title: str
    source_url: Optional[str]
    source_type: str
    status: str
    target_format: str
    target_duration: Optional[int]
    agent_state: Optional[dict] = None
    cover_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    composition: Optional[CompositionOut] = None

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
