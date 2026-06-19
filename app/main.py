import threading

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.auth import SessionStore
from app.config import get_settings
from app.db import get_connection, init_db
from app.routers import client, ui

app = FastAPI(title="AE2 + Flux Networks Dashboard")

app.state.settings = get_settings()
app.state.db = get_connection(app.state.settings.db_path)
init_db(app.state.db)
# serializes access to the shared sqlite3.Connection across worker threads
app.state.db_lock = threading.Lock()
app.state.sessions = SessionStore()

app.include_router(client.router)
app.include_router(ui.router)


@app.get("/healthz")
def healthz():
    return {"ok": True}


app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
