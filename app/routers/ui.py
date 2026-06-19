import time

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response

from app.auth import create_session_token
from app.config import Settings
from app.models import CreateOrderPayload, LoginPayload
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
def login(payload: LoginPayload, request: Request, response: Response):
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
    with request.app.state.db_lock:
        history = get_flux_history(conn)
        inventory = get_inventory(conn)
    current = history[-1] if history else None
    last_seen = inventory["ts"] if inventory else None
    return {"current": current, "history": history, "last_seen": last_seen}


@router.get("/items", dependencies=[Depends(require_ui_auth)])
def get_items(request: Request):
    conn = request.app.state.db
    with request.app.state.db_lock:
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
    with request.app.state.db_lock:
        order_id = create_order(conn, payload, now_ts=int(time.time()))
    return {"id": order_id}


@router.get("/orders", dependencies=[Depends(require_ui_auth)])
def list_orders(request: Request):
    conn = request.app.state.db
    with request.app.state.db_lock:
        orders = get_all_orders(conn)
    return {"orders": orders}
