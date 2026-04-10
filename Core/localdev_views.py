import json
import os
import runpy
import time
import importlib.util
from pathlib import Path
from email.utils import parseaddr
from collections import Counter
from datetime import datetime, timezone

from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from Lib.api import data_return
from Lib.baseview import BaseView
from Lib.configs import get_local_data_path
from Lib.log import logger
from Core.localdev_playbooks import select_local_case_playbook_name
from Core.localdev_soc import (
    generate_fim_demo,
    generate_vulnerability_demo,
    get_asset,
    list_assets,
    update_asset_state,
)
from PLUGINS.SIRP.nocolymodel import Group
from PLUGINS.SIRP.sirpapi import Alert, Case, Message, Playbook, Ticket
from PLUGINS.SIRP.sirpmodel import (
    AlertStatus,
    CaseModel,
    CaseStatus,
    CaseVerdict,
    PlaybookType,
    TicketModel,
    TicketStatus,
    TicketType,
)


LOCAL_DEV_API_ENABLED = os.getenv("ASF_LOCAL_SIRP", "0") == "1"
ROOT_DIR = Path(__file__).resolve().parents[1]
PHISHING_MOCK_SCRIPT = ROOT_DIR / "DATA" / "ES-Rule-21-Phishing-User-Report-Mail" / "mock_alert.py"
PHISHING_MODULE_FILE = ROOT_DIR / "MODULES" / "ES-Rule-21-Phishing-User-Report-Mail.py"
LOCAL_AUDIT_LOG_PATH = Path(get_local_data_path("local_soc_audit_log.json"))
LOCAL_RESPONSE_JOB_LOG_PATH = Path(get_local_data_path("local_soc_response_jobs.json"))
LOCAL_DEV_PLACEHOLDER_FILES = {
    "alerts.json": "[]",
    "cases.json": "[]",
    "messages.json": "[]",
    "playbooks.json": "[]",
    "audit.json": "[]",
    "assets.json": "[]",
}


def _require_local_dev_api():
    if not LOCAL_DEV_API_ENABLED:
        raise NotFound("Local-dev SOC API is only available when ASF_LOCAL_SIRP=1.")
    _bootstrap_local_dev_state()


def _extract_email(value: str) -> str:
    _, email_address = parseaddr(value or "")
    return (email_address or value or "").strip().lower()


def _extract_domain(value: str) -> str:
    email_address = _extract_email(value)
    if "@" in email_address:
        return email_address.split("@", 1)[1]
    return ""


def _safe_json_load(value: str) -> dict:
    if not value:
        return {}
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}


def _normalize_timestamp(value) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(value or "")


def _parse_timestamp(value):
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _confidence_to_score(value) -> float:
    return {
        "High": 0.92,
        "Medium": 0.74,
        "Low": 0.46,
        "Unknown": 0.25,
        "Other": 0.25,
    }.get(str(value or "Unknown"), 0.25)


def _risk_to_score(severity, criticality="Medium") -> int:
    severity_score = {
        "Critical": 95,
        "High": 78,
        "Medium": 56,
        "Low": 30,
        "Informational": 15,
    }.get(str(severity or "Informational"), 20)
    criticality_boost = {
        "Critical": 15,
        "High": 10,
        "Medium": 5,
        "Low": 0,
    }.get(str(criticality or "Medium"), 5)
    return min(100, severity_score + criticality_boost)


def _ensure_runtime_dir():
    LOCAL_AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not LOCAL_AUDIT_LOG_PATH.exists():
        LOCAL_AUDIT_LOG_PATH.write_text("[]", encoding="utf-8")
    if not LOCAL_RESPONSE_JOB_LOG_PATH.exists():
        LOCAL_RESPONSE_JOB_LOG_PATH.write_text("[]", encoding="utf-8")
    for filename, default_content in LOCAL_DEV_PLACEHOLDER_FILES.items():
        placeholder_path = Path(get_local_data_path(filename))
        if not placeholder_path.exists():
            placeholder_path.write_text(default_content, encoding="utf-8")


def _bootstrap_local_dev_state():
    _ensure_runtime_dir()
    try:
        list_assets()
    except Exception:
        logger.exception("Failed to initialize local asset inventory; continuing with empty fallback state.")


def _empty_overview_payload() -> dict:
    return {
        "stats": {
            "alerts": 0,
            "cases": 0,
            "playbooks": 0,
            "messages": 0,
            "assets": 0,
            "critical_alerts": 0,
            "running_playbooks": 0,
            "open_cases": 0,
            "campaigns": 0,
            "mtta_minutes": 0,
            "mttr_minutes": 0,
        },
        "metrics": {
            "severity_distribution": [],
            "top_assets": [],
            "top_users": [],
            "top_campaigns": [],
            "agent_status": [
                {"name": "Online", "count": 0},
                {"name": "Attention", "count": 0},
                {"name": "Contained", "count": 0},
            ],
        },
        "recent_activity": [],
    }


def _safe_local_dev_items(loader, label: str) -> list:
    try:
        return loader()
    except Exception:
        logger.exception("Local-dev endpoint fallback activated for %s.", label)
        return []


