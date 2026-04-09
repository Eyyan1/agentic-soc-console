import os


SIRP_URL = os.getenv("SIRP_URL", "http://127.0.0.1:8880")
SIRP_APPKEY = os.getenv("SIRP_APPKEY", "local-appkey")
SIRP_SIGN = os.getenv("SIRP_SIGN", "local-sign")
SIRP_NOTICE_WEBHOOK = os.getenv("SIRP_NOTICE_WEBHOOK", "")
