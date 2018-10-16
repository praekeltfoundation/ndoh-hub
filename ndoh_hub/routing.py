from urllib.parse import parse_qs

from channels.routing import ProtocolTypeRouter, URLRouter
from django.conf.urls import url
from django.utils.functional import SimpleLazyObject
from rest_framework.authtoken.models import Token

import registrations.consumers as registrations


class TokenAuthMiddleware(object):
    """
    Custom middleware that uses django rest framework auth tokens in the
    querystring
    """

    def __init__(self, inner):
        self.inner = inner

    def get_user(self, scope):
        try:
            token = parse_qs(scope["query_string"])[b"token"][0].decode()
            return Token.objects.select_related("user").get(key=token).user
        except (KeyError, IndexError, Token.DoesNotExist):
            return None

    def __call__(self, scope):
        if "user" not in scope:
            scope["user"] = SimpleLazyObject(lambda: self.get_user(scope))

        return self.inner(scope)


application = ProtocolTypeRouter(
    {
        "websocket": TokenAuthMiddleware(
            URLRouter(
                [
                    url(
                        r"^api/v1/jembiregistration/$",
                        registrations.JembiAppRegistrationConsumer,
                    )
                ]
            )
        )
    }
)
