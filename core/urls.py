from django.urls import path, include
from rest_framework import routers

from core.views import (
    SignupView, LoginView, TenantViewSet, CheckTenantExist
)

router = routers.SimpleRouter()
router.register('tenant', TenantViewSet, basename='tenant')

urlpatterns = [
    path('exist/', CheckTenantExist.as_view(), name='check_tenant_exist'),
    path('auth/signup/', SignupView.as_view(), name='signup-view'),
    path('auth/login/', LoginView.as_view(), name='login-view'),

    path('', include(router.urls))
]

