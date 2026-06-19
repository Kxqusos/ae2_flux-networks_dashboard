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
