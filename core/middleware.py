import re

from django.conf import settings
from django.db import connection, transaction
from django.db.models import Q
from django.http import Http404, JsonResponse

from core.contexts import _current_tenant_id
from core.models import Tenant


class SubDomainMiddleware:
    """
    Resolves tenant context from request subdomain, X-Tenant header, or query param.
    Configures PostgreSQL RLS session variables when available.
    Bypasses root-domain endpoints (auth, search, my tenants, swagger).
    """

    def __init__(self, get_response):
        self.get_response = get_response

        self.IGNORED_PATHS = [
            ("ANY", r"^/admin(/.*)?$"),
            ("ANY", r"^/api/schema(/.*)?$"),
            ("ANY", r"^/auth(/.*)?$"),
            ("ANY", r"^/profile(/.*)?$"),
            ("ANY", r"^/tenant(/.*)?$"),
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

        tenant_param = request.headers.get("X-Tenant") or request.GET.get("tenant")
        if tenant_param:
            tenant_param = tenant_param.strip()
            tenant = Tenant.objects.filter(
                Q(name__iexact=tenant_param) | Q(id__iexact=tenant_param)
            ).first()
            if not tenant:
                return JsonResponse(
                    {"error": f"Tenant '{tenant_param}' not found."}, status=404
                )
            return self._process_tenant_request(request, tenant)

        # 2. Check Host subdomain
        host = request.get_host().split(":")[0]
        host_parts = host.split(".")
        base_domain_length = int(getattr(settings, "BASE_DOMAIN_LENGTH", 2))

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
        request.tenant = tenant
        try:
            # transaction.atomic() pins the connection to this request so PgBouncer
            # doesn't take it back between queries.
            with transaction.atomic():
                # But this also makes this slow due to sync nature.
                # Not using atomic transaction or transactional mode, can potential
                # lead to not able to put RLS on db calls after first in a single request.
                # for now going with secure way. TODO: later explore other ways which can't block but also is secure
                with connection.cursor() as cursor:
                    # true = transaction scoped. It auto-clears when atomic block ends,
                    # keeping the PgBouncer pool clean.
                    cursor.execute(
                        "SELECT set_config('app.current_tenant', %s, true);",
                        [str(tenant.id)],
                    )
                return self.get_response(request)
        finally:
            _current_tenant_id.reset(token)