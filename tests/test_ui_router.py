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


def test_login_with_correct_password_sets_cookie(app_client):
    resp = app_client.post("/api/ui/login", json={"password": "test-pass"})
    assert resp.status_code == 200
    assert "session" in resp.cookies


def test_login_with_wrong_password_rejected(app_client):
    resp = app_client.post("/api/ui/login", json={"password": "wrong"})
    assert resp.status_code == 401


def test_stats_requires_session(app_client):
    resp = app_client.get("/api/ui/stats")
    assert resp.status_code == 401


def test_stats_returns_empty_state_before_any_flux_data(app_client):
    app_client.post("/api/ui/login", json={"password": "test-pass"})
    resp = app_client.get("/api/ui/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["current"] is None
    assert body["history"] == []


def test_items_returns_empty_state_before_any_inventory(app_client):
    app_client.post("/api/ui/login", json={"password": "test-pass"})
    resp = app_client.get("/api/ui/items")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["craftables"] == []


def test_create_order_then_list(app_client):
    app_client.post("/api/ui/login", json={"password": "test-pass"})

    create_resp = app_client.post(
        "/api/ui/orders",
        json={"kind": "fluid", "item": "minecraft:lava", "label": "Lava", "amount": 8000},
    )
    assert create_resp.status_code == 200
    order_id = create_resp.json()["id"]

    list_resp = app_client.get("/api/ui/orders")
    orders = list_resp.json()["orders"]
    assert orders[0]["id"] == order_id
    assert orders[0]["status"] == "queued"


def test_full_flow_client_posts_then_ui_reads(app_client):
    client_resp = app_client.post(
        "/api/client/flux",
        json={"energy_in": 5, "energy_out": 3, "buffer": 10},
        headers={"Authorization": "Bearer test-token"},
    )
    assert client_resp.status_code == 200

    app_client.post("/api/ui/login", json={"password": "test-pass"})
    stats_resp = app_client.get("/api/ui/stats")
    body = stats_resp.json()
    assert body["current"]["energy_in"] == 5
    assert len(body["history"]) == 1
