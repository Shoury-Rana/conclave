import urllib.parse

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.conf import settings
from django.db.models import Q
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from chats.models import ChatRooms
from core.contexts import _current_tenant_id
from core.models import Tenant


class WebSocketScopeMiddleware(BaseMiddleware):
    """
    Authenticates WebSocket connections using JWT tokens passed via
    query string, Authorization header, or sec-websocket-protocol.
    Resolves tenant context and requested room identifiers.
    """

    async def __call__(self, scope, receive, send):
        headers = dict(scope.get("headers", []))
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = urllib.parse.parse_qs(query_string)

        token = None
        if "token" in query_params:
            token = query_params["token"][0]
        elif b"authorization" in headers:
            auth_header = headers[b"authorization"].decode("utf-8").strip()
            if auth_header.lower().startswith("bearer "):
                token = auth_header[7:].strip()

        subprotocol = headers.get(b"sec-websocket-protocol", b"").decode("utf-8")
        if subprotocol:
            protocols = [p.strip() for p in subprotocol.split(",")]
            for p in protocols:
                if p.startswith("access_token:"):
                    token = p.split("access_token:")[1].strip()
                elif p.startswith("room_id:"):
                    scope["room_id"] = p.split("room_id:")[1].strip()
                elif p.startswith("room_name:"):
                    scope["room_name"] = p.split("room_name:")[1].strip()
                elif not token and p and not p.startswith("room_"):
                    token = p

        if "room_id" in query_params:
            scope["room_id"] = query_params["room_id"][0]
        if "room_name" in query_params:
            scope["room_name"] = query_params["room_name"][0]

        if token:
            scope["user"] = await self.is_valid_user(token)

        tenant_token = await self.process_tenant(headers, query_params, scope)

        if tenant_token:
            try:
                return await super().__call__(scope, receive, send)
            finally:
                _current_tenant_id.reset(tenant_token)

        return await super().__call__(scope, receive, send)

    async def is_valid_user(self, access_token):
        authenticator = JWTAuthentication()

        try:
            validated_token = await sync_to_async(authenticator.get_validated_token)(
                access_token
            )
            user = await sync_to_async(authenticator.get_user)(validated_token)
            return user
        except (InvalidToken, TokenError, Exception):
            return None

    async def process_tenant(self, headers, query_params, scope):
        host = headers.get(b"host", b"").decode("utf-8")
        host_parts = host.split(":")[0].split(".")
        base_domain_length = int(getattr(settings, "BASE_DOMAIN_LENGTH", 2))

        tenant = None
        if len(host_parts) == base_domain_length + 1:
            subdomain = host_parts[0]
            tenant = await database_sync_to_async(
                Tenant.objects.filter(name__iexact=subdomain).first
            )()

        if not tenant and b"x-tenant" in headers:
            tenant_hdr = headers[b"x-tenant"].decode("utf-8").strip()
            tenant = await database_sync_to_async(
                Tenant.objects.filter(
                    Q(name__iexact=tenant_hdr) | Q(id__iexact=tenant_hdr)
                ).first
            )()

        if not tenant and "tenant" in query_params:
            tenant_param = query_params["tenant"][0].strip()
            tenant = await database_sync_to_async(
                Tenant.objects.filter(
                    Q(name__iexact=tenant_param) | Q(id__iexact=tenant_param)
                ).first
            )()

        # Fallback: resolve tenant from requested room_id
        if not tenant and scope.get("room_id"):
            room = await database_sync_to_async(
                ChatRooms.objects.filter(id=scope["room_id"])
                .select_related("tenant")
                .first
            )()
            if room:
                tenant = room.tenant

        if tenant:
            scope["tenant"] = tenant
            scope["tenant_id"] = str(tenant.id)
            return _current_tenant_id.set(tenant.id)

        return None