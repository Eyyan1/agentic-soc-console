# Render Demo Deployment

This backend can be deployed to Render as a web service without blocking port binding.

## Web service goal

The public Render web service should:

- boot quickly
- bind `0.0.0.0:$PORT`
- serve Django HTTP traffic only

It should not start the SOC background pipeline in the same web process.

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
```

If you attach a persistent disk, mount it at:

```text
/var/data
```

## Build command

```bash
pip install -r requirements.txt
```

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

## Health check

Set the Render health check path to:

```text
/api/health
```

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

That keeps the web service responsive while letting the SOC pipeline run separately.

## Behavior preservation

- Production behavior is unchanged unless these env vars are explicitly set.
- Local single-process demo behavior is preserved with:

```text
ASF_ENABLE_BACKGROUND_SERVICES=1
ASF_PROCESS_ROLE=all
```
