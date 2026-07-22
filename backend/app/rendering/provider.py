from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class RenderRequest:
    composition: dict
    assets: dict
    engine: Optional[str] = None
    user_prompt: Optional[str] = None
    source_url: Optional[str] = None
    raw_assets: Optional[list[str]] = None
    # Agent-recommended engine from the approved plan (e.g. "hyperframes").
    # Used by the selector when the user did not explicitly pick an engine.
    engine_hint: Optional[str] = None
    # Pre-generated HyperFrames HTML from the render task. When present,
    # providers must reuse it instead of calling the (slow) LLM HTML generator
    # a second time.
    html_path: Optional[str] = None
    html_url: Optional[str] = None
    # HyperFrames / render-engine tuning.  Keep them optional so older callers
    # and tests continue to work; providers supply sensible low-memory defaults.
    quality: Optional[str] = None  # draft | standard | high
    fps: Optional[int] = None
    format: Optional[str] = None  # mp4 | webm | mov
    resolution: Optional[str] = None  # landscape | portrait | square | 1080p | 4k
    workers: Optional[int] = None


@dataclass
class RenderResult:
    success: bool
    output_url: Optional[str] = None
    html_output_url: Optional[str] = None
    error_message: Optional[str] = None


class RenderProvider(Protocol):
    name: str

    def can_handle(self, request: RenderRequest) -> bool:
        ...

    async def render(self, job, project, request: RenderRequest) -> RenderResult:
        ...
