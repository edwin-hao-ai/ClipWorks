import pytest
from unittest.mock import MagicMock, patch
from app.rendering.provider import RenderRequest
from app.rendering.providers.remotion import RemotionProvider


def test_build_assembly_composition_uses_scene_mp4():
    from app.tasks.render_task import _build_assembly_composition
    comp = {
        "width": 1920, "height": 1080, "duration": 6,
        "metadata": {"plan": {"scenes": []}},
        "tracks": [
            {"type": "video", "index": 0, "clips": [
                {"start_time": 0, "duration": 3, "asset_id": "a1"},
                {"start_time": 3, "duration": 3, "asset_id": "a2"},
            ]},
            {"type": "text", "index": 1, "clips": [
                {"start_time": 0, "duration": 3, "text_content": "S1"},
                {"start_time": 3, "duration": 3, "text_content": "S2"},
            ]},
        ],
    }
    scenes = [
        {"start": 0, "duration": 3, "text": "S1", "transition": "fade"},
        {"start": 3, "duration": 3, "text": "S2", "transition": "slide"},
    ]
    scene_results = {0: ("mp4_0", False), 1: ("mp4_1", False)}
    project = MagicMock()
    project.id = "p1"
    project.assets = []
    assembly = _build_assembly_composition(comp, scenes, scene_results, project)
    video_clips = assembly["tracks"][0]["clips"]
    assert [c["asset_id"] for c in video_clips] == ["mp4_0", "mp4_1"]
    assert assembly["metadata"]["engine"] == "hybrid"


def test_build_assembly_composition_fallback_keeps_original_clip():
    from app.tasks.render_task import _build_assembly_composition
    comp = {
        "width": 1920, "height": 1080, "duration": 3,
        "tracks": [
            {"type": "image", "index": 0, "clips": [
                {"start_time": 0, "duration": 3, "asset_id": "orig"},
            ]},
        ],
    }
    scenes = [{"start": 0, "duration": 3, "text": "S1"}]
    scene_results = {0: ("", True)}
    project = MagicMock()
    project.id = "p1"
    project.assets = []
    assembly = _build_assembly_composition(comp, scenes, scene_results, project)
    assert assembly["tracks"][0]["clips"][0]["asset_id"] == "orig"


def test_remotion_provider_hybrid_can_handle():
    provider = RemotionProvider()
    assert provider.can_handle(RenderRequest(composition={}, assets={}, engine="hybrid"))
