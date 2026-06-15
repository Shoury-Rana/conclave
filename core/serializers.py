from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from core.models import (
    User, Tenant, Profile
)


class AuthSerializer(ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    class Meta:
        model = User
        fields = ['email', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }


class TenantSerializer(ModelSerializer):
    name = serializers.CharField()
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Tenant
        fields = ['name', 'id']