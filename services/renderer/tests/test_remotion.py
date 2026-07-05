import os
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app, ASSETS_DIR

client = TestClient(app)


def test_render_remotion_writes_output():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    comp_path = os.path.join(ASSETS_DIR, "comp.json")
    output_path = os.path.join(ASSETS_DIR, "remotion.mp4")
    with open(comp_path, "w") as f:
        f.write('{"duration": 10, "tracks": []}')

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
