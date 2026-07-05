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
