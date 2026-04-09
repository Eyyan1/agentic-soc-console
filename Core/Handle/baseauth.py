import datetime

from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication

from Lib.configs import EXPIRE_MINUTES
from Lib.xcache import Xcache
from Lib.log import logger


class BaseAuth(TokenAuthentication):
    def authenticate_credentials(self, key=None):
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
