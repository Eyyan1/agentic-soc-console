import os


HTTP_PROXY = os.getenv("ALIENVAULT_HTTP_PROXY") or None
API_KEY = os.getenv("ALIENVAULT_API_KEY", "")
