from PLAYBOOKS.CASE.L3_SOC_Analyst_Agent_With_Tools import Playbook as BasePlaybook


class Playbook(BasePlaybook):
    NAME = "File Integrity Investigation Playbook"
    DESC = "Specialized local-dev playbook for FIM drift, suspicious file changes, and containment."
    DATA_DIR_CANDIDATES = ["Case_L3_SOC_Analyst_Agent_With_Tools"]
