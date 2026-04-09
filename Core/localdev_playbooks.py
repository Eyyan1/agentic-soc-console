LOCAL_DEFAULT_CASE_PLAYBOOK = "L3 SOC Analyst Agent With Tools"
LOCAL_PHISHING_CASE_PLAYBOOK = "Phishing Investigation Playbook"
LOCAL_FIM_CASE_PLAYBOOK = "File Integrity Investigation Playbook"
LOCAL_VULNERABILITY_CASE_PLAYBOOK = "Vulnerability Remediation Playbook"


def select_local_case_playbook_name(rule_id: str | None = None, title: str | None = None, product_category: str | None = None) -> str:
    rule_value = str(rule_id or "")
    title_value = str(title or "").lower()
    category_value = str(product_category or "").lower()

    if rule_value == "ES-Rule-21-Phishing-User-Report-Mail" or "phishing" in title_value:
        return LOCAL_PHISHING_CASE_PLAYBOOK
    if rule_value.startswith("FIM-Rule"):
        return LOCAL_FIM_CASE_PLAYBOOK
    if rule_value.startswith("VULN-Rule") or "vulnerability" in title_value or "cve" in title_value:
        return LOCAL_VULNERABILITY_CASE_PLAYBOOK
    if "edr" in category_value or "ndr" in category_value:
        return LOCAL_DEFAULT_CASE_PLAYBOOK
    return LOCAL_DEFAULT_CASE_PLAYBOOK
