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
    with request.app.state.db_lock:
        record_flux_sample(conn, payload, now_ts)
        cutoff = now_ts - settings.retention_days * 24 * HOUR_SECONDS
        prune_flux_samples(conn, cutoff)
    return {"ok": True}


@router.post("/inventory", dependencies=[Depends(require_client_auth)])
def post_inventory(payload: InventoryPayload, request: Request):
    conn = request.app.state.db
    with request.app.state.db_lock:
        save_inventory(conn, payload, now_ts=int(time.time()))
    return {"ok": True}


@router.get("/orders/pending", dependencies=[Depends(require_client_auth)])
def get_orders_pending(request: Request):
    conn = request.app.state.db
    with request.app.state.db_lock:
        orders = get_pending_orders(conn)
    return {"orders": orders}


@router.post("/orders/{order_id}/result", dependencies=[Depends(require_client_auth)])
def post_order_result(order_id: int, payload: OrderResultPayload, request: Request):
    conn = request.app.state.db
    with request.app.state.db_lock:
        found = update_order_status(conn, order_id, payload, now_ts=int(time.time()))
    if not found:
        raise HTTPException(status_code=404, detail="order not found")
    return {"ok": True}
