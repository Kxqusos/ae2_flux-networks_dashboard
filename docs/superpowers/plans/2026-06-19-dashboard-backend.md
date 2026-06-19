# Dashboard (FastAPI) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `dashboard` repo — a FastAPI service with SQLite storage and a vanilla-JS frontend that lets a browser user view AE2 items/fluids + Flux Networks energy history, place orders, and lets an OpenComputers client push data and pull pending orders.

**Architecture:** Single FastAPI app. `store.py` holds all SQLite read/write logic (no ORM — raw `sqlite3`). Two routers: `client.py` (Bearer-token auth, called by OpenComputers) and `ui.py` (session-cookie auth, called by the browser). Static frontend served by FastAPI's `StaticFiles`. No background workers — all writes happen synchronously inside request handlers.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, `sqlite3` (stdlib), `pytest` + `httpx`/`TestClient`, Chart.js (CDN) for frontend graphs, vanilla JS (no build step).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-06-19-ae2-flux-dashboard-design.md` (this plan implements that spec's `dashboard/` section + API contract).
- All client-facing endpoints (`/api/client/*`) require header `Authorization: Bearer <API_TOKEN>` — `401` on mismatch or missing.
- All UI endpoints (`/api/ui/*`) except `/api/ui/login` require a valid session cookie — `401` if missing/invalid.
- `kind` field is `"item"` or `"fluid"` everywhere an inventory/order entry appears. For `"fluid"`, quantities are in mB; for `"item"`, quantities are item counts.
- Flux history retention: 7 days, one row per hour bucket (`flux_samples`).
- No build tooling for frontend — plain HTML/CSS/JS files served as static assets.
- Config via environment variables: `API_TOKEN`, `UI_PASSWORD`, `DB_PATH`, `RETENTION_DAYS` (default 7).

---

## File Structure

```
dashboard/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   ├── models.py
│   ├── auth.py
│   ├── store.py
│   └── routers/
│       ├── __init__.py
│       ├── client.py
│       └── ui.py
├── app/static/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_db.py
│   ├── test_auth.py
│   ├── test_store_flux.py
│   ├── test_store_inventory.py
│   ├── test_store_orders.py
│   ├── test_client_router.py
│   └── test_ui_router.py
├── requirements.txt
├── pytest.ini
├── .gitignore (already created)
└── README.md
```

---

### Task 1: Project scaffolding + health check

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `app/__init__.py` (empty)
- Create: `app/main.py`
- Test: `tests/conftest.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Produces: `app.main:app` — the FastAPI instance, importable by all later routers and by tests.

- [ ] **Step 1: Write requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
pydantic==2.9.2
pytest==8.3.3
httpx==0.27.2
```

- [ ] **Step 2: Write pytest.ini**

```ini
[pytest]
testpaths = tests
pythonpath = .
```

- [ ] **Step 3: Create venv and install deps**

Run:
```bash
cd dashboard
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```
Expected: install completes with no errors.

- [ ] **Step 4: Create empty `app/__init__.py`**

```python
```

- [ ] **Step 5: Write minimal `app/main.py`**

```python
from fastapi import FastAPI

app = FastAPI(title="AE2 + Flux Networks Dashboard")


@app.get("/healthz")
def healthz():
    return {"ok": True}
```

- [ ] **Step 6: Write the failing test**

`tests/conftest.py`:
```python
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)
```

`tests/test_main.py`:
```python
def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd dashboard && . .venv/bin/activate && pytest tests/test_main.py -v`
Expected: `test_healthz PASSED`

- [ ] **Step 8: Commit**

```bash
git add requirements.txt pytest.ini app/__init__.py app/main.py tests/conftest.py tests/test_main.py
git commit -m "feat: scaffold FastAPI app with health check"
```

---

### Task 2: Config module

**Files:**
- Create: `app/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `app.config.Settings` (Pydantic `BaseModel` subclass) with fields `api_token: str`, `ui_password: str`, `db_path: str`, `retention_days: int`. Produces `app.config.get_settings() -> Settings`, reads from env vars `API_TOKEN`, `UI_PASSWORD`, `DB_PATH` (default `"dashboard.db"`), `RETENTION_DAYS` (default `7`). Raises `ValueError` if `API_TOKEN` or `UI_PASSWORD` is unset/empty.
- Consumes: nothing.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import pytest

from app.config import get_settings


def test_get_settings_reads_env(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "secret-token")
    monkeypatch.setenv("UI_PASSWORD", "secret-pass")
    monkeypatch.setenv("DB_PATH", "/tmp/test.db")
    monkeypatch.setenv("RETENTION_DAYS", "3")

    settings = get_settings()

    assert settings.api_token == "secret-token"
    assert settings.ui_password == "secret-pass"
    assert settings.db_path == "/tmp/test.db"
    assert settings.retention_days == 3


def test_get_settings_defaults(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "secret-token")
    monkeypatch.setenv("UI_PASSWORD", "secret-pass")
    monkeypatch.delenv("DB_PATH", raising=False)
    monkeypatch.delenv("RETENTION_DAYS", raising=False)

    settings = get_settings()

    assert settings.db_path == "dashboard.db"
    assert settings.retention_days == 7


def test_get_settings_requires_api_token(monkeypatch):
    monkeypatch.delenv("API_TOKEN", raising=False)
    monkeypatch.setenv("UI_PASSWORD", "secret-pass")

    with pytest.raises(ValueError):
        get_settings()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.config'`

- [ ] **Step 3: Write implementation**

```python
# app/config.py
import os

from pydantic import BaseModel


class Settings(BaseModel):
    api_token: str
    ui_password: str
    db_path: str = "dashboard.db"
    retention_days: int = 7


def get_settings() -> Settings:
    api_token = os.environ.get("API_TOKEN", "")
    ui_password = os.environ.get("UI_PASSWORD", "")
    if not api_token:
        raise ValueError("API_TOKEN environment variable is required")
    if not ui_password:
        raise ValueError("UI_PASSWORD environment variable is required")

    return Settings(
        api_token=api_token,
        ui_password=ui_password,
        db_path=os.environ.get("DB_PATH", "dashboard.db"),
        retention_days=int(os.environ.get("RETENTION_DAYS", "7")),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat: add environment-based settings"
```

---

### Task 3: Database module (schema + connection)

