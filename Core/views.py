import datetime
import os

from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.generics import UpdateAPIView, DestroyAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from Core.Handle.currentuser import CurrentUser
from Lib.api import data_return
from Lib.baseview import BaseView
from Lib.configs import get_local_data_dir
from Lib.configs import BASEAUTH_MSG_ZH, BASEAUTH_MSG_EN, EXPIRE_MINUTES
from Lib.log import logger


class BaseAuthView(ModelViewSet, UpdateAPIView, DestroyAPIView):
    queryset = []
    serializer_class = AuthTokenSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    def create(self, request, pk=None, **kwargs):

        null_response = {"status": "error", "type": "account", "currentAuthority": "guest",
                         "token": "forguest"}

        # Get encrypted password and decrypt it
        username = request.data.get('username')
        password = request.data.get('password')

        try:
            serializer = AuthTokenSerializer(data={"username": username, "password": password})
            if serializer.is_valid():
                token, created = Token.objects.get_or_create(user=serializer.validated_data['user'])
                time_now = datetime.datetime.now()
                if created or token.created < time_now - datetime.timedelta(minutes=EXPIRE_MINUTES):
                    # Update creation time to keep token valid
                    token.delete()
                    token = Token.objects.create(user=serializer.validated_data['user'])
                    token.created = time_now
                    token.save()
                null_response['status'] = 'ok'
                null_response['currentAuthority'] = 'admin'  # Currently in single-user mode, default is admin
                null_response['token'] = token.key
                context = data_return(201, null_response, BASEAUTH_MSG_ZH.get(201), BASEAUTH_MSG_EN.get(201))
                return Response(context)
            else:
                context = data_return(301, null_response, BASEAUTH_MSG_ZH.get(301), BASEAUTH_MSG_EN.get(301))
                return Response(context)
        except Exception as E:
            logger.exception(E)
            context = data_return(301, null_response, BASEAUTH_MSG_ZH.get(301), BASEAUTH_MSG_EN.get(301))
            return Response(context)


class CurrentUserView(BaseView):
    def list(self, request, **kwargs):
        """Query host information in the database"""
        user = request.user
        user_info = CurrentUser.list(user)
        context = data_return(301, user_info, BASEAUTH_MSG_ZH.get(301), BASEAUTH_MSG_EN.get(301))
        return Response(context)


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
                "mode": "simulated_only" if flags["ASF_LOCAL_SIRP"] else "backend_defined"
            },
            "time": datetime.datetime.utcnow().isoformat() + "Z",
        }
        context = data_return(200, payload, "成功", "Success")
        return Response(context)
