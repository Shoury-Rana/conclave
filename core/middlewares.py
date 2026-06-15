from django.conf import settings

from core.models import Tenant


class SubDomainMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host_parts = request.get_host().split(':')[0].split('.')
        expected_length = int(settings.DOMAIN_LENGTH_AFTER_HTTPS)
        if len(host_parts) <= expected_length:
            subdomain = host_parts[0]

            tenant = Tenant.objects.filter(name__iexact=subdomain).first()
            if tenant:
                request.tenant = tenant
            request.tenant_name = subdomain
        else:
            print('Configure domain properly.')

        response = self.get_response(request)
        return response
