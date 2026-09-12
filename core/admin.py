from django.contrib import admin

from core.models import Profile, Tenant, TenantInvitation, TenantJoinRequest, User


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    pass


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    pass


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    pass


@admin.register(TenantInvitation)
class TenantInvitationAdmin(admin.ModelAdmin):
    pass


@admin.register(TenantJoinRequest)
class TenantJoinRequestAdmin(admin.ModelAdmin):
    pass