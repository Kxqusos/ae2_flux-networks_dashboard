from fastapi import FastAPI

app = FastAPI(title="AE2 + Flux Networks Dashboard")


@app.get("/healthz")
def healthz():
    return {"ok": True}
