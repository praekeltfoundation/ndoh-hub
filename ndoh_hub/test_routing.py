from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token
from urllib.parse import urlencode

from ndoh_hub.routing import TokenAuthMiddleware


class TokenAuthMiddlewareTests(TestCase):
    def test_user_exists(self):
        """
        If the token leads to a valid user, then that user should be added
        to the scope
        """
        user = User.objects.create_user('test')
        token = Token.objects.create(user=user)
        scope = {
            'query_string': urlencode({'token': str(token.key)}).encode(),
        }
        mw = TokenAuthMiddleware(lambda _: None)
        mw(scope)
        self.assertEqual(scope['user'], user)

    def test_no_token(self):
        """
        If the token doesn't exist, then then the user should be set to None
        """
        scope = {
            'query_string': urlencode({'token': 'bad-token'}).encode(),
        }
        mw = TokenAuthMiddleware(lambda _: None)
        mw(scope)
        self.assertEqual(scope['user'], None)

    def test_no_token_provided(self):
        """
        If no token is given in the query string, then the user should be set
        to None
        """
        scope = {
            'query_string': ''.encode(),
        }
        mw = TokenAuthMiddleware(lambda _: None)
        mw(scope)
        self.assertEqual(scope['user'], None)

    def test_blank_token_provided(self):
        """
        If the token provided is blank, then the user should be set to None
        """
        scope = {
            'query_string': urlencode({'token': ''}).encode(),
        }
        mw = TokenAuthMiddleware(lambda _: None)
        mw(scope)
        self.assertEqual(scope['user'], None)
