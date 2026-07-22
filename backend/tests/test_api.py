import io
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


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_db(client):
    response = client.get("/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "users" in data["tables"]
    assert "projects" in data["tables"]


def test_me_requires_authentication(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_mock_login_sets_cookie_and_returns_user(client):
    response = client.post("/auth/mock-login?provider=google")
    assert response.status_code == 200
    assert "session_user_id" in response.cookies
    data = response.json()
    assert data["user"]["email"] == "demo@google.com"


def test_auth_flow(client):
    login_response = client.post("/auth/mock-login?provider=google")
    assert login_response.status_code == 200
    me_response = client.get("/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["user"]["id"] == login_response.json()["user"]["id"]


def test_create_and_list_project(auth_client):
    r = auth_client.post("/projects/", json={"title": "Test Project", "source_url": "https://example.com"})
    assert r.status_code == 201
    project = r.json()
    assert project["title"] == "Test Project"

    r2 = auth_client.get("/projects/")
    assert r2.status_code == 200
    assert any(p["id"] == project["id"] for p in r2.json())


def test_get_project_not_found(auth_client):
    r = auth_client.get("/projects/does-not-exist")
    assert r.status_code == 404


def test_project_ownership(auth_client, other_client):
    r = auth_client.post("/projects/", json={"title": "Private Project"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    r2 = other_client.get(f"/projects/{project_id}")
    assert r2.status_code == 403


def test_update_project(auth_client):
    r = auth_client.post("/projects/", json={"title": "Old Title", "source_url": "https://old.com"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    r2 = auth_client.put(
        f"/projects/{project_id}",
        json={"title": "New Title", "source_url": "https://new.com", "target_duration": 60},
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["title"] == "New Title"
    assert data["source_url"] == "https://new.com"
    assert data["target_duration"] == 60


def test_create_project_seeds_default_composition(auth_client):
    r = auth_client.post("/projects/", json={"title": "Seeded Project", "source_url": "https://example.com"})
    assert r.status_code == 201
    project = r.json()

    r2 = auth_client.get(f"/compositions/{project['id']}")
    assert r2.status_code == 200
    composition = r2.json()
    assert "error" not in composition
    assert len(composition["tracks"]) == 2

    track_types = {t["type"]: t for t in composition["tracks"]}
    assert "text" in track_types
    assert "video" in track_types
    assert any(c.get("text_content") == "ClipWorks" for c in track_types["text"]["clips"])
    assert any(c["duration"] == 10 for c in track_types["video"]["clips"])


def test_update_composition_with_seeded_default_succeeds(auth_client):
    r = auth_client.post("/projects/", json={"title": "Update Composition Project", "source_url": "https://example.com"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    r2 = auth_client.get(f"/compositions/{project_id}")
    assert r2.status_code == 200
    composition = r2.json()

    r3 = auth_client.put(f"/compositions/{project_id}", json=composition)
    assert r3.status_code == 200
    updated = r3.json()
    assert len(updated["tracks"]) == len(composition["tracks"])
    assert all(len(t.get("clips", [])) > 0 for t in updated["tracks"])


def test_get_composition_not_found(auth_client):
    r = auth_client.get("/compositions/does-not-exist")
    assert r.status_code == 404


def test_generate_video_not_found(auth_client):
    r = auth_client.post("/projects/does-not-exist/renders/generate")
    assert r.status_code == 404


def test_generate_video_accepts_quality(auth_client, monkeypatch):
    # 共享演示账号额度会被 e2e 消耗，切换套餐补足额度。
    auth_client.put("/auth/me", json={"plan": "free"})
    auth_client.put("/auth/me", json={"plan": "pro"})

    r = auth_client.post("/projects/", json={"title": "Quality Test Project"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    captured = {}

    def fake_delay(job_id, project_id, prompt=None, engine=None, plan=None, quality=None):
        captured["quality"] = quality

    monkeypatch.setattr("app.routers.renders.render_video_task.delay", fake_delay)

    r2 = auth_client.post(f"/projects/{project_id}/renders/generate", json={"quality": "high"})
    assert r2.status_code == 202
    assert captured.get("quality") == "high"


def test_generate_video_defaults_quality_when_body_empty(auth_client, monkeypatch):
    auth_client.put("/auth/me", json={"plan": "free"})
    auth_client.put("/auth/me", json={"plan": "pro"})

    r = auth_client.post("/projects/", json={"title": "Default Quality Project"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    captured = {}

    def fake_delay(job_id, project_id, prompt=None, engine=None, plan=None, quality=None):
        captured["quality"] = quality

    monkeypatch.setattr("app.routers.renders.render_video_task.delay", fake_delay)

    r2 = auth_client.post(f"/projects/{project_id}/renders/generate")
    assert r2.status_code == 202
    assert captured.get("quality") is None


def test_get_render_not_found(auth_client):
    r = auth_client.get("/projects/does-not-exist/renders/does-not-exist")
    assert r.status_code == 404


def test_plan_switch_refills_credits(auth_client):
    # 演示环境没有真实支付：切换套餐即按套餐额度补足生成次数，
    # 保证「额度耗尽 -> 升级套餐」这条 UI 指引不是死局。
    r = auth_client.put("/auth/me", json={"plan": "free"})
    assert r.status_code == 200
    r = auth_client.get("/auth/me/stats")
    assert r.json()["remaining_credits"] == 10

    r = auth_client.put("/auth/me", json={"plan": "pro"})
    assert r.status_code == 200
    r = auth_client.get("/auth/me/stats")
    assert r.json()["remaining_credits"] == 200


def test_render_polling(auth_client):
    # 共享演示账号的额度会被 e2e 渲染消耗殆尽；切换套餐补足额度（演示环境），
    # 确保能通过 renders/generate 的 402 门禁。
    auth_client.put("/auth/me", json={"plan": "free"})
    auth_client.put("/auth/me", json={"plan": "pro"})

    r = auth_client.post("/projects/", json={"title": "Render Poll Project"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    r2 = auth_client.post(f"/projects/{project_id}/renders/generate")
    assert r2.status_code == 202
    job_id = r2.json()["job_id"]

    r3 = auth_client.get(f"/projects/{project_id}/renders/{job_id}")
    assert r3.status_code == 200
    job = r3.json()
    assert job["id"] == job_id
    assert job["status"] in {"queued", "running", "completed"}
    assert 0 <= job["progress"] <= 100


def test_asset_upload_validation(auth_client):
    r = auth_client.post("/projects/", json={"title": "Asset Upload Project"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    invalid = io.BytesIO(b"not an image")
    r2 = auth_client.post(
        f"/projects/{project_id}/assets/",
        files={"file": ("bad.exe", invalid, "application/octet-stream")},
    )
    assert r2.status_code == 400

    too_large = io.BytesIO(b"x" * (50 * 1024 * 1024 + 1))
    r3 = auth_client.post(
        f"/projects/{project_id}/assets/",
        files={"file": ("big.png", too_large, "image/png")},
    )
    assert r3.status_code == 413

    valid = io.BytesIO(b"fake png bytes")
    r4 = auth_client.post(
        f"/projects/{project_id}/assets/",
        files={"file": ("logo.png", valid, "image/png")},
    )
    assert r4.status_code == 201
    asset = r4.json()
    assert asset["type"] == "image"
    assert asset["original_url"] == "logo.png"


def test_delete_project_removes_assets_dir(auth_client):
    """删项目必须级联删除素材目录，杜绝「DB 删了、磁盘残留」的孤立目录泄漏。"""
    import os
    from app.config import ASSETS_DIR

    r = auth_client.post("/projects/", json={"title": "Delete Cascade Project"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    proj_dir = os.path.join(ASSETS_DIR, project_id)
    os.makedirs(proj_dir, exist_ok=True)
    with open(os.path.join(proj_dir, "marker.txt"), "w") as f:
        f.write("x")

    r2 = auth_client.delete(f"/projects/{project_id}")
    assert r2.status_code == 200
    assert not os.path.exists(proj_dir)
