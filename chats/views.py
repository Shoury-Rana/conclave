from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from chats.models import ChatRooms, Messages, RoomMembers
from chats.serializers import ChatRoomSerializer, MessageSerializer

@extend_schema(tags=['Chats'])
class ChatRoomListView(ListAPIView):
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return ChatRooms.objects.filter(room__profile__user=user).distinct()

@extend_schema(tags=['Chats'])
class ChatRoomMessageListView(ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        room_id = self.kwargs.get('room_id')
        user = self.request.user

        if not RoomMembers.objects.filter(room_id=room_id, profile__user=user).exists():
            return Messages.objects.none()

        return Messages.objects.filter(room_id=room_id).order_by('sent_at')