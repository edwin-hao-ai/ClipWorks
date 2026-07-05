import pytest
from app.agent.modifier import modify_video
from app.routers.agent import AgentChatPayload


def test_modify_video_returns_reply_and_composition():
    comp = {"duration": 30, "tracks": [{"type": "text", "clips": [{"duration": 5, "style": {}}]}]}
    result = modify_video(comp, "把视频缩短一点")
    assert "reply" in result
    assert isinstance(result["reply"], str)
    assert "composition" in result
    assert result["composition"]["duration"] < 30


def test_modify_video_fallback_global():
    comp = {"duration": 30, "tracks": [{"type": "text", "clips": [{"duration": 5, "style": {}}]}]}
    result = modify_video(comp, "把视频缩短一点")
    assert result["composition"]["duration"] < 30


def test_modify_video_fallback_scene():
    comp = {
        "duration": 30,
        "tracks": [{
            "type": "text",
            "clips": [{"id": "scene-1", "duration": 5, "style": {}}]
        }]
    }
    result = modify_video(comp, "把标题改成红色", scene_id="scene-1")
    assert result["composition"]["tracks"][0]["clips"][0]["style"]["color"] == "#ef4444"


def test_modify_video_fallback_scene_by_clip_id():
    comp = {
        "duration": 30,
        "tracks": [{
            "type": "text",
            "clips": [{"id": "clip-abc", "duration": 5, "style": {}}]
        }]
    }
    result = modify_video(comp, "make it bigger", scene_id="clip-abc")
    assert result["composition"]["tracks"][0]["clips"][0]["style"]["fontSize"] == 96


def test_modify_video_fallback_scene_not_found_falls_back_to_global():
    comp = {
        "duration": 30,
        "tracks": [{
            "type": "text",
            "clips": [{"id": "scene-1", "duration": 5, "style": {}}]
        }]
    }
    result = modify_video(comp, "把标题改成红色", scene_id="missing-scene")
    # Scene not found; global fallback applies the red color to all clips
    assert result["composition"]["tracks"][0]["clips"][0]["style"]["color"] == "#ef4444"


def test_agent_chat_payload_defaults():
    payload = AgentChatPayload(message="hello")
    assert payload.message == "hello"
    assert payload.scene_id is None
    assert payload.render is True


def test_agent_chat_payload_with_optional_fields():
    payload = AgentChatPayload(message="hello", scene_id="scene-1", render=False)
    assert payload.scene_id == "scene-1"
    assert payload.render is False
