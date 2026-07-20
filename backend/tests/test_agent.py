import json
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from app.agent.modifier import modify_video
from app.main import app
from app.routers.agent import AgentChatPayload, _persist_composition


@pytest.fixture
def auth_client():
    c = TestClient(app)
    # 用 e2e 账户（10 额度）而非 google（0 额度硬拦截 402），让规划/确认等
    # 路径走真实有额度分支；额度扣减发生在渲染完成时，这些测试不触发渲染，
    # 不会消耗额度。0 额度的 402 拦截由专门的 credit-gate 测试覆盖。
    r = c.post("/auth/mock-login?provider=e2e")
    assert r.status_code == 200
    return c


@patch("app.agent.modifier.KimiClient")
def test_modify_video_returns_reply_and_composition(mock_client_cls):
    mock_client_cls.return_value.chat_completion_json.side_effect = Exception("LLM unavailable")
    comp = {"duration": 30, "tracks": [{"type": "text", "clips": [{"duration": 5, "style": {}}]}]}
    result = modify_video(comp, "把视频缩短一点")
    assert "reply" in result
    assert isinstance(result["reply"], str)
    assert "composition" in result
    assert result["composition"]["duration"] < 30


@patch("app.agent.modifier.KimiClient")
def test_modify_video_fallback_global(mock_client_cls):
    mock_client_cls.return_value.chat_completion_json.side_effect = Exception("LLM unavailable")
    comp = {"duration": 30, "tracks": [{"type": "text", "clips": [{"duration": 5, "style": {}}]}]}
    result = modify_video(comp, "把视频缩短一点")
    assert result["composition"]["duration"] < 30


@patch("app.agent.modifier.KimiClient")
def test_modify_video_fallback_scene(mock_client_cls):
    mock_client_cls.return_value.chat_completion_json.side_effect = Exception("LLM unavailable")
    comp = {
        "duration": 30,
        "tracks": [{
            "type": "text",
            "clips": [{"id": "scene-1", "duration": 5, "style": {}}]
        }]
    }
    result = modify_video(comp, "把标题改成红色", scene_id="scene-1")
    assert result["composition"]["tracks"][0]["clips"][0]["style"]["color"] == "#ef4444"


@patch("app.agent.modifier.KimiClient")
def test_modify_video_fallback_scene_by_clip_id(mock_client_cls):
    mock_client_cls.return_value.chat_completion_json.side_effect = Exception("LLM unavailable")
    comp = {
        "duration": 30,
        "tracks": [{
            "type": "text",
            "clips": [{"id": "clip-abc", "duration": 5, "style": {}}]
        }]
    }
    result = modify_video(comp, "make it bigger", scene_id="clip-abc")
    assert result["composition"]["tracks"][0]["clips"][0]["style"]["fontSize"] == 96


@patch("app.agent.modifier.KimiClient")
def test_modify_video_fallback_scene_not_found_falls_back_to_global(mock_client_cls):
    mock_client_cls.return_value.chat_completion_json.side_effect = Exception("LLM unavailable")
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


# ---- 画幅指令：确定性解析，不依赖 LLM ----


@patch("app.agent.modifier.KimiClient")
def test_modify_video_format_change_by_ratio(mock_client_cls):
    mock_client_cls.return_value.chat_completion_json.side_effect = Exception("LLM unavailable")
    comp = {
        "width": 1920, "height": 1080, "duration": 30,
        "tracks": [{
            "type": "video",
            "clips": [{
                "duration": 10,
                "position": {"x": 960, "y": 540, "width": 960, "height": 540},
                "style": {"fontSize": 80},
            }],
        }],
    }
    result = modify_video(comp, "把画幅改成 9:16")
    out = result["composition"]
    assert (out["width"], out["height"]) == (1080, 1920)
    assert result["target_format"] == "9:16"
    assert result["changed"] is True
    clip = out["tracks"][0]["clips"][0]
    # 按轴比例缩放：x/width * 0.5625，y/height * 16/9，字号按纵向比例
    assert clip["position"]["x"] == 540
    assert clip["position"]["width"] == 540
    assert clip["position"]["y"] == 960
    assert clip["position"]["height"] == 960
    assert clip["style"]["fontSize"] == 142


@patch("app.agent.modifier.KimiClient")
@pytest.mark.parametrize("message,fmt", [
    ("换成竖屏", "9:16"),
    ("改成横屏吧", "16:9"),
    ("我要方形视频", "1:1"),
])
def test_modify_video_format_change_by_keyword(mock_client_cls, message, fmt):
    mock_client_cls.return_value.chat_completion_json.side_effect = Exception("LLM unavailable")
    comp = {"width": 1920, "height": 1080, "duration": 30, "tracks": []}
    result = modify_video(comp, message)
    assert result["target_format"] == fmt
    assert (result["composition"]["width"], result["composition"]["height"]) == {
        "16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080),
    }[fmt]


@patch("app.agent.modifier.KimiClient")
def test_modify_video_unsupported_marks_not_changed(mock_client_cls):
    mock_client_cls.return_value.chat_completion_json.side_effect = Exception("LLM unavailable")
    comp = {"duration": 30, "tracks": [{"type": "text", "clips": [{"duration": 5, "style": {}}]}]}
    result = modify_video(comp, "请帮我把视频做得更有电影感一些")
    assert result["changed"] is False
    assert result["composition"] == comp  # 原样返回


@patch("app.routers.agent.render_video_task")
def test_agent_chat_format_change_updates_project_and_renders(mock_render_task, auth_client):
    r = auth_client.post("/projects/", json={"title": "Format Change Project"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    r2 = auth_client.post(
        f"/projects/{project_id}/agent/chat",
        json={"message": "把画幅改成 9:16", "render": True},
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["job_id"]  # 画幅真变化：入队渲染
    assert (data["composition"]["width"], data["composition"]["height"]) == (1080, 1920)
    mock_render_task.delay.assert_called_once()

    project = auth_client.get(f"/projects/{project_id}").json()
    assert project["target_format"] == "9:16"
    assert project["status"] == "generating"


@patch("app.routers.agent.render_video_task")
@patch("app.agent.modifier.KimiClient")
def test_agent_chat_unsupported_does_not_render(mock_client_cls, mock_render_task, auth_client):
    mock_client_cls.return_value.chat_completion_json.side_effect = Exception("LLM unavailable")
    r = auth_client.post("/projects/", json={"title": "Unsupported Chat Project"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    r2 = auth_client.post(
        f"/projects/{project_id}/agent/chat",
        json={"message": "请帮我把视频做得更有电影感一些", "render": True},
    )
    assert r2.status_code == 200
    data = r2.json()
    # 什么都没改：不入队、不扣额度、项目不进入 generating
    assert data["job_id"] is None
    assert "我目前能直接处理" in data["reply"]
    mock_render_task.delay.assert_not_called()

    project = auth_client.get(f"/projects/{project_id}").json()
    assert project["status"] == "draft"


def test_agent_chat_payload_defaults():
    payload = AgentChatPayload(message="hello")
    assert payload.message == "hello"
    assert payload.scene_id is None
    assert payload.render is True


def test_agent_chat_payload_with_optional_fields():
    payload = AgentChatPayload(message="hello", scene_id="scene-1", render=False)
    assert payload.scene_id == "scene-1"
    assert payload.render is False


@pytest.mark.parametrize("invalid", [{}, {"tracks": []}, {"tracks": "not-a-list"}])
def test_persist_composition_rejects_invalid_tracks(invalid):
    project = MagicMock()
    db = MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        _persist_composition(project, invalid, db)
    assert exc_info.value.status_code == 422
    db.delete.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()


def test_persist_composition_preserves_existing_tracks_for_empty_list():
    project = MagicMock()
    project.composition.tracks = [MagicMock(), MagicMock()]
    db = MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        _persist_composition(project, {"tracks": []}, db)
    assert exc_info.value.status_code == 422
    db.delete.assert_not_called()
    db.commit.assert_not_called()
    # Original tracks should still be present on the mocked project.
    assert len(project.composition.tracks) == 2


@patch("app.routers.agent.stream_planning_response")
def test_agent_planning_stream_returns_plan(mock_stream, auth_client):
    plan = {
        "final_plan": True,
        "title": "Test Plan",
        "hook": "Hook",
        "format": "16:9",
        "duration": 15,
        "scenes": [{"start": 0, "duration": 15, "description": "Scene", "visual": "visual", "text": "text"}],
        "assets_needed": [],
        "engine_hint": "hyperframes",
    }
    # Simulate streaming text followed by the plan-ready marker.
    def fake_stream(project, message, history):
        yield "好的"
        yield "，"
        yield "方案如下"
        yield f"\n\n[PLAN_READY]{json.dumps(plan, ensure_ascii=False)}"

    mock_stream.side_effect = fake_stream

    r = auth_client.post("/projects/", json={"title": "Plan Project"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    response = auth_client.post(
        f"/projects/{project_id}/agent/chat/stream",
        json={"message": "帮我做个视频"},
    )
    assert response.status_code == 200
    body = response.text
    assert "data:" in body
    assert "[PLAN_READY]" not in body  # marker is consumed server-side

    # Verify the project moved to planning and persisted the plan.
    project = auth_client.get(f"/projects/{project_id}").json()
    assert project["status"] == "planning"
    assert project["agent_state"]["pending_plan"]["title"] == "Test Plan"


@patch("app.routers.agent.render_video_task")
def test_agent_approve_plan_triggers_generation(mock_render_task, auth_client):
    r = auth_client.post("/projects/", json={"title": "Approve Project"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Seed a pending plan directly via the state endpoint is not exposed, so use the chat endpoint.
    plan = {
        "final_plan": True,
        "title": "Approve Plan",
        "hook": "Hook",
        "format": "16:9",
        "duration": 15,
        "scenes": [{"start": 0, "duration": 15, "description": "Scene", "visual": "visual", "text": "text"}],
        "assets_needed": [],
        "engine_hint": "hyperframes",
    }
    with patch("app.routers.agent.stream_planning_response") as mock_stream:
        mock_stream.side_effect = lambda p, m, h: iter([f"\n\n[PLAN_READY]{json.dumps(plan, ensure_ascii=False)}"])
        auth_client.post(f"/projects/{project_id}/agent/chat/stream", json={"message": "生成"})

    r = auth_client.post(f"/projects/{project_id}/agent/approve", json={})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "queued"
    assert data["job_id"]
    mock_render_task.delay.assert_called_once()

    project = auth_client.get(f"/projects/{project_id}").json()
    assert project["status"] == "generating"


def test_agent_approve_without_plan_returns_400(auth_client):
    r = auth_client.post("/projects/", json={"title": "No Plan Project"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    r2 = auth_client.post(f"/projects/{project_id}/agent/approve", json={})
    assert r2.status_code == 400


@patch("app.routers.agent.stream_planning_response")
def test_agent_reject_plan_clears_plan_and_streams(mock_stream, auth_client):
    plan = {
        "final_plan": True,
        "title": "Rejected Plan",
        "hook": "Hook",
        "format": "16:9",
        "duration": 15,
        "scenes": [{"start": 0, "duration": 15, "description": "Scene", "visual": "visual", "text": "text"}],
        "assets_needed": [],
        "engine_hint": "hyperframes",
    }

    def fake_stream(project, message, history):
        yield "了解了，请告诉我更详细的需求"

    mock_stream.side_effect = fake_stream

    r = auth_client.post("/projects/", json={"title": "Reject Project"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    with patch("app.routers.agent.stream_planning_response") as mock_first:
        mock_first.side_effect = lambda p, m, h: iter([f"\n\n[PLAN_READY]{json.dumps(plan, ensure_ascii=False)}"])
        auth_client.post(f"/projects/{project_id}/agent/chat/stream", json={"message": "生成"})

    response = auth_client.post(f"/projects/{project_id}/agent/reject", json={"message": "再短一点"})
    assert response.status_code == 200
    assert "data:" in response.text

    project = auth_client.get(f"/projects/{project_id}").json()
    assert project["status"] == "draft"
    assert project["agent_state"]["pending_plan"] is None


# ---- build_fallback_plan：分镜与 duration 一致性 ----

from types import SimpleNamespace

from app.agent.conversation import build_fallback_plan
from app.agent.planner import DEFAULT_PLAN


def _project(duration=None, fmt="16:9"):
    return SimpleNamespace(target_duration=duration, target_format=fmt)


def test_fallback_plan_scenes_tile_duration_when_target_is_15():
    plan = build_fallback_plan(_project(15))
    assert plan["duration"] == 15
    scenes = plan["scenes"]
    assert len(scenes) == 3
    # 首尾相接、无重叠无空隙
    assert scenes[0]["start"] == 0
    assert scenes[1]["start"] == scenes[0]["start"] + scenes[0]["duration"]
    assert scenes[2]["start"] == scenes[1]["start"] + scenes[1]["duration"]
    # 总时长精确等于 duration
    assert scenes[2]["start"] + scenes[2]["duration"] == 15
    assert all(s["duration"] >= 1 for s in scenes)


@pytest.mark.parametrize("duration", [3, 10, 20, 30, 45])
def test_fallback_plan_scenes_sum_equals_duration(duration):
    plan = build_fallback_plan(_project(duration))
    assert plan["duration"] == duration
    scenes = plan["scenes"]
    assert scenes[-1]["start"] + scenes[-1]["duration"] == duration
    for prev, cur in zip(scenes, scenes[1:]):
        assert cur["start"] == prev["start"] + prev["duration"]


def test_fallback_plan_default_duration_is_20_when_unset():
    plan = build_fallback_plan(_project(None))
    assert plan["duration"] == 20
    assert plan["scenes"][-1]["start"] + plan["scenes"][-1]["duration"] == 20


def test_fallback_plan_does_not_mutate_default_plan():
    before = [(s["start"], s["duration"]) for s in DEFAULT_PLAN["scenes"]]
    build_fallback_plan(_project(45))
    after = [(s["start"], s["duration"]) for s in DEFAULT_PLAN["scenes"]]
    assert before == after == [(0, 5), (5, 10), (15, 5)]


def test_fallback_plan_preserves_scene_copy():
    plan = build_fallback_plan(_project(20))
    # 文案来自 DEFAULT_PLAN，未被时间缩放覆盖丢失
    assert plan["scenes"][0]["description"] == DEFAULT_PLAN["scenes"][0]["description"]
    assert plan["scenes"][0]["text"] == DEFAULT_PLAN["scenes"][0]["text"]
