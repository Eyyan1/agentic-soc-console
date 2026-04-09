# Railway Demo Deployment

This backend can run on Railway in local-demo mode without external SIRP or paid LLM dependencies.

## Intended demo mode

Use these environment variables:

```text
ASF_LOCAL_SIRP=1
ASF_ENABLE_BACKGROUND_SERVICES=1
ASF_FAKE_LLM=1
ASF_DISABLE_EMBEDDINGS=1
```

These keep the demo behavior local and deterministic:

- file-backed local SIRP storage is enabled
- background monitor/services start in the Django process
- LLM calls stay on the fake local path
- embeddings stay disabled instead of requiring local model assets

## Local data directory

Local-demo data is now rooted under:

```text
ASF_LOCAL_DATA_DIR
```

If `ASF_LOCAL_DATA_DIR` is not set, the backend defaults safely to:

```text
<repo>/.runtime
```

The following local-demo files are stored there:

- `local_sirp_store.json`
- `local_soc_audit_log.json`
- `local_soc_response_jobs.json`

## Railway volume recommendation

For Railway, mount a persistent volume at:

```text
/data
```

Then set:

```text
ASF_LOCAL_DATA_DIR=/data
```

This keeps local-demo alerts, cases, audit history, and response-job history across restarts.

## Health endpoint

Unauthenticated health endpoint:

```text
GET /api/health
```

It returns:

- overall status
- current demo-mode flags
- resolved local data directory
- response action mode

## Response actions

In local-demo mode, response actions remain simulated only.

Examples:

- isolate host
- disable user
- block IP/domain/hash
- create ticket
- assign owner
- run playbook

They update local-demo state and audit/response-job history, but they do not call external containment systems.

## Recommended Railway start command

For a simple demo deployment:

```bash
python manage.py migrate && python manage.py runserver 0.0.0.0:$PORT --noreload
```

This is a demo-oriented command, not a production-grade WSGI/ASGI setup.

The repo now includes a committed [Procfile](/C:/Users/USER/Documents/agentic-soc-platform-master/Procfile) with that exact command so Railway can use it directly.

## Recommended Railway variables

Minimum:

```text
SECRET_KEY=<generate-a-random-value>
ASF_LOCAL_SIRP=1
ASF_ENABLE_BACKGROUND_SERVICES=1
ASF_FAKE_LLM=1
ASF_DISABLE_EMBEDDINGS=1
ASF_LOCAL_DATA_DIR=/data
```

Also ensure your existing Redis/Qdrant-related config is set appropriately for the demo environment if those services are attached.

## Deploy steps

1. Connect the GitHub repository to Railway.
2. Create a persistent volume and mount it at:

```text
/data
```

3. Set the demo environment variables:

```text
SECRET_KEY=<generate-a-random-value>
ASF_LOCAL_SIRP=1
ASF_ENABLE_BACKGROUND_SERVICES=1
ASF_FAKE_LLM=1
ASF_DISABLE_EMBEDDINGS=1
ASF_LOCAL_DATA_DIR=/data
```

4. Set any Redis/Qdrant-related variables required by your demo environment if those services are attached.
5. Deploy the service. Railway can use the committed `Procfile` start command:

```text
python manage.py migrate && python manage.py runserver 0.0.0.0:$PORT --noreload
```

6. After deployment, verify the health endpoint:

```text
GET /api/health
```

Expected result:

- HTTP `200`
- JSON payload with:
  - `"status": "ok"`
  - demo flag values
  - resolved `local_data_dir`

## Files committed for Railway

- [Procfile](/C:/Users/USER/Documents/agentic-soc-platform-master/Procfile)
  - Railway-friendly demo backend start command
- [docs/RAILWAY_DEMO.md](/C:/Users/USER/Documents/agentic-soc-platform-master/docs/RAILWAY_DEMO.md)
  - exact deploy steps, env vars, volume mount path, and health verification

No `railway.json` was added. It is optional here, and the committed `Procfile` is sufficient for this demo deployment flow while keeping the repo simpler.

## Behavior preservation

- Production behavior is unchanged unless these local-demo environment variables are explicitly enabled.
- The file-backed local SIRP path and simulated response actions are only used for the local-demo mode.
