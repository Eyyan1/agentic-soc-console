# Agentic SOC Platform

Local-first Django SOC platform with:

- token-authenticated backend API
- file-backed local-demo SOC mode
- Redis/Qdrant-supported pipeline execution
- React/Tailwind frontend under `frontend/`
- case, alert, playbook, campaign, asset, and response-job views

This repository is currently set up to run well for local development and demo deployments without requiring an external SIRP backend or paid LLM usage.

## What is in this repo

- Django backend in `ASP/`, `Core/`, `Lib/`, `PLUGINS/`
- streaming and playbook automation in `MODULES/` and `PLAYBOOKS/`
- bundled mock data and prompt assets in `DATA/`
- local frontend in `frontend/`
- deployment and local-dev docs in `docs/`

## Main capabilities

- Local SOC dashboard with:
  - alerts
  - cases
  - campaigns
  - assets
  - playbooks
  - activity timeline
  - response jobs
- Local-dev correlation and campaign grouping
- Deterministic fake-LLM mode for demos
- Simulated active response actions:
  - isolate host
  - disable user
  - block IP/domain/hash
  - create ticket
  - assign owner
  - run playbook
- Specialized local playbooks for:
  - phishing
  - file integrity monitoring
  - vulnerability remediation

## Architecture at a glance

The local demo flow is:

1. Mock or forwarded alerts are sent into Redis streams.
2. Modules consume those alerts and normalize them.
3. Local SIRP mode persists alerts, cases, artifacts, playbooks, audit history, and response jobs to file-backed storage.
4. The frontend reads that state through `/api/local-dev/*`.
5. Analysts can investigate alerts and cases, run playbooks, and trigger simulated response actions.

## Quick start

### Backend

Use Python `3.12`.

Create and activate a virtual environment, then install dependencies:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\activate
pip install -e .
```

Run database migrations:

```powershell
python manage.py migrate
```

Start the backend:

```powershell
python manage.py runserver 127.0.0.1:7000 --noreload
```

### Local demo mode

For the local SOC demo flow, start Django with:

```powershell
$env:ASF_LOCAL_SIRP='1'
$env:ASF_ENABLE_BACKGROUND_SERVICES='1'
$env:ASF_FAKE_LLM='1'
$env:ASF_DISABLE_EMBEDDINGS='1'
python manage.py runserver 127.0.0.1:7000 --noreload
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## Authentication

Backend auth is token-based.

Main endpoints:

- `POST /api/login/account`
- `GET /api/currentUser`

The frontend supports:

1. username/password login against `/api/login/account`
2. manual DRF token paste as fallback

## Local-dev API surface

When `ASF_LOCAL_SIRP=1`, the frontend and local demo flows use:

- `GET /api/health`
- `GET /api/local-dev/overview`
- `GET /api/local-dev/alerts`
- `GET /api/local-dev/assets`
- `GET /api/local-dev/campaigns`
- `GET /api/local-dev/cases`
- `GET /api/local-dev/playbooks`
- `GET /api/local-dev/messages`
- `GET /api/local-dev/audit`
- `GET /api/local-dev/response-jobs`
- `POST /api/local-dev/respond`
- `POST /api/local-dev/case-workflow`
- `POST /api/local-dev/demo-alerts`
- `POST /api/local-dev/fim-scan`
- `POST /api/local-dev/vulnerability-scan`

## Local storage

File-backed local SOC state is stored under:

- `ASF_LOCAL_DATA_DIR` if set
- otherwise `<repo>/.runtime`

That storage includes:

- local SIRP records
- audit log
- response jobs

## Health check

Unauthenticated health endpoint:

```text
GET /api/health
```

Use it to verify:

- backend reachability
- demo-mode flags
- resolved local data directory

## Demo deployment

Railway demo deployment guidance is in:

- [docs/RAILWAY_DEMO.md](docs/RAILWAY_DEMO.md)

The repo includes a committed:

- [Procfile](Procfile)

## Additional docs

- Local frontend UI: [docs/LOCAL_FRONTEND_UI.md](docs/LOCAL_FRONTEND_UI.md)
- Local SOC flow: [docs/LOCAL_DEV_SOC_FLOW.md](docs/LOCAL_DEV_SOC_FLOW.md)
- Frontend-specific notes: [frontend/README.md](frontend/README.md)

## Notes

- Production behavior is unchanged unless local-demo environment variables are explicitly enabled.
- In local-demo mode, response actions are simulated only.
- Fake-LLM mode is recommended for demos unless you intentionally configure a real OpenAI-compatible model backend.
