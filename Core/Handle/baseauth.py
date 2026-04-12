import datetime
import os
from types import SimpleNamespace

from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication

from Lib.configs import EXPIRE_MINUTES
from Lib.xcache import Xcache
from Lib.log import logger


DEFAULT_DEMO_TOKEN = "asf-local-demo-token"


class BaseAuth(TokenAuthentication):
    def authenticate_credentials(self, key=None):
        if os.getenv("ASF_LOCAL_SIRP", "0") == "1" and key == os.getenv("ASF_DEMO_AUTH_TOKEN", DEFAULT_DEMO_TOKEN):
            return SimpleNamespace(
                id="local-demo-admin",
                username=os.getenv("ASF_DEMO_ADMIN_USERNAME", "admin"),
                is_active=True,
                is_authenticated=True,
                is_staff=True,
                is_superuser=True,
            ), key

        # search cached user token
        try:
            cache_user = Xcache.alive_token(key)
        except Exception as exc:
            logger.warning(f"Token cache lookup failed, falling back to database auth: {exc}")
            cache_user = None
        if cache_user:
            return cache_user, key

        # search user token in database
        model = self.get_model()
        try:
            token = model.objects.select_related('user').get(key=key)
        except model.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid or expired token.")

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed("User account is inactive.")

        # token timeout clean
        time_now = datetime.datetime.now()
        if token.created < time_now - datetime.timedelta(minutes=EXPIRE_MINUTES):
            token.delete()
            raise exceptions.AuthenticationFailed("Invalid or expired token.")

        # cache token
        if token:
            try:
                Xcache.set_token_user(key, token.user)
            except Exception as exc:
                logger.warning(f"Token cache write failed, continuing without cache: {exc}")
        return token.user, token
