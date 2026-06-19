import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    monkeypatch.setenv("API_TOKEN", "test-token")
    monkeypatch.setenv("UI_PASSWORD", "test-pass")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))

    import app.main as main_module

    importlib.reload(main_module)
    return TestClient(main_module.app)


def test_root_serves_index_html(app_client):
    resp = app_client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_api_routes_still_work_after_static_mount(app_client):
    resp = app_client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
