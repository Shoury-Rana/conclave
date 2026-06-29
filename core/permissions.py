from rest_framework import permissions
from core.contexts import get_current_tenant_id
from core.models import Tenant


class IsCreator(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        tenant = get_current_tenant_id()
        if not tenant:
            raise AttributeError('tenant context is None')

        if request.method in permissions.SAFE_METHODS:
            return True
        return Tenant.objects.filter(pk=get_current_tenant_id()).first().created_by == request.user