from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import (
    User, Tenant, Profile
)
from core.permissions import IsCreator
from core.serializers import (
    AuthSerializer, TenantSerializer
)


class SignupView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = AuthSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            user = User.objects.create_user(email=email, password=password)
            refresh_token = RefreshToken.for_user(user)
            return Response({'refresh': str(refresh_token)}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=400)

@extend_schema(request=AuthSerializer)
class LoginView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = AuthSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            user = User.objects.get(email=email)
            if user and authenticate(email=email, password=password):
                refresh_token = RefreshToken.for_user(user)

                return Response({
                    "refresh_token": str(refresh_token),
                    "access_token": str(refresh_token.access_token)

                })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TenantViewSet(ModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [IsAuthenticated, IsCreator]
    lookup_field = 'id'

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class CheckTenantExist(APIView):
    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        tenant_name = getattr(request, 'create_name', None)

        if not tenant_name and not tenant:
            return Response('tenant does not exist. create new tenant if required.', status=status.HTTP_204_NO_CONTENT)
        user_belong_to_tenant = Profile.objects.filter(tenant=request.tenant,user=request.user).exists()
        if user_belong_to_tenant and tenant:
            return Response({'tenant': tenant.id, 'tenant_name': tenant.name, 'belongs_to': user_belong_to_tenant}, status=status.HTTP_200_OK)
        else:
            return Response("User doesn't belong to this tenant", status=status.HTTP_400_BAD_REQUEST)

