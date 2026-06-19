import contextvars

_current_tenant_id = contextvars.ContextVar('tenant_id', default=None)

def set_current_tenant_id(tenant_id):
    _current_tenant_id.set(tenant_id)

def get_current_tenant_id():
    _current_tenant_id.get()

