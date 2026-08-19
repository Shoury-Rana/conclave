from datetime import datetime

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView, ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chats.choices import RoomTypes
from chats.models import ChatRooms, Messages, RoomMembers
from chats.serializers import (
    ChatRoomSerializer,
    CreateChatRoomSerializer,
    MessageSerializer,
)
from core.contexts import get_current_tenant_id
from core.models import Profile, Tenant, User
from core.permissions import IsTenantMember


@extend_schema(tags=["Chats"])
class ChatRoomListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsTenantMember]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateChatRoomSerializer
        return ChatRoomSerializer

    def get_serializer_context(self):
        return {"request": self.request}

    def get_queryset(self):
        tenant_id = get_current_tenant_id()
        user = self.request.user
        return (
            ChatRooms.objects.filter(tenant_id=tenant_id)
            .filter(members__profile__user=user)
            .distinct()
            .order_by("name")
        )

    def perform_create(self, serializer):
        tenant_id = get_current_tenant_id()
        tenant = Tenant.objects.get(pk=tenant_id)
        room = serializer.save(tenant=tenant)

        # Automatically join creator to newly created room
        profile = Profile.objects.get(tenant=tenant, user=self.request.user)
        RoomMembers.objects.get_or_create(room=room, profile=profile)


@extend_schema(tags=["Chats"])
class ChatRoomJoinView(APIView):
    permission_classes = [IsAuthenticated, IsTenantMember]

    def post(self, request, room_id):
        tenant_id = get_current_tenant_id()
        room = ChatRooms.objects.filter(id=room_id, tenant_id=tenant_id).first()
        if not room:
            raise NotFound("Chat room not found.")

        profile = Profile.objects.get(tenant_id=tenant_id, user=request.user)
        member, created = RoomMembers.objects.get_or_create(room=room, profile=profile)

        return Response(
            {
                "message": f"Joined #{room.name}.",
                "room_id": str(room.id),
                "room_member_id": str(member.id),
            },
            status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Chats"])
class ChatRoomMessageListView(ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        room_id = self.kwargs.get("room_id")
        tenant_id = get_current_tenant_id()
        user = self.request.user

        room = ChatRooms.objects.filter(id=room_id, tenant_id=tenant_id).first()
        if not room:
            raise NotFound("Chat room not found.")

        # Ensure user is a room member
        if not RoomMembers.objects.filter(room=room, profile__user=user).exists():
            profile = Profile.objects.filter(tenant_id=tenant_id, user=user).first()
            if profile:
                RoomMembers.objects.create(room=room, profile=profile)

        queryset = Messages.objects.filter(room_id=room_id).select_related(
            "sender__profile__user"
        )

        # Timestamp Cursor Pagination for Terminal Viewport (PageUp/Scroll)
        before_timestamp = self.request.query_params.get("before")
        limit = int(self.request.query_params.get("limit", 50))
        limit = min(max(limit, 1), 100)

        if before_timestamp:
            try:
                dt = datetime.fromisoformat(before_timestamp.replace("Z", "+00:00"))
                queryset = queryset.filter(sent_at__lt=dt)
            except ValueError:
                pass

        # Return latest messages sorted chronologically
        messages = list(queryset.order_by("-sent_at")[:limit])
        messages.reverse()
        return messages


@extend_schema(tags=["Chats"])
class ChatRoomReadStateView(APIView):
    permission_classes = [IsAuthenticated, IsTenantMember]

    def get(self, request, room_id):
        tenant_id = get_current_tenant_id()
        room = ChatRooms.objects.filter(id=room_id, tenant_id=tenant_id).first()
        if not room:
            raise NotFound("Chat room not found.")

        member = RoomMembers.objects.filter(
            room=room, profile__user=request.user
        ).first()
        if not member:
            return Response({"unread_count": 0, "last_read_message_id": None})

        last_read_id = (
            str(member.last_read_message_id) if member.last_read_message_id else None
        )
        if not member.last_read_message:
            unread_count = room.messages.count()
        else:
            unread_count = room.messages.filter(
                sent_at__gt=member.last_read_message.sent_at
            ).count()

        return Response(
            {
                "room_id": str(room.id),
                "unread_count": unread_count,
                "last_read_message_id": last_read_id,
            }
        )


@extend_schema(tags=["Chats"])
class DirectMessageRoomView(APIView):
    """
    Retrieves or creates a 1-on-1 Direct Message room between the current user
    and the target user in the active tenant workspace.
    """

    permission_classes = [IsAuthenticated, IsTenantMember]

    def post(self, request, target_user_id):
        tenant_id = get_current_tenant_id()
        tenant = Tenant.objects.get(pk=tenant_id)
        current_user = request.user

        if str(current_user.id) == str(target_user_id):
            return Response(
                {"error": "Cannot start a direct message with yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_user = User.objects.filter(id=target_user_id).first()
        if not target_user:
            raise NotFound("Target user does not exist.")

        current_profile = Profile.objects.filter(
            tenant=tenant, user=current_user
        ).first()
        target_profile = Profile.objects.filter(tenant=tenant, user=target_user).first()

        if not target_profile:
            return Response(
                {"error": "Target user is not a member of this workspace."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Deterministic room name: dm_{min_id}_{max_id}
        ids = sorted([str(current_user.id), str(target_user_id)])
        dm_room_name = f"dm_{ids[0]}_{ids[1]}"

        room, created = ChatRooms.objects.get_or_create(
            tenant=tenant,
            name=dm_room_name,
            defaults={"type": RoomTypes.DIRECT_MESSAGE},
        )

        RoomMembers.objects.get_or_create(room=room, profile=current_profile)
        RoomMembers.objects.get_or_create(room=room, profile=target_profile)

        serializer = ChatRoomSerializer(room, context={"request": request})
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
