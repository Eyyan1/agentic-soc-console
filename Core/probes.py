import datetime
import os

from django.http import JsonResponse


def root_probe(_request):
    return JsonResponse(
        {
            "status": "ok",
            "service": "agentic-soc-console",
            "mode": "local-demo" if os.getenv("ASF_LOCAL_SIRP", "0") == "1" else "standard",
            "time": datetime.datetime.utcnow().isoformat() + "Z",
        }
    )
