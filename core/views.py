from django.contrib.admin.utils import lookup_field
from django.contrib.auth import authenticate
from django.db.migrations import serializer
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import RetrieveAPIView, RetrieveUpdateAPIView, ListCreateAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.contexts import get_current_tenant_id
from core.permissions import IsCreator
from core.models import (
    User, Tenant, Profile
)
from core.serializers import (
    SignupSerializer, LoginSerializer, UserProfileSerializer,
    ListCreateTenantSerializer, TenantDetailSerializer, TenantSettingSerializer
)


@extend_schema(request=SignupSerializer)
class SignupView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            name = serializer.validated_data['name']

            if User.objects.filter(email=email).exists():
                return Response('User already exists, please login instead.', status=status.HTTP_400_BAD_REQUEST)
            user = User.objects.create_user(email=email, password=password, name=name)
            refresh_token = RefreshToken.for_user(user)
            return Response({
                    "refresh_token": str(refresh_token),
                    "access_token": str(refresh_token.access_token)
                }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(request=LoginSerializer)
class LoginView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            user = authenticate(request, email=email, password=password)
            if user:
                refresh_token = RefreshToken.for_user(user)

                return Response({
                    "refresh_token": str(refresh_token),
                    "access_token": str(refresh_token.access_token),
                    "user_id": user.id,
                    "user_name": user.name
                }, status=status.HTTP_200_OK)
        return Response('Credential not found, make sure you have sign up first.', status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    lookup_field = 'name'
    queryset = User.objects.all()



@extend_schema(request=ListCreateTenantSerializer)
class ListCreateTenantView(ListCreateAPIView):
    serializer_class = ListCreateTenantSerializer
    permission_classes = [IsAuthenticated]
    queryset = Tenant.objects.all()


@extend_schema(operation_id="tenant_detail_view", responses=TenantDetailSerializer)
class TenantDetailView(RetrieveAPIView):
    queryset = Tenant.objects.all()
    serializer_class = TenantDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = self.request.user
        tenant_id = get_current_tenant_id()
        tenant = get_object_or_404(self.queryset, pk=tenant_id)

        if Profile.objects.filter(user=user, tenant=tenant_id).exists() or tenant.created_by == user:
            return tenant
        raise PermissionDenied("User not member of tenant.")

@extend_schema(request=TenantSettingSerializer)
class TenantSettingView(RetrieveUpdateAPIView):
    queryset = Tenant.objects.all()
    serializer_class = TenantSettingSerializer
    permission_classes = [IsAuthenticated, IsCreator]

    def get_object(self):
        tenant_id = get_current_tenant_id()
        tenant = get_object_or_404(self.queryset, pk=tenant_id)
        return tenant

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
