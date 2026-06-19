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
