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
