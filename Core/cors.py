from django.http import HttpResponse


DEFAULT_ALLOWED_ORIGINS = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
}


def _parse_allowed_origins():
    import os

    configured = os.getenv("ASF_ALLOWED_FRONTEND_ORIGINS", "")
    origins = {
        origin.strip().rstrip("/")
        for origin in configured.split(",")
        if origin.strip()
    }
    return DEFAULT_ALLOWED_ORIGINS | origins


class SimpleCorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = (request.headers.get("Origin") or "").rstrip("/")
        allowed_origins = _parse_allowed_origins()
        is_allowed = origin in allowed_origins
        is_preflight = request.method == "OPTIONS" and request.headers.get("Access-Control-Request-Method")

        if is_preflight and is_allowed:
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        if is_allowed:
            response["Access-Control-Allow-Origin"] = origin
            response["Vary"] = "Origin"
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response["Access-Control-Max-Age"] = "86400"

        return response
