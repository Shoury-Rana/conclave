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


class UserProfileSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'name', 'tenants_joined']

    def get_tenants_joined(self):
        return Tenant.objects.all()


class ListCreateTenantSerializer(ModelSerializer):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Tenant
        fields = '__all__'
        extra_kwargs = {
            'id': {'read_only': True},
        }
