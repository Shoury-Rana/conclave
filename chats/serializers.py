from rest_framework import serializers
from chats.models import ChatRooms, Messages, RoomMembers
from core.models import Profile


class MessageSerializer(serializers.ModelSerializer):
    room_id = serializers.UUIDField(source="room.id", read_only=True)
    sender_id = serializers.UUIDField(source="sender.profile.user.id", read_only=True)
    sender_name = serializers.CharField(
        source="sender.profile.user.name", read_only=True
    )
    sender_username = serializers.CharField(
        source="sender.profile.username", read_only=True
    )

    class Meta:
        model = Messages
        fields = [
            "id",
            "room_id",
            "sender_id",
            "sender_name",
            "sender_username",
            "content",
            "sent_at",
        ]


class ChatRoomSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatRooms
        fields = [
            "id",
            "name",
            "type",
            "created_at",
            "member_count",
            "unread_count",
            "last_message",
        ]

    def get_member_count(self, obj):
        return obj.members.count()

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0

        member = obj.members.filter(profile__user=request.user).first()
        if not member:
            return 0
        if not member.last_read_message:
            return obj.messages.count()

        return obj.messages.filter(sent_at__gt=member.last_read_message.sent_at).count()

    def get_last_message(self, obj):
        last_msg = obj.messages.order_by("-sent_at").first()
        if last_msg:
            return {
                "id": str(last_msg.id),
                "content": last_msg.content,
                "sender_username": last_msg.sender.profile.username,
                "sent_at": last_msg.sent_at.isoformat(),
            }
        return None


class CreateChatRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatRooms
        fields = ["id", "name", "type"]
        read_only_fields = ["id"]


class RoomMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="profile.username", read_only=True)
    user_name = serializers.CharField(source="profile.user.name", read_only=True)

    class Meta:
        model = RoomMembers
        fields = ["id", "username", "user_name", "joined_at", "last_read_message"]
