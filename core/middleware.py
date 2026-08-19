import re

from django.conf import settings
from django.db import transaction, connection
from django.http import Http404, JsonResponse

from core.models import Tenant
from core.contexts import _current_tenant_id


class SubDomainMiddleware:
    """
    Resolves tenant context from request subdomain and configures RLS.
    Bypasses root-domain endpoints (auth, search, my tenants, swagger).
    """

    def __init__(self, get_response):
        self.get_response = get_response

        self.IGNORED_PATHS = [
            ("ANY", r"^/admin/.*"),
            ("ANY", r"^/api/schema/.*"),
            ("ANY", r"^/auth/.*"),
            ("ANY", r"^/profile/.*"),
            ("ANY", r"^/tenant/$"),
            ("ANY", r"^/tenant/mine/.*"),
            ("ANY", r"^/tenant/search/.*"),
            ("ANY", r"^/tenant/join/.*"),
            ("ANY", r"^/tenant/invitations/.*"),
        ]
        self.ignored_patterns = [
            (method, re.compile(pattern)) for method, pattern in self.IGNORED_PATHS
        ]

    def __call__(self, request):
        method = request.method
        path = request.path

        is_ignored = any(
            route_method in ("ANY", method) and pattern.match(path)
            for route_method, pattern in self.ignored_patterns
        )
        if is_ignored:
            return self.get_response(request)

        host_parts = request.get_host().split(":")[0].split(".")
        base_domain_length = int(settings.BASE_DOMAIN_LENGTH)

        if len(host_parts) == base_domain_length:
            if method == "GET" and path == "/":
                return self.get_response(request)
            raise Http404("Invalid Base Domain Route")

        elif len(host_parts) == base_domain_length + 1:
            subdomain = host_parts[0]
            tenant = Tenant.objects.filter(name__iexact=subdomain).first()

            if not tenant:
                return JsonResponse(
                    {"error": f"Tenant '{subdomain}' not found."}, status=404
                )

            return self._process_tenant_request(request, tenant)

        else:
            raise Http404("Invalid Domain Configuration")

    def _process_tenant_request(self, request, tenant):
        token = _current_tenant_id.set(tenant.id)
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT set_config('app.current_tenant', %s, true);",
                        [str(tenant.id)],
                    )
                return self.get_response(request)
        finally:
            _current_tenant_id.reset(token)
