from django.db import models


class RoomTypes(models.TextChoices):
    DIRECT_MESSAGE = "DIRECT_MESSAGE", "Direct Message"
    TENANT_CHATS = "TENANT_CHATS", "Tenant Chats"
    BROADCAST = "BROADCAST", "Broadcast"