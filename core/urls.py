from django.urls import path

from core.views import (
    SignupView, LoginView, UserProfileView,
    ListCreateTenantView
)

urlpatterns = [
    # Auth
    path('auth/signup/', SignupView.as_view(), name='signup-view'),
    path('auth/login/', LoginView.as_view(), name='login-view'),
    path('profile/<name>/', UserProfileView.as_view(), name='user-profile-view'),

    # Tenants
    path('tenant/', ListCreateTenantView.as_view(), name='list-create-tenant')
]