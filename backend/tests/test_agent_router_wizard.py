"""Router tests for the Agent Loop Wizard.

These tests use self-contained fixtures because backend/tests/conftest.py
only provides the table-cleanup fixture; it does not expose client,
auth_headers, test_user, or test_project fixtures. Using local fixtures
keeps the wizard router tests isolated from the planning/chat flow tests
and avoids coupling to the broader agent test suite.
"""
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def auth_client():
    c = TestClient(app)
    r = c.post("/auth/mock-login?provider=google")
    assert r.status_code == 200
    return c


@pytest.fixture
def other_client():
    c = TestClient(app)
    r = c.post("/auth/mock-login?provider=github")
    assert r.status_code == 200
    return c


@pytest.fixture
def project(auth_client):
    r = auth_client.post("/projects/", json={"title": "Wizard Project"})
    assert r.status_code == 201
    return r.json()


def test_get_state_requires_auth(client):
    response = client.get("/projects/any/agent/state")
    assert response.status_code == 401


def test_state_lifecycle(auth_client, project):
    """GET initial state returns idle wizard state."""
    r = auth_client.get(f"/projects/{project['id']}/agent/state")
    assert r.status_code == 200
    data = r.json()
    assert data["step"] == "idle"


def test_get_state_returns_fresh_state(auth_client, project):
    r = auth_client.get(f"/projects/{project['id']}/agent/state")
    assert r.status_code == 200
    data = r.json()
    assert data["step"] == "idle"
    assert data["script"] is None
    assert data["assets"] is None
    assert data["scenes"] is None
    assert data["effects"] is None
    assert data["messages"] == []


def test_get_state_project_not_found(auth_client):
    r = auth_client.get("/projects/does-not-exist/agent/state")
    assert r.status_code == 404


def test_get_state_ownership(auth_client, other_client, project):
    r = other_client.get(f"/projects/{project['id']}/agent/state")
    assert r.status_code == 403


def test_update_state_requires_auth(client, project):
    r = client.post(f"/projects/{project['id']}/agent/state", json={"state": {"step": "script"}})
    assert r.status_code == 401


def test_update_state_partial_preserve_messages(auth_client, project):
    pid = project["id"]
    # seed messages
    auth_client.post(f"/projects/{pid}/agent/state", json={"state": {"messages": [{"role": "user", "content": "hi"}]}})
    # partial update should not wipe messages
    r = auth_client.post(f"/projects/{pid}/agent/state", json={"state": {"script": {"title": "T"}, "step": "script"}})
    assert r.status_code == 200
    data = r.json()
    assert data["script"]["title"] == "T"
    assert data["step"] == "script"
    assert data["messages"] == [{"role": "user", "content": "hi"}]


def test_update_state_can_overwrite_messages(auth_client, project):
    pid = project["id"]
    auth_client.post(f"/projects/{pid}/agent/state", json={"state": {"messages": [{"role": "user", "content": "hi"}]}})
    r = auth_client.post(f"/projects/{pid}/agent/state", json={"state": {"messages": []}})
    assert r.status_code == 200
    assert r.json()["messages"] == []


def test_update_state_invalid_payload(auth_client, project):
    r = auth_client.post(f"/projects/{project['id']}/agent/state", json={"state": "not-a-dict"})
    assert r.status_code == 422


def test_step_invalid_name(auth_client, project):
    r = auth_client.post(f"/projects/{project['id']}/agent/step/badstep", json={})
    assert r.status_code == 400
    assert "Invalid step name" in r.json()["detail"]


def test_skip_step_returns_400(auth_client, project):
    """Running scenes before script/assets must be rejected."""
    r = auth_client.post(f"/projects/{project['id']}/agent/step/scenes", json={})
    assert r.status_code == 400
    assert r.json()["detail"] == "Please complete assets before running scenes"


def test_step_out_of_order(auth_client, project):
    r = auth_client.post(f"/projects/{project['id']}/agent/step/scenes", json={})
    assert r.status_code == 400
    assert "Please complete assets" in r.json()["detail"]


