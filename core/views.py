from django.contrib.auth import authenticate
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateAPIView,
    get_object_or_404,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from chats.choices import RoomTypes
from chats.models import ChatRooms, RoomMembers
from core.contexts import get_current_tenant_id
from core.models import Profile, Tenant, TenantInvitation, TenantJoinRequest, User
from core.permissions import IsCreator, IsTenantMember
from core.serializers import (
    ListCreateTenantSerializer,
    LoginSerializer,
    MemberSerializer,
    MeSerializer,
    SignupSerializer,
    TenantDetailSerializer,
    TenantInvitationSerializer,
    TenantJoinRequestSerializer,
    TenantSerializer,
    TenantSettingSerializer,
    UserProfileSerializer,
)


@extend_schema(request=SignupSerializer, responses={201: MeSerializer})
class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        password = serializer.validated_data["password"]
        name = serializer.validated_data["name"]

        if User.objects.filter(email=email).exists():
            return Response(
                {"error": "User with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_user(email=email, password=password, name=name)
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": MeSerializer(user).data,
                "refresh_token": str(refresh),
                "access_token": str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(request=LoginSerializer)
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        password = serializer.validated_data["password"]

        user = authenticate(request, email=email, password=password)
        if not user:
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": MeSerializer(user).data,
                "refresh_token": str(refresh),
                "access_token": str(refresh.access_token),
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(responses=MeSerializer)
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = MeSerializer(request.user)
        return Response(serializer.data)


class UserProfileView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    queryset = User.objects.all()

    def get_object(self):
        pk = self.kwargs.get("pk")
        if pk == "me" or not pk:
            return self.request.user
        return get_object_or_404(User, pk=pk)


@extend_schema(request=ListCreateTenantSerializer, responses=TenantSerializer)
class ListCreateTenantView(ListCreateAPIView):
    serializer_class = ListCreateTenantSerializer
    permission_classes = [IsAuthenticated]
    queryset = Tenant.objects.filter(is_public=True)

    def perform_create(self, serializer):
        tenant = serializer.save(created_by=self.request.user)
        profile, _ = Profile.objects.get_or_create(
            user=self.request.user,
            tenant=tenant,
            defaults={
                "username": self.request.user.name.lower().replace(" ", "_")
                or self.request.user.email.split("@")[0],
                "role": "owner",
            },
        )
        general_room, _ = ChatRooms.objects.get_or_create(
            tenant=tenant, name="general", defaults={"type": RoomTypes.TENANT_CHATS}
        )
        RoomMembers.objects.get_or_create(room=general_room, profile=profile)


class MyTenantsListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TenantSerializer

    def get_queryset(self):
        user = self.request.user
        return Tenant.objects.filter(
            Q(members__user=user) | Q(created_by=user)
        ).distinct()


class SearchTenantsView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TenantSerializer

    def get_queryset(self):
        query = self.request.query_params.get("q", "").strip()
        if not query:
            return Tenant.objects.filter(is_public=True)[:20]
        return Tenant.objects.filter(name__icontains=query, is_public=True)[:20]


class JoinTenantView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tenant_name = request.data.get("tenant_name") or request.data.get("name")
        tenant_id = request.data.get("tenant_id")

        tenant = None
        if tenant_id:
            tenant = get_object_or_404(Tenant, id=tenant_id)
        elif tenant_name:
            tenant = get_object_or_404(Tenant, name__iexact=tenant_name)
        else:
            return Response(
                {"error": "tenant_name or tenant_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Profile.objects.filter(tenant=tenant, user=request.user).exists():
            return Response(
                {"message": "Already a member of this workspace."},
                status=status.HTTP_200_OK,
            )

        if tenant.is_public:
            username = (
                request.data.get("username")
                or request.user.name.lower().replace(" ", "_")
                or request.user.email.split("@")[0]
            )
            base_username = username
            counter = 1
            while Profile.objects.filter(tenant=tenant, username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1

            profile = Profile.objects.create(
                user=request.user, tenant=tenant, username=username, role="member"
            )
            general_room = ChatRooms.objects.filter(
                tenant=tenant, name="general"
            ).first()
            if general_room:
                RoomMembers.objects.get_or_create(room=general_room, profile=profile)

            return Response(
                {
                    "message": f"Successfully joined {tenant.name}.",
                    "profile_id": profile.id,
                },
                status=status.HTTP_201_CREATED,
            )
        else:
            join_req, created = TenantJoinRequest.objects.get_or_create(
                tenant=tenant,
                user=request.user,
                defaults={"status": TenantJoinRequest.Status.PENDING},
            )
            return Response(
                {
                    "message": "Join request submitted to workspace owner.",
                    "request_id": join_req.id,
                },
                status=status.HTTP_202_ACCEPTED,
            )


@extend_schema(responses=TenantDetailSerializer)
class TenantDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return Response(
                {"error": "No workspace context in request."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tenant = get_object_or_404(Tenant, pk=tenant_id)
        if (
            not Profile.objects.filter(user=request.user, tenant=tenant).exists()
            and tenant.created_by != request.user
        ):
            raise PermissionDenied("You are not a member of this workspace.")

        serializer = TenantDetailSerializer(tenant)
        return Response(serializer.data)


class TenantSettingView(RetrieveUpdateAPIView):
    serializer_class = TenantSettingSerializer
    permission_classes = [IsAuthenticated, IsCreator]

    def get_object(self):
        tenant_id = get_current_tenant_id()
        return get_object_or_404(Tenant, pk=tenant_id)


class WorkspaceMembersListView(ListAPIView):
    permission_classes = [IsAuthenticated, IsTenantMember]
    serializer_class = MemberSerializer

    def get_queryset(self):
        tenant_id = get_current_tenant_id()
        return Profile.objects.filter(tenant_id=tenant_id).select_related("user")


class InviteMemberView(APIView):
    permission_classes = [IsAuthenticated, IsTenantMember]

    def post(self, request):
        tenant_id = get_current_tenant_id()
        tenant = get_object_or_404(Tenant, pk=tenant_id)
        email = request.data.get("email", "").strip().lower()

        if not email:
            return Response(
                {"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        target_user = User.objects.filter(email=email).first()
        if not target_user:
            return Response(
                {"error": f"No user registered with email {email}."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if Profile.objects.filter(tenant=tenant, user=target_user).exists():
            return Response(
                {"error": "User is already a member of this workspace."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invitation, created = TenantInvitation.objects.get_or_create(
            tenant=tenant,
            invited_user=target_user,
            defaults={
                "invited_by": request.user,
                "status": TenantInvitation.Status.PENDING,
            },
        )
        return Response(
            TenantInvitationSerializer(invitation).data, status=status.HTTP_201_CREATED
        )


class UserInvitationsListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TenantInvitationSerializer

    def get_queryset(self):
        return TenantInvitation.objects.filter(
            invited_user=self.request.user, status=TenantInvitation.Status.PENDING
        )


class RespondInvitationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        invitation = get_object_or_404(
            TenantInvitation, pk=pk, invited_user=request.user
        )
        action = request.data.get("action", "accept").lower()

        if action == "accept":
            invitation.status = TenantInvitation.Status.ACCEPTED
            invitation.save()

            username = (
                request.user.name.lower().replace(" ", "_")
                or request.user.email.split("@")[0]
            )
            base_username = username
            counter = 1
            while Profile.objects.filter(
                tenant=invitation.tenant, username=username
            ).exists():
                username = f"{base_username}_{counter}"
                counter += 1

            profile, _ = Profile.objects.get_or_create(
                user=request.user,
                tenant=invitation.tenant,
                defaults={
                    "username": username,
                    "role": "member",
                    "invited_by": invitation.invited_by,
                    "accepted_by": request.user,
                },
            )
            # Add to general room
            general_room = ChatRooms.objects.filter(
                tenant=invitation.tenant, name="general"
            ).first()
            if general_room:
                RoomMembers.objects.get_or_create(room=general_room, profile=profile)

            return Response(
                {
                    "message": f"Accepted invitation to {invitation.tenant.name}.",
                    "profile_id": profile.id,
                }
            )
        else:
            invitation.status = TenantInvitation.Status.DECLINED
            invitation.save()
            return Response({"message": "Invitation declined."})


class WorkspaceJoinRequestsView(ListAPIView):
    permission_classes = [IsAuthenticated, IsCreator]
    serializer_class = TenantJoinRequestSerializer

    def get_queryset(self):
        tenant_id = get_current_tenant_id()
        return TenantJoinRequest.objects.filter(
            tenant_id=tenant_id, status=TenantJoinRequest.Status.PENDING
        )


class RespondJoinRequestView(APIView):
    permission_classes = [IsAuthenticated, IsCreator]

    def post(self, request, pk):
        tenant_id = get_current_tenant_id()
        join_req = get_object_or_404(TenantJoinRequest, pk=pk, tenant_id=tenant_id)
        action = request.data.get("action", "approve").lower()

        if action == "approve":
            join_req.status = TenantJoinRequest.Status.APPROVED
            join_req.save()

            username = (
                join_req.user.name.lower().replace(" ", "_")
                or join_req.user.email.split("@")[0]
            )
            profile, _ = Profile.objects.get_or_create(
                user=join_req.user,
                tenant=join_req.tenant,
                defaults={
                    "username": username,
                    "role": "member",
                    "accepted_by": request.user,
                },
            )
            general_room = ChatRooms.objects.filter(
                tenant=join_req.tenant, name="general"
            ).first()
            if general_room:
                RoomMembers.objects.get_or_create(room=general_room, profile=profile)

            return Response(
                {"message": f"Approved {join_req.user.name} into workspace."}
            )
        else:
            join_req.status = TenantJoinRequest.Status.REJECTED
            join_req.save()
            return Response({"message": "Join request rejected."})
