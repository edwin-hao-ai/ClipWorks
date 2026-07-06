import os
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@pytest.fixture
def assets_dir(monkeypatch, tmp_path):
    monkeypatch.setattr("main.ASSETS_DIR", str(tmp_path))
    return str(tmp_path)


def test_render_remotion_writes_output(assets_dir):
    os.makedirs(assets_dir, exist_ok=True)
    comp_path = os.path.join(assets_dir, "comp.json")
    output_path = os.path.join(assets_dir, "remotion.mp4")
    with open(comp_path, "w") as f:
        f.write('{"composition": {"duration": 10, "tracks": []}}')

    with patch("main.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        response = client.post(
            "/render/remotion",
            json={"composition_path": comp_path, "output_path": output_path},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["output_url"] == "/api/static/remotion.mp4"
