import contextvars
from contextlib import contextmanager

from django.db import connection, transaction

_current_tenant_id = contextvars.ContextVar("tenant_id", default=None)


def set_current_tenant_id(tenant_id):
    return _current_tenant_id.set(tenant_id)


def get_current_tenant_id():
    return _current_tenant_id.get()


@contextmanager
def tenant_rls_transaction(tenant_id):
    """
    Context manager for applying PostgreSQL RLS safely in root-domain views
    that are bypassed by the SubDomainMiddleware.
    """
    token = _current_tenant_id.set(tenant_id)
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('app.current_tenant', %s, true);",
                    [str(tenant_id)],
                )
            yield
    finally:
        _current_tenant_id.reset(token)