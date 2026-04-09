# Local-Dev SOC Flow

This repository supports an automatic local-only SOC handoff when `ASF_LOCAL_SIRP=1`.

## Scope

This behavior is gated entirely behind:

```powershell
$env:ASF_LOCAL_SIRP='1'
```

Production behavior is unchanged because the local auto case and auto playbook flow is never triggered unless local SIRP mode is active.

## What happens

When a phishing alert is persisted through `PLUGINS.SIRP.sirpapi.Alert.create()` and local SIRP mode is enabled:

1. The alert is saved to the local worksheet store in `.runtime/local_sirp_store.json`.
2. If the alert looks like the phishing pipeline output (`rule_id == ES-Rule-21-Phishing-User-Report-Mail` or phishing labels are present), the backend derives a deterministic local correlation key.
3. The backend checks whether a `Case` already exists for that correlation key.
4. If a case exists, the new alert is linked to it.
5. If no case exists, the backend creates a new local case and links the alert.
6. It then enqueues the default case playbook:
   - `L3 SOC Analyst Agent With Tools`
7. `MainMonitor.subscribe_pending_playbook()` picks up that queued playbook and runs it as usual.

## Local Correlation Rule

The local phishing correlation key is intentionally simpler than a production correlation strategy. Its purpose is to make the bundled mock data usable in local development without exploding into one case per email.

Current local rule:

1. `alert.rule_id`
2. normalized target recipient email from the message `To` header
3. UTC day bucket derived from `first_seen_time`

If the target recipient email is missing, the sender domain is used as a deterministic fallback key.

In concrete terms, the local key format is:

```text
local-phishing|<rule_id>|<target_email_or_sender_domain>|<YYYY-MM-DD>
```

Example:

```text
local-phishing|ES-Rule-21-Phishing-User-Report-Mail|user@example.com|2025-11-03
```

Why this rule is intentionally coarse:

- The bundled phishing mock batch contains many different sender domains.
- Including sender domain in the primary grouping key caused too many local cases and playbooks.
- Grouping by target recipient plus a daily time window keeps the flow deterministic while reducing local case explosion.

## Measured Before And After

These numbers came from one run of the bundled phishing mock through `scripts/run_local_soc_flow.py`.

Before correlation tightening:

- After module processing: `alert=12`, `case=10`, `playbook=10`
- After playbook processing: `alert=21`, `case=19`, `playbook=19`

After local recipient-plus-day correlation:

- After module processing: `alert=14`, `case=5`, `playbook=5`
- After playbook processing: `alert=20`, `case=6`, `playbook=6`

That local-only rule reduced the final case count from `19` to `6` in the same style of run.

## Entry Points Involved

- Alert persistence and local auto handoff:
  [PLUGINS/SIRP/sirpapi.py](C:/Users/USER/Documents/agentic-soc-platform-master/PLUGINS/SIRP/sirpapi.py)
- Background monitor:
  [Lib/montior.py](C:/Users/USER/Documents/agentic-soc-platform-master/Lib/montior.py)
- Module ingestion example:
  [MODULES/ES-Rule-21-Phishing-User-Report-Mail.py](C:/Users/USER/Documents/agentic-soc-platform-master/MODULES/ES-Rule-21-Phishing-User-Report-Mail.py)
- Local runner:
  [scripts/run_local_soc_flow.py](C:/Users/USER/Documents/agentic-soc-platform-master/scripts/run_local_soc_flow.py)

## Quick Test

```powershell
.\.venv\Scripts\python.exe scripts\run_local_soc_flow.py
```

Expected local flow:

1. Mock phishing alerts are written into Redis.
2. The phishing module consumes them and persists alerts.
3. Related phishing alerts for the same recipient and UTC day are folded into the same local case.
4. A new local case is created only when no matching local case exists.
5. The default case playbook is auto-queued.
6. The playbook executes and writes back case AI fields plus playbook messages.
