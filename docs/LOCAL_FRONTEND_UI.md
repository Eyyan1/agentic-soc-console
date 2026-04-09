# Local Frontend UI

This repo now includes a separate React and Tailwind frontend under [frontend](C:/Users/USER/Documents/agentic-soc-platform-master/frontend).

## Purpose

The frontend provides a local SOC dashboard for:

- overview metrics
- alerts
- cases
- playbooks
- activity messages

It is intended for local development and does not replace any hosted production UI.

## Auth flow

The frontend uses the existing backend token flow and now provides a simple local login helper on top of it:

- login endpoint: `POST /api/login/account`
- token validation endpoint: `GET /api/currentUser`

Supported local frontend auth paths:

1. Username and password login
   - the user enters credentials in the frontend
   - the frontend calls `POST /api/login/account`
   - the returned token is stored in browser local storage
   - the frontend validates that token through `GET /api/currentUser`
2. Manual token fallback
   - the user pastes an existing DRF token
   - the frontend validates it through `GET /api/currentUser`

This does not change backend production auth behavior. It only automates the existing token acquisition flow for local development.

## Local-dev data endpoints

When the backend is running with `ASF_LOCAL_SIRP=1`, the frontend reads:

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
- `POST /api/local-dev/respond`
- `POST /api/local-dev/demo-alerts`
- `POST /api/local-dev/fim-scan`
- `POST /api/local-dev/vulnerability-scan`

These endpoints are authenticated and read-only.

The local-dev write exceptions are:

- `POST /api/local-dev/demo-alerts`
- `POST /api/local-dev/respond`

They remain gated behind `ASF_LOCAL_SIRP=1` and exist only to make the local UI behave like a SOC console.

They are intentionally local-dev-only. If `ASF_LOCAL_SIRP` is not enabled in the Django process, the endpoints return unavailable and the frontend falls back to seeded demo data.

## Run commands

Backend:

```powershell
$env:ASF_LOCAL_SIRP='1'
python manage.py runserver 127.0.0.1:7000 --noreload
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://127.0.0.1:5173
```

## Notes

- Vite proxies `/api/*` to `http://127.0.0.1:7000` in local development.
- If the backend is already running without `ASF_LOCAL_SIRP=1`, restart it to expose live local SOC data to the frontend.
- The frontend still works in fallback mode even when those local-dev endpoints are unavailable.

## Added UI components and views

- `TopBar.jsx`
  - login flow
  - token fallback
  - demo alert trigger
  - FIM scan trigger
  - vulnerability scan trigger
- `EnvironmentStatus.jsx`
  - backend/token/data-mode state
  - refresh time
  - counts
- `AlertsPage.jsx`
  - alert list
  - alert detail drawer
  - threat analysis section
  - linked campaigns
  - enrichment panel
  - recommended actions
- `CampaignsPage.jsx`
  - correlated alert clusters
  - grouped alerts
  - attack summary and correlation basis
- `CasesPage.jsx`
  - case cards
  - case detail drawer
  - owner assignment
  - analyst note entry
  - status changes across `New`, `Triage`, `Investigating`, `Contained`, `Resolved`, and `Closed`
  - close as true positive / false positive / benign positive
  - related alerts
  - linked assets
  - artifacts
  - SLA timer
  - assignment state
  - attack timeline
  - activity timeline
  - notes and disposition
  - case actions
  - response history
- `AssetsPage.jsx`
  - host and agent inventory
  - criticality and last-seen status
  - software inventory
  - vulnerability exposure
  - integrity findings
- `PlaybooksPage.jsx`
  - playbook list
  - playbook run detail
  - step trace and outputs
- `ActivityPage.jsx`
  - unified playbook, audit log, and response job timeline
- `ResponseJobsPage.jsx`
  - dedicated execution history for local-dev response actions
  - action status, target, timestamps, and output summary
- `OverviewPage.jsx`
  - severity distribution
  - open cases
  - MTTA and MTTR placeholders
  - top affected assets

## Local-dev SOC modules

These local-only write endpoints simulate Wazuh-style capabilities while preserving production behavior:

- `POST /api/local-dev/demo-alerts`
  - replays the bundled phishing mail dataset
- `POST /api/local-dev/fim-scan`
  - simulates file integrity monitoring drift
  - creates alerts, local cases, and playbook runs
- `POST /api/local-dev/vulnerability-scan`
  - correlates software inventory with a local CVE catalog
  - creates alerts, local cases, and playbook runs

## Response behavior

The alert and case drawers can trigger local-dev active response actions through `POST /api/local-dev/respond`:

- isolate host
- disable user
- block IP/domain/hash
- create ticket
- run playbook
- assign analyst
- close as false positive

Those actions update the local file-backed SOC state and append structured audit entries. They remain gated behind `ASF_LOCAL_SIRP=1`.

Each action now also emits a structured response job record through `GET /api/local-dev/response-jobs`. The frontend surfaces those records in:

- the alert detail drawer
- the case detail drawer
- the dedicated `Response Jobs` page
- the `Activity` timeline

## Case workflow endpoint

`POST /api/local-dev/case-workflow` updates local case state in a structured way:

- `case_rowid`
- optional `owner`
- optional `note`
- optional `status`
- optional `disposition`

The frontend uses this endpoint from the case detail drawer so analysts can keep the case list visible while updating workflow state in a right-side panel.