**Files:**
- Create: `app/db.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Produces: `app.db.get_connection(db_path: str) -> sqlite3.Connection` (row_factory set to `sqlite3.Row`, foreign keys on). Produces `app.db.init_db(conn: sqlite3.Connection) -> None` — creates tables `flux_samples`, `inventory`, `orders` if not exist.
- Schema:
  - `flux_samples(id INTEGER PRIMARY KEY AUTOINCREMENT, bucket_ts INTEGER NOT NULL UNIQUE, energy_in REAL NOT NULL, energy_out REAL NOT NULL, buffer REAL NOT NULL, capacity REAL)`
  - `inventory(id INTEGER PRIMARY KEY CHECK (id = 1), ts INTEGER NOT NULL, items_json TEXT NOT NULL, craftables_json TEXT NOT NULL)`
  - `orders(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, item TEXT NOT NULL, label TEXT NOT NULL, amount REAL NOT NULL, status TEXT NOT NULL, message TEXT, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)`
- Consumes: nothing.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_db.py
import sqlite3

from app.db import get_connection, init_db


def test_init_db_creates_tables(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = get_connection(db_path)
    init_db(conn)

    tables = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert {"flux_samples", "inventory", "orders"} <= tables


def test_get_connection_returns_row_factory(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = get_connection(db_path)
    assert conn.row_factory is sqlite3.Row


def test_flux_samples_bucket_ts_unique(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = get_connection(db_path)
    init_db(conn)

    conn.execute(
        "INSERT INTO flux_samples (bucket_ts, energy_in, energy_out, buffer, capacity) "
        "VALUES (1000, 1.0, 2.0, 3.0, 4.0)"
    )
    conn.commit()

    try:
        conn.execute(
            "INSERT INTO flux_samples (bucket_ts, energy_in, energy_out, buffer, capacity) "
            "VALUES (1000, 9.0, 9.0, 9.0, 9.0)"
        )
        conn.commit()
        assert False, "expected IntegrityError"
    except sqlite3.IntegrityError:
        pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_db.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.db'`

- [ ] **Step 3: Write implementation**

```python
# app/db.py
import sqlite3


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS flux_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bucket_ts INTEGER NOT NULL UNIQUE,
            energy_in REAL NOT NULL,
            energy_out REAL NOT NULL,
            buffer REAL NOT NULL,
            capacity REAL
        );

        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            ts INTEGER NOT NULL,
            items_json TEXT NOT NULL,
            craftables_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            item TEXT NOT NULL,
            label TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
        """
    )
    conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_db.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add app/db.py tests/test_db.py
git commit -m "feat: add SQLite schema and connection helper"
```

---

### Task 4: Pydantic models for API payloads

**Files:**
- Create: `app/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces (all `pydantic.BaseModel`):
  - `InventoryEntry(kind: Literal["item", "fluid"], name: str, label: str, count: float)`
  - `CraftableEntry(kind: Literal["item", "fluid"], name: str, label: str)`
  - `FluxPayload(energy_in: float, energy_out: float, buffer: float, capacity: float | None = None)`
  - `InventoryPayload(items: list[InventoryEntry], craftables: list[CraftableEntry])`
  - `OrderResultPayload(status: Literal["requested", "done", "failed"], message: str | None = None)`
  - `CreateOrderPayload(kind: Literal["item", "fluid"], item: str, label: str, amount: float)`
  - `LoginPayload(password: str)`
- Consumes: nothing.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
import pytest
from pydantic import ValidationError

from app.models import (
    CraftableEntry,
    CreateOrderPayload,
    FluxPayload,
    InventoryEntry,
    InventoryPayload,
    LoginPayload,
    OrderResultPayload,
)


def test_inventory_entry_rejects_unknown_kind():
    with pytest.raises(ValidationError):
        InventoryEntry(kind="gas", name="x", label="X", count=1)


def test_inventory_entry_accepts_item_and_fluid():
    InventoryEntry(kind="item", name="minecraft:iron_ingot", label="Iron Ingot", count=64)
    InventoryEntry(kind="fluid", name="minecraft:lava", label="Lava", count=8000)


def test_flux_payload_capacity_optional():
    payload = FluxPayload(energy_in=1.0, energy_out=2.0, buffer=3.0)
    assert payload.capacity is None


def test_inventory_payload_nested():
    payload = InventoryPayload(
        items=[InventoryEntry(kind="item", name="a", label="A", count=1)],
        craftables=[CraftableEntry(kind="fluid", name="b", label="B")],
    )
    assert payload.items[0].name == "a"
    assert payload.craftables[0].kind == "fluid"


def test_order_result_payload_rejects_unknown_status():
    with pytest.raises(ValidationError):
        OrderResultPayload(status="queued")


def test_create_order_payload_requires_amount():
    with pytest.raises(ValidationError):
        CreateOrderPayload(kind="item", item="a", label="A")


def test_login_payload():
    assert LoginPayload(password="x").password == "x"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models'`

- [ ] **Step 3: Write implementation**

```python
# app/models.py
from typing import Literal

from pydantic import BaseModel


class InventoryEntry(BaseModel):
    kind: Literal["item", "fluid"]
    name: str
    label: str
    count: float


class CraftableEntry(BaseModel):
    kind: Literal["item", "fluid"]
    name: str
    label: str


class FluxPayload(BaseModel):
    energy_in: float
    energy_out: float
    buffer: float
    capacity: float | None = None


class InventoryPayload(BaseModel):
    items: list[InventoryEntry]
    craftables: list[CraftableEntry]


class OrderResultPayload(BaseModel):
    status: Literal["requested", "done", "failed"]
    message: str | None = None


class CreateOrderPayload(BaseModel):
    kind: Literal["item", "fluid"]
    item: str
    label: str
    amount: float


class LoginPayload(BaseModel):
    password: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add app/models.py tests/test_models.py
git commit -m "feat: add pydantic models for API payloads"
```

---

### Task 5: Auth helpers (Bearer token + session cookie)

**Files:**
- Create: `app/auth.py`
- Test: `tests/test_auth.py`

**Interfaces:**
- Produces:
  - `app.auth.verify_client_token(authorization: str | None, expected_token: str) -> bool` — `True` iff `authorization == f"Bearer {expected_token}"`.
  - `app.auth.create_session_token(password: str, expected_password: str) -> str | None` — returns a random opaque session token if `password == expected_password`, else `None`.
  - `app.auth.SessionStore` — in-memory class with `.add(token: str) -> None`, `.contains(token: str) -> bool`, `.clear() -> None`.
- Consumes: nothing (pure functions / standalone class; FastAPI dependency wiring happens in routers in Task 7/8).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_auth.py
from app.auth import SessionStore, create_session_token, verify_client_token


