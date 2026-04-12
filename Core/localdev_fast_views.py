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
        return Response(data_return(200, {"generated_alerts": 0, "mode": "fast_web_fallback"}, "Success", "Success"))


class LocalDevFIMScanView(LocalDevDemoAlertsView):
    pass


class LocalDevVulnerabilityScanView(LocalDevDemoAlertsView):
    pass
