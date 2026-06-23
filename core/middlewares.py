import re

from django.conf import settings
from django.db import transaction, connection
from django.http import Http404, JsonResponse

from core.models import Tenant
from core.contexts import set_current_tenant_id


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
            ('GET', '^/$'),
            ('ANY', '^/admin/.*'),
            ('POST', '^/auth/signup/$'),
            ('POST', '^/auth/login/$'),
            ('GET', '^/profile/username/$'),
            ('GET', '^/api/schema/.*'),
        ]
        for method, route_path in self.IGNORED_PATHS:
            self.ignored_patterns.append((method, re.compile(route_path)))


    def __call__(self, request):
        method = request.method
        path = request.path
        is_ignored = any(route_method == 'ANY' or method == route_method and pattern.match(path)
                         for route_method, pattern in self.ignored_patterns)
        if is_ignored:
            return self.get_response(request)


        host_parts = request.get_host().split(':')[0].split('.')
        base_domain_length = int(settings.BASE_DOMAIN_LENGTH)
        if len(host_parts) == base_domain_length + 1:
            subdomain = host_parts[0]
            tenant = Tenant.objects.filter(name__iexact=subdomain).first()

            if tenant:
                with transaction.atomic():
                    set_current_tenant_id(tenant)

                    with connection.cursor() as cursor:
                        cursor.execute(f"SET LOCAL app.current_tenant = '{tenant.id}';")

                        response = self.get_response(request)
                        return response
            else:
                return JsonResponse({'error': 'Tenant not found.'}, status=400)
        else:
            raise Http404('Where are you trying to even go??')
