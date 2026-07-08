from django.contrib import admin

from chats.models import ChatRooms, RoomMembers, Messages


# Register your models here.
@admin.register(ChatRooms)
class ChatRoomsAdmin(admin.ModelAdmin):
    pass


@admin.register(RoomMembers)
class RoomMembersAdmin(admin.ModelAdmin):
    pass


@admin.register(Messages)
class MessagesAdmin(admin.ModelAdmin):
    pass