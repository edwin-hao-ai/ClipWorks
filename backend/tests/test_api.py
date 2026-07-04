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
