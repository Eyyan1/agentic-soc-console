import os


ELK_HOST = os.getenv("ELK_HOST", "http://localhost:9200")
ELK_USER = os.getenv("ELK_USER", "elastic")
ELK_PASS = os.getenv("ELK_PASS", "changeme")
ACTION_INDEX_NAME = os.getenv("ACTION_INDEX_NAME", "siem-alert")
POLL_INTERVAL_MINUTES = int(os.getenv("ACTION_POLL_INTERVAL_MINUTES", "5"))