def test_verify_client_token_accepts_matching_bearer():
    assert verify_client_token("Bearer secret", "secret") is True


def test_verify_client_token_rejects_mismatch():
    assert verify_client_token("Bearer wrong", "secret") is False


def test_verify_client_token_rejects_missing_header():
    assert verify_client_token(None, "secret") is False


def test_verify_client_token_rejects_malformed_header():
    assert verify_client_token("secret", "secret") is False


def test_create_session_token_returns_token_on_match():
    token = create_session_token("pw", "pw")
    assert isinstance(token, str)
    assert len(token) > 10


def test_create_session_token_returns_none_on_mismatch():
    assert create_session_token("wrong", "pw") is None


def test_session_store_add_and_contains():
    store = SessionStore()
    assert store.contains("abc") is False
    store.add("abc")
    assert store.contains("abc") is True


def test_session_store_clear():
    store = SessionStore()
    store.add("abc")
    store.clear()
    assert store.contains("abc") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_auth.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.auth'`

- [ ] **Step 3: Write implementation**

```python
# app/auth.py
import secrets


def verify_client_token(authorization: str | None, expected_token: str) -> bool:
    if authorization is None:
        return False
    if not authorization.startswith("Bearer "):
        return False
    token = authorization[len("Bearer "):]
    return secrets.compare_digest(token, expected_token)


def create_session_token(password: str, expected_password: str) -> str | None:
    if not secrets.compare_digest(password, expected_password):
        return None
    return secrets.token_urlsafe(32)


class SessionStore:
    def __init__(self) -> None:
        self._tokens: set[str] = set()

    def add(self, token: str) -> None:
        self._tokens.add(token)

    def contains(self, token: str) -> bool:
        return token in self._tokens

    def clear(self) -> None:
        self._tokens.clear()
```

