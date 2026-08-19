import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Conclave.settings")
django_asgi_app = (
    get_asgi_application()
)  # Must be initialized first so that django can set up before calling apps.

from channels.routing import ProtocolTypeRouter, URLRouter

from chats import routing
from chats.middleware import WebSocketScopeMiddleware

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": WebSocketScopeMiddleware(URLRouter(routing.websocket_urlpatterns)),
    }
)


# TODO: Use Granian or Hypercorn instead of uvicorn` for performance
