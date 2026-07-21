import json
import threading
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


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


def test_vibe_stream_requires_auth(client):
    r = client.post("/projects/p1/agent/vibe/stream", json={"message": "hi"})
    assert r.status_code == 401


def test_vibe_stream_empty_message_returns_400(auth_client):
    r = auth_client.post("/projects/", json={"title": "Empty Message Project"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    r = auth_client.post(f"/projects/{project_id}/agent/vibe/stream", json={"message": "   "})
    assert r.status_code == 400
    assert "message is required" in r.json()["detail"]


def test_vibe_stream_project_not_found(auth_client):
    r = auth_client.post("/projects/does-not-exist/agent/vibe/stream", json={"message": "hi"})
    assert r.status_code == 404


def test_vibe_stream_ownership(auth_client, other_client):
    r = auth_client.post("/projects/", json={"title": "Vibe Project"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    r2 = other_client.post(f"/projects/{project_id}/agent/vibe/stream", json={"message": "hi"})
    assert r2.status_code == 403


@patch("app.agent.session.AgentSession")
@patch("app.agent.orchestrator.Orchestrator")
def test_vibe_stream_returns_events_and_persists_state(
    mock_orchestrator_cls, mock_session_cls, auth_client
):
    r = auth_client.post("/projects/", json={"title": "Vibe Stream Project"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    mock_session = MagicMock()
    mock_session.step = "understand"
    mock_session.to_dict.return_value = {
        "step": "understand",
        "payload": {"topic": "test"},
        "messages": [{"role": "user", "content": "hi"}],
        "autonomy_level": "confirm_each",
        "pending_user_confirmation": False,
    }
    mock_session.run.return_value = iter([
        'data: {"type": "token", "text": "Hello"}\n\n',
        'data: {"type": "question", "text": "What do you want?"}\n\n',
    ])
    mock_session_cls.return_value = mock_session

    mock_orchestrator = MagicMock()
    mock_orchestrator_cls.return_value = mock_orchestrator

    response = auth_client.post(
        f"/projects/{project_id}/agent/vibe/stream",
        json={"message": "hi"},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    lines = [line for line in response.iter_lines() if line]
    assert len(lines) >= 3

    first = json.loads(lines[0].replace("data: ", ""))
    assert first["type"] == "token"
    assert first["text"] == "Hello"

    second = json.loads(lines[1].replace("data: ", ""))
    assert second["type"] == "question"

    last = json.loads(lines[-1].replace("data: ", ""))
    assert last["type"] == "done"
    assert last["step"] == "understand"

    mock_session.run.assert_called_once()
    call_args = mock_session.run.call_args
    assert call_args.args[1] == "hi"
    assert call_args.args[2] is mock_orchestrator

    project = auth_client.get(f"/projects/{project_id}").json()
    assert project["agent_state"]["step"] == "understand"
    assert project["agent_state"]["payload"]["topic"] == "test"


@patch("app.agent.session.AgentSession")
@patch("app.agent.orchestrator.Orchestrator")
def test_vibe_stream_error_event(mock_orchestrator_cls, mock_session_cls, auth_client):
    r = auth_client.post("/projects/", json={"title": "Vibe Error Project"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    mock_session = MagicMock()
    mock_session.step = "understand"
    mock_session.to_dict.return_value = {
        "step": "understand",
        "payload": {},
        "messages": [],
        "autonomy_level": "confirm_each",
        "pending_user_confirmation": False,
    }
    mock_session.run.side_effect = RuntimeError("boom")
    mock_session_cls.return_value = mock_session

    response = auth_client.post(
        f"/projects/{project_id}/agent/vibe/stream",
        json={"message": "hi"},
    )
    assert response.status_code == 200

    lines = [line for line in response.iter_lines() if line]
    assert len(lines) >= 2

    error_line = json.loads(lines[-2].replace("data: ", ""))
    assert error_line["type"] == "error"
    assert "boom" in error_line["message"]

    last = json.loads(lines[-1].replace("data: ", ""))
    assert last["type"] == "done"
    assert last["step"] == "understand"


def test_vibe_stream_uses_project_level_lock():
    """同一项目的 vibe stream 锁是同一实例，可串行化并发请求。"""
    from app.routers.agent import _get_vibe_lock

    lock_a = _get_vibe_lock("proj-1")
    lock_b = _get_vibe_lock("proj-1")
    lock_other = _get_vibe_lock("proj-2")

    assert lock_a is lock_b
    assert lock_a is not lock_other

    # 验证确实是可重入的 threading.Lock 且能阻塞第二个线程
    acquired_order = []
    barrier = threading.Event()

    def holder():
        with lock_a:
            acquired_order.append("first")
            barrier.set()
            # 短暂持有，让第二个线程尝试获取
            time.sleep(0.3)
        acquired_order.append("first-released")

    def waiter():
        barrier.wait()
        with lock_a:
            acquired_order.append("second")

    t1 = threading.Thread(target=holder)
    t2 = threading.Thread(target=waiter)
    t1.start()
    t2.start()
    t1.join(timeout=2)
    t2.join(timeout=2)

    assert acquired_order == ["first", "first-released", "second"]
