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
