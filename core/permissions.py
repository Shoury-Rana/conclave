from rest_framework import permissions
from core.contexts import get_current_tenant_id
from core.models import Tenant, Profile


class IsCreator(permissions.BasePermission):
    def has_permission(self, request, view):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return False
        tenant = Tenant.objects.filter(pk=tenant_id).first()
        return bool(tenant and tenant.created_by == request.user)

    def has_object_permission(self, request, view, obj):
        tenant_id = (
            get_current_tenant_id()
            or getattr(obj, "tenant_id", None)
            or getattr(obj, "id", None)
        )
        tenant = Tenant.objects.filter(pk=tenant_id).first()
        return bool(tenant and tenant.created_by == request.user)


class IsTenantMember(permissions.BasePermission):
    def has_permission(self, request, view):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return False
        return Profile.objects.filter(tenant_id=tenant_id, user=request.user).exists()
