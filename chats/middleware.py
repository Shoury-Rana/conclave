from asgiref.sync import sync_to_async
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.conf import settings
from core.contexts import _current_tenant_id
from core.models import Tenant
from channels.db import database_sync_to_async


class WebSocketScopeMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        headers = dict(scope.get('headers', {}))

        tenant_token = await self.process_http_headers(headers)
        subprotocol = headers.get(b'sec-websocket-protocol', b'').decode('utf-8')

        if subprotocol:
            protocol = [p.strip() for p in subprotocol.split(',')]

            access_token = (at := next((at for at in protocol if at.startswith('access_token')), None)) and at.split(':')[1]
            user = await self.is_valid_user(access_token)
            if access_token and user is not None:
                scope['user'] = user

            room_name = (rn:= next((rn for rn in protocol if rn.startswith('room_name')), None)) and rn.split(':')[1]
            if room_name:
                scope['room_name'] = room_name

        if tenant_token:
            try:
                return await super().__call__(scope, receive, send)
            finally:
                _current_tenant_id.reset(tenant_token)

        return await super().__call__(scope, receive, send)

    async def is_valid_user(self, access_token):
        authenticator = JWTAuthentication()

        try:
            validated_token = await sync_to_async(authenticator.get_validated_token)(access_token)
            user = await sync_to_async(authenticator.get_user)(validated_token)
            return user
        except (InvalidToken, TokenError):
            return None

    async def process_http_headers(self, headers):

        host = headers.get(b'host', b'').decode('utf-8')
        host_parts = host.split(':')[0].split('.')
        base_domain_length = int(settings.BASE_DOMAIN_LENGTH)

        if len(host_parts) == base_domain_length + 1:
            subdomain = host_parts[0]
            tenant = await database_sync_to_async(Tenant.objects.filter(name__iexact=subdomain).first)()

            if tenant:
                tenant_id = tenant.id
                token = _current_tenant_id.set(tenant_id)
                return token
        else:
            return None