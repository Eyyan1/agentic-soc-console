import json
import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

from Core.localdev_playbooks import select_local_case_playbook_name
from Lib.configs import get_local_data_path
from PLUGINS.SIRP.nocolymodel import Group
from PLUGINS.SIRP.sirpapi import Alert, Case, Playbook
from PLUGINS.SIRP.sirpmodel import (
    AlertModel,
    AlertStatus,
    ArtifactModel,
    ArtifactRole,
    ArtifactType,
    CaseModel,
    CasePriority,
    CaseStatus,
    Confidence,
    PlaybookType,
    ProductCategory,
    Severity,
)

LOCAL_ASSET_INVENTORY_PATH = Path(get_local_data_path("local_asset_inventory.json"))

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _minutes_ago(minutes: int) -> str:
    return _iso(_now() - timedelta(minutes=minutes))


def _today_bucket() -> str:
    return _now().strftime("%Y-%m-%d")


DEFAULT_ASSETS = [
    {
        "rowid": "asset-fin-ws-01",
        "agent_id": "agent-fin-ws-01",
        "hostname": "fin-ws-01",
        "ip_address": "10.10.20.11",
        "owner": "finance@company.local",
        "site": "hq-finance",
        "criticality": "High",
        "status": "Online",
        "isolation_state": "Connected",
        "last_seen": _minutes_ago(2),
        "operating_system": "Windows 11 Enterprise",
        "tags": ["finance", "workstation", "sensitive"],
        "software_inventory": [
            {"name": "7-Zip", "version": "22.01"},
            {"name": "OpenSSL", "version": "1.1.1k"},
            {"name": "Microsoft Office", "version": "2024.2401"},
        ],
        "vulnerabilities": [],
        "blocked_indicators": [],
        "integrity_findings": [],
    },
    {
        "rowid": "asset-edge-proxy-01",
        "agent_id": "agent-edge-proxy-01",
        "hostname": "edge-proxy-01",
        "ip_address": "10.10.10.5",
        "owner": "platform@company.local",
        "site": "hq-dmz",
        "criticality": "Critical",
        "status": "Online",
        "isolation_state": "Connected",
        "last_seen": _minutes_ago(1),
        "operating_system": "Ubuntu 22.04 LTS",
        "tags": ["dmz", "proxy", "internet-facing"],
        "software_inventory": [
            {"name": "Nginx", "version": "1.22.0"},
            {"name": "OpenSSH", "version": "8.9p1"},
            {"name": "OpenSSL", "version": "3.0.2"},
        ],
        "vulnerabilities": [],
        "blocked_indicators": [],
        "integrity_findings": [],
    },
    {
        "rowid": "asset-db-core-01",
        "agent_id": "agent-db-core-01",
        "hostname": "db-core-01",
        "ip_address": "10.10.30.20",
        "owner": "dba@company.local",
        "site": "hq-datacenter",
        "criticality": "Critical",
        "status": "Online",
        "isolation_state": "Not Applicable",
        "last_seen": _minutes_ago(4),
        "operating_system": "Ubuntu 20.04 LTS",
        "tags": ["database", "crown-jewel"],
        "software_inventory": [
            {"name": "PostgreSQL", "version": "13.8"},
            {"name": "glibc", "version": "2.31"},
            {"name": "OpenSSL", "version": "1.1.1f"},
        ],
        "vulnerabilities": [],
        "blocked_indicators": [],
        "integrity_findings": [],
    },
]


def _ensure_runtime_dir() -> None:
    LOCAL_ASSET_INVENTORY_PATH.parent.mkdir(parents=True, exist_ok=True)


def _save_assets(assets: list[dict]) -> None:
    _ensure_runtime_dir()
    LOCAL_ASSET_INVENTORY_PATH.write_text(json.dumps(assets, ensure_ascii=False, indent=2), encoding="utf-8")


