from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        message = str(getattr(exc, "detail", "")) or "Authentication credentials were not provided."
        response.data = {
            "code": status.HTTP_401_UNAUTHORIZED,
            "data": None,
            "msg_zh": "未提供或无效的认证信息",
            "msg_en": message,
        }
        response.status_code = status.HTTP_401_UNAUTHORIZED

    return response
