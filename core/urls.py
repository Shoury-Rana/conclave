from django.urls import path
from core.views import (
    SignupView,
    LoginView,
    MeView,
    UserProfileView,
    ListCreateTenantView,
    MyTenantsListView,
    SearchTenantsView,
    JoinTenantView,
    TenantDetailView,
    TenantSettingView,
    WorkspaceMembersListView,
    InviteMemberView,
    UserInvitationsListView,
    RespondInvitationView,
    WorkspaceJoinRequestsView,
    RespondJoinRequestView,
)

urlpatterns = [
    # Auth & Identity
    path("auth/signup/", SignupView.as_view(), name="signup-view"),
    path("auth/login/", LoginView.as_view(), name="login-view"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("profile/me/", MeView.as_view(), name="profile-me"),
    path("profile/<str:pk>/", UserProfileView.as_view(), name="user-profile-view"),
    # Global Tenant Operations (Root Domain)
    path("tenant/", ListCreateTenantView.as_view(), name="list-create-tenant"),
    path("tenant/mine/", MyTenantsListView.as_view(), name="my-tenants"),
    path("tenant/search/", SearchTenantsView.as_view(), name="search-tenants"),
    path("tenant/join/", JoinTenantView.as_view(), name="join-tenant"),
    path(
        "tenant/invitations/",
        UserInvitationsListView.as_view(),
        name="user-invitations",
    ),
    path(
        "tenant/invitations/<uuid:pk>/respond/",
        RespondInvitationView.as_view(),
        name="respond-invitation",
    ),
    # Workspace Scoped Operations (Subdomain)
    path("", TenantDetailView.as_view(), name="tenant-detail-view"),
    path("setting/", TenantSettingView.as_view(), name="tenant-setting"),
    path("members/", WorkspaceMembersListView.as_view(), name="workspace-members"),
    path("invite/", InviteMemberView.as_view(), name="invite-member"),
    path("requests/", WorkspaceJoinRequestsView.as_view(), name="workspace-requests"),
    path(
        "requests/<uuid:pk>/respond/",
        RespondJoinRequestView.as_view(),
        name="respond-request",
    ),
]
