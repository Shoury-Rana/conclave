from channels.db import database_sync_to_async
from django.db import connection, transaction
from core.contexts import get_current_tenant_id


def rls_db_sync_to_async(sync_func):
    def sync_wrapper(*args, **kwargs):
        tenant_id = get_current_tenant_id()

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('app.current_tenant', %s, true);",
                    [str(tenant_id)],
                )
            return sync_func(*args, **kwargs)

    return database_sync_to_async(sync_wrapper)
