import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    avatar_url = Column(String)
    provider = Column(String)
    provider_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    projects = relationship("Project", back_populates="user")


class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    source_url = Column(String)
    source_type = Column(String, default="url")  # url | upload
    status = Column(String, default="draft")  # draft | generating | ready | failed
    target_format = Column(String, default="16:9")  # 16:9 | 9:16 | 1:1
    target_duration = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="projects")
    composition = relationship("Composition", uselist=False, back_populates="project", cascade="all, delete-orphan")
    assets = relationship("MediaAsset", back_populates="project", cascade="all, delete-orphan")
    render_jobs = relationship("RenderJob", back_populates="project", cascade="all, delete-orphan")
    scripts = relationship("Script", back_populates="project", cascade="all, delete-orphan")


class Composition(Base):
    __tablename__ = "compositions"
    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), unique=True, nullable=False)
    width = Column(Integer, default=1920)
    height = Column(Integer, default=1080)
    duration = Column(Integer, default=30)
    fps = Column(Integer, default=30)
    metadata_ = Column("metadata", JSON, default=lambda: {})

    project = relationship("Project", back_populates="composition")
    tracks = relationship("Track", back_populates="composition", order_by="Track.index", cascade="all, delete-orphan")


class Track(Base):
    __tablename__ = "tracks"
    id = Column(String, primary_key=True, default=generate_uuid)
    composition_id = Column(String, ForeignKey("compositions.id"), nullable=False)
    type = Column(String, nullable=False)  # video | image | audio | text | overlay
    index = Column(Integer, nullable=False)
    name = Column(String)

    composition = relationship("Composition", back_populates="tracks")
    clips = relationship("Clip", back_populates="track", order_by="Clip.start_time", cascade="all, delete-orphan")


class Clip(Base):
    __tablename__ = "clips"
    id = Column(String, primary_key=True, default=generate_uuid)
    track_id = Column(String, ForeignKey("tracks.id"), nullable=False)
    asset_id = Column(String, ForeignKey("media_assets.id"), nullable=True)
    start_time = Column(Float, default=0.0)
    duration = Column(Float, default=5.0)
    position = Column(JSON, default=lambda: {})
    style = Column(JSON, default=lambda: {})
    text_content = Column(Text)
    metadata_ = Column("metadata", JSON, default=lambda: {})

    track = relationship("Track", back_populates="clips")
    asset = relationship("MediaAsset", back_populates="clips")


class MediaAsset(Base):
    __tablename__ = "media_assets"
    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    type = Column(String, nullable=False)  # image | video | audio | font | generated
    source = Column(String, nullable=False)  # upload | pexels | generated | user_url
    original_url = Column(String)
    local_path = Column(String)
    thumbnail_url = Column(String)
    metadata_ = Column("metadata", JSON, default=lambda: {})
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="assets")
    clips = relationship("Clip", back_populates="asset")


class Script(Base):
    __tablename__ = "scripts"
    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    version = Column(Integer, default=1)
    title = Column(String)
    hook = Column(Text)
    scenes = Column(JSON, default=lambda: [])
    narration = Column(JSON, default=lambda: [])
    keywords = Column(JSON, default=lambda: [])
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="scripts")


class RenderJob(Base):
    __tablename__ = "render_jobs"
    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    composition_id = Column(String, ForeignKey("compositions.id"))
    status = Column(String, default="queued")  # queued | running | completed | failed
    output_path = Column(String)
    output_url = Column(String)
    html_output_path = Column(String)
    html_output_url = Column(String)
    progress = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="render_jobs")
