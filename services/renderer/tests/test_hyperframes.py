import os
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app, ASSETS_DIR

client = TestClient(app)


def test_render_hyperframes_writes_output(tmp_path):
    os.makedirs(ASSETS_DIR, exist_ok=True)
    html_path = os.path.join(ASSETS_DIR, "test.html")
    output_path = os.path.join(ASSETS_DIR, "test.mp4")
    with open(html_path, "w") as f:
        f.write("<html><body>hi</body></html>")

    with patch("main.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        response = client.post(
            "/render/hyperframes",
            json={"html_path": html_path, "output_path": output_path, "duration": 5, "fps": 30},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["output_url"] == "/api/static/test.mp4"
    assert data["html_output_url"] == "/api/static/test.html"
