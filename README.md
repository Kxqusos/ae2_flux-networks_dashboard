# AE2 + Flux Networks Dashboard

FastAPI backend + vanilla-JS frontend for ordering AE2 items/fluids and viewing Flux Networks
energy stats, pushed to by an OpenComputers client (see the separate `client` repo).

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

export API_TOKEN=<shared secret for the OpenComputers client>
export UI_PASSWORD=<browser login password>
export DB_PATH=dashboard.db        # optional, defaults to dashboard.db
export RETENTION_DAYS=7            # optional, defaults to 7

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Tests

```bash
pytest -v
```

## Docker

To make the dashboard reachable from outside your machine (e.g. for the OpenComputers client
running in a separate Minecraft server), run it in Docker and expose port 8000:

```bash
docker build -t ae2-flux-dashboard .

docker run -d \
  --name ae2-flux-dashboard \
  -p 8000:8000 \
  -e API_TOKEN=<shared secret for the OpenComputers client> \
  -e UI_PASSWORD=<browser login password> \
  -v ae2-flux-dashboard-data:/data \
  ae2-flux-dashboard
```

- The container listens on `0.0.0.0:8000`, so `-p 8000:8000` (or any `<host-port>:8000`) makes
  it reachable from other machines on your network/internet, not just `localhost`.
- The SQLite database is stored at `/data/dashboard.db` inside the container; the named volume
  `ae2-flux-dashboard-data` persists it across container restarts/upgrades.
- Set `client`'s `config.lua` `dashboard_url` to `http://<host-ip-or-domain>:8000` and
  `api_token` to the same value as `API_TOKEN` above.
- Health check: `curl http://<host>:8000/healthz` → `{"ok": true}`.

## API Contract (shared with the `client` repo)

All `/api/client/*` endpoints require header `Authorization: Bearer <API_TOKEN>` (401 otherwise).
All `/api/ui/*` endpoints except `/api/ui/login` require a `session` cookie (401 otherwise).

`kind` is `"item"` or `"fluid"` on every inventory/craftable/order entry. For `"fluid"`,
quantities (`count`/`amount`) are in mB; for `"item"`, they are item counts.

### `POST /api/client/flux`
Request: `{"energy_in": number, "energy_out": number, "buffer": number, "capacity"?: number}`
Response: `{"ok": true}`

### `POST /api/client/inventory`
Request:
```json
{
  "items": [{"kind": "item"|"fluid", "name": "...", "label": "...", "count": number}],
  "craftables": [{"kind": "item"|"fluid", "name": "...", "label": "..."}]
}
```
Response: `{"ok": true}`

### `GET /api/client/orders/pending`
Response: `{"orders": [{"id": number, "kind": "item"|"fluid", "item": "...", "label": "...", "amount": number}]}`

### `POST /api/client/orders/{id}/result`
Request: `{"status": "requested"|"done"|"failed", "message"?: "..."}`
Response: `{"ok": true}` or `404` if the order id is unknown.

### Order lifecycle

```
queued ──(client picks it up, calls requestCrafting)──▶ requested
requested ──(craft job finishes)──▶ done
requested ──(error)──▶ failed
```