def test_concurrent_step_returns_409(auth_client, project, monkeypatch):
    """A second step request while one is generating must return 409."""
    pid = project["id"]

    def slow_step(*args, **kwargs):
        yield json.dumps({"type": "token", "text": "working"})

    monkeypatch.setattr("app.routers.agent.run_step", slow_step)

    # start a step but do not consume the stream
    r = auth_client.post(f"/projects/{pid}/agent/step/script", json={})
    assert r.status_code == 200

    # second step while first is in progress
    r2 = auth_client.post(f"/projects/{pid}/agent/step/assets", json={})
    assert r2.status_code == 409
    assert "Already generating" in r2.json()["detail"]

    # consume first stream to release lock
    list(r.iter_lines())


def test_step_script_stream(auth_client, project, monkeypatch):
    pid = project["id"]

    def fake_step(step_name, project_obj, state, user_input):
        assert step_name == "script"
        yield json.dumps({"type": "script", "title": "Hello"}, ensure_ascii=False)

    monkeypatch.setattr("app.routers.agent.run_step", fake_step)

    r = auth_client.post(f"/projects/{pid}/agent/step/script", json={"user_input": "make a promo"})
    assert r.status_code == 200
    lines = [line for line in r.iter_lines() if line]
    assert lines
    last = json.loads(lines[-1].replace("data: ", ""))
    assert last["type"] == "done"
    assert last["step"] == "script"

    state_r = auth_client.get(f"/projects/{pid}/agent/state")
    assert state_r.json()["step"] == "script"
    assert state_r.json()["generating_step"] is None


def test_step_outputs_persist_after_stream(auth_client, project, monkeypatch):
    pid = project["id"]

    def fake_step(step_name, project_obj, state, user_input):
        assert step_name == "script"
        # Simulate run_step mutating state in place and emitting a chunk.
        state["script"] = {"title": "Persisted Script", "hook": "Hello world"}
        yield json.dumps({"type": "script", "title": "Persisted Script"}, ensure_ascii=False)

    monkeypatch.setattr("app.routers.agent.run_step", fake_step)

    r = auth_client.post(f"/projects/{pid}/agent/step/script", json={"user_input": "write a script"})
    assert r.status_code == 200
    # Consume the stream to trigger the finally block that persists state.
    list(r.iter_lines())

    state_r = auth_client.get(f"/projects/{pid}/agent/state")
    assert state_r.status_code == 200
    data = state_r.json()
    assert data["step"] == "script"
    assert data["generating_step"] is None
    assert data["script"] == {"title": "Persisted Script", "hook": "Hello world"}


