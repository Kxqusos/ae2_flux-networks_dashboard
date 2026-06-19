import json
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
