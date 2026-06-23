import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Conclave.settings')

application = get_asgi_application()


# TODO: Use Daphne instead of uvicorn for performance