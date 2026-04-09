# Render Demo Deployment

This backend can be deployed to Render as a web service without blocking port binding.

## Web service goal

The public Render web service should:

- boot quickly
- bind `0.0.0.0:$PORT`
- serve Django HTTP traffic only
- expose a tiny unauthenticated root probe at `/`

It should not start the SOC background pipeline in the same web process.

## Startup-safety changes

To keep Render port binding non-blocking in demo mode, the web startup path now avoids eager local-dev SOC imports:

- `ASP/urls.py`
  - no longer imports `Core.localdev_views` at module import time
  - uses explicit URL patterns with lazy dispatch for local-dev endpoints
- `Core/views.py`
  - no longer imports `Lib.api` during startup
  - `/api/health` uses a small local response helper
- `Lib/api.py`
  - DNS, domain parsing, and Excel libraries now import inside the helper functions that actually use them

This keeps `/` and `/api/health` light while preserving the rest of the local-dev API behavior on first request.

## Process role split

This repo now supports:

```text
ASF_PROCESS_ROLE=web|worker|all
```

Behavior:

- `web`
  - never starts `MainMonitor`
- `worker`
  - may start `MainMonitor` if `ASF_ENABLE_BACKGROUND_SERVICES=1`
- `all`
  - preserves current local single-process demo behavior

## Recommended Render web-service env

```text
SECRET_KEY=<random-secret>
PYTHON_VERSION=3.12
ASF_LOCAL_SIRP=1
ASF_FAKE_LLM=1
ASF_DISABLE_EMBEDDINGS=1
ASF_ENABLE_BACKGROUND_SERVICES=0
ASF_PROCESS_ROLE=web
ASF_LOCAL_DATA_DIR=/var/data
ASF_ALLOWED_FRONTEND_ORIGINS=https://agentic-soc-console.vercel.app
```

If you attach a persistent disk, mount it at:

```text
/var/data
```

`ASF_ALLOWED_FRONTEND_ORIGINS` is a comma-separated allowlist for browser frontend origins. The backend always allows these local dev origins by default:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

For deployed frontends, add the exact Vercel origin, for example:

```text
ASF_ALLOWED_FRONTEND_ORIGINS=https://agentic-soc-console.vercel.app
```

Multiple origins:

```text
ASF_ALLOWED_FRONTEND_ORIGINS=https://agentic-soc-console.vercel.app,https://staging-agentic-soc-console.vercel.app
```

## Build command

```bash
pip install -r requirements-demo.txt
```

`requirements-demo.txt` is intentionally lean for demo web deployments:

- keeps Django, DRF, ASGI serving, and Redis/Qdrant client packages needed by current local-dev API imports
- removes heavy ML/runtime packages not needed for fake-LLM plus embeddings-disabled demo mode
- leaves the full `requirements.txt` unchanged for broader local development

## Pre-deploy command

```bash
python manage.py migrate
```

## Render-ready start command

Use ASGI via gunicorn + uvicorn worker:

```bash
gunicorn ASP.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --workers 1 --timeout 120
```

This is preferred over `runserver` for Render.

## CORS behavior

The backend now includes a lightweight in-repo CORS middleware for demo deployment:

- allows the configured frontend origins above
- allows local Vite dev origins by default
- supports authenticated cross-origin requests for:
  - `/api/currentUser`
  - `/api/login/account`
  - `/api/local-dev/*`
- handles browser preflight `OPTIONS` requests without importing the heavier local-dev SOC modules

## Health check

Set the Render health check path to:

```text
/api/health
```

The root path `/` now returns a tiny unauthenticated JSON probe for platform port checks and lightweight smoke tests, but `/api/health` remains the main health endpoint.

Expected result:

- HTTP `200`
- payload includes:
  - `status: ok`
  - `process_role: web`

## Future split

Recommended future deployment:

1. Web service
   - `ASF_PROCESS_ROLE=web`
   - `ASF_ENABLE_BACKGROUND_SERVICES=0`
2. Background worker
   - `ASF_PROCESS_ROLE=worker`
   - `ASF_ENABLE_BACKGROUND_SERVICES=1`
   - install the full `requirements.txt`

That keeps the web service responsive while letting the SOC pipeline run separately.

## Behavior preservation

- Production behavior is unchanged unless these env vars are explicitly set.
- Local single-process demo behavior is preserved with:

```text
ASF_ENABLE_BACKGROUND_SERVICES=1
ASF_PROCESS_ROLE=all
```