def _load_audit_entries() -> list[dict]:
    _ensure_runtime_dir()
    if not LOCAL_AUDIT_LOG_PATH.exists():
        return []
    try:
        return json.loads(LOCAL_AUDIT_LOG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def _load_response_jobs() -> list[dict]:
    _ensure_runtime_dir()
    if not LOCAL_RESPONSE_JOB_LOG_PATH.exists():
        return []
    try:
        return json.loads(LOCAL_RESPONSE_JOB_LOG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def _save_response_jobs(entries: list[dict]) -> None:
    _ensure_runtime_dir()
    LOCAL_RESPONSE_JOB_LOG_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_response_job(entry: dict) -> dict:
    entries = _load_response_jobs()
    entries.append(entry)
    entries.sort(key=lambda item: item.get("finished_at") or item.get("started_at") or "", reverse=True)
    _save_response_jobs(entries[:500])
    return entry


def _save_audit_entries(entries: list[dict]) -> None:
    _ensure_runtime_dir()
    LOCAL_AUDIT_LOG_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_audit_entry(entry: dict) -> dict:
    entries = _load_audit_entries()
    entries.append(entry)
    entries.sort(key=lambda item: item.get("ts") or "", reverse=True)
    _save_audit_entries(entries[:500])
    return entry


def _make_audit_entry(action: str, target_type: str, target_rowid: str, status: str = "completed", details: dict | None = None) -> dict:
    return {
        "rowid": f"audit-{int(time.time() * 1000)}-{target_rowid[-6:]}",
        "action": action,
        "target_type": target_type,
        "target_rowid": target_rowid,
        "status": status,
        "details": details or {},
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "role": "AuditLog",
    }


def _matches_query(payload: dict, query: str, fields: list[str]) -> bool:
    if not query:
        return True
    haystack = " ".join(str(payload.get(field, "")) for field in fields).lower()
    return query in haystack


def _serialize_alert(alert_model) -> dict:
    raw_data = _safe_json_load(alert_model.raw_data)
    headers = raw_data.get("headers", {})
    target_email = _extract_email(headers.get("To", ""))
    sender_email = _extract_email(headers.get("From", ""))

    payload = {
        "rowid": alert_model.rowid,
        "id": alert_model.id,
        "title": alert_model.title,
        "severity": alert_model.severity,
        "confidence": alert_model.confidence,
        "confidence_score": _confidence_to_score(alert_model.confidence),
        "status": alert_model.status,
        "rule_id": alert_model.rule_id,
        "rule_name": alert_model.rule_name,
        "target": target_email,
        "sender": sender_email,
        "sender_domain": _extract_domain(headers.get("From", "")),
        "summary": alert_model.summary_ai or alert_model.comment_ai or alert_model.desc,
        "first_seen_time": _normalize_timestamp(alert_model.first_seen_time),
        "utime": _normalize_timestamp(alert_model.utime),
        "correlation_uid": alert_model.correlation_uid,
        "labels": alert_model.labels or [],
        "product_name": alert_model.product_name,
        "product_category": alert_model.product_category,
    }
    payload["threat_analysis"] = _build_detection_intelligence(payload, raw_data)
    return payload


def _serialize_artifact(artifact_model) -> dict:
    return {
        "rowid": artifact_model.rowid,
        "name": artifact_model.name,
        "type": artifact_model.type,
        "role": artifact_model.role,
        "value": artifact_model.value,
        "reputation_score": artifact_model.reputation_score,
    }


def _serialize_case(case_model, playbooks_by_source: dict[str, list[dict]]) -> dict:
    playbooks = playbooks_by_source.get(case_model.rowid, [])
    latest_playbook = playbooks[0] if playbooks else None
    alerts = case_model.alerts or []
    owner = getattr(case_model, "assignee_l3", None) or getattr(case_model, "assignee_l2", None) or getattr(case_model, "assignee_l1", None) or "Local SOC Pipeline"
    status = str(case_model.status or CaseStatus.NEW)
    if status == CaseStatus.IN_PROGRESS:
        status = CaseStatus.INVESTIGATING

    return {
        "rowid": case_model.rowid,
        "id": case_model.id,
        "title": case_model.title,
        "severity": case_model.severity,
        "priority": case_model.priority,
        "confidence": case_model.confidence,
        "status": status,
        "owner": owner,
        "correlation_uid": case_model.correlation_uid,
        "linked_alerts": len(alerts),
        "alert_rowids": alerts,
        "tags": case_model.tags or [],
        "summary": case_model.summary_ai or case_model.description,
        "verdict": case_model.verdict_ai or case_model.verdict,
        "playbook": latest_playbook["name"] if latest_playbook else None,
        "last_updated": _normalize_timestamp(case_model.utime),
        "assignment": {
            "owner": owner,
            "assigned": owner != "Local SOC Pipeline",
        },
    }


def _serialize_playbook(playbook_model) -> dict:
    is_finished = str(playbook_model.job_status) in {"Success", "Failed"}
    return {
        "rowid": playbook_model.rowid,
        "id": playbook_model.id,
        "name": playbook_model.name,
        "status": playbook_model.job_status,
        "job_id": playbook_model.job_id,
        "type": playbook_model.type,
        "source_rowid": playbook_model.source_rowid,
        "target_id": playbook_model.source_rowid,
        "remark": playbook_model.remark,
        "started_at": _normalize_timestamp(playbook_model.ctime),
        "finished_at": _normalize_timestamp(playbook_model.utime) if is_finished else None,
        "user_input": playbook_model.user_input,
    }


def _serialize_message(message_model) -> dict:
    return {
        "rowid": message_model.rowid,
        "playbook": message_model.playbook,
        "node": message_model.node,
        "role": message_model.type,
        "content": message_model.content,
        "data": message_model.data,
        "ts": _normalize_timestamp(message_model.ctime or message_model.utime),
    }


def _serialize_audit_entry(entry: dict) -> dict:
    return {
        "rowid": entry.get("rowid"),
        "role": "AuditLog",
        "action": entry.get("action"),
        "target_type": entry.get("target_type"),
        "target_rowid": entry.get("target_rowid"),
        "status": entry.get("status"),
        "content": entry.get("details", {}).get("summary") or entry.get("action"),
        "details": entry.get("details", {}),
        "ts": entry.get("ts"),
    }


def _make_response_job(action: str, target_type: str, target_rowid: str, status: str = "completed", outputs: dict | None = None) -> dict:
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return {
        "rowid": f"resp-{int(time.time() * 1000)}-{target_rowid[-6:]}",
        "action": action,
        "target_type": target_type,
        "target_rowid": target_rowid,
        "status": status,
        "started_at": started_at,
        "finished_at": started_at,
        "outputs": outputs or {},
    }


def _serialize_response_job(entry: dict) -> dict:
    outputs = entry.get("outputs", {})
    return {
        "rowid": entry.get("rowid"),
        "action": entry.get("action"),
        "target_type": entry.get("target_type"),
        "target_rowid": entry.get("target_rowid"),
        "status": entry.get("status"),
        "started_at": entry.get("started_at"),
        "finished_at": entry.get("finished_at"),
        "summary": outputs.get("summary") or entry.get("action"),
        "outputs": outputs,
        "role": "ResponseJob",
        "ts": entry.get("finished_at") or entry.get("started_at"),
    }


def _serialize_asset(asset: dict) -> dict:
    payload = dict(asset)
    payload["software_count"] = len(payload.get("software_inventory") or [])
    payload["vulnerability_count"] = len(payload.get("vulnerabilities") or [])
    payload["integrity_findings_count"] = len(payload.get("integrity_findings") or [])
    return payload


def _infer_alert_entities(alert_payload: dict, raw_event: dict | None = None) -> dict:
    raw_event = raw_event or {}
    artifacts = alert_payload.get("artifacts") or []
    target = alert_payload.get("target") or ""
    user = target if "@" in str(target) else _extract_email(raw_event.get("user") or "")

    hostname = raw_event.get("hostname") or ""
    if not hostname:
        for artifact in artifacts:
            if str(artifact.get("type")) in {"Hostname", "Endpoint", "Device"}:
                hostname = artifact.get("value") or ""
                break
    if not hostname and target and "@" not in str(target):
        hostname = target

    domain = alert_payload.get("sender_domain") or ""
    ip_address = ""
    for artifact in artifacts:
        if str(artifact.get("type")) == "IP Address" and artifact.get("value"):
            ip_address = artifact.get("value")
            break

    return {
        "user": user,
        "asset": hostname,
        "domain": domain,
        "ip": ip_address,
    }


def _build_detection_intelligence(alert_payload: dict, raw_event: dict | None = None) -> dict:
    raw_event = raw_event or {}
    entities = _infer_alert_entities(alert_payload, raw_event)
    hostname = entities.get("asset")
    asset = get_asset(f"asset-{hostname}") if hostname else None
    criticality = (asset or {}).get("criticality", "Medium")

    if alert_payload.get("rule_id") == "ES-Rule-21-Phishing-User-Report-Mail":
        mitre = [
            {"tactic": "Initial Access", "technique": "Phishing", "id": "T1566"},
            {"tactic": "Credential Access", "technique": "Steal or Forge Authentication Certificates", "id": "T1649"},
        ]
        explanation = "User-reported phishing with suspicious sender/domain patterns and credential-harvesting language."
        action_plan = [
            "Validate the suspicious sender domain and email authentication failures.",
            "Confirm whether the targeted user submitted credentials or clicked links.",
            "Contain the impacted mailbox or endpoint and block the sender infrastructure.",
        ]
    elif str(alert_payload.get("rule_id", "")).startswith("FIM-Rule"):
        mitre = [
            {"tactic": "Persistence", "technique": "Event Triggered Execution", "id": "T1546"},
            {"tactic": "Defense Evasion", "technique": "Modify Existing Service", "id": "T1031"},
        ]
        explanation = "Unexpected file integrity drift on a monitored path suggests unauthorized persistence or web-shell placement."
        action_plan = [
            "Verify the file change against approved deployment activity.",
            "Collect the file, hash, and execution context for triage.",
            "Contain the host if the modified file appears malicious or externally reachable.",
        ]
    elif str(alert_payload.get("rule_id", "")).startswith("VULN-Rule"):
        mitre = [
            {"tactic": "Initial Access", "technique": "Exploit Public-Facing Application", "id": "T1190"},
            {"tactic": "Execution", "technique": "Exploitation for Client Execution", "id": "T1203"},
        ]
        explanation = "Software inventory correlates with a known vulnerable package/CVE and elevates exploitability risk."
        action_plan = [
            "Validate the vulnerable package version and confirm the asset business criticality.",
            "Prioritize internet-facing or critical assets for emergency patching or compensating controls.",
            "Block known exploit paths, restrict exposure, and track remediation to fixed version.",
        ]
    else:
        mitre = [
            {"tactic": "Command and Control", "technique": "Application Layer Protocol", "id": "T1071"},
        ]
        explanation = "Behavior and indicators align with a suspicious attack sequence requiring triage."
        action_plan = [
            "Confirm the triggering evidence and affected entities.",
            "Scope related activity across linked assets and users.",
            "Apply containment and escalate to deeper investigation if malicious intent is confirmed.",
        ]

    confidence_score = _confidence_to_score(alert_payload.get("confidence"))
    risk_score = _risk_to_score(alert_payload.get("severity"), criticality)
    return {
        "mitre_attack": mitre,
        "risk_score": risk_score,
        "confidence_score": confidence_score,
        "explanation": explanation,
        "action_plan": action_plan,
        "entities": entities,
        "asset_criticality": criticality,
    }


def _campaign_bucket(timestamp: str) -> str:
    dt = _parse_timestamp(timestamp)
    if not dt:
        return "unknown-window"
    bucket_hour = (dt.hour // 8) * 8
    return f"{dt.strftime('%Y-%m-%d')}-h{bucket_hour:02d}"


def _build_campaigns(alert_payloads: list[dict]) -> list[dict]:
    grouped = {}

    for alert_payload in alert_payloads:
        threat = alert_payload.get("threat_analysis") or {}
        entities = threat.get("entities") or _infer_alert_entities(alert_payload, alert_payload.get("raw_event") or {})
        window = _campaign_bucket(alert_payload.get("first_seen_time"))
        user_part = entities.get("user") or "-"
        asset_part = entities.get("asset") or "-"
        network_part = entities.get("domain") or entities.get("ip") or "-"
        if all(part == "-" for part in [user_part, asset_part, network_part]):
            campaign_basis = f"rule:{alert_payload.get('rule_id') or 'unknown'}"
        else:
            campaign_basis = f"user:{user_part}|asset:{asset_part}|network:{network_part}"
        campaign_key = f"{campaign_basis}|window:{window}"

        campaign = grouped.setdefault(
            campaign_key,
            {
                "rowid": campaign_key.replace(":", "-").replace("|", "-"),
                "name": f"Campaign around {campaign_basis.split('|', 1)[0].split(':', 1)[-1]}",
                "window": window,
                "correlation_basis": campaign_basis,
                "alerts": [],
                "users": set(),
                "assets": set(),
                "domains": set(),
                "ips": set(),
                "mitre": set(),
                "max_risk_score": 0,
                "latest_seen": "",
            },
        )
        campaign["alerts"].append({
            "rowid": alert_payload.get("rowid"),
            "title": alert_payload.get("title"),
            "severity": alert_payload.get("severity"),
            "rule_id": alert_payload.get("rule_id"),
            "first_seen_time": alert_payload.get("first_seen_time"),
        })
        if entities.get("user"):
            campaign["users"].add(entities["user"])
        if entities.get("asset"):
            campaign["assets"].add(entities["asset"])
        if entities.get("domain"):
            campaign["domains"].add(entities["domain"])
        if entities.get("ip"):
            campaign["ips"].add(entities["ip"])
        for item in threat.get("mitre_attack", []):
            campaign["mitre"].add(f"{item.get('id')} {item.get('technique')}")
        campaign["max_risk_score"] = max(campaign["max_risk_score"], threat.get("risk_score") or 0)
        latest_seen = alert_payload.get("first_seen_time") or ""
        if latest_seen > campaign["latest_seen"]:
            campaign["latest_seen"] = latest_seen

    campaigns = []
    for campaign in grouped.values():
        campaigns.append(
            {
                "rowid": campaign["rowid"],
                "name": campaign["name"],
                "window": campaign["window"],
                "correlation_basis": campaign["correlation_basis"],
                "alert_count": len(campaign["alerts"]),
                "alerts": sorted(campaign["alerts"], key=lambda item: item.get("first_seen_time") or "", reverse=True),
                "users": sorted(campaign["users"]),
                "assets": sorted(campaign["assets"]),
                "domains": sorted(campaign["domains"]),
                "ips": sorted(campaign["ips"]),
                "attack_summary": sorted(campaign["mitre"]),
                "risk_score": campaign["max_risk_score"],
                "latest_seen": campaign["latest_seen"],
            }
        )
    campaigns.sort(key=lambda item: item.get("latest_seen") or "", reverse=True)
    return campaigns


def _campaign_membership_map(campaigns: list[dict]) -> dict[str, list[dict]]:
    membership = {}
    for campaign in campaigns:
        summary = {
            "rowid": campaign.get("rowid"),
            "name": campaign.get("name"),
            "window": campaign.get("window"),
            "risk_score": campaign.get("risk_score"),
            "alert_count": campaign.get("alert_count"),
            "attack_summary": campaign.get("attack_summary", []),
        }
        for alert in campaign.get("alerts", []):
            membership.setdefault(alert.get("rowid"), []).append(summary)
    return membership


def _build_case_sla(case_payload: dict, alert_payloads: list[dict]) -> dict:
    severity = str(case_payload.get("severity") or "Medium")
    target_minutes = {
        "Critical": 30,
        "High": 60,
        "Medium": 240,
        "Low": 480,
        "Informational": 720,
    }.get(severity, 240)
    first_seen_values = [item.get("first_seen_time") for item in alert_payloads if item.get("first_seen_time")]
    start_dt = _parse_timestamp(min(first_seen_values)) if first_seen_values else _parse_timestamp(case_payload.get("last_updated"))
    end_dt = _parse_timestamp(case_payload.get("last_updated"))
    elapsed_minutes = 0
    if start_dt and end_dt:
        elapsed_minutes = max(0, int((end_dt - start_dt).total_seconds() // 60))
    remaining_minutes = max(0, target_minutes - elapsed_minutes)
    return {
        "target_minutes": target_minutes,
        "elapsed_minutes": elapsed_minutes,
        "remaining_minutes": remaining_minutes,
        "breached": elapsed_minutes > target_minutes,
    }


def _build_attack_timeline(alert_payloads: list[dict], playbook_payloads: list[dict], message_payloads: list[dict], audit_payloads: list[dict]) -> list[dict]:
    items = []

    for alert in alert_payloads:
        items.append(
            {
                "rowid": f"timeline-alert-{alert.get('rowid')}",
                "type": "alert",
                "title": alert.get("title"),
                "summary": f"Alert {alert.get('rule_id')} observed for {alert.get('target') or 'unknown target'}",
                "severity": alert.get("severity"),
                "ts": alert.get("first_seen_time"),
            }
        )

    for playbook in playbook_payloads:
        items.append(
            {
                "rowid": f"timeline-playbook-{playbook.get('rowid')}",
                "type": "playbook",
                "title": playbook.get("name"),
                "summary": f"Playbook {playbook.get('status')} for case {playbook.get('source_rowid')}",
                "severity": None,
                "ts": playbook.get("started_at"),
            }
        )

    for message in message_payloads:
        items.append(
            {
                "rowid": f"timeline-message-{message.get('rowid')}",
                "type": "message",
                "title": message.get("role"),
                "summary": message.get("content") or message.get("data") or "Message recorded",
                "severity": None,
                "ts": _normalize_timestamp(message.get("ts")),
            }
        )

    for audit in audit_payloads:
        items.append(
            {
                "rowid": f"timeline-audit-{audit.get('rowid')}",
                "type": "response",
                "title": audit.get("action") or "audit",
                "summary": audit.get("content") or audit.get("details", {}).get("summary") or "Response action recorded",
                "severity": None,
                "ts": _normalize_timestamp(audit.get("ts")),
            }
        )

    items.sort(key=lambda item: item.get("ts") or "")
    return items[:40]


def _build_all_campaigns_from_store() -> list[dict]:
    alert_payloads = [_serialize_alert(item) for item in Alert.list(Group(), lazy_load=True)]
    return _build_campaigns(alert_payloads)


def _find_linked_case_for_alert(alert_rowid: str):
    for case_model in Case.list(Group(), lazy_load=False):
        case_alerts = case_model.alerts or []
        if any(getattr(item, "rowid", item) == alert_rowid for item in case_alerts):
            return case_model
    return None


def _ensure_case_for_alert(alert_model):
    linked_case = _find_linked_case_for_alert(alert_model.rowid)
    if linked_case:
        return linked_case, False

    case_model = CaseModel(
        title=f"Local SOC Case: {alert_model.title}",
        severity=alert_model.severity,
        confidence=alert_model.confidence,
        status=CaseStatus.NEW,
        category=alert_model.product_category,
        description=f"Manually escalated local case for alert {alert_model.rowid}.",
        correlation_uid=alert_model.correlation_uid,
        alerts=[alert_model.rowid],
        tags=["local-dev", "manual-escalation"],
    )
    case_rowid = Case.create(case_model)
    return Case.get(case_rowid, lazy_load=False), True


def _extract_action_targets(linked_alert=None, linked_case=None) -> tuple[str | None, str | None]:
    hostname = None
    owner = None

    alerts = []
    if linked_alert:
        alerts.append(linked_alert)
    if linked_case:
        alerts.extend(linked_case.alerts or [])

    for alert in alerts:
        alert_model = alert if hasattr(alert, "artifacts") else Alert.get(alert, lazy_load=False)
        raw_payload = _safe_json_load(getattr(alert_model, "raw_data", ""))
        hostname = hostname or raw_payload.get("hostname")
        owner = owner or _extract_email(raw_payload.get("user") or "")
        for artifact in getattr(alert_model, "artifacts", []) or []:
            if str(getattr(artifact, "type", "")) in {"Hostname", "Endpoint", "Device"} and not hostname:
                hostname = getattr(artifact, "value", None)
            if str(getattr(artifact, "type", "")) in {"Email Address", "User Name", "User"} and not owner:
                owner = _extract_email(getattr(artifact, "value", ""))
        if hostname and owner:
            break

    return hostname, owner


def _collect_linked_assets_from_alerts(alert_payloads: list[dict]) -> list[dict]:
    assets = []
    seen = set()
    inventory = list_assets()

    for alert_payload in alert_payloads:
        raw_event = alert_payload.get("raw_event") or {}
        hostname_candidates = []
        if raw_event.get("hostname"):
            hostname_candidates.append(raw_event.get("hostname"))
        if alert_payload.get("target"):
            hostname_candidates.append(alert_payload.get("target"))
        for artifact in alert_payload.get("artifacts", []):
            if artifact.get("type") in {"Hostname", "Endpoint", "Device"} and artifact.get("value"):
                hostname_candidates.append(artifact.get("value"))

        for asset in inventory:
            if asset.get("rowid") in seen:
                continue
            if asset.get("hostname") in hostname_candidates or asset.get("owner") == alert_payload.get("target"):
                assets.append(_serialize_asset(asset))
                seen.add(asset.get("rowid"))
    return assets


def _build_alert_enrichment_context(alert_payload: dict) -> dict:
    target_email = alert_payload.get("target") or ""
    sender_domain = alert_payload.get("sender_domain") or ""
    related_values = [item.get("value") for item in alert_payload.get("artifacts", []) if item.get("value")]
    ip_candidates = [value for value in related_values if isinstance(value, str) and value.count(".") == 3 and "@" not in value]
    host_candidates = [value for value in related_values if isinstance(value, str) and any(token in value.lower() for token in ["host", "laptop", "win", "srv"])]
    host_asset = get_asset(f"asset-{host_candidates[0]}") if host_candidates else None
    user_asset = None
    if not host_asset and target_email:
        for asset in list_assets():
            if asset.get("owner") == target_email:
                user_asset = asset
                break
    asset_context = host_asset or user_asset

    return {
        "user": {
            "email": target_email or "unknown user",
            "department": target_email.split("@", 1)[0] if "@" in target_email else "unknown",
            "risk": "Elevated" if alert_payload.get("severity") in {"High", "Critical"} else "Monitor",
        },
        "domain": {
            "value": sender_domain or "unknown domain",
            "reputation": "Suspicious" if sender_domain and not sender_domain.endswith((".google.com", ".amazon.com", ".microsoft.com")) else "Unknown",
            "recommended_block": bool(sender_domain),
        },
        "ip": {
            "value": ip_candidates[0] if ip_candidates else "Not observed",
            "geo": "Local demo context",
            "reputation": "Needs lookup" if ip_candidates else "Unavailable",
        },
        "host": {
            "value": (asset_context or {}).get("hostname") or (host_candidates[0] if host_candidates else "Not observed"),
            "state": (asset_context or {}).get("status") or ("Isolate candidate" if host_candidates else "No direct host artifact"),
            "criticality": (asset_context or {}).get("criticality") or "Unknown",
            "last_seen": (asset_context or {}).get("last_seen") or "",
        },
    }


def _build_recommended_actions(alert_payload: dict) -> list[dict]:
    sender_domain = alert_payload.get("sender_domain") or "suspicious-domain.local"
    target = alert_payload.get("target") or "user@example.local"
    actions = [
        {"id": "isolate_host", "label": "Isolate host", "description": "Contain the affected endpoint if a host artifact exists."},
        {"id": "disable_user", "label": "Disable user", "description": f"Temporarily disable {target} pending validation."},
        {"id": "block_domain_ip", "label": "Block IP/domain/hash", "description": f"Block {sender_domain} or related indicators at the edge."},
        {"id": "create_ticket", "label": "Create ticket", "description": "Open a tracked incident task for analyst follow-up."},
        {"id": "run_playbook", "label": "Run playbook", "description": "Queue the default investigation playbook for the linked case."},
        {"id": "assign", "label": "Assign", "description": "Simulate assignment to a local SOC analyst."},
        {"id": "resolve_true_positive", "label": "Resolve as true positive", "description": "Mark the alert as validated and remediated."},
        {"id": "resolve_benign_positive", "label": "Resolve as benign positive", "description": "Mark the alert as benign but expected activity."},
        {"id": "reopen_alert", "label": "Reopen alert", "description": "Move the alert back into the active queue."},
        {"id": "close_false_positive", "label": "Close as false positive", "description": "Mark the alert benign and close associated case work."},
    ]
    if str(alert_payload.get("rule_id", "")).startswith("VULN-Rule"):
        actions.insert(0, {"id": "create_ticket", "label": "Create remediation ticket", "description": "Create a remediation task for patching, workaround, or compensating controls."})
        actions.insert(1, {"id": "block_domain_ip", "label": "Apply compensating control", "description": "Block exploit infrastructure or restrict exposure while patching is pending."})
    return actions


def _update_alert_workflow_state(alert_model, status, status_detail: str, remediation: str = ""):
    if not alert_model:
        return
    alert_model.status = status
    alert_model.status_detail = status_detail
    if remediation:
        alert_model.remediation = remediation
    Alert.update(alert_model)


def _sync_case_alerts(case_model, alert_status, status_detail: str, remediation: str = ""):
    for alert_ref in case_model.alerts or []:
        alert_model = alert_ref if hasattr(alert_ref, "rowid") else Alert.get(alert_ref, lazy_load=False)
        _update_alert_workflow_state(alert_model, alert_status, status_detail, remediation)


def _build_alert_resolution_guidance(alert_model, alert_payload: dict, linked_case) -> dict:
    if not linked_case:
        return {
            "state": "untriaged",
            "headline": "No linked case yet",
            "recommendation": "Escalate this alert to a case or assign it for analyst review.",
            "next_action": "escalate_to_case",
        }

    linked_playbooks = [
        _serialize_playbook(item)
        for item in Playbook.list(Group(), lazy_load=True)
        if item.source_rowid == linked_case.rowid
    ]
    linked_playbooks.sort(key=lambda item: item.get("started_at") or "", reverse=True)
    latest_playbook = linked_playbooks[0] if linked_playbooks else None

    if latest_playbook and latest_playbook.get("status") == "Success":
        rule_id = str(alert_payload.get("rule_id") or "")
        if rule_id.startswith("VULN-Rule"):
            return {
                "state": "ready_to_resolve",
                "headline": "Playbook completed. Vulnerability remediation should now be tracked.",
                "recommendation": "Create or confirm a remediation ticket, apply compensating controls if needed, then resolve the alert as true positive once patching is tracked.",
                "next_action": "resolve_true_positive",
                "playbook": latest_playbook,
            }
        if alert_payload.get("severity") in {"High", "Critical"}:
            return {
                "state": "ready_to_resolve",
                "headline": "Playbook completed. Analyst can finalize the alert.",
                "recommendation": "If the incident was validated and contained, resolve as true positive. If evidence indicates expected behavior, resolve as benign positive.",
                "next_action": "resolve_true_positive",
                "playbook": latest_playbook,
            }
        return {
            "state": "ready_to_resolve",
            "headline": "Playbook completed with low residual risk.",
            "recommendation": "If no malicious intent remains, resolve as benign positive or false positive based on analyst review.",
            "next_action": "resolve_benign_positive",
            "playbook": latest_playbook,
        }

    if latest_playbook and latest_playbook.get("status") == "Running":
        return {
            "state": "automation_running",
            "headline": "Playbook is still running",
            "recommendation": "Wait for playbook completion or review intermediate messages before resolving the alert.",
            "next_action": "run_playbook",
            "playbook": latest_playbook,
        }

    return {
        "state": "needs_playbook",
        "headline": "Automation has not completed yet",
        "recommendation": "Run the investigation playbook, then review the outcome before resolving the alert.",
        "next_action": "run_playbook",
        "playbook": latest_playbook,
    }


def _derive_notes_for_case(case_model) -> list[dict]:
    notes = []
    if case_model.comment:
        notes.append({"author": "Analyst", "content": case_model.comment, "ts": case_model.utime})
    if case_model.comment_ai:
        notes.append({"author": "Agent", "content": case_model.comment_ai, "ts": case_model.utime})
    return notes


def _build_playbook_trace(playbook_model) -> list[dict]:
    trace = []
    related_messages = [item for item in Message.list(Group(), lazy_load=True) if playbook_model.rowid in (item.playbook or [])]
    related_messages.sort(key=lambda item: item.ctime or item.utime or "")
    for index, message_model in enumerate(related_messages, start=1):
        trace.append(
            {
                "step": index,
                "node": message_model.node or f"step-{index}",
                "role": message_model.type,
                "content": message_model.content,
                "output": _safe_json_load(message_model.data) if message_model.data else None,
                "ts": message_model.ctime or message_model.utime,
            }
        )
    return trace


def _calculate_top_entities(alerts: list[dict], key: str, limit: int = 5) -> list[dict]:
    counter = Counter(item.get(key) or "unknown" for item in alerts)
    return [{"name": name, "count": count} for name, count in counter.most_common(limit)]


def _get_store_counts() -> dict:
    try:
        return {
            "alerts": len(Alert.list(Group(), lazy_load=True)),
            "cases": len(Case.list(Group(), lazy_load=True)),
            "playbooks": len(Playbook.list(Group(), lazy_load=True)),
            "messages": len(Message.list(Group(), lazy_load=True)),
        }
    except Exception:
        logger.exception("Failed to read local SIRP counts; returning zeroed demo counts.")
        return {
            "alerts": 0,
            "cases": 0,
            "playbooks": 0,
            "messages": 0,
        }


def _message_links_playbook(message_payload: dict, playbook_rowid: str) -> bool:
    playbook_links = message_payload.get("playbook") or []
    return playbook_rowid in playbook_links


def _load_phishing_module_class():
    spec = importlib.util.spec_from_file_location(PHISHING_MODULE_FILE.stem, PHISHING_MODULE_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "Module")


def _run_local_demo_fallback(records: list[dict]) -> None:
    if not records:
        return

    os.environ["ASF_FAKE_LLM"] = "1"
    os.environ["ASF_DISABLE_EMBEDDINGS"] = "1"
    from PLUGINS.LLM import llmapi as llmapi_module

    llmapi_module.FAKE_LLM_ENABLED = True

    module_class = _load_phishing_module_class()

    for record in records:
        module_instance = module_class()
        module_instance._thread_name = "localdev-demo"
        module_instance.read_message = lambda record=record: record
        module_instance.run()

    from Lib.montior import MainMonitor

    MainMonitor.subscribe_pending_playbook()
    deadline = time.time() + 8
    while time.time() < deadline:
        pending = [item for item in Playbook.list_pending_playbooks() if getattr(item, "rowid", None)]
        if not pending:
            break
        time.sleep(1)


def _serialize_alert_detail(alert_model) -> dict:
    payload = _serialize_alert(alert_model)
    raw_data = _safe_json_load(alert_model.raw_data)
    payload["artifacts"] = [_serialize_artifact(item) for item in (alert_model.artifacts or [])]
    payload["artifact_summary"] = {
        "total": len(payload["artifacts"]),
        "actors": [item for item in payload["artifacts"] if item["role"] == "Actor"],
        "targets": [item for item in payload["artifacts"] if item["role"] == "Target"],
        "related": [item for item in payload["artifacts"] if item["role"] == "Related"],
    }
    payload["raw_headers"] = raw_data.get("headers", {})
    payload["raw_body"] = raw_data.get("body", {})
    payload["raw_event"] = raw_data
    payload["attachments"] = raw_data.get("attachments", [])
    linked_case = _find_linked_case_for_alert(alert_model.rowid)
    payload["linked_case"] = _serialize_case(linked_case, {}) if linked_case else None
    payload["enrichment_context"] = _build_alert_enrichment_context(payload)
    payload["recommended_actions"] = _build_recommended_actions(payload)
    payload["threat_analysis"] = _build_detection_intelligence(payload, raw_data)
    campaign_membership = _campaign_membership_map(_build_all_campaigns_from_store())
    payload["linked_campaigns"] = campaign_membership.get(alert_model.rowid, [])
    payload["resolution_guidance"] = _build_alert_resolution_guidance(alert_model, payload, linked_case)
    payload["response_jobs"] = [
        _serialize_response_job(item)
        for item in _load_response_jobs()
        if item.get("target_type") == "alert" and item.get("target_rowid") == alert_model.rowid
    ][:10]
    return payload


def _serialize_case_detail(case_model) -> dict:
    playbook_models = [
        item for item in Playbook.list(Group(), lazy_load=True)
        if item.source_rowid == case_model.rowid
    ]
    playbook_payloads = [_serialize_playbook(item) for item in playbook_models]
    playbook_payloads.sort(key=lambda item: item.get("started_at") or "", reverse=True)

    all_message_payloads = [_serialize_message(item) for item in Message.list(Group(), lazy_load=True)]
    recent_messages = [
        payload for payload in all_message_payloads
        if any(_message_links_playbook(payload, playbook["rowid"]) for playbook in playbook_payloads)
    ]
    recent_messages.sort(key=lambda item: _normalize_timestamp(item.get("ts")), reverse=True)

    alerts = case_model.alerts or []
    alert_payloads = [_serialize_alert_detail(item) for item in alerts]
    artifacts = []
    for alert_payload in alert_payloads:
        artifacts.extend(alert_payload.get("artifacts", []))

    playbooks_by_source = {case_model.rowid: playbook_payloads}
    payload = _serialize_case(case_model, playbooks_by_source)
    payload["alerts"] = alert_payloads
    payload["linked_playbooks"] = playbook_payloads
    payload["recent_messages"] = recent_messages[:10]
    case_audits = [
        _serialize_audit_entry(entry)
        for entry in _load_audit_entries()
        if entry.get("target_rowid") == case_model.rowid
    ]
    timeline = recent_messages + case_audits
    timeline.sort(key=lambda item: _normalize_timestamp(item.get("ts")), reverse=True)
    payload["activity_timeline"] = timeline[:20]
    payload["related_alerts"] = alert_payloads
    payload["linked_assets"] = _collect_linked_assets_from_alerts(alert_payloads)
    payload["notes"] = _derive_notes_for_case(case_model)
    payload["disposition"] = case_model.verdict or case_model.verdict_ai or "Undispositioned"
    payload["sla"] = _build_case_sla(payload, alert_payloads)
    payload["assignment"] = {
        "owner": payload.get("owner"),
        "assigned": payload.get("owner") != "Local SOC Pipeline",
    }
    payload["recommended_actions"] = _build_recommended_actions({"severity": str(case_model.severity or ""), "target": "", "sender_domain": ""})
    payload["artifact_summary"] = {
        "total": len(artifacts),
        "actors": [item for item in artifacts if item["role"] == "Actor"],
        "targets": [item for item in artifacts if item["role"] == "Target"],
        "related": [item for item in artifacts if item["role"] == "Related"],
    }
    payload["response_history"] = [item for item in case_audits if item.get("action")]
    payload["attack_timeline"] = _build_attack_timeline(alert_payloads, playbook_payloads, recent_messages, case_audits)
    payload["response_jobs"] = [
        _serialize_response_job(item)
        for item in _load_response_jobs()
        if item.get("target_type") == "case" and item.get("target_rowid") == case_model.rowid
    ][:10]
    return payload


def _serialize_playbook_detail(playbook_model) -> dict:
    payload = _serialize_playbook(playbook_model)
    payload["step_trace"] = _build_playbook_trace(playbook_model)
    payload["outputs"] = [item.get("output") for item in payload["step_trace"] if item.get("output")]
    payload["audit_log"] = [
        _serialize_audit_entry(entry)
        for entry in _load_audit_entries()
        if entry.get("target_rowid") == playbook_model.source_rowid
    ][:10]
    return payload


class LocalDevOverviewView(BaseView):
    def list(self, request, **kwargs):
        _require_local_dev_api()
        try:
            alerts = [_serialize_alert(item) for item in Alert.list(Group(), lazy_load=True)]
            playbooks = [_serialize_playbook(item) for item in Playbook.list(Group(), lazy_load=True)]
            messages = [_serialize_message(item) for item in Message.list(Group(), lazy_load=True)]
            audits = [_serialize_audit_entry(item) for item in _load_audit_entries()]
            playbooks_by_source = {}
            for playbook in playbooks:
                playbooks_by_source.setdefault(playbook["source_rowid"], []).append(playbook)
            cases = [_serialize_case(item, playbooks_by_source) for item in Case.list(Group(), lazy_load=True)]
            campaigns = _build_all_campaigns_from_store()
            severity_distribution = Counter(item.get("severity") or "Unknown" for item in alerts)
            assets = [_serialize_asset(item) for item in list_assets()]
            payload = {
                "stats": {
                    "alerts": len(alerts),
                    "cases": len(cases),
                    "playbooks": len(playbooks),
                    "messages": len(messages),
                    "assets": len(assets),
                    "critical_alerts": sum(1 for item in alerts if item["severity"] == "Critical"),
                    "running_playbooks": sum(1 for item in playbooks if item["status"] == "Running"),
                    "open_cases": sum(1 for item in cases if item.get("status") not in {"Resolved", "Closed"}),
                    "campaigns": len(campaigns),
                    "mtta_minutes": 8,
                    "mttr_minutes": 42,
                },
                "metrics": {
                    "severity_distribution": [{"name": name, "count": count} for name, count in severity_distribution.items()],
                    "top_assets": _calculate_top_entities(alerts, "target"),
                    "top_users": _calculate_top_entities(alerts, "target"),
                    "top_campaigns": [{"name": item["name"], "count": item["alert_count"]} for item in campaigns[:5]],
                    "agent_status": [
                        {"name": "Online", "count": sum(1 for item in assets if item.get("status") == "Online")},
                        {"name": "Attention", "count": sum(1 for item in assets if item.get("status") == "Attention")},
                        {"name": "Contained", "count": sum(1 for item in assets if item.get("status") == "Contained")},
                    ],
                },
                "recent_activity": sorted(
                    messages + audits,
                    key=lambda item: _normalize_timestamp(item.get("ts")),
                    reverse=True,
                )[:12],
            }
        except Exception:
            logger.exception("Local-dev overview failed; returning empty overview payload.")
            payload = _empty_overview_payload()
        return Response(data_return(200, payload, "æˆåŠŸ", "Success"))

        """
        try:
            alerts = [_serialize_alert(item) for item in Alert.list(Group(), lazy_load=True)]
            playbooks = [_serialize_playbook(item) for item in Playbook.list(Group(), lazy_load=True)]
            messages = [_serialize_message(item) for item in Message.list(Group(), lazy_load=True)]
            audits = [_serialize_audit_entry(item) for item in _load_audit_entries()]
        playbooks_by_source = {}
        for playbook in playbooks:
            playbooks_by_source.setdefault(playbook["source_rowid"], []).append(playbook)
        cases = [_serialize_case(item, playbooks_by_source) for item in Case.list(Group(), lazy_load=True)]
        campaigns = _build_all_campaigns_from_store()

        severity_distribution = Counter(item.get("severity") or "Unknown" for item in alerts)
        assets = [_serialize_asset(item) for item in list_assets()]
        stats = {
            "alerts": len(alerts),
            "cases": len(cases),
            "playbooks": len(playbooks),
            "messages": len(messages),
            "assets": len(assets),
            "critical_alerts": sum(1 for item in alerts if item["severity"] == "Critical"),
            "running_playbooks": sum(1 for item in playbooks if item["status"] == "Running"),
            "open_cases": sum(1 for item in cases if item.get("status") not in {"Resolved", "Closed"}),
            "campaigns": len(campaigns),
            "mtta_minutes": 8,
            "mttr_minutes": 42,
        }
        metrics = {
            "severity_distribution": [{"name": name, "count": count} for name, count in severity_distribution.items()],
            "top_assets": _calculate_top_entities(alerts, "target"),
            "top_users": _calculate_top_entities(alerts, "target"),
            "top_campaigns": [{"name": item["name"], "count": item["alert_count"]} for item in campaigns[:5]],
            "agent_status": [
                {"name": "Online", "count": sum(1 for item in assets if item.get("status") == "Online")},
                {"name": "Attention", "count": sum(1 for item in assets if item.get("status") == "Attention")},
                {"name": "Contained", "count": sum(1 for item in assets if item.get("status") == "Contained")},
            ],
        }
        recent_activity = sorted(
            messages + audits,
            key=lambda item: _normalize_timestamp(item.get("ts")),
            reverse=True,
        )[:12]

        context = data_return(200, {"stats": stats, "metrics": metrics, "recent_activity": recent_activity}, "成功", "Success")
        return Response(context)

        """


class LocalDevAlertsView(BaseView):
    def list(self, request, **kwargs):
        _require_local_dev_api()
        query = request.query_params.get("q", "").strip().lower()
        items = []
        for alert_model in _safe_local_dev_items(lambda: Alert.list(Group(), lazy_load=True), "alerts"):
            payload = _serialize_alert(alert_model)
            if _matches_query(payload, query, ["title", "rule_id", "rule_name", "target", "sender", "summary", "rowid"]):
                items.append(payload)
        return Response(data_return(200, items, "æˆåŠŸ", "Success"))
        items = []
        for alert_model in Alert.list(Group(), lazy_load=True):
            payload = _serialize_alert(alert_model)
            if _matches_query(payload, query, ["title", "rule_id", "rule_name", "target", "sender", "summary", "rowid"]):
                items.append(payload)
        context = data_return(200, items, "成功", "Success")
        return Response(context)

    def retrieve(self, request, pk=None, **kwargs):
        _require_local_dev_api()
        payload = _serialize_alert_detail(Alert.get(pk, lazy_load=False))
        context = data_return(200, payload, "成功", "Success")
        return Response(context)


class LocalDevCasesView(BaseView):
    def list(self, request, **kwargs):
        _require_local_dev_api()
        query = request.query_params.get("q", "").strip().lower()
        playbooks_by_source = {}
        for playbook_model in _safe_local_dev_items(lambda: Playbook.list(Group(), lazy_load=True), "cases.playbooks"):
            payload = _serialize_playbook(playbook_model)
            playbooks_by_source.setdefault(payload["source_rowid"], []).append(payload)

        items = []
        for case_model in _safe_local_dev_items(lambda: Case.list(Group(), lazy_load=True), "cases"):
            payload = _serialize_case(case_model, playbooks_by_source)
            if _matches_query(payload, query, ["title", "correlation_uid", "playbook", "rowid"]):
                items.append(payload)
        return Response(data_return(200, items, "æˆåŠŸ", "Success"))
        playbooks_by_source = {}
        for playbook_model in Playbook.list(Group(), lazy_load=True):
            payload = _serialize_playbook(playbook_model)
            playbooks_by_source.setdefault(payload["source_rowid"], []).append(payload)

        items = []
        for case_model in Case.list(Group(), lazy_load=True):
            payload = _serialize_case(case_model, playbooks_by_source)
            if _matches_query(payload, query, ["title", "correlation_uid", "playbook", "rowid"]):
                items.append(payload)
        context = data_return(200, items, "成功", "Success")
        return Response(context)

    def retrieve(self, request, pk=None, **kwargs):
        _require_local_dev_api()
        payload = _serialize_case_detail(Case.get(pk, lazy_load=False))
        context = data_return(200, payload, "成功", "Success")
        return Response(context)


class LocalDevCampaignsView(BaseView):
    def list(self, request, **kwargs):
        _require_local_dev_api()
        query = request.query_params.get("q", "").strip().lower()
        items = _safe_local_dev_items(_build_all_campaigns_from_store, "campaigns")
        if query:
            filtered = []
            for item in items:
                payload = {
                    "name": item.get("name"),
                    "users": " ".join(item.get("users", [])),
                    "assets": " ".join(item.get("assets", [])),
                    "domains": " ".join(item.get("domains", [])),
                    "ips": " ".join(item.get("ips", [])),
                    "attack_summary": " ".join(item.get("attack_summary", [])),
                }
                if _matches_query(payload, query, ["name", "users", "assets", "domains", "ips", "attack_summary"]):
                    filtered.append(item)
            items = filtered
        return Response(data_return(200, items, "æˆåŠŸ", "Success"))
        items = _build_all_campaigns_from_store()
        if query:
            filtered = []
            for item in items:
                payload = {
                    "name": item.get("name"),
                    "users": " ".join(item.get("users", [])),
                    "assets": " ".join(item.get("assets", [])),
                    "domains": " ".join(item.get("domains", [])),
                    "ips": " ".join(item.get("ips", [])),
                    "attack_summary": " ".join(item.get("attack_summary", [])),
                }
                if _matches_query(payload, query, ["name", "users", "assets", "domains", "ips", "attack_summary"]):
                    filtered.append(item)
            items = filtered
        context = data_return(200, items, "æˆåŠŸ", "Success")
        return Response(context)


class LocalDevPlaybooksView(BaseView):
    def list(self, request, **kwargs):
        _require_local_dev_api()
        query = request.query_params.get("q", "").strip().lower()
        items = []
        for playbook_model in _safe_local_dev_items(lambda: Playbook.list(Group(), lazy_load=True), "playbooks"):
            payload = _serialize_playbook(playbook_model)
            if _matches_query(payload, query, ["name", "status", "source_rowid", "job_id", "rowid"]):
                items.append(payload)
        return Response(data_return(200, items, "æˆåŠŸ", "Success"))
        items = []
        for playbook_model in Playbook.list(Group(), lazy_load=True):
            payload = _serialize_playbook(playbook_model)
            if _matches_query(payload, query, ["name", "status", "source_rowid", "job_id", "rowid"]):
                items.append(payload)
        context = data_return(200, items, "成功", "Success")
        return Response(context)

    def retrieve(self, request, pk=None, **kwargs):
        _require_local_dev_api()
        payload = _serialize_playbook_detail(Playbook.get(pk, lazy_load=False))
        context = data_return(200, payload, "成功", "Success")
        return Response(context)


class LocalDevMessagesView(BaseView):
    def list(self, request, **kwargs):
        _require_local_dev_api()
        query = request.query_params.get("q", "").strip().lower()
        items = []
        for message_model in _safe_local_dev_items(lambda: Message.list(Group(), lazy_load=True), "messages"):
            payload = _serialize_message(message_model)
            if _matches_query(payload, query, ["role", "node", "content", "rowid"]):
                items.append(payload)
        return Response(data_return(200, items, "æˆåŠŸ", "Success"))
        items = []
        for message_model in Message.list(Group(), lazy_load=True):
            payload = _serialize_message(message_model)
            if _matches_query(payload, query, ["role", "node", "content", "rowid"]):
                items.append(payload)
        context = data_return(200, items, "成功", "Success")
        return Response(context)


class LocalDevAuditView(BaseView):
    def list(self, request, **kwargs):
        _require_local_dev_api()
        items = [_serialize_audit_entry(item) for item in _safe_local_dev_items(_load_audit_entries, "audit")]
        return Response(data_return(200, items, "æˆåŠŸ", "Success"))
        items = [_serialize_audit_entry(item) for item in _load_audit_entries()]
        context = data_return(200, items, "成功", "Success")
        return Response(context)


class LocalDevResponseJobsView(BaseView):
    def list(self, request, **kwargs):
        _require_local_dev_api()
        items = [_serialize_response_job(item) for item in _safe_local_dev_items(_load_response_jobs, "response-jobs")]
        return Response(data_return(200, items, "æˆåŠŸ", "Success"))
        items = [_serialize_response_job(item) for item in _load_response_jobs()]
        context = data_return(200, items, "成功", "Success")
        return Response(context)


class LocalDevAssetsView(BaseView):
    def list(self, request, **kwargs):
        _require_local_dev_api()
        query = request.query_params.get("q", "").strip().lower()
        items = []
        for asset in _safe_local_dev_items(list_assets, "assets"):
            payload = _serialize_asset(asset)
            if _matches_query(payload, query, ["hostname", "owner", "criticality", "status", "site", "ip_address"]):
                items.append(payload)
        return Response(data_return(200, items, "æˆåŠŸ", "Success"))
        items = []
        for asset in list_assets():
            payload = _serialize_asset(asset)
            if _matches_query(payload, query, ["hostname", "owner", "criticality", "status", "site", "ip_address"]):
                items.append(payload)
        context = data_return(200, items, "成功", "Success")
        return Response(context)

    def retrieve(self, request, pk=None, **kwargs):
        _require_local_dev_api()
        asset = get_asset(pk)
        if not asset:
            raise NotFound("Local asset not found.")
        context = data_return(200, _serialize_asset(asset), "成功", "Success")
        return Response(context)


class LocalDevCaseWorkflowView(BaseView):
    def create(self, request, pk=None, **kwargs):
        _require_local_dev_api()

        case_rowid = request.data.get("case_rowid")
        owner = request.data.get("owner")
        note = request.data.get("note")
        status = request.data.get("status")
        disposition = request.data.get("disposition")

        if not case_rowid:
            context = data_return(400, {}, "失败", "case_rowid is required")
            return Response(context, status=400)

        case_model = Case.get(case_rowid, lazy_load=False)
        update_payload = CaseModel(rowid=case_rowid)
        audit_messages = []

        if owner:
            update_payload.assignee_l2 = owner
            audit_messages.append(f"Owner assigned to {owner}.")

        if note:
            existing_comment = case_model.comment or ""
            update_payload.comment = f"{existing_comment}\n{note}".strip()
            audit_messages.append("Analyst note added.")

        if status:
            normalized_status = CaseStatus.INVESTIGATING if status in {"Investigating", "In Progress"} else CaseStatus(status)
            update_payload.status = normalized_status
            audit_messages.append(f"Status changed to {normalized_status}.")

        if disposition:
            verdict = CaseVerdict(disposition)
            update_payload.verdict = verdict
            if verdict == CaseVerdict.TRUE_POSITIVE:
                update_payload.status = CaseStatus.RESOLVED
            elif verdict in {CaseVerdict.FALSE_POSITIVE, CaseVerdict.BENIGN}:
                update_payload.status = CaseStatus.CLOSED
            audit_messages.append(f"Disposition set to {disposition}.")

        Case.update(update_payload)
        refreshed_case = Case.get(case_rowid, lazy_load=False)
        if disposition == CaseVerdict.TRUE_POSITIVE:
            _sync_case_alerts(
                refreshed_case,
                AlertStatus.RESOLVED,
                "Case resolved as true positive in local-dev mode.",
                "Validated incident. Verify remediation and closure evidence.",
            )
        elif disposition in {CaseVerdict.FALSE_POSITIVE, CaseVerdict.BENIGN}:
            _sync_case_alerts(
                refreshed_case,
                AlertStatus.RESOLVED,
                f"Case closed as {disposition} in local-dev mode.",
                "No further alert remediation required.",
            )

        entry = _append_audit_entry(
            _make_audit_entry(
                action="case_workflow_update",
                target_type="case",
                target_rowid=case_rowid,
                details={
                    "summary": " ".join(audit_messages) or "Case workflow updated.",
                    "owner": owner,
                    "note": note,
                    "status": status,
                    "disposition": disposition,
                },
            )
        )

        response_job = _append_response_job(
            _make_response_job(
                action="case_workflow_update",
                target_type="case",
                target_rowid=case_rowid,
                outputs={
                    "summary": " ".join(audit_messages) or "Case workflow updated.",
                    "owner": owner,
                    "note": note,
                    "status": status,
                    "disposition": disposition,
                },
            )
        )

        payload = {
            "audit_entry": _serialize_audit_entry(entry),
            "response_job": _serialize_response_job(response_job),
            "case": _serialize_case_detail(refreshed_case),
        }
        context = data_return(200, payload, "成功", "Success")
        return Response(context)


class LocalDevResponseActionsView(BaseView):
    def create(self, request, pk=None, **kwargs):
        _require_local_dev_api()

        action = request.data.get("action")
        target_type = request.data.get("target_type")
        target_rowid = request.data.get("target_rowid")
        note = request.data.get("note", "")

        if target_type not in {"alert", "case"} or not target_rowid or not action:
            context = data_return(400, {}, "失败", "Invalid local-dev response action payload")
            return Response(context, status=400)

        linked_case = None
        linked_alert = None

        if target_type == "alert":
            linked_alert = Alert.get(target_rowid, lazy_load=False)
            linked_case = _find_linked_case_for_alert(target_rowid)
        else:
            linked_case = Case.get(target_rowid, lazy_load=False)

        summary = ""
        hostname, owner = _extract_action_targets(linked_alert, linked_case)

        if action == "isolate_host":
            summary = "Host isolation simulated in local-dev mode."
            if hostname:
                update_asset_state(hostname=hostname, status="Contained", isolation_state="Isolated")
            if linked_alert:
                _update_alert_workflow_state(
                    linked_alert,
                    AlertStatus.IN_PROGRESS,
                    "Host isolation initiated in local-dev mode.",
                    "Review containment effectiveness and collect endpoint evidence.",
                )
            if linked_case:
                linked_case.comment = f"{linked_case.comment}\nHost isolation simulated. {note}".strip()
                Case.update(linked_case)
        elif action == "disable_user":
            summary = "User disable simulated in local-dev mode."
            if owner:
                update_asset_state(owner=owner, status="User Action Required")
            if linked_alert:
                _update_alert_workflow_state(
                    linked_alert,
                    AlertStatus.IN_PROGRESS,
                    "User disable initiated in local-dev mode.",
                    "Confirm identity impact and rotate credentials if compromise is suspected.",
                )
            if linked_case:
                linked_case.comment = f"{linked_case.comment}\nUser disable simulated. {note}".strip()
                Case.update(linked_case)
        elif action == "block_domain_ip":
            summary = "IP/domain/hash block simulated in local-dev mode."
            if hostname:
                asset = get_asset(f"asset-{hostname}") or update_asset_state(hostname=hostname)
                if asset:
                    blocked = list(asset.get("blocked_indicators") or [])
                    blocked.append({"value": note or "indicator-from-alert", "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
                    update_asset_state(hostname=hostname, blocked_indicators=blocked)
            if linked_alert:
                _update_alert_workflow_state(
                    linked_alert,
                    AlertStatus.IN_PROGRESS,
                    "Compensating control applied in local-dev mode.",
                    "Monitor for recurring communications and validate control propagation.",
                )
            if linked_case:
                linked_case.comment = f"{linked_case.comment}\nIP/domain/hash block simulated. {note}".strip()
                Case.update(linked_case)
        elif action == "create_ticket":
            ticket = TicketModel(
                title=f"Local SOC ticket for {linked_case.title if linked_case else target_rowid}",
                uid=f"LOCAL-{int(time.time())}",
                type=TicketType.OTHER,
                status=TicketStatus.NEW,
                src_url="local://ticket",
            )
            ticket_rowid = Ticket.create(ticket)
            if linked_case:
                linked_case.tickets = (linked_case.tickets or []) + [ticket_rowid]
                linked_case.comment = f"{linked_case.comment}\nTicket created: {ticket_rowid}. {note}".strip()
                Case.update(linked_case)
            if linked_alert:
                _update_alert_workflow_state(
                    linked_alert,
                    AlertStatus.IN_PROGRESS,
                    f"Ticket {ticket_rowid} created for follow-up.",
                    "Track remediation progress through the linked ticket.",
                )
            summary = f"Ticket created: {ticket_rowid}"
        elif action == "escalate_to_case":
            if not linked_alert:
                context = data_return(400, {}, "失败", "Escalation requires an alert target")
                return Response(context, status=400)
            linked_case, created = _ensure_case_for_alert(linked_alert)
            _update_alert_workflow_state(
                linked_alert,
                AlertStatus.IN_PROGRESS,
                "Escalated to case for active investigation.",
                "Continue investigation in the linked case workspace.",
            )
            summary = f"{'Created' if created else 'Reused'} local case {linked_case.rowid} for alert escalation."
        elif action == "run_playbook":
            if linked_alert and not linked_case:
                linked_case, _ = _ensure_case_for_alert(linked_alert)
            if not linked_case:
                context = data_return(400, {}, "失败", "Run playbook requires a linked case")
                return Response(context, status=400)

            playbook = Playbook.add_pending_playbook(
                type=PlaybookType.CASE,
                name=select_local_case_playbook_name(
                    rule_id=getattr(linked_alert, "rule_id", None),
                    title=getattr(linked_alert, "title", None) or getattr(linked_case, "title", None),
                    product_category=getattr(linked_alert, "product_category", None),
                ),
                source_rowid=linked_case.rowid,
                user_input="Manually queued from local SOC alert drawer",
            )

            try:
                from Lib.montior import MainMonitor

                MainMonitor.subscribe_pending_playbook()
            except Exception:
                pass
            if linked_alert:
                _update_alert_workflow_state(
                    linked_alert,
                    AlertStatus.IN_PROGRESS,
                    "Investigation playbook queued in local-dev mode.",
                    "Review playbook output and update case disposition.",
                )

            summary = f"Queued playbook {playbook.rowid} for case {linked_case.rowid}."
        elif action == "assign":
            assignee = note or "Local SOC Analyst"
            if linked_case:
                linked_case.comment = f"{linked_case.comment}\nAssigned to {assignee} in local-dev mode.".strip()
                Case.update(linked_case)
            elif linked_alert:
                linked_alert.comment = f"{linked_alert.comment}\nAssigned to {assignee} in local-dev mode.".strip()
                _update_alert_workflow_state(
                    linked_alert,
                    AlertStatus.IN_PROGRESS,
                    f"Assigned to {assignee} in local-dev mode.",
                    "Analyst review pending.",
                )
            summary = f"Assigned to {assignee} in local-dev mode."
        elif action == "close_false_positive":
            summary = "Marked as false positive in local-dev mode."
            if linked_case:
                linked_case.verdict = CaseVerdict.FALSE_POSITIVE
                linked_case.status = CaseStatus.CLOSED
                linked_case.summary = "Closed as false positive during local demo."
                linked_case.comment = f"{linked_case.comment}\nClosed as false positive. {note}".strip()
                Case.update(linked_case)
                _sync_case_alerts(
                    linked_case,
                    AlertStatus.RESOLVED,
                    "Case closed as false positive in local-dev mode.",
                    "No further remediation required.",
                )
            if linked_alert:
                linked_alert.comment = f"{linked_alert.comment}\nClosed as false positive. {note}".strip()
                _update_alert_workflow_state(
                    linked_alert,
                    AlertStatus.RESOLVED,
                    "Closed as false positive in local-dev mode.",
                    "No further remediation required.",
                )
        elif action == "resolve_true_positive":
            summary = "Marked as true positive and resolved in local-dev mode."
            if linked_case:
                linked_case.verdict = CaseVerdict.TRUE_POSITIVE
                linked_case.status = CaseStatus.RESOLVED
                linked_case.summary = "Resolved as true positive during local demo."
                linked_case.comment = f"{linked_case.comment}\nResolved as true positive. {note}".strip()
                Case.update(linked_case)
                _sync_case_alerts(
                    linked_case,
                    AlertStatus.RESOLVED,
                    "Case resolved as true positive in local-dev mode.",
                    "Validated incident. Confirm remediation evidence before final closure.",
                )
            if linked_alert:
                linked_alert.comment = f"{linked_alert.comment}\nResolved as true positive. {note}".strip()
                _update_alert_workflow_state(
                    linked_alert,
                    AlertStatus.RESOLVED,
                    "Resolved as true positive in local-dev mode.",
                    "Validated incident. Confirm remediation evidence before final closure.",
                )
        elif action == "resolve_benign_positive":
            summary = "Marked as benign positive and resolved in local-dev mode."
            if linked_case:
                linked_case.verdict = CaseVerdict.BENIGN
                linked_case.status = CaseStatus.CLOSED
                linked_case.summary = "Closed as benign positive during local demo."
                linked_case.comment = f"{linked_case.comment}\nClosed as benign positive. {note}".strip()
                Case.update(linked_case)
                _sync_case_alerts(
                    linked_case,
                    AlertStatus.RESOLVED,
                    "Case closed as benign positive in local-dev mode.",
                    "Expected activity confirmed. No further remediation required.",
                )
            if linked_alert:
                linked_alert.comment = f"{linked_alert.comment}\nResolved as benign positive. {note}".strip()
                _update_alert_workflow_state(
                    linked_alert,
                    AlertStatus.RESOLVED,
                    "Resolved as benign positive in local-dev mode.",
                    "Expected activity confirmed. No further remediation required.",
                )
        elif action == "reopen_alert":
            summary = "Alert reopened in local-dev mode."
            if linked_alert:
                linked_alert.comment = f"{linked_alert.comment}\nAlert reopened. {note}".strip()
                _update_alert_workflow_state(
                    linked_alert,
                    AlertStatus.NEW,
                    "Alert reopened for active triage in local-dev mode.",
                    "Resume investigation and validate current scope.",
                )
        else:
            context = data_return(400, {}, "失败", "Unsupported local-dev response action")
            return Response(context, status=400)

        entry = _append_audit_entry(
            _make_audit_entry(
                action=action,
                target_type=target_type,
                target_rowid=target_rowid,
                details={
                    "summary": summary,
                    "note": note,
                    "linked_case": getattr(linked_case, "rowid", None),
                },
            )
        )

        response_job = _append_response_job(
            _make_response_job(
                action=action,
                target_type=target_type,
                target_rowid=target_rowid,
                outputs={
                    "summary": summary,
                    "note": note,
                    "linked_case": getattr(linked_case, "rowid", None),
                    "linked_alert": getattr(linked_alert, "rowid", None),
                },
            )
        )

        context = data_return(
            200,
            {
                "audit_entry": _serialize_audit_entry(entry),
                "response_job": _serialize_response_job(response_job),
            },
            "成功",
            "Success",
        )
        return Response(context)


class LocalDevFIMScanView(BaseView):
    def create(self, request, pk=None, **kwargs):
        _require_local_dev_api()
        counts_before = _get_store_counts()
        result = generate_fim_demo()
        counts_after = _get_store_counts()
        entry = _append_audit_entry(
            _make_audit_entry(
                action="fim_scan",
                target_type="scan",
                target_rowid="local-fim",
                details={
                    "summary": f"Generated {result['generated_alerts']} FIM alerts across {len(result['assets_touched'])} assets.",
                    **result,
                },
            )
        )
        context = data_return(
            200,
            {
                **result,
                "counts_before": counts_before,
                "counts_after": counts_after,
                "processed_delta": {
                    "alerts": counts_after["alerts"] - counts_before["alerts"],
                    "cases": counts_after["cases"] - counts_before["cases"],
                    "playbooks": counts_after["playbooks"] - counts_before["playbooks"],
                    "messages": counts_after["messages"] - counts_before["messages"],
                },
                "audit_entry": _serialize_audit_entry(entry),
            },
            "成功",
            "Success",
        )
        return Response(context)


class LocalDevVulnerabilityScanView(BaseView):
    def create(self, request, pk=None, **kwargs):
        _require_local_dev_api()
        counts_before = _get_store_counts()
        result = generate_vulnerability_demo()
        counts_after = _get_store_counts()
        entry = _append_audit_entry(
            _make_audit_entry(
                action="vulnerability_scan",
                target_type="scan",
                target_rowid="local-vuln",
                details={
                    "summary": f"Generated {result['generated_alerts']} vulnerability alerts across {len(result['assets_touched'])} assets.",
                    **result,
                },
            )
        )
        context = data_return(
            200,
            {
                **result,
                "counts_before": counts_before,
                "counts_after": counts_after,
                "processed_delta": {
                    "alerts": counts_after["alerts"] - counts_before["alerts"],
                    "cases": counts_after["cases"] - counts_before["cases"],
                    "playbooks": counts_after["playbooks"] - counts_before["playbooks"],
                    "messages": counts_after["messages"] - counts_before["messages"],
                },
                "audit_entry": _serialize_audit_entry(entry),
            },
            "成功",
            "Success",
        )
        return Response(context)


class LocalDevDemoAlertsView(BaseView):
    def create(self, request, pk=None, **kwargs):
        _require_local_dev_api()
        counts_before = _get_store_counts()
        result = runpy.run_path(str(PHISHING_MOCK_SCRIPT), run_name="__main__")
        generated_records = result.get("mail_records", [])
        deadline = time.time() + 8
        counts_after = counts_before

        while time.time() < deadline:
            counts_after = _get_store_counts()
            if counts_after["alerts"] > counts_before["alerts"]:
                break
            time.sleep(1)

        if counts_after["alerts"] == counts_before["alerts"]:
            _run_local_demo_fallback(generated_records)
            counts_after = _get_store_counts()

        context = data_return(
            200,
            {
                "generated_alerts": len(generated_records),
                "stream": "ES-Rule-21-Phishing-User-Report-Mail",
                "processing_hint_seconds": 4,
                "counts_before": counts_before,
                "counts_after": counts_after,
                "processed_delta": {
                    "alerts": counts_after["alerts"] - counts_before["alerts"],
                    "cases": counts_after["cases"] - counts_before["cases"],
                    "playbooks": counts_after["playbooks"] - counts_before["playbooks"],
                    "messages": counts_after["messages"] - counts_before["messages"],
                },
            },
            "成功",
            "Success",
        )
        return Response(context)
