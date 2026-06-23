from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import RetrieveAPIView, UpdateAPIView, RetrieveUpdateAPIView, ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.utils.representation import serializer_repr
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken

from core.contexts import get_current_tenant_id
from core.models import (
    User, Tenant, Profile
)
from core.permissions import IsCreator
from core.serializers import (
    SignupSerializer, LoginSerializer, UserProfileSerializer,
    ListCreateTenantSerializer
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
    permission_classes = [IsAuthenticated, IsCreator]
    serializer_class = UserProfileSerializer
    lookup_field = 'name'
    queryset = User.objects.all()


@extend_schema(request=ListCreateTenantSerializer)
class ListCreateTenantView(ListCreateAPIView):
    serializer_class = ListCreateTenantSerializer
    permission_classes = [IsAuthenticated]
    queryset = Tenant.objects.all()
