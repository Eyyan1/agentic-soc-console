import json
import os
import runpy
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
RUNTIME_DIR = ROOT / ".runtime"
LOCAL_SIRP_STORE = RUNTIME_DIR / "local_sirp_store.json"
PHISHING_STREAM = "ES-Rule-21-Phishing-User-Report-Mail"
NDR_STREAM = "NDR-Rule-05-Suspect-C2-Communication"
CLOUD_STREAM = "Cloud-01-AWS-IAM-Privilege-Escalation-via-AttachUserPolicy"


def configure_env():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ASP.settings")
    os.environ["ASF_ENABLE_BACKGROUND_SERVICES"] = "1"
    os.environ["ASF_LOCAL_SIRP"] = "1"
    os.environ["ASF_FAKE_LLM"] = "1"
    os.environ["ASF_DISABLE_EMBEDDINGS"] = "1"
    os.environ.setdefault("PYTHONUNBUFFERED", "1")


def reset_local_state():
    from PLUGINS.Redis.redis_stream_api import RedisStreamAPI

    RUNTIME_DIR.mkdir(exist_ok=True)
    if LOCAL_SIRP_STORE.exists():
        LOCAL_SIRP_STORE.unlink()

    redis_api = RedisStreamAPI()
    for stream_name in [PHISHING_STREAM, NDR_STREAM, CLOUD_STREAM]:
        redis_api.delete_stream(stream_name)


def load_store():
    if not LOCAL_SIRP_STORE.exists():
        return {}
    return json.loads(LOCAL_SIRP_STORE.read_text(encoding="utf-8"))


def print_store_counts(stage: str):
    store = load_store()
    print(f"\n=== {stage} ===", flush=True)
    for key in ["alert", "case", "playbook", "message", "artifact"]:
        print(f"{key}: {len(store.get(key, {}))}", flush=True)


def wait_for_playbook(timeout_seconds: int = 30):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        playbooks = list(load_store().get("playbook", {}).values())
        if playbooks:
            playbook = playbooks[-1]
            if playbook.get("job_status") not in {"Pending", "Running", None, ""}:
                print(f"Playbook finished with status: {playbook.get('job_status')}", flush=True)
                return playbook
        time.sleep(1)
    playbooks = list(load_store().get("playbook", {}).values())
    playbook = playbooks[-1] if playbooks else {}
    print(f"Playbook timed out in state: {playbook.get('job_status')}", flush=True)
    return playbook


def print_record_samples():
    store = load_store()
    latest_alert = list(store.get("alert", {}).values())[-1]
    latest_case = list(store.get("case", {}).values())[-1]
    latest_playbook = list(store.get("playbook", {}).values())[-1]
    messages = list(store.get("message", {}).values())

    print("\n=== Latest Alert ===", flush=True)
    print(json.dumps({
        "rowid": latest_alert.get("rowid"),
        "title": latest_alert.get("title"),
        "severity": latest_alert.get("severity"),
        "confidence": latest_alert.get("confidence"),
        "labels": latest_alert.get("labels"),
    }, indent=2, ensure_ascii=False), flush=True)

    print("\n=== Latest Case ===", flush=True)
    print(json.dumps({
        "rowid": latest_case.get("rowid"),
        "title": latest_case.get("title"),
        "alerts": latest_case.get("alerts"),
        "status": latest_case.get("status"),
        "severity_ai": latest_case.get("severity_ai"),
        "confidence_ai": latest_case.get("confidence_ai"),
    }, indent=2, ensure_ascii=False), flush=True)

    print("\n=== Latest Playbook ===", flush=True)
    print(json.dumps({
        "rowid": latest_playbook.get("rowid"),
        "name": latest_playbook.get("name"),
        "job_status": latest_playbook.get("job_status"),
        "job_id": latest_playbook.get("job_id"),
        "remark": latest_playbook.get("remark"),
    }, indent=2, ensure_ascii=False), flush=True)

    print("\n=== Playbook Messages ===", flush=True)
    for message in messages[-5:]:
        print(json.dumps({
            "rowid": message.get("rowid"),
            "node": message.get("node"),
            "type": message.get("type"),
            "content": message.get("content"),
            "data": message.get("data"),
        }, ensure_ascii=False), flush=True)


def main():
    configure_env()

    import django

    django.setup()

    from Lib.montior import MainMonitor

    reset_local_state()
    monitor = MainMonitor()
    monitor.start()
    print("MainMonitor started in local-dev mode.", flush=True)

    time.sleep(2)
    print("\nRunning bundled mock alert script: DATA/ES-Rule-21-Phishing-User-Report-Mail/mock_alert.py", flush=True)
    runpy.run_path(str(ROOT / "DATA" / "ES-Rule-21-Phishing-User-Report-Mail" / "mock_alert.py"), run_name="__main__")

    time.sleep(8)
    print_store_counts("After Module Processing")

    wait_for_playbook()
    print_store_counts("After Playbook Processing")
    print_record_samples()


if __name__ == "__main__":
    main()