def test_step_error_stream(auth_client, project, monkeypatch):
    pid = project["id"]

    def failing_step(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.routers.agent.run_step", failing_step)

    r = auth_client.post(f"/projects/{pid}/agent/step/script", json={})
    assert r.status_code == 200
    lines = [line for line in r.iter_lines() if line]
    error_line = json.loads(lines[-2].replace("data: ", ""))
    assert error_line["type"] == "error"
    assert "boom" in error_line["message"]
    done_line = json.loads(lines[-1].replace("data: ", ""))
    assert done_line["type"] == "done"


def test_back_from_idle(auth_client, project):
    r = auth_client.post(f"/projects/{project['id']}/agent/back", json={})
    assert r.status_code == 400
    assert "Cannot go back from idle" in r.json()["detail"]


def test_back_moves_to_previous_step(auth_client, project, monkeypatch):
    pid = project["id"]

    def fake_step(*args, **kwargs):
        yield json.dumps({"type": "ok"})

    monkeypatch.setattr("app.routers.agent.run_step", fake_step)

    auth_client.post(f"/projects/{pid}/agent/step/script", json={})
    for line in auth_client.post(f"/projects/{pid}/agent/step/assets", json={}).iter_lines():
        pass

    r = auth_client.post(f"/projects/{pid}/agent/back", json={})
    assert r.status_code == 200
    assert r.json()["step"] == "script"


def test_reset_clears_state(auth_client, project, monkeypatch):
    pid = project["id"]

    def fake_step(*args, **kwargs):
        yield json.dumps({"type": "ok"})

    monkeypatch.setattr("app.routers.agent.run_step", fake_step)

    auth_client.post(f"/projects/{pid}/agent/step/script", json={}).iter_lines()
    auth_client.post(f"/projects/{pid}/agent/state", json={"state": {"script": {"title": "T"}}})

    r = auth_client.post(f"/projects/{pid}/agent/reset", json={})
    assert r.status_code == 200
    data = r.json()
    assert data["step"] == "idle"
    assert data["script"] is None
    assert data["messages"] == []


def test_approve_requires_auth(client, project):
    r = client.post(f"/projects/{project['id']}/agent/approve", json={})
    assert r.status_code == 401


def test_approve_fallback_to_pending_plan(auth_client, project, monkeypatch, db_session):
    pid = project["id"]
    plan = {
        "title": "Pending Plan",
        "format": "9:16",
        "duration": 45,
        "scenes": [{"description": "scene"}],
        "engine_hint": "remotion",
    }
    from app.models import Project as ProjectModel
    proj = db_session.query(ProjectModel).filter(ProjectModel.id == pid).first()
    state = dict(proj.agent_state or {})
    state["pending_plan"] = plan
    proj.agent_state = state
    db_session.commit()

    with patch("app.routers.agent.render_video_task") as mock_task:
        r = auth_client.post(f"/projects/{pid}/agent/approve", json={"engine": "remotion"})
        assert r.status_code == 200
        assert "job_id" in r.json()
        mock_task.delay.assert_called_once()
        _, _, _, engine, passed_plan = mock_task.delay.call_args[0]
        assert engine == "remotion"
        assert passed_plan["title"] == "Pending Plan"


def test_approve_no_plan(auth_client, project):
    r = auth_client.post(f"/projects/{project['id']}/agent/approve", json={})
    assert r.status_code == 400
    assert "No plan to approve" in r.json()["detail"]


def test_approve_four_step_builds_plan(auth_client, project, monkeypatch):
    pid = project["id"]
    state = {
        "script": {"title": "Wizard Plan", "hook": "H", "format": "16:9", "duration": 30},
        "assets": {"needed": [{"description": "img1"}, {"description": "img2"}]},
        "scenes": {
            "scenes": [
                {"description": "open", "start": 0, "duration": 5},
                {"description": "close", "start": 5, "duration": 5},
            ]
        },
        "effects": {
            "effects": [
                {"scene_index": 0, "visual_style": "bold", "animation_keywords": ["zoom"], "generate_image": True, "generate_image_prompt": "p1"},
                {"scene_index": 1, "visual_style": "soft", "animation_keywords": ["fade"]},
            ]
        },
    }
    auth_client.post(f"/projects/{pid}/agent/state", json={"state": state})

    with patch("app.routers.agent.render_video_task") as mock_task:
        r = auth_client.post(f"/projects/{pid}/agent/approve", json={})
        assert r.status_code == 200
        assert "job_id" in r.json()
        mock_task.delay.assert_called_once()
        _, _, _, engine, plan = mock_task.delay.call_args[0]
        assert engine == "hyperframes"
        assert plan["title"] == "Wizard Plan"
        assert plan["hook"] == "H"
        assert plan["format"] == "16:9"
        assert plan["duration"] == 30
        assert plan["assets_needed"] == ["img1", "img2"]
        assert len(plan["scenes"]) == 2
        assert plan["scenes"][0]["visual_style"] == "bold"
        assert plan["scenes"][0]["animation_keywords"] == ["zoom"]
        assert plan["scenes"][0]["generate_image"] is True
        assert plan["scenes"][0]["generate_image_prompt"] == "p1"
        assert plan["scenes"][1]["visual_style"] == "soft"

    # state moved to approved and project status generating
    state_r = auth_client.get(f"/projects/{pid}/agent/state")
    assert state_r.json()["step"] == "approved"
    assert state_r.json()["pending_plan"] is None

    project_r = auth_client.get(f"/projects/{pid}")
    assert project_r.json()["status"] == "generating"
    assert project_r.json()["title"] == "Wizard Plan"


def test_approve_four_step_missing_effects_falls_back(auth_client, project, db_session):
    pid = project["id"]
    state = {
        "script": {"title": "Partial", "duration": 20},
        "assets": {"needed": []},
        "scenes": {"scenes": []},
    }
    auth_client.post(f"/projects/{pid}/agent/state", json={"state": state})

    from app.models import Project as ProjectModel
    proj = db_session.query(ProjectModel).filter(ProjectModel.id == pid).first()
    proj_state = dict(proj.agent_state or {})
    proj_state["pending_plan"] = {"title": "Fallback"}
    proj.agent_state = proj_state
    db_session.commit()

    with patch("app.routers.agent.render_video_task") as mock_task:
        r = auth_client.post(f"/projects/{pid}/agent/approve", json={})
        assert r.status_code == 200
        _, _, _, _, plan = mock_task.delay.call_args[0]
        assert plan["title"] == "Fallback"
