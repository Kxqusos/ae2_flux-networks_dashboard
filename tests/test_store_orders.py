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
