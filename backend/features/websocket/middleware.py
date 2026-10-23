from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class JwtAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner
        self.jwt_auth = JWTAuthentication()

    async def __call__(self, scope, receive, send):
        scope['user'] = await self._get_user(scope)
        return await self.inner(scope, receive, send)

    async def _get_user(self, scope):
        token = self._get_token_from_scope(scope)
        if not token:
            return AnonymousUser()
        try:
            validated = self.jwt_auth.get_validated_token(token)
            return await database_sync_to_async(self.jwt_auth.get_user)(validated)
        except (InvalidToken, TokenError):
            return AnonymousUser()

    @staticmethod
    def _get_token_from_scope(scope):
        query_string = scope.get('query_string', b'').decode('utf-8')
        query_params = parse_qs(query_string)
        token_list = query_params.get('token') or query_params.get('access')
        if token_list:
            return token_list[0]

        headers = dict(scope.get('headers') or [])
        auth_header = headers.get(b'authorization')
        if auth_header:
            auth_value = auth_header.decode('utf-8')
            parts = auth_value.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                return parts[1]
        return None


def JwtAuthMiddlewareStack(inner):
    return JwtAuthMiddleware(inner)
