import uuid

from django.db import models

from chats.choices import RoomTypes


class ChatRooms(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField()
    tenant = models.ForeignKey('core.Tenant', related_name='tenant', on_delete=models.CASCADE)
    type = models.CharField(choices=RoomTypes, default=RoomTypes.BROADCAST)
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name', 'tenant'], name='unique_constraint_name_tenant')
        ]


class RoomMembers(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    room = models.ForeignKey('ChatRooms', related_name='room', on_delete=models.CASCADE)
    profile = models.ForeignKey('core.Profile', related_name='profile', on_delete=models.CASCADE)
    last_read_message = models.ForeignKey('Messages', related_name='last_read', on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['room', 'profile'], name='unique_constraint_room_profile')
        ]


class Messages(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    room = models.ForeignKey('ChatRooms', related_name='member', on_delete=models.CASCADE)
    sender = models.ForeignKey('RoomMembers', related_name='member', on_delete=models.CASCADE)
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now=True)