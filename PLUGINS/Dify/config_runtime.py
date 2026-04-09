import os
import json


DIFY_BASE_URL = os.getenv("DIFY_BASE_URL", "http://127.0.0.1/v1")
DIFY_PROXY = os.getenv("DIFY_PROXY") or None

try:
    DIFY_API_KEY = json.loads(os.getenv("DIFY_API_KEY_JSON", "{}"))
except json.JSONDecodeError:
    DIFY_API_KEY = {}
