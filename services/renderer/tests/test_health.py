from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_returns_status_and_engines():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "engines" in data
    assert "hyperframes" in data["engines"]
