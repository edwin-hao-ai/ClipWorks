from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_and_list_project():
    r = client.post("/projects/", json={"title": "Test Project", "source_url": "https://example.com"})
    assert r.status_code == 200
    project = r.json()
    assert project["title"] == "Test Project"

    r2 = client.get("/projects/")
    assert r2.status_code == 200
    assert any(p["id"] == project["id"] for p in r2.json())


def test_create_project_seeds_default_composition():
    r = client.post("/projects/", json={"title": "Seeded Project", "source_url": "https://example.com"})
    assert r.status_code == 200
    project = r.json()

    r2 = client.get(f"/compositions/{project['id']}")
    assert r2.status_code == 200
    composition = r2.json()
    assert "error" not in composition
    assert len(composition["tracks"]) == 2

    track_types = {t["type"]: t for t in composition["tracks"]}
    assert "text" in track_types
    assert "video" in track_types
    assert any(c.get("text_content") == "ClipWorks" for c in track_types["text"]["clips"])
    assert any(c["duration"] == 10 for c in track_types["video"]["clips"])