Note: `secrets.compare_digest` requires `str` or `bytes` of any length (it's constant-time regardless of equal length), used here to avoid timing attacks on token/password comparison.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_auth.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add app/auth.py tests/test_auth.py
git commit -m "feat: add bearer token and session auth helpers"
```

---

### Task 6: Store — Flux samples (hourly bucketing + retention)

**Files:**
- Create: `app/store.py` (this task adds the flux-related functions; later tasks append to this file)
- Test: `tests/test_store_flux.py`

**Interfaces:**
- Produces:
  - `app.store.record_flux_sample(conn: sqlite3.Connection, payload: FluxPayload, now_ts: int) -> None` — computes `bucket_ts = now_ts - (now_ts % 3600)`; if a row with that `bucket_ts` already exists, does nothing; otherwise inserts. Also deletes rows older than `retention_days` (passed as second now-based cutoff) — see signature below, retention is a separate function so it's independently testable.
  - `app.store.get_flux_history(conn: sqlite3.Connection) -> list[dict]` — returns all `flux_samples` rows ordered by `bucket_ts` ascending, as plain dicts with keys `bucket_ts, energy_in, energy_out, buffer, capacity`.
  - `app.store.prune_flux_samples(conn: sqlite3.Connection, cutoff_ts: int) -> None` — deletes rows with `bucket_ts < cutoff_ts`.
- Consumes: `app.models.FluxPayload` (Task 4), `app.db.get_connection`/`init_db` (Task 3) in tests.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_store_flux.py
from app.db import get_connection, init_db
from app.models import FluxPayload
from app.store import get_flux_history, prune_flux_samples, record_flux_sample


def _conn(tmp_path):
    conn = get_connection(str(tmp_path / "test.db"))
    init_db(conn)
    return conn


def test_record_flux_sample_inserts_new_bucket(tmp_path):
    conn = _conn(tmp_path)
    payload = FluxPayload(energy_in=10.0, energy_out=5.0, buffer=100.0, capacity=200.0)

    record_flux_sample(conn, payload, now_ts=3700)  # bucket 0 (3700 % 3600 = 100)

    history = get_flux_history(conn)
    assert len(history) == 1
    assert history[0]["bucket_ts"] == 3600
    assert history[0]["energy_in"] == 10.0


def test_record_flux_sample_dedupes_same_bucket(tmp_path):
    conn = _conn(tmp_path)
    first = FluxPayload(energy_in=10.0, energy_out=5.0, buffer=100.0)
    second = FluxPayload(energy_in=99.0, energy_out=99.0, buffer=99.0)

    record_flux_sample(conn, first, now_ts=3700)
    record_flux_sample(conn, second, now_ts=3650)  # same bucket (3600)

    history = get_flux_history(conn)
    assert len(history) == 1
    assert history[0]["energy_in"] == 10.0  # first write wins, second is a no-op


def test_record_flux_sample_creates_new_bucket_next_hour(tmp_path):
    conn = _conn(tmp_path)
    record_flux_sample(conn, FluxPayload(energy_in=1.0, energy_out=1.0, buffer=1.0), now_ts=3700)
    record_flux_sample(conn, FluxPayload(energy_in=2.0, energy_out=2.0, buffer=2.0), now_ts=7300)

    history = get_flux_history(conn)
    assert [row["bucket_ts"] for row in history] == [3600, 7200]


def test_get_flux_history_orders_ascending(tmp_path):
    conn = _conn(tmp_path)
    record_flux_sample(conn, FluxPayload(energy_in=2.0, energy_out=2.0, buffer=2.0), now_ts=7300)
    record_flux_sample(conn, FluxPayload(energy_in=1.0, energy_out=1.0, buffer=1.0), now_ts=3700)

    history = get_flux_history(conn)
    assert [row["bucket_ts"] for row in history] == [3600, 7200]


def test_prune_flux_samples_removes_old_rows(tmp_path):
    conn = _conn(tmp_path)
    record_flux_sample(conn, FluxPayload(energy_in=1.0, energy_out=1.0, buffer=1.0), now_ts=3700)
    record_flux_sample(conn, FluxPayload(energy_in=2.0, energy_out=2.0, buffer=2.0), now_ts=99999999)

    prune_flux_samples(conn, cutoff_ts=99999999 - 3600)

    history = get_flux_history(conn)
    assert len(history) == 1
    assert history[0]["bucket_ts"] != 3600
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_store_flux.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.store'`

- [ ] **Step 3: Write implementation**

```python
# app/store.py
import sqlite3

from app.models import CreateOrderPayload, FluxPayload, InventoryPayload, OrderResultPayload

HOUR_SECONDS = 3600


def record_flux_sample(conn: sqlite3.Connection, payload: FluxPayload, now_ts: int) -> None:
    bucket_ts = now_ts - (now_ts % HOUR_SECONDS)
    existing = conn.execute(
        "SELECT 1 FROM flux_samples WHERE bucket_ts = ?", (bucket_ts,)
    ).fetchone()
    if existing is not None:
        return
    conn.execute(
        "INSERT INTO flux_samples (bucket_ts, energy_in, energy_out, buffer, capacity) "
        "VALUES (?, ?, ?, ?, ?)",
        (bucket_ts, payload.energy_in, payload.energy_out, payload.buffer, payload.capacity),
    )
    conn.commit()


def get_flux_history(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT bucket_ts, energy_in, energy_out, buffer, capacity "
        "FROM flux_samples ORDER BY bucket_ts ASC"
    ).fetchall()
    return [dict(row) for row in rows]


def prune_flux_samples(conn: sqlite3.Connection, cutoff_ts: int) -> None:
    conn.execute("DELETE FROM flux_samples WHERE bucket_ts < ?", (cutoff_ts,))
    conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_store_flux.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add app/store.py tests/test_store_flux.py
git commit -m "feat: add flux sample storage with hourly bucketing and retention"
```

---

### Task 7: Store — Inventory (latest snapshot)

**Files:**
- Modify: `app/store.py` (append)
- Test: `tests/test_store_inventory.py`

**Interfaces:**
- Produces:
  - `app.store.save_inventory(conn: sqlite3.Connection, payload: InventoryPayload, now_ts: int) -> None` — upserts the single row `id=1` in `inventory` (replace `ts`, `items_json`, `craftables_json`).
  - `app.store.get_inventory(conn: sqlite3.Connection) -> dict | None` — returns `{"ts": int, "items": [...], "craftables": [...]}` or `None` if no snapshot has ever been saved.
- Consumes: `app.models.InventoryPayload` (Task 4).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_store_inventory.py
from app.db import get_connection, init_db
from app.models import CraftableEntry, InventoryEntry, InventoryPayload
from app.store import get_inventory, save_inventory


def _conn(tmp_path):
    conn = get_connection(str(tmp_path / "test.db"))
    init_db(conn)
    return conn


def test_get_inventory_returns_none_when_empty(tmp_path):
    conn = _conn(tmp_path)
    assert get_inventory(conn) is None


def test_save_and_get_inventory_roundtrip(tmp_path):
    conn = _conn(tmp_path)
    payload = InventoryPayload(
        items=[InventoryEntry(kind="item", name="a", label="A", count=10)],
        craftables=[CraftableEntry(kind="fluid", name="b", label="B")],
    )

    save_inventory(conn, payload, now_ts=1000)
    result = get_inventory(conn)

    assert result["ts"] == 1000
    assert result["items"] == [{"kind": "item", "name": "a", "label": "A", "count": 10.0}]
    assert result["craftables"] == [{"kind": "fluid", "name": "b", "label": "B"}]


def test_save_inventory_overwrites_previous_snapshot(tmp_path):
    conn = _conn(tmp_path)
    first = InventoryPayload(
        items=[InventoryEntry(kind="item", name="a", label="A", count=1)], craftables=[]
    )
    second = InventoryPayload(
        items=[InventoryEntry(kind="item", name="z", label="Z", count=2)], craftables=[]
    )

    save_inventory(conn, first, now_ts=1000)
    save_inventory(conn, second, now_ts=2000)
    result = get_inventory(conn)

    assert result["ts"] == 2000
    assert result["items"] == [{"kind": "item", "name": "z", "label": "Z", "count": 2.0}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_store_inventory.py -v`
Expected: FAIL with `ImportError: cannot import name 'save_inventory' from 'app.store'`

- [ ] **Step 3: Write implementation**

Append to `app/store.py`:
```python
import json


def save_inventory(conn: sqlite3.Connection, payload: InventoryPayload, now_ts: int) -> None:
    items_json = json.dumps([item.model_dump() for item in payload.items])
    craftables_json = json.dumps([c.model_dump() for c in payload.craftables])
    conn.execute(
        "INSERT INTO inventory (id, ts, items_json, craftables_json) VALUES (1, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET ts = excluded.ts, "
        "items_json = excluded.items_json, craftables_json = excluded.craftables_json",
        (now_ts, items_json, craftables_json),
    )
    conn.commit()


def get_inventory(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute(
        "SELECT ts, items_json, craftables_json FROM inventory WHERE id = 1"
    ).fetchone()
    if row is None:
        return None
    return {
        "ts": row["ts"],
        "items": json.loads(row["items_json"]),
        "craftables": json.loads(row["craftables_json"]),
    }
```

Move the `import json` line to the top of the file alongside `import sqlite3` (keep imports grouped at the top, not inline).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_store_inventory.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add app/store.py tests/test_store_inventory.py
git commit -m "feat: add inventory snapshot storage"
```

---

### Task 8: Store — Orders (create, pending, update status)

**Files:**
- Modify: `app/store.py` (append)
- Test: `tests/test_store_orders.py`

**Interfaces:**
- Produces:
  - `app.store.create_order(conn: sqlite3.Connection, payload: CreateOrderPayload, now_ts: int) -> int` — inserts a row with `status="queued"`, returns the new `id`.
  - `app.store.get_pending_orders(conn: sqlite3.Connection) -> list[dict]` — rows with `status="queued"`, each `{"id", "kind", "item", "label", "amount"}`.
  - `app.store.get_all_orders(conn: sqlite3.Connection) -> list[dict]` — all rows ordered by `created_at` descending, each with all columns.
  - `app.store.update_order_status(conn: sqlite3.Connection, order_id: int, payload: OrderResultPayload, now_ts: int) -> bool` — sets `status`, `message`, `updated_at`; returns `False` if `order_id` doesn't exist, `True` otherwise.
- Consumes: `app.models.CreateOrderPayload`, `app.models.OrderResultPayload` (Task 4).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_store_orders.py
from app.db import get_connection, init_db
from app.models import CreateOrderPayload, OrderResultPayload
from app.store import (
    create_order,
    get_all_orders,
    get_pending_orders,
    update_order_status,
)


def _conn(tmp_path):
    conn = get_connection(str(tmp_path / "test.db"))
    init_db(conn)
    return conn


def test_create_order_returns_id_and_is_queued(tmp_path):
    conn = _conn(tmp_path)
    payload = CreateOrderPayload(kind="item", item="minecraft:iron_ingot", label="Iron Ingot", amount=64)

    order_id = create_order(conn, payload, now_ts=1000)

    pending = get_pending_orders(conn)
    assert len(pending) == 1
    assert pending[0]["id"] == order_id
    assert pending[0]["kind"] == "item"
    assert pending[0]["amount"] == 64.0


def test_get_pending_orders_excludes_non_queued(tmp_path):
    conn = _conn(tmp_path)
    payload = CreateOrderPayload(kind="fluid", item="minecraft:lava", label="Lava", amount=8000)
    order_id = create_order(conn, payload, now_ts=1000)

    update_order_status(conn, order_id, OrderResultPayload(status="requested"), now_ts=1500)

    assert get_pending_orders(conn) == []


def test_update_order_status_unknown_id_returns_false(tmp_path):
    conn = _conn(tmp_path)
    result = update_order_status(conn, 999, OrderResultPayload(status="done"), now_ts=1000)
    assert result is False


def test_update_order_status_sets_message_and_timestamp(tmp_path):
    conn = _conn(tmp_path)
    order_id = create_order(
        conn, CreateOrderPayload(kind="item", item="a", label="A", amount=1), now_ts=1000
    )

    result = update_order_status(
        conn, order_id, OrderResultPayload(status="failed", message="no pattern"), now_ts=2000
    )

    assert result is True
    orders = get_all_orders(conn)
    assert orders[0]["status"] == "failed"
    assert orders[0]["message"] == "no pattern"
    assert orders[0]["updated_at"] == 2000


def test_get_all_orders_ordered_by_created_at_desc(tmp_path):
    conn = _conn(tmp_path)
    create_order(conn, CreateOrderPayload(kind="item", item="a", label="A", amount=1), now_ts=1000)
    create_order(conn, CreateOrderPayload(kind="item", item="b", label="B", amount=2), now_ts=2000)

    orders = get_all_orders(conn)
    assert [o["item"] for o in orders] == ["b", "a"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_store_orders.py -v`
Expected: FAIL with `ImportError: cannot import name 'create_order' from 'app.store'`

- [ ] **Step 3: Write implementation**

Append to `app/store.py`:
```python
def create_order(conn: sqlite3.Connection, payload: CreateOrderPayload, now_ts: int) -> int:
    cursor = conn.execute(
        "INSERT INTO orders (kind, item, label, amount, status, message, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, 'queued', NULL, ?, ?)",
        (payload.kind, payload.item, payload.label, payload.amount, now_ts, now_ts),
    )
    conn.commit()
    return cursor.lastrowid


def get_pending_orders(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT id, kind, item, label, amount FROM orders WHERE status = 'queued' "
        "ORDER BY created_at ASC"
    ).fetchall()
    return [dict(row) for row in rows]


def get_all_orders(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT id, kind, item, label, amount, status, message, created_at, updated_at "
        "FROM orders ORDER BY created_at DESC"
    ).fetchall()
    return [dict(row) for row in rows]


def update_order_status(
    conn: sqlite3.Connection, order_id: int, payload: OrderResultPayload, now_ts: int
) -> bool:
    cursor = conn.execute(
        "UPDATE orders SET status = ?, message = ?, updated_at = ? WHERE id = ?",
        (payload.status, payload.message, now_ts, order_id),
    )
    conn.commit()
    return cursor.rowcount > 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_store_orders.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add app/store.py tests/test_store_orders.py
git commit -m "feat: add order creation, pending lookup, and status updates"
```

---

### Task 9: Client router (`/api/client/*`)

**Files:**
- Create: `app/routers/__init__.py` (empty)
- Create: `app/routers/client.py`
- Modify: `app/main.py`
- Test: `tests/test_client_router.py`

**Interfaces:**
- Produces: `app.routers.client.router` (an `APIRouter`, prefix `/api/client`) with:
  - `POST /api/client/flux` — body `FluxPayload` → `{"ok": True}`. Calls `store.record_flux_sample` + `store.prune_flux_samples`.
  - `POST /api/client/inventory` — body `InventoryPayload` → `{"ok": True}`. Calls `store.save_inventory`.
  - `GET /api/client/orders/pending` → `{"orders": [...]}`. Calls `store.get_pending_orders`.
  - `POST /api/client/orders/{order_id}/result` — body `OrderResultPayload` → `{"ok": True}` or `404`.
  - All routes depend on a Bearer-token check via FastAPI `Depends`.
- Consumes: `app.auth.verify_client_token` (Task 5), `app.store.*` (Tasks 6-8), `app.config.get_settings`/`app.db.get_connection`+`init_db` (Tasks 2-3).
- Wiring detail: `app/main.py` creates one shared `sqlite3.Connection` at startup (via `app.state`) and a `Settings` instance, exposed to routers via dependency functions `get_db(request: Request) -> sqlite3.Connection` and `get_settings_dep(request: Request) -> Settings`, both reading from `request.app.state`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_client_router.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_client_router.py -v`
Expected: FAIL with `404 Not Found` for `/api/client/flux` (router not wired) or import error.

- [ ] **Step 3: Write implementation**

```python
# app/routers/__init__.py
```

```python
# app/routers/client.py
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.auth import verify_client_token
from app.config import Settings
from app.models import FluxPayload, InventoryPayload, OrderResultPayload
from app.store import (
    get_pending_orders,
    record_flux_sample,
    save_inventory,
    prune_flux_samples,
    update_order_status,
)

router = APIRouter(prefix="/api/client")

HOUR_SECONDS = 3600


def require_client_auth(
    request: Request, authorization: str | None = Header(default=None)
) -> None:
    settings: Settings = request.app.state.settings
    if not verify_client_token(authorization, settings.api_token):
        raise HTTPException(status_code=401, detail="invalid or missing token")


@router.post("/flux", dependencies=[Depends(require_client_auth)])
def post_flux(payload: FluxPayload, request: Request):
    conn = request.app.state.db
    settings: Settings = request.app.state.settings
    now_ts = int(time.time())
    record_flux_sample(conn, payload, now_ts)
    cutoff = now_ts - settings.retention_days * 24 * HOUR_SECONDS
    prune_flux_samples(conn, cutoff)
    return {"ok": True}


@router.post("/inventory", dependencies=[Depends(require_client_auth)])
def post_inventory(payload: InventoryPayload, request: Request):
    conn = request.app.state.db
    save_inventory(conn, payload, now_ts=int(time.time()))
    return {"ok": True}


@router.get("/orders/pending", dependencies=[Depends(require_client_auth)])
def get_orders_pending(request: Request):
    conn = request.app.state.db
    return {"orders": get_pending_orders(conn)}


@router.post("/orders/{order_id}/result", dependencies=[Depends(require_client_auth)])
def post_order_result(order_id: int, payload: OrderResultPayload, request: Request):
    conn = request.app.state.db
    found = update_order_status(conn, order_id, payload, now_ts=int(time.time()))
    if not found:
        raise HTTPException(status_code=404, detail="order not found")
    return {"ok": True}
```

Update `app/main.py`:
```python
from fastapi import FastAPI

from app.config import get_settings
from app.db import get_connection, init_db
from app.routers import client

app = FastAPI(title="AE2 + Flux Networks Dashboard")

app.state.settings = get_settings()
app.state.db = get_connection(app.state.settings.db_path)
init_db(app.state.db)

app.include_router(client.router)


@app.get("/healthz")
def healthz():
    return {"ok": True}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_client_router.py -v`
Expected: 6 passed

- [ ] **Step 5: Run full test suite to check no regressions**

Run: `pytest -v`
Expected: all tests so far pass.

- [ ] **Step 6: Commit**

```bash
git add app/routers/__init__.py app/routers/client.py app/main.py tests/test_client_router.py
git commit -m "feat: add client-facing API router with bearer auth"
```

---

### Task 10: UI router (`/api/ui/*`)

**Files:**
- Create: `app/routers/ui.py`
- Modify: `app/main.py`
- Test: `tests/test_ui_router.py`

**Interfaces:**
- Produces: `app.routers.ui.router` (an `APIRouter`, prefix `/api/ui`) with:
  - `POST /api/ui/login` — body `LoginPayload` → on success, sets cookie `session` and returns `{"ok": True}`; on failure, `401`.
  - `GET /api/ui/stats` — requires session cookie → `{"current": {...} | None, "history": [...], "last_seen": int | None}`. `current` is the most recent flux sample as a dict, `history` is `store.get_flux_history`, `last_seen` is the inventory's `ts` (used by frontend to detect "client offline" — reusing inventory `ts` since flux and inventory arrive together each poll cycle).
  - `GET /api/ui/items` — requires session cookie → `{"items": [...], "craftables": [...], "last_seen": int | None}`.
  - `POST /api/ui/orders` — requires session cookie, body `CreateOrderPayload` → `{"id": int}`.
  - `GET /api/ui/orders` — requires session cookie → `{"orders": [...]}`.
  - Session dependency `require_ui_auth(request: Request, session: str | None = Cookie(default=None))` raises `401` if cookie missing or not in `app.state.sessions` (a `SessionStore`).
- Consumes: `app.auth.create_session_token`, `app.auth.SessionStore` (Task 5); `app.store.get_flux_history`, `get_inventory`, `create_order`, `get_all_orders` (Tasks 6-8).
- Wiring: `app.state.sessions = SessionStore()` added in `app/main.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ui_router.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui_router.py -v`
Expected: FAIL (404 on `/api/ui/login`, router not wired).

- [ ] **Step 3: Write implementation**

```python
# app/routers/ui.py
import time

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response

from app.auth import create_session_token
from app.config import Settings
from app.models import CreateOrderPayload
from app.store import (
    create_order,
    get_all_orders,
    get_flux_history,
    get_inventory,
)

router = APIRouter(prefix="/api/ui")


def require_ui_auth(request: Request, session: str | None = Cookie(default=None)) -> None:
    if session is None or not request.app.state.sessions.contains(session):
        raise HTTPException(status_code=401, detail="not logged in")


@router.post("/login")
def login(payload: "LoginPayload", request: Request, response: Response):
    settings: Settings = request.app.state.settings
    token = create_session_token(payload.password, settings.ui_password)
    if token is None:
        raise HTTPException(status_code=401, detail="invalid password")
    request.app.state.sessions.add(token)
    response.set_cookie("session", token, httponly=True, samesite="lax")
    return {"ok": True}


@router.get("/stats", dependencies=[Depends(require_ui_auth)])
def get_stats(request: Request):
    conn = request.app.state.db
    history = get_flux_history(conn)
    current = history[-1] if history else None
    inventory = get_inventory(conn)
    last_seen = inventory["ts"] if inventory else None
    return {"current": current, "history": history, "last_seen": last_seen}


@router.get("/items", dependencies=[Depends(require_ui_auth)])
def get_items(request: Request):
    conn = request.app.state.db
    inventory = get_inventory(conn)
    if inventory is None:
        return {"items": [], "craftables": [], "last_seen": None}
    return {
        "items": inventory["items"],
        "craftables": inventory["craftables"],
        "last_seen": inventory["ts"],
    }


@router.post("/orders", dependencies=[Depends(require_ui_auth)])
def post_order(payload: CreateOrderPayload, request: Request):
    conn = request.app.state.db
    order_id = create_order(conn, payload, now_ts=int(time.time()))
    return {"id": order_id}


@router.get("/orders", dependencies=[Depends(require_ui_auth)])
def list_orders(request: Request):
    conn = request.app.state.db
    return {"orders": get_all_orders(conn)}
```

Fix the forward-reference import — add at the top of `app/routers/ui.py`:
```python
from app.models import LoginPayload
```
and change the `login` signature to `def login(payload: LoginPayload, ...)` (remove the string-quoted forward reference used above; it was illustrative only — write the real import).

Update `app/main.py`:
```python
from fastapi import FastAPI

from app.auth import SessionStore
from app.config import get_settings
from app.db import get_connection, init_db
from app.routers import client, ui

app = FastAPI(title="AE2 + Flux Networks Dashboard")

app.state.settings = get_settings()
app.state.db = get_connection(app.state.settings.db_path)
init_db(app.state.db)
app.state.sessions = SessionStore()

app.include_router(client.router)
app.include_router(ui.router)


@app.get("/healthz")
def healthz():
    return {"ok": True}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ui_router.py -v`
Expected: 7 passed

- [ ] **Step 5: Run full test suite**

Run: `pytest -v`
Expected: all tests pass, no regressions.

- [ ] **Step 6: Commit**

```bash
git add app/routers/ui.py app/main.py tests/test_ui_router.py
git commit -m "feat: add UI-facing API router with session auth"
```

---

### Task 11: Static serving wiring

**Files:**
- Modify: `app/main.py`
- Test: `tests/test_static.py`

**Interfaces:**
- Produces: `app/main.py` mounts `app/static/` at `/` via `StaticFiles(html=True)`, so `GET /` serves `app/static/index.html`. Mounted **after** all API routers so it doesn't shadow `/api/*` or `/healthz`.
- Consumes: nothing new.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_static.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_static.py -v`
Expected: FAIL — `/` returns 404 (no `app/static/index.html` yet, no mount).

- [ ] **Step 3: Create a placeholder static file and wire the mount**

```bash
mkdir -p app/static
```

`app/static/index.html` (placeholder, replaced with real UI in Task 12):
```html
<!DOCTYPE html>
<html>
<head><title>AE2 + Flux Dashboard</title></head>
<body>Loading...</body>
</html>
```

Update `app/main.py` — add at the bottom, after `app.include_router(ui.router)` and the `/healthz` route:
```python
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_static.py -v`
Expected: 2 passed

- [ ] **Step 5: Run full test suite**

Run: `pytest -v`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/main.py app/static/index.html tests/test_static.py
git commit -m "feat: serve static frontend, mounted after API routes"
```

---

### Task 12: Frontend — login + stats panel

**Files:**
- Modify: `app/static/index.html`
- Create: `app/static/styles.css`
- Create: `app/static/app.js`

**Interfaces:**
- Produces: a working login form and a stats panel that polls `/api/ui/stats` every 5s and renders a Chart.js line chart (energy_in/energy_out over `history`) plus current buffer/capacity numbers. No automated test (vanilla JS, no test runner per spec's YAGNI) — verified manually in Step 4 below.
- Consumes: `/api/ui/login`, `/api/ui/stats` (Task 10).

- [ ] **Step 1: Write `app/static/index.html`**

```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <title>AE2 + Flux Dashboard</title>
  <link rel="stylesheet" href="/styles.css" />
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
</head>
<body>
  <div id="login-view">
    <h1>Вход</h1>
    <form id="login-form">
      <input type="password" id="password" placeholder="Пароль" required />
      <button type="submit">Войти</button>
    </form>
    <p id="login-error" class="error"></p>
  </div>

  <div id="dashboard-view" hidden>
    <header>
      <h1>AE2 + Flux Networks Dashboard</h1>
      <span id="offline-badge" class="badge" hidden>client offline</span>
    </header>

    <section id="stats-panel">
      <h2>Энергия (Flux Networks)</h2>
      <div id="stats-current"></div>
      <canvas id="stats-chart" height="100"></canvas>
    </section>

    <section id="orders-panel">
      <h2>Заказы</h2>
      <input type="text" id="item-search" placeholder="Поиск предмета/жидкости..." />
      <ul id="craftables-list"></ul>
      <h3>Очередь заказов</h3>
      <ul id="orders-list"></ul>
    </section>
  </div>

  <script src="/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write `app/static/styles.css`**

```css
body {
  font-family: system-ui, sans-serif;
  margin: 0;
  padding: 1rem;
  background: #1a1a1a;
  color: #eee;
}

header {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.badge {
  background: #b33;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.85rem;
}

.error {
  color: #f55;
}

section {
  margin-top: 1.5rem;
}

input, button {
  font-size: 1rem;
  padding: 0.4rem;
}

ul {
  list-style: none;
  padding: 0;
}

li {
  display: flex;
  justify-content: space-between;
  padding: 0.3rem 0;
  border-bottom: 1px solid #333;
}
```

- [ ] **Step 3: Write `app/static/app.js`**

```javascript
const loginView = document.getElementById("login-view");
const dashboardView = document.getElementById("dashboard-view");
const loginForm = document.getElementById("login-form");
const loginError = document.getElementById("login-error");
const offlineBadge = document.getElementById("offline-badge");
const statsCurrent = document.getElementById("stats-current");
const craftablesList = document.getElementById("craftables-list");
const ordersList = document.getElementById("orders-list");
const itemSearch = document.getElementById("item-search");

let chart = null;
let allCraftables = [];

async function api(path, options = {}) {
  const resp = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (resp.status === 401) {
    showLogin();
    throw new Error("unauthorized");
  }
  return resp;
}

function showLogin() {
  loginView.hidden = false;
  dashboardView.hidden = true;
}

function showDashboard() {
  loginView.hidden = true;
  dashboardView.hidden = false;
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const password = document.getElementById("password").value;
  const resp = await fetch("/api/ui/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (resp.ok) {
    loginError.textContent = "";
    showDashboard();
    refreshAll();
    startPolling();
  } else {
    loginError.textContent = "Неверный пароль";
  }
});

function isOffline(lastSeen) {
  if (lastSeen === null || lastSeen === undefined) return true;
  return Date.now() / 1000 - lastSeen > 120;
}

function unitFor(kind) {
  return kind === "fluid" ? "мБ" : "шт";
}

async function refreshStats() {
  const resp = await api("/api/ui/stats");
  const data = await resp.json();
  offlineBadge.hidden = !isOffline(data.last_seen);

  if (data.current) {
    statsCurrent.textContent =
      `Приход: ${data.current.energy_in} | Расход: ${data.current.energy_out} | ` +
      `Буфер: ${data.current.buffer}${data.current.capacity ? " / " + data.current.capacity : ""}`;
  } else {
    statsCurrent.textContent = "Нет данных";
  }

  const labels = data.history.map((row) =>
    new Date(row.bucket_ts * 1000).toLocaleString("ru-RU", { hour: "2-digit", day: "2-digit", month: "2-digit" })
  );
  const energyIn = data.history.map((row) => row.energy_in);
  const energyOut = data.history.map((row) => row.energy_out);

  if (chart === null) {
    const ctx = document.getElementById("stats-chart");
    chart = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "Приход", data: energyIn, borderColor: "#4caf50" },
          { label: "Расход", data: energyOut, borderColor: "#f44336" },
        ],
      },
    });
  } else {
    chart.data.labels = labels;
    chart.data.datasets[0].data = energyIn;
    chart.data.datasets[1].data = energyOut;
    chart.update();
  }
}

function renderCraftables(craftables) {
  craftablesList.innerHTML = "";
  for (const c of craftables) {
    const li = document.createElement("li");
    const label = document.createElement("span");
    label.textContent = `${c.label} (${c.kind === "fluid" ? "жидкость" : "предмет"})`;

    const amountInput = document.createElement("input");
    amountInput.type = "number";
    amountInput.min = "1";
    amountInput.placeholder = unitFor(c.kind);
    amountInput.style.width = "5rem";

    const orderButton = document.createElement("button");
    orderButton.textContent = "Заказать";
    orderButton.addEventListener("click", async () => {
      const amount = parseFloat(amountInput.value);
      if (!amount || amount <= 0) return;
      await api("/api/ui/orders", {
        method: "POST",
        body: JSON.stringify({ kind: c.kind, item: c.name, label: c.label, amount }),
      });
      refreshOrders();
    });

    const controls = document.createElement("span");
    controls.append(amountInput, orderButton);

    li.append(label, controls);
    craftablesList.appendChild(li);
  }
}

async function refreshItems() {
  const resp = await api("/api/ui/items");
  const data = await resp.json();
  allCraftables = data.craftables;
  renderCraftables(allCraftables);
}

itemSearch.addEventListener("input", () => {
  const query = itemSearch.value.toLowerCase();
  renderCraftables(allCraftables.filter((c) => c.label.toLowerCase().includes(query)));
});

async function refreshOrders() {
  const resp = await api("/api/ui/orders");
  const data = await resp.json();
  ordersList.innerHTML = "";
  for (const order of data.orders) {
    const li = document.createElement("li");
    li.textContent =
      `${order.label} x${order.amount}${unitFor(order.kind)} — ${order.status}` +
      (order.message ? ` (${order.message})` : "");
    ordersList.appendChild(li);
  }
}

function refreshAll() {
  refreshStats();
  refreshItems();
  refreshOrders();
}

function startPolling() {
  setInterval(refreshAll, 5000);
}

// On load, probe auth by trying an authenticated endpoint.
(async () => {
  try {
    await api("/api/ui/stats");
    showDashboard();
    refreshAll();
    startPolling();
  } catch {
    showLogin();
  }
})();
```

- [ ] **Step 4: Manual verification**

Run: `cd dashboard && API_TOKEN=test UI_PASSWORD=test123 uvicorn app.main:app --reload`

Open `http://127.0.0.1:8000` in a browser. Expected:
- Login form appears.
- Entering wrong password shows "Неверный пароль".
- Entering `test123` shows the dashboard with "Нет данных" (no flux data yet) and an empty craftables list.

In a second terminal, push a fake client update to confirm wiring end-to-end:
```bash
curl -X POST http://127.0.0.1:8000/api/client/flux \
  -H "Authorization: Bearer test" -H "Content-Type: application/json" \
  -d '{"energy_in": 100, "energy_out": 80, "buffer": 5000, "capacity": 10000}'

curl -X POST http://127.0.0.1:8000/api/client/inventory \
  -H "Authorization: Bearer test" -H "Content-Type: application/json" \
  -d '{"items": [{"kind": "item", "name": "minecraft:iron_ingot", "label": "Iron Ingot", "count": 64}], "craftables": [{"kind": "item", "name": "minecraft:iron_ingot", "label": "Iron Ingot"}, {"kind": "fluid", "name": "minecraft:lava", "label": "Lava"}]}'
```
Within 5 seconds, the dashboard should show the energy numbers, a chart point, and two craftable rows (Iron Ingot, Lava). Place an order on Lava and confirm it appears in "Очередь заказов" with status `queued`.

- [ ] **Step 5: Commit**

```bash
git add app/static/index.html app/static/styles.css app/static/app.js
git commit -m "feat: build login, stats chart, and orders frontend"
```

---

### Task 13: README with API contract

**Files:**
- Create: `README.md`

**Interfaces:**
- Produces: human-readable setup + API contract doc. No code interface.

- [ ] **Step 1: Write `README.md`**

```markdown
# AE2 + Flux Networks Dashboard

FastAPI backend + vanilla-JS frontend for ordering AE2 items/fluids and viewing Flux Networks
energy stats, pushed to by an OpenComputers client (see the separate `client` repo).

## Setup

\`\`\`bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

export API_TOKEN=<shared secret for the OpenComputers client>
export UI_PASSWORD=<browser login password>
export DB_PATH=dashboard.db        # optional, defaults to dashboard.db
export RETENTION_DAYS=7            # optional, defaults to 7

uvicorn app.main:app --host 0.0.0.0 --port 8000
\`\`\`

## Tests

\`\`\`bash
pytest -v
\`\`\`

## API Contract (shared with the `client` repo)

All `/api/client/*` endpoints require header `Authorization: Bearer <API_TOKEN>` (401 otherwise).
All `/api/ui/*` endpoints except `/api/ui/login` require a `session` cookie (401 otherwise).

`kind` is `"item"` or `"fluid"` on every inventory/craftable/order entry. For `"fluid"`,
quantities (`count`/`amount`) are in mB; for `"item"`, they are item counts.

### `POST /api/client/flux`
Request: `{"energy_in": number, "energy_out": number, "buffer": number, "capacity"?: number}`
Response: `{"ok": true}`

### `POST /api/client/inventory`
Request:
\`\`\`json
{
  "items": [{"kind": "item"|"fluid", "name": "...", "label": "...", "count": number}],
  "craftables": [{"kind": "item"|"fluid", "name": "...", "label": "..."}]
}
\`\`\`
Response: `{"ok": true}`

### `GET /api/client/orders/pending`
Response: `{"orders": [{"id": number, "kind": "item"|"fluid", "item": "...", "label": "...", "amount": number}]}`

### `POST /api/client/orders/{id}/result`
Request: `{"status": "requested"|"done"|"failed", "message"?: "..."}`
Response: `{"ok": true}` or `404` if the order id is unknown.

### Order lifecycle

\`\`\`
queued ──(client picks it up, calls requestCrafting)──▶ requested
requested ──(craft job finishes)──▶ done
requested ──(error)──▶ failed
\`\`\`
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add setup instructions and API contract"
```

---

## Self-Review Notes

- **Spec coverage:** Bearer auth (Task 5/9), session auth (Task 5/10), flux hourly bucketing + 7-day retention (Task 6/9), inventory snapshot with `kind` (Task 4/7), order lifecycle `queued→requested→done/failed` (Task 8/9), UI polling/chart/orders panel (Task 12), README contract (Task 13) — all covered.
- **Placeholder scan:** no TBD/TODO; all steps have full code.
- **Type consistency:** `FluxPayload`, `InventoryPayload`, `CreateOrderPayload`, `OrderResultPayload` field names match across `models.py`, `store.py`, both routers, and `app.js`. `bucket_ts` naming consistent between store and UI router response.
