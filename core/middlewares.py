from django.conf import settings
from django.db import transaction, connection
from django.http import Http404
from rest_framework.exceptions import ValidationError

from core.models import Tenant
from core.contexts import set_current_tenant_id


class SubDomainMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        IGNORE_ENDPOINT = (
            'POST:/tenant/',        # Tenant don't have subdomain before creation, so will have to ignore this middleware here
            'POST:/auth/signup/',
            'POST:/auth/login/'
        )
        # maybe can make if efficient by using dict(path, method) and checking
        # for path first and loop over methods to ignore only if path matches
        for endpoint in IGNORE_ENDPOINT:
            method, path = endpoint.split(':')

            if method == request.method or path == request.path:
                response = self.get_response(request)
                return response

        host_parts = request.get_host().split(':')[0].split('.')
        expected_length = int(settings.DOMAIN_LENGTH_AFTER_HTTPS)
        if len(host_parts) == expected_length:
            subdomain = host_parts[0]
            tenant = Tenant.objects.filter(name__iexact=subdomain).first()

            if tenant:
                with transaction.atomic():
                    set_current_tenant_id(tenant)

                    with connection.cursor() as cursor:
                        cursor.execute(f"SET LOCAL app.current_tenant = '{tenant.id}';")

                        response = self.get_response(request)
                        return response

            else:       # Returns 400
                return ValidationError({'error': 'Tenant does not exist.'})
        else:
            return Http404('Where are you trying to even go??')


