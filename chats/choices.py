from django.db.models import Choices


class RoomTypes(Choices):
    DIRECT_MESSAGE = 'DIRECT_MESSAGE'
    TENANT_CHATS = 'TENANT_CHATS'
    BROADCAST = 'BROADCAST'