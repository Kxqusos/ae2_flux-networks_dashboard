import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    monkeypatch.setenv("API_TOKEN", "test-token")
    monkeypatch.setenv("UI_PASSWORD", "test-pass")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))

    # Import after env vars are set so get_settings() picks them up at app creation.
    import importlib

    import app.main as main_module

    importlib.reload(main_module)
    return TestClient(main_module.app)


AUTH = {"Authorization": "Bearer test-token"}


def test_flux_endpoint_requires_auth(app_client):
    resp = app_client.post(
        "/api/client/flux", json={"energy_in": 1, "energy_out": 2, "buffer": 3}
    )
    assert resp.status_code == 401


def test_flux_endpoint_accepts_valid_token(app_client):
    resp = app_client.post(
        "/api/client/flux",
        json={"energy_in": 1, "energy_out": 2, "buffer": 3},
        headers=AUTH,
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_inventory_endpoint_stores_payload(app_client):
    resp = app_client.post(
        "/api/client/inventory",
        json={
            "items": [{"kind": "item", "name": "a", "label": "A", "count": 1}],
            "craftables": [],
        },
        headers=AUTH,
    )
    assert resp.status_code == 200


def test_orders_pending_empty_initially(app_client):
    resp = app_client.get("/api/client/orders/pending", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json() == {"orders": []}


def test_order_result_unknown_id_returns_404(app_client):
    resp = app_client.post(
        "/api/client/orders/999/result", json={"status": "done"}, headers=AUTH
    )
    assert resp.status_code == 404


def test_order_result_no_auth_returns_401(app_client):
    resp = app_client.post("/api/client/orders/1/result", json={"status": "done"})
    assert resp.status_code == 401
