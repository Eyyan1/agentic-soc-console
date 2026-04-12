import json
import os
import time
from pathlib import Path

from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from Lib.api import data_return
from Lib.baseview import BaseView
from Lib.configs import get_local_data_path


LOCAL_DEV_API_ENABLED = os.getenv("ASF_LOCAL_SIRP", "0") == "1"
DATA_FILES = {
    "alerts": "alerts.json",
    "cases": "cases.json",
    "messages": "messages.json",
    "playbooks": "playbooks.json",
    "audit": "audit.json",
    "assets": "assets.json",
    "response_jobs": "local_soc_response_jobs.json",
    "campaigns": "campaigns.json",
}


def _require_local_dev_api():
    if not LOCAL_DEV_API_ENABLED:
        raise NotFound("Local-dev SOC API is only available when ASF_LOCAL_SIRP=1.")
    _ensure_store()


def _path(name: str) -> Path:
    return Path(get_local_data_path(DATA_FILES[name]))


def _ensure_store():
    for filename in DATA_FILES.values():
        path = Path(get_local_data_path(filename))
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("[]", encoding="utf-8")


def _read_items(name: str) -> list:
    try:
        payload = json.loads(_path(name).read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _write_items(name: str, items: list):
    _path(name).write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _counts() -> dict:
    return {
        "alerts": len(_read_items("alerts")),
        "cases": len(_read_items("cases")),
        "playbooks": len(_read_items("playbooks")),
        "messages": len(_read_items("messages")),
    }


def _delta(before: dict, after: dict) -> dict:
    return {key: after.get(key, 0) - before.get(key, 0) for key in before}


def _append_unique(name: str, records: list[dict]) -> int:
    items = _read_items(name)
    existing = {item.get("rowid") or item.get("id") for item in items}
    inserted = []
    for record in records:
        record_id = record.get("rowid") or record.get("id")
        if record_id not in existing:
            inserted.append(record)
            existing.add(record_id)
    if inserted:
        _write_items(name, inserted + items)
    return len(inserted)


def _append_activity(role: str, content: str, target_rowid: str):
    record = {
        "rowid": f"msg-{int(time.time() * 1000)}-{len(_read_items('messages'))}",
        "role": role,
        "node": role,
        "content": content,
        "target_rowid": target_rowid,
        "ts": _now(),
    }
    _append_unique("messages", [record])
    _append_unique("audit", [{
        "rowid": f"audit-{int(time.time() * 1000)}-{len(_read_items('audit'))}",
        "role": role,
        "action": content,
        "target_rowid": target_rowid,
        "status": "completed",
        "ts": record["ts"],
        "details": {"mode": "simulated_only"},
    }])


def _seed_related_records(alerts: list[dict], case_id: str, title: str):
    first_alert = alerts[0]
    now = _now()
    case = {
        "rowid": case_id,
        "title": title,
        "status": "Triage",
        "priority": "P2" if first_alert.get("severity") != "Critical" else "P1",
        "owner": "Local SOC Analyst",
        "linked_alerts": [item["rowid"] for item in alerts],
        "linked_assets": list({item.get("target") for item in alerts if item.get("target")}),
        "artifacts": first_alert.get("artifacts", {}),
        "summary": f"Local demo case created for {len(alerts)} related alerts.",
        "disposition": "Undetermined",
        "sla_due_at": now,
        "last_updated": now,
    }
    playbook = {
        "rowid": f"pb-{case_id}",
        "name": "Local SOC Triage Playbook",
        "status": "Success",
        "source_rowid": case_id,
        "target_id": case_id,
        "job_id": f"job-{case_id}",
        "started_at": now,
        "finished_at": now,
        "step_trace": [
            {"name": "Normalize alert", "status": "Success", "output": "Parsed local demo event."},
            {"name": "Enrich artifacts", "status": "Success", "output": "Attached deterministic mock enrichment."},
            {"name": "Recommend action", "status": "Success", "output": "Escalate, contain, and document response."},
        ],
    }
    _append_unique("cases", [case])
    _append_unique("playbooks", [playbook])
    for alert in alerts:
        alert["linked_case"] = case_id
    _append_activity("agent", f"[AI] Created triage case {case_id} and completed local playbook.", case_id)


def _fim_alerts() -> list[dict]:
    now = _now()
    return [
        {
            "rowid": f"fim-webshell-{int(time.time())}",
            "title": "Critical web directory file modification",
            "severity": "High",
            "status": "New",
            "rule_id": "FIM-Rule-01-Webroot-Executable-Change",
            "rule_name": "Unexpected executable file in webroot",
            "source": "local-fim",
            "target": "web-prod-01",
            "first_seen_time": now,
            "summary": "File integrity monitoring detected a new executable script under the web application directory.",
            "raw_event": {"path": "/var/www/html/uploads/shell.php", "operation": "created", "sha256": "f1d2d2f924e986ac86fdf7b36c94bcdf32beec15"},
            "artifacts": {"ips": ["10.10.4.21"], "domains": [], "emails": [], "hashes": ["f1d2d2f924e986ac86fdf7b36c94bcdf32beec15"]},
            "enrichment": {"risk_score": 82, "confidence": 0.86, "mitre": ["T1505.003"], "explanation": "Executable content appeared in a sensitive web path."},
            "recommended_actions": ["isolate host", "create ticket", "review file hash", "run playbook"],
        },
        {
            "rowid": f"fim-ssh-{int(time.time())}",
            "title": "Sensitive SSH configuration changed",
            "severity": "Medium",
            "status": "New",
            "rule_id": "FIM-Rule-04-SSH-Config-Change",
            "rule_name": "SSH daemon configuration modified",
            "source": "local-fim",
            "target": "linux-build-02",
            "first_seen_time": now,
            "summary": "SSH configuration changed outside the normal maintenance window.",
            "raw_event": {"path": "/etc/ssh/sshd_config", "operation": "modified", "changed_by": "root"},
            "artifacts": {"ips": ["10.10.8.44"], "domains": [], "emails": [], "hashes": []},
            "enrichment": {"risk_score": 58, "confidence": 0.74, "mitre": ["T1098"], "explanation": "Authentication configuration changed on a managed host."},
            "recommended_actions": ["review change ticket", "verify admin activity", "create ticket"],
        },
    ]


def _vulnerability_alerts() -> list[dict]:
    now = _now()
    return [
        {
            "rowid": f"vuln-openssl-{int(time.time())}",
            "title": "Critical OpenSSL vulnerability detected",
            "severity": "Critical",
            "status": "New",
            "rule_id": "VULN-Rule-01-Critical-CVE",
            "rule_name": "Critical CVE on internet-facing asset",
            "source": "local-vulnerability",
            "target": "edge-gateway-01",
            "first_seen_time": now,
            "summary": "Software inventory matched OpenSSL against a critical CVE requiring urgent remediation.",
            "raw_event": {"package": "openssl", "version": "3.0.7", "cve": "CVE-2024-5535", "cvss": 9.1},
            "artifacts": {"ips": ["203.0.113.25"], "domains": ["vpn.company.local"], "emails": [], "hashes": []},
            "enrichment": {"risk_score": 96, "confidence": 0.91, "mitre": ["T1190"], "explanation": "High-severity vulnerable package exists on a critical exposed asset."},
            "recommended_actions": ["create remediation ticket", "apply patch", "restrict exposure", "run playbook"],
        }
    ]


def _phishing_alerts() -> list[dict]:
    now = _now()
    return [
        {
            "rowid": f"phish-finance-{int(time.time())}",
            "title": "User-reported phishing email",
            "severity": "High",
            "status": "New",
            "rule_id": "ES-Rule-21-Phishing-User-Report-Mail",
            "rule_name": "Phishing user report",
            "source": "alerts-mailbox",
            "target": "finance@company.local",
            "first_seen_time": now,
            "summary": "Credential harvesting language and suspicious sender domain detected.",
            "raw_event": {"from": "billing@secure-payments.example", "to": "finance@company.local", "subject": "Urgent invoice verification"},
            "artifacts": {"ips": ["198.51.100.44"], "domains": ["secure-payments.example"], "emails": ["billing@secure-payments.example"], "hashes": []},
            "enrichment": {"risk_score": 78, "confidence": 0.82, "mitre": ["T1566.002"], "explanation": "Sender domain and message intent match phishing indicators."},
            "recommended_actions": ["block domain/IP", "disable user if credentials entered", "create ticket", "run playbook"],
        }
    ]


def _run_fast_generation(stream: str, alerts: list[dict], case_id: str, case_title: str) -> dict:
    before = _counts()
    inserted = _append_unique("alerts", alerts)
    if inserted:
        _seed_related_records(alerts, case_id, case_title)
        _write_items("alerts", alerts + [item for item in _read_items("alerts") if item.get("rowid") not in {alert["rowid"] for alert in alerts}])
    after = _counts()
    return {
        "generated_alerts": len(alerts),
        "stream": stream,
        "mode": "fast_web_fallback",
        "counts_before": before,
        "counts_after": after,
        "processed_delta": _delta(before, after),
    }


def _matches_query(item: dict, query: str) -> bool:
    if not query:
        return True
    return query in json.dumps(item, ensure_ascii=False).lower()


def _find_item(items: list, pk: str):
    for item in items:
        if str(item.get("rowid") or item.get("id") or "") == str(pk):
            return item
    raise NotFound("Record not found.")


def _empty_overview():
    alerts = _read_items("alerts")
    cases = _read_items("cases")
    playbooks = _read_items("playbooks")
    messages = _read_items("messages")
    assets = _read_items("assets")
    campaigns = _read_items("campaigns")
    severity_counts = {}
    for alert in alerts:
        severity = alert.get("severity") or "Unknown"
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    return {
        "stats": {
            "alerts": len(alerts),
            "cases": len(cases),
            "playbooks": len(playbooks),
            "messages": len(messages),
            "assets": len(assets),
            "critical_alerts": sum(1 for item in alerts if str(item.get("severity")).lower() == "critical"),
            "running_playbooks": sum(1 for item in playbooks if str(item.get("status")).lower() == "running"),
            "open_cases": sum(1 for item in cases if item.get("status") not in {"Resolved", "Closed"}),
            "campaigns": len(campaigns),
            "mtta_minutes": 0,
            "mttr_minutes": 0,
        },
        "metrics": {
            "severity_distribution": [{"name": name, "count": count} for name, count in severity_counts.items()],
            "top_assets": [],
            "top_users": [],
            "top_campaigns": [],
            "agent_status": [
                {"name": "Online", "count": 0},
                {"name": "Attention", "count": 0},
                {"name": "Contained", "count": 0},
            ],
        },
        "recent_activity": sorted(messages + _read_items("audit"), key=lambda item: item.get("ts") or "", reverse=True)[:12],
    }


class LocalDevOverviewView(BaseView):
    def list(self, request, **kwargs):
        _require_local_dev_api()
        return Response(data_return(200, _empty_overview(), "Success", "Success"))


class _ListRetrieveView(BaseView):
    store_name = ""

    def list(self, request, **kwargs):
        _require_local_dev_api()
        query = request.query_params.get("q", "").strip().lower()
        items = [item for item in _read_items(self.store_name) if _matches_query(item, query)]
        return Response(data_return(200, items, "Success", "Success"))

    def retrieve(self, request, pk=None, **kwargs):
        _require_local_dev_api()
        return Response(data_return(200, _find_item(_read_items(self.store_name), pk), "Success", "Success"))


class LocalDevAlertsView(_ListRetrieveView):
    store_name = "alerts"


class LocalDevCasesView(_ListRetrieveView):
    store_name = "cases"


class LocalDevCampaignsView(_ListRetrieveView):
    store_name = "campaigns"


class LocalDevPlaybooksView(_ListRetrieveView):
    store_name = "playbooks"


class LocalDevMessagesView(_ListRetrieveView):
    store_name = "messages"


class LocalDevAuditView(_ListRetrieveView):
    store_name = "audit"


class LocalDevResponseJobsView(_ListRetrieveView):
    store_name = "response_jobs"


class LocalDevAssetsView(_ListRetrieveView):
    store_name = "assets"


class LocalDevResponseActionsView(BaseView):
    def create(self, request, pk=None, **kwargs):
        _require_local_dev_api()
        jobs = _read_items("response_jobs")
        audits = _read_items("audit")
        action = request.data.get("action") or "demo_action"
        target_rowid = request.data.get("target_rowid") or request.data.get("alert_id") or request.data.get("case_id") or "local-demo"
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        job = {
            "rowid": f"job-{int(time.time() * 1000)}",
            "action": action,
            "target_rowid": target_rowid,
            "status": "completed",
            "started_at": now,
            "finished_at": now,
            "summary": f"Simulated local-dev action completed: {action}",
        }
        audit = {
            "rowid": f"audit-{int(time.time() * 1000)}",
            "role": "human",
            "action": action,
            "target_rowid": target_rowid,
            "status": "completed",
            "ts": now,
            "details": {"mode": "simulated_only"},
        }
        jobs.insert(0, job)
        audits.insert(0, audit)
        _write_items("response_jobs", jobs[:500])
        _write_items("audit", audits[:500])
        return Response(data_return(200, job, "Success", "Success"))


class LocalDevCaseWorkflowView(LocalDevResponseActionsView):
    pass


class LocalDevDemoAlertsView(BaseView):
    def create(self, request, pk=None, **kwargs):
        _require_local_dev_api()
        payload = _run_fast_generation(
            "ES-Rule-21-Phishing-User-Report-Mail",
            _phishing_alerts(),
            "case-local-phishing",
            "Local phishing investigation",
        )
        return Response(data_return(200, payload, "Success", "Success"))


class LocalDevFIMScanView(BaseView):
    def create(self, request, pk=None, **kwargs):
        _require_local_dev_api()
        payload = _run_fast_generation(
            "local-fim",
            _fim_alerts(),
            "case-local-fim",
            "Local file integrity investigation",
        )
        return Response(data_return(200, payload, "Success", "Success"))


class LocalDevVulnerabilityScanView(BaseView):
    def create(self, request, pk=None, **kwargs):
        _require_local_dev_api()
        payload = _run_fast_generation(
            "local-vulnerability",
            _vulnerability_alerts(),
            "case-local-vulnerability",
            "Local vulnerability remediation case",
        )
        return Response(data_return(200, payload, "Success", "Success"))
