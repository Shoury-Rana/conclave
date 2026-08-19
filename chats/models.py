import uuid

from django.db import models

from chats.choices import RoomTypes


class ChatRooms(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    name = models.CharField(max_length=128)
    tenant = models.ForeignKey(
        "core.Tenant", related_name="chat_rooms", on_delete=models.CASCADE
    )
    type = models.CharField(
        max_length=32, choices=RoomTypes.choices, default=RoomTypes.BROADCAST
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "tenant"], name="unique_constraint_name_tenant"
            )
        ]

    def __str__(self):
        return f"#{self.name} ({self.tenant.name})"


class RoomMembers(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    room = models.ForeignKey(
        ChatRooms, related_name="members", on_delete=models.CASCADE
    )
    profile = models.ForeignKey(
        "core.Profile", related_name="room_memberships", on_delete=models.CASCADE
    )
    last_read_message = models.ForeignKey(
        "Messages", related_name="+", on_delete=models.SET_NULL, null=True, blank=True
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["room", "profile"], name="unique_constraint_room_profile"
            )
        ]

    def __str__(self):
        return f"{self.profile.username} in {self.room.name}"


class Messages(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    room = models.ForeignKey(
        ChatRooms, related_name="messages", on_delete=models.CASCADE
    )
    sender = models.ForeignKey(
        RoomMembers, related_name="messages", on_delete=models.CASCADE
    )
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sent_at"]

    def __str__(self):
        return f"{self.sender.profile.username}: {self.content[:30]}"
