from rest_framework import permissions
from core.contexts import get_current_tenant_id


class IsCreator(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.created_by == request.user