import pytest


@pytest.fixture
def assets_dir(monkeypatch, tmp_path):
    monkeypatch.setattr("main.ASSETS_DIR", str(tmp_path))
    return str(tmp_path)