def list_assets() -> list[dict]:
    _ensure_runtime_dir()
    if not LOCAL_ASSET_INVENTORY_PATH.exists():
        _save_assets([])
    try:
        assets = json.loads(LOCAL_ASSET_INVENTORY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        assets = []
        _save_assets(assets)
    return assets


def get_asset(rowid: str) -> dict | None:
    for asset in list_assets():
        if asset.get("rowid") == rowid:
            return asset
    return None


def _find_asset_index(assets: list[dict], hostname: str | None = None, rowid: str | None = None, owner: str | None = None) -> int | None:
    for index, asset in enumerate(assets):
        if rowid and asset.get("rowid") == rowid:
            return index
        if hostname and asset.get("hostname") == hostname:
            return index
        if owner and asset.get("owner") == owner:
            return index
    return None


def _write_asset_update(asset: dict) -> dict:
    assets = list_assets()
    index = _find_asset_index(assets, rowid=asset.get("rowid"))
    if index is None:
        assets.append(asset)
    else:
        assets[index] = asset
    _save_assets(assets)
    return asset


def update_asset_state(hostname: str | None = None, rowid: str | None = None, owner: str | None = None, **changes) -> dict | None:
    assets = list_assets()
    index = _find_asset_index(assets, hostname=hostname, rowid=rowid, owner=owner)
    if index is None:
        return None

    asset = assets[index]
    asset.update(changes)
    asset["last_seen"] = _iso(_now())
    assets[index] = asset
    _save_assets(assets)
    return asset


def _append_unique(asset: dict, field: str, item: dict) -> None:
    values = list(asset.get(field) or [])
    if item not in values:
        values.append(item)
    asset[field] = values


def _make_artifact(artifact_type, role, value: str, name: str) -> ArtifactModel:
    return ArtifactModel(
        type=artifact_type,
        role=role,
        value=value,
        name=name,
    )


def _queue_case_playbook(case_rowid: str, user_input: str, rule_id: str | None = None, title: str | None = None, product_category: str | None = None) -> str:
    playbook = Playbook.add_pending_playbook(
        type=PlaybookType.CASE,
        name=select_local_case_playbook_name(rule_id=rule_id, title=title, product_category=product_category),
        source_rowid=case_rowid,
        user_input=user_input,
    )
    return playbook.rowid


def _ensure_case(alert_rowid: str, alert_model: AlertModel, title: str, description: str, correlation_uid: str, tags: list[str]) -> tuple[str, bool]:
    existing_cases = Case.list_by_correlation_uid(correlation_uid, lazy_load=True)
    if existing_cases:
        case_model = existing_cases[0]
        linked_alerts = list(case_model.alerts or [])
        if alert_rowid not in linked_alerts:
            Case.update(CaseModel(rowid=case_model.rowid, alerts=[*linked_alerts, alert_rowid]))
        return case_model.rowid, False

    case_model = CaseModel(
        title=title,
        severity=alert_model.severity,
        priority=CasePriority.CRITICAL if str(alert_model.severity) == "Critical" else CasePriority.HIGH,
        confidence=alert_model.confidence,
        status=CaseStatus.NEW,
        category=alert_model.product_category,
        description=description,
        correlation_uid=correlation_uid,
        alerts=[alert_rowid],
        tags=tags,
        summary="Automatically generated by local-dev SOC module.",
    )
    return Case.create(case_model), True


def _persist_alert_and_case(alert_model: AlertModel, case_title: str, case_description: str, correlation_uid: str, tags: list[str], playbook_note: str) -> dict:
    alert_model.correlation_uid = correlation_uid
    alert_rowid = Alert.create(alert_model)
    case_rowid, created_case = _ensure_case(alert_rowid, alert_model, case_title, case_description, correlation_uid, tags)
    playbook_rowid = _queue_case_playbook(
        case_rowid,
        playbook_note,
        rule_id=alert_model.rule_id,
        title=alert_model.title,
        product_category=alert_model.product_category,
    ) if created_case else None
    return {
        "alert_rowid": alert_rowid,
        "case_rowid": case_rowid,
        "playbook_rowid": playbook_rowid,
        "created_case": created_case,
    }


def generate_fim_demo() -> dict:
    scenarios = [
        {
            "asset_rowid": "asset-fin-ws-01",
            "title": "Critical startup script modified on finance workstation",
            "severity": Severity.HIGH,
            "rule_id": "FIM-Rule-01-Critical-System-File-Changed",
            "file_path": r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup\invoice_updater.ps1",
            "user": "finance@company.local",
            "sha256": "80bd0e8d32c4f1f05f8c934b53d5a8d1d2a0a6c8707b854bc1f5ad4be5a81291",
            "old_sha256": "e1c52e45e47b5d91dd2b157db95e44bd91c4067f2858ab49f1b4e4c27d23f577",
            "summary": "Startup folder PowerShell script changed outside approved deployment window.",
        },
        {
            "asset_rowid": "asset-edge-proxy-01",
            "title": "Web root file drift detected on internet-facing proxy",
            "severity": Severity.CRITICAL,
            "rule_id": "FIM-Rule-02-Web-Root-Drift",
            "file_path": "/var/www/html/uploads/invoice-review.php",
            "user": "www-data",
            "sha256": "90d44527ff995c830c2e37c95a1a6e8b5af7d3e6dc5fef7d5f1245792a5a3d22",
            "old_sha256": "baseline-missing",
            "summary": "Internet-facing upload path contains a newly created executable PHP file.",
        },
    ]

    results = []
    touched_assets = []
    created_cases = 0
    queued_playbooks = 0

    for scenario in scenarios:
        asset = get_asset(scenario["asset_rowid"])
        if not asset:
            continue

        raw_event = {
            "event_type": "fim",
            "hostname": asset["hostname"],
            "agent_id": asset["agent_id"],
            "path": scenario["file_path"],
            "user": scenario["user"],
            "action": "modified",
            "sha256": scenario["sha256"],
            "old_sha256": scenario["old_sha256"],
            "site": asset["site"],
            "criticality": asset["criticality"],
            "ts": _iso(_now()),
        }

        alert_model = AlertModel(
            title=scenario["title"],
            severity=scenario["severity"],
            confidence=Confidence.HIGH,
            status=AlertStatus.NEW,
            rule_id=scenario["rule_id"],
            rule_name="File Integrity Monitoring",
            product_category=ProductCategory.EDR,
            product_name="Local FIM Agent",
            product_vendor="Agentic SOC",
            first_seen_time=_iso(_now()),
            desc=scenario["summary"],
            summary_ai=scenario["summary"],
            comment_ai="File integrity deviation requires analyst verification.",
            labels=["fim", "file-integrity-monitoring", "local-dev"],
            data_sources=["Endpoint Agent", "FIM"],
            raw_data=json.dumps(raw_event),
            source_uid=f"fim-{asset['hostname']}-{int(time.time())}",
        )
        alert_model.artifacts = [
            _make_artifact(ArtifactType.HOSTNAME, ArtifactRole.TARGET, asset["hostname"], "Affected host"),
            _make_artifact(ArtifactType.USER_NAME, ArtifactRole.ACTOR, scenario["user"], "Observed user"),
            _make_artifact(ArtifactType.FILE_PATH, ArtifactRole.RELATED, scenario["file_path"], "Modified file"),
            _make_artifact(ArtifactType.HASH, ArtifactRole.RELATED, scenario["sha256"], "Observed SHA256"),
        ]

        correlation_uid = f"fim|{asset['hostname']}|{scenario['rule_id']}|{_today_bucket()}"
        persisted = _persist_alert_and_case(
            alert_model=alert_model,
            case_title=f"FIM drift on {asset['hostname']}",
            case_description=scenario["summary"],
            correlation_uid=correlation_uid,
            tags=["local-dev", "fim", asset["hostname"]],
            playbook_note="Auto-queued from local FIM scan",
        )

        asset["status"] = "Attention"
        asset["last_seen"] = _iso(_now())
        _append_unique(
            asset,
            "integrity_findings",
            {
                "path": scenario["file_path"],
                "severity": str(scenario["severity"]),
                "observed_at": _iso(_now()),
                "alert_rowid": persisted["alert_rowid"],
            },
        )
        _write_asset_update(asset)

        touched_assets.append(asset["rowid"])
        created_cases += 1 if persisted["created_case"] else 0
        queued_playbooks += 1 if persisted["playbook_rowid"] else 0
        results.append(persisted)

    return {
        "generated_alerts": len(results),
        "created_cases": created_cases,
        "queued_playbooks": queued_playbooks,
        "assets_touched": touched_assets,
    }


def generate_vulnerability_demo() -> dict:
    cve_catalog = {
        "OpenSSL": {
            "cve": "CVE-2026-12001",
            "severity": Severity.CRITICAL,
            "cvss": 9.8,
            "summary": "OpenSSL remote code execution vulnerability affecting legacy TLS handling.",
            "fixed_in": "3.0.15",
        },
        "Nginx": {
            "cve": "CVE-2026-22014",
            "severity": Severity.HIGH,
            "cvss": 8.1,
            "summary": "Nginx request smuggling issue on reverse proxy deployments.",
            "fixed_in": "1.24.1",
        },
        "glibc": {
            "cve": "CVE-2026-33177",
            "severity": Severity.HIGH,
            "cvss": 8.4,
            "summary": "glibc resolver flaw can lead to controlled memory corruption.",
            "fixed_in": "2.39",
        },
    }

    results = []
    touched_assets = []
    created_cases = 0
    queued_playbooks = 0

    for asset in list_assets():
        for package in asset.get("software_inventory", []):
            advisory = cve_catalog.get(package.get("name"))
            if not advisory:
                continue

            raw_event = {
                "event_type": "vulnerability",
                "hostname": asset["hostname"],
                "agent_id": asset["agent_id"],
                "package": package["name"],
                "installed_version": package["version"],
                "cve": advisory["cve"],
                "cvss": advisory["cvss"],
                "fixed_in": advisory["fixed_in"],
                "summary": advisory["summary"],
                "ts": _iso(_now()),
            }

            alert_model = AlertModel(
                title=f"{asset['hostname']} exposed to {advisory['cve']}",
                severity=advisory["severity"],
                confidence=Confidence.HIGH,
                status=AlertStatus.NEW,
                rule_id="VULN-Rule-01-CVE-Correlation",
                rule_name="Software inventory to CVE correlation",
                product_category=ProductCategory.EDR,
                product_name="Local Vulnerability Detector",
                product_vendor="Agentic SOC",
                first_seen_time=_iso(_now()),
                desc=advisory["summary"],
                summary_ai=f"{package['name']} {package['version']} is below the fixed version {advisory['fixed_in']}.",
                comment_ai="Patch validation and containment review recommended.",
                labels=["vulnerability", "cve", "local-dev"],
                data_sources=["Software Inventory", "Vulnerability Feed"],
                raw_data=json.dumps(raw_event),
                source_uid=f"vuln-{asset['hostname']}-{advisory['cve']}",
            )
            alert_model.artifacts = [
                _make_artifact(ArtifactType.HOSTNAME, ArtifactRole.TARGET, asset["hostname"], "Affected host"),
                _make_artifact(ArtifactType.CVE, ArtifactRole.RELATED, advisory["cve"], "Linked CVE"),
                _make_artifact(ArtifactType.RESOURCE, ArtifactRole.RELATED, package["name"], "Affected software"),
            ]

            correlation_uid = f"vuln|{asset['hostname']}|{advisory['cve']}"
            persisted = _persist_alert_and_case(
                alert_model=alert_model,
                case_title=f"Vulnerability exposure on {asset['hostname']}",
                case_description=advisory["summary"],
                correlation_uid=correlation_uid,
                tags=["local-dev", "vulnerability", asset["hostname"]],
                playbook_note="Auto-queued from local vulnerability scan",
            )

            vulnerability_entry = {
                "cve": advisory["cve"],
                "severity": str(advisory["severity"]),
                "cvss": advisory["cvss"],
                "package": package["name"],
                "installed_version": package["version"],
                "fixed_in": advisory["fixed_in"],
                "alert_rowid": persisted["alert_rowid"],
                "detected_at": _iso(_now()),
            }
            _append_unique(asset, "vulnerabilities", vulnerability_entry)
            asset["status"] = "Attention"
            asset["last_seen"] = _iso(_now())
            _write_asset_update(asset)

            touched_assets.append(asset["rowid"])
            created_cases += 1 if persisted["created_case"] else 0
            queued_playbooks += 1 if persisted["playbook_rowid"] else 0
            results.append(persisted)
            break

    return {
        "generated_alerts": len(results),
        "created_cases": created_cases,
        "queued_playbooks": queued_playbooks,
        "assets_touched": touched_assets,
    }
