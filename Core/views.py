import datetime
import os

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.generics import DestroyAPIView, UpdateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from Core.Handle.currentuser import CurrentUser
from Lib.baseview import BaseView
from Lib.configs import BASEAUTH_MSG_EN, BASEAUTH_MSG_ZH, EXPIRE_MINUTES, get_local_data_dir
from Lib.log import logger


def _data_return(code=500, data=None, msg_zh="服务器发生错误,请检查服务器", msg_en="An error occurred on the server, please check the server."):
    return {"code": code, "data": data, "msg_zh": msg_zh, "msg_en": msg_en}


def _ensure_local_demo_admin(username: str | None, password: str | None) -> User | None:
    if os.getenv("ASF_LOCAL_SIRP", "0") != "1":
        return None

    demo_username = os.getenv("ASF_DEMO_ADMIN_USERNAME", "admin")
    demo_password = os.getenv("ASF_DEMO_ADMIN_PASSWORD", "admin12345")
    sync_password = os.getenv("ASF_SYNC_DEMO_ADMIN_PASSWORD", "1") == "1"

    if username != demo_username or password != demo_password:
        return None

    user, created = User.objects.get_or_create(
        username=demo_username,
        defaults={
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
        },
    )
    changed = False
    if created or (sync_password and not user.check_password(demo_password)):
        user.set_password(demo_password)
        changed = True
    if not user.is_active:
        user.is_active = True
        changed = True
    if not user.is_staff:
        user.is_staff = True
        changed = True
    if not user.is_superuser:
        user.is_superuser = True
        changed = True
    if changed:
        user.save()
    return user


def _build_login_success(user: User, authority: str = "admin") -> dict:
    token, created = Token.objects.get_or_create(user=user)
    time_now = datetime.datetime.now()
    if created or token.created < time_now - datetime.timedelta(minutes=EXPIRE_MINUTES):
        token.delete()
        token = Token.objects.create(user=user)
        token.created = time_now
        token.save()
    return {
        "status": "ok",
        "type": "account",
        "currentAuthority": authority,
        "token": token.key,
    }


class BaseAuthView(ModelViewSet, UpdateAPIView, DestroyAPIView):
    queryset = []
    serializer_class = AuthTokenSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    def create(self, request, pk=None, **kwargs):
        null_response = {"status": "error", "type": "account", "currentAuthority": "guest", "token": "forguest"}

        username = request.data.get("username")
        password = request.data.get("password")

        try:
            demo_user = _ensure_local_demo_admin(username, password)
            if demo_user is not None:
                context = _data_return(201, _build_login_success(demo_user), BASEAUTH_MSG_ZH.get(201), BASEAUTH_MSG_EN.get(201))
                return Response(context)

            serializer = AuthTokenSerializer(data={"username": username, "password": password})
            if serializer.is_valid():
                context = _data_return(
                    201,
                    _build_login_success(serializer.validated_data["user"]),
                    BASEAUTH_MSG_ZH.get(201),
                    BASEAUTH_MSG_EN.get(201),
                )
                return Response(context)
            context = _data_return(301, null_response, BASEAUTH_MSG_ZH.get(301), BASEAUTH_MSG_EN.get(301))
            return Response(context)
        except Exception as exc:
            logger.exception(exc)
            context = _data_return(301, null_response, BASEAUTH_MSG_ZH.get(301), BASEAUTH_MSG_EN.get(301))
            return Response(context)


class CurrentUserView(BaseView):
    def list(self, request, **kwargs):
        if not getattr(request.user, "is_authenticated", False):
            return Response(
                _data_return(401, None, "未提供或无效的认证信息", "Authentication credentials were not provided."),
                status=401,
            )
        user_info = CurrentUser.list(request.user)
        context = _data_return(200, user_info, "成功", "Success")
        return Response(context, status=200)


class HealthView(BaseView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def list(self, request, **kwargs):
        flags = {
            "ASF_LOCAL_SIRP": os.getenv("ASF_LOCAL_SIRP", "0") == "1",
            "ASF_ENABLE_BACKGROUND_SERVICES": os.getenv("ASF_ENABLE_BACKGROUND_SERVICES", "0") == "1",
            "ASF_FAKE_LLM": os.getenv("ASF_FAKE_LLM", "0") == "1",
            "ASF_DISABLE_EMBEDDINGS": os.getenv("ASF_DISABLE_EMBEDDINGS", "0") == "1",
        }
        payload = {
            "status": "ok",
            "mode": "local-demo" if flags["ASF_LOCAL_SIRP"] else "standard",
            "process_role": os.getenv("ASF_PROCESS_ROLE", "all"),
            "flags": flags,
            "local_data_dir": get_local_data_dir(),
            "response_actions": {
                "mode": "simulated_only" if flags["ASF_LOCAL_SIRP"] else "backend_defined",
            },
            "time": datetime.datetime.utcnow().isoformat() + "Z",
        }
        return Response(_data_return(200, payload, "成功", "Success"))
