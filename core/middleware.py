import re

from django.conf import settings
from django.db import transaction, connection
from django.http import Http404, JsonResponse

from core.models import Tenant
from core.contexts import _current_tenant_id, set_current_tenant_id


class SubDomainMiddleware:
    """
    Do following:
    1. Ignores subdomain completely if meant to be ignored (path present in IGNORED_PATHS)
    2. Add subdomain context (i.e., tenant_id to request), and adhere to RLS (according to tenant_id)
    """
    def __init__(self, get_response):
        self.get_response = get_response

        self.ignored_patterns = []
        self.IGNORED_PATHS = [
            ('ANY', '^/admin/.*'),
            ('POST', '^/auth/signup/$'),
            ('POST', '^/auth/login/$'),
            ('GET', '^/profile/.*'),
            ('GET', '^/api/schema/.*'),
            ('GET', '^/tenant/$'),
            ('POST', '^/tenant/$')
        ]
        for method, route_path in self.IGNORED_PATHS:
            self.ignored_patterns.append((method, re.compile(route_path)))


    def __call__(self, request):
        method = request.method
        path = request.path

        is_ignored = any(
            route_method in ('ANY', method) and pattern.match(path)
            for route_method, pattern in self.ignored_patterns
        )
        if is_ignored:
            return self.get_response(request)

        host_parts = request.get_host().split(':')[0].split('.')
        base_domain_length = int(settings.BASE_DOMAIN_LENGTH)

        if len(host_parts) == base_domain_length:
            if method == 'GET' and path == '/':
                return self.get_response(request)
            raise Http404('Invalid Base Domain Route')

        elif len(host_parts) == base_domain_length + 1:
            subdomain = host_parts[0]
            tenant = Tenant.objects.filter(name__iexact=subdomain).first()

            if not tenant:
                return JsonResponse({'error': 'Tenant not found.'}, status=404)

            token = _current_tenant_id.set(tenant.id)
            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute(f"SET LOCAL app.current_tenant = '{tenant.id}';")
                    return self.get_response(request)
            finally:
                _current_tenant_id.reset(token)
        else:
            raise Http404('Invalid Domain Configuration')

