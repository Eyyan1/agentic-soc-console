# Agentic SOC Frontend

Local React and Tailwind frontend for the Django-based Agentic SOC backend.

## What it does

- supports username and password login against `POST /api/login/account`
- stores the returned DRF token in browser local storage
- validates a pasted DRF token against `GET /api/currentUser`
- reads local-dev SOC data from:
  - `GET /api/local-dev/overview`
  - `GET /api/local-dev/alerts`
  - `GET /api/local-dev/assets`
  - `GET /api/local-dev/campaigns`
  - `GET /api/local-dev/cases`
  - `GET /api/local-dev/playbooks`
  - `GET /api/local-dev/messages`
  - `GET /api/local-dev/audit`
  - `GET /api/local-dev/response-jobs`
  - `GET /api/local-dev/alerts/<rowid>`
  - `GET /api/local-dev/assets/<rowid>`
  - `GET /api/local-dev/cases/<rowid>`
  - `GET /api/local-dev/playbooks/<rowid>`
  - `POST /api/local-dev/case-workflow`
- can trigger demo alert generation through:
  - `POST /api/local-dev/demo-alerts`
  - `POST /api/local-dev/fim-scan`
  - `POST /api/local-dev/vulnerability-scan`
- supports local-dev response actions through:
  - `POST /api/local-dev/respond`
- automatically falls back to seeded demo data if the local-dev endpoints are unavailable

## Run locally

From the repo root:

```powershell
cd frontend
npm install
npm run dev
```

The Vite dev server runs on:

```text
http://127.0.0.1:5173
```

## Backend assumptions

- Django backend is already running on `http://127.0.0.1:7000`
- local-dev SOC mode is enabled when you want real alert/case/playbook/message data:

```powershell
$env:ASF_LOCAL_SIRP='1'
```

## Login flow

The frontend supports two local auth paths:

1. Preferred path:
   - enter `username` and `password`
   - the UI calls `POST /api/login/account`
   - the returned token is stored in local storage
   - the UI then validates the session with `GET /api/currentUser`
2. Fallback path:
   - paste a DRF token manually into the token field
   - the UI validates it with `GET /api/currentUser`

This does not change backend auth behavior. It only makes the existing token-based flow easier to use from the local frontend.

## Demo action

When the backend is running with `ASF_LOCAL_SIRP=1`, the `Generate Demo Alerts` button calls `POST /api/local-dev/demo-alerts`.

That endpoint replays the bundled phishing mock batch into Redis so the local SOC pipeline can ingest and correlate it. After the request completes, the frontend waits briefly and refreshes alerts, cases, playbooks, and messages automatically.

## New local-dev SOC views

- Alert detail drawer
  - raw event
  - artifacts
  - linked case
  - linked campaigns
  - MITRE ATT&CK, risk score, confidence score, and explanation
  - enrichment context for user/domain/IP/host
  - recommended response actions
- Campaigns page
  - correlated alert clusters by user, asset, domain or IP, and time window
  - grouped alerts and attack summary
- Case detail drawer
  - case summary
  - linked alerts
  - linked assets
  - artifacts
  - related alerts
  - SLA timer and assignment state
  - attack timeline
  - activity timeline
  - notes
  - disposition
  - linked playbooks
  - response history
  - owner, note, status, and disposition workflow updates
- Asset inventory page
  - host criticality
  - last-seen and status
  - software inventory
  - vulnerability exposure
  - integrity findings
- Playbook run detail
  - step trace
  - output payloads
- Overview dashboard
  - severity distribution
  - open case count
  - MTTA and MTTR placeholders
  - top affected assets/users
- Activity page
  - merged playbook messages, structured audit entries, and response jobs
- Response Jobs page
  - explicit execution history for local-dev response actions
  - target, status, timestamps, and outputs summary

## Response actions in local-dev mode

The frontend can trigger these local-dev-only demo actions:

- isolate host
- disable user
- block IP, domain, or hash
- create ticket
- close as false positive
- run playbook
- assign analyst

The frontend can also run local-dev scan modules:

- `Run FIM Scan`
  - simulates file integrity monitoring drift on tracked hosts
  - creates alerts and local cases
- `Run Vulnerability Scan`
  - correlates software inventory against a local CVE catalog
  - creates alerts and local cases

These actions do not change production behavior. They update the local file-backed SIRP state and append structured audit entries so the UI behaves more like a SOC console.

Every local-dev response action now also creates a response job record. Those jobs are visible:

- in the alert detail drawer
- in the case detail drawer
- on the dedicated `Response Jobs` page
- in the unified `Activity` timeline

## Case workflow

The case drawer supports local-dev workflow operations through `POST /api/local-dev/case-workflow`:

- assign owner
- add analyst note
- change status
- close as true positive
- close as false positive
- close as benign positive

## Notes

- Vite proxies `/api/*` to `http://127.0.0.1:7000` during local development, so the default backend URL works without adding Django CORS middleware.
- If you change the backend URL to another origin, browser CORS rules will apply unless that backend explicitly allows cross-origin requests.
