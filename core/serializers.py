from rest_framework import serializers
from django_redis import get_redis_connection
from core.models import User, Tenant, Profile, TenantInvitation, TenantJoinRequest


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    name = serializers.CharField(max_length=150)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class TenantSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = ["id", "name", "is_public", "creation_date", "member_count"]

    def get_member_count(self, obj):
        return obj.members.count()


class MeSerializer(serializers.ModelSerializer):
    tenants_joined = TenantSerializer(many=True, read_only=True)
    tenants_owned = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "date_joined",
            "tenants_joined",
            "tenants_owned",
        ]

    def get_tenants_owned(self, obj):
        return TenantSerializer(obj.creator.all(), many=True).data


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "date_joined"]
        read_only_fields = ["id", "email", "date_joined"]


class ListCreateTenantSerializer(serializers.ModelSerializer):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Tenant
        fields = ["id", "name", "is_public", "created_by", "creation_date"]
        read_only_fields = ["id", "creation_date"]


class MemberSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    name = serializers.CharField(source="user.name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    is_online = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            "id",
            "user_id",
            "name",
            "email",
            "username",
            "role",
            "tags",
            "joined_at",
            "is_online",
        ]

    def get_is_online(self, obj):
        try:
            redis_conn = get_redis_connection("default")
            return bool(redis_conn.get(f"user:{obj.user_id}:is_online"))
        except Exception:
            return False


class TenantDetailSerializer(serializers.ModelSerializer):
    members = MemberSerializer(many=True, read_only=True)
    owner = serializers.CharField(source="created_by.name", read_only=True)
    member_count = serializers.SerializerMethodField()
    room_count = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = [
            "id",
            "name",
            "is_public",
            "owner",
            "creation_date",
            "member_count",
            "room_count",
            "members",
        ]

    def get_member_count(self, obj):
        return obj.members.count()

    def get_room_count(self, obj):
        return obj.chat_rooms.count()


class TenantSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ["id", "name", "is_public", "last_update"]
        read_only_fields = ["id", "last_update"]


class TenantInvitationSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    invited_by_name = serializers.CharField(source="invited_by.name", read_only=True)
    invited_user_email = serializers.CharField(
        source="invited_user.email", read_only=True
    )

    class Meta:
        model = TenantInvitation
        fields = [
            "id",
            "tenant",
            "tenant_name",
            "invited_user",
            "invited_user_email",
            "invited_by_name",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "tenant", "invited_by", "status", "created_at"]


class TenantJoinRequestSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    user_name = serializers.CharField(source="user.name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = TenantJoinRequest
        fields = [
            "id",
            "tenant",
            "tenant_name",
            "user",
            "user_name",
            "user_email",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "tenant", "user", "status", "created_at"]
