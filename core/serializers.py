from django.db.models import Model
from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from core.models import (
    User, Tenant, Profile
)


class SignupSerializer(ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    name = serializers.CharField()

    class Meta:
        model = User
        fields = ['email', 'password', 'name']
        extra_kwargs = {
            'password': {'write_only': True},
        }


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name']


class UserProfileSerializer(ModelSerializer):
    tenant_owned = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['email', 'name', 'tenants_joined', 'tenant_owned']

    def get_tenant_owned(self, obj):
        tenant = obj.creator.all()
        return TenantSerializer(tenant, many=True).data

class ListCreateTenantSerializer(ModelSerializer):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Tenant
        fields = '__all__'
        extra_kwargs = {
            'id': {'read_only': True},
        }


class MemberSerializer(ModelSerializer):
    class Meta:
        model = Profile
        fields = '__all__'


class TenantDetailSerializer(ModelSerializer):
    tenant_details = TenantSerializer(read_only=True)
    members = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    class Meta:
        model = Tenant
        fields = ['tenant_details', 'members', 'owner']

    def get_members(self, obj):
        members = obj.members.all()
        return MemberSerializer(members, many=True).data

    def get_owner(self, obj):
        return obj.created_by.name


class TenantSettingSerializer(ModelSerializer):
    class Meta:
        model = Tenant
        fields = '__all__'
