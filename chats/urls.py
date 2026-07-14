from django.urls import path
from chats.views import ChatRoomListView, ChatRoomMessageListView

urlpatterns = [
    path('rooms/', ChatRoomListView.as_view(), name='chat-room-list'),
    path('rooms/<uuid:room_id>/messages/', ChatRoomMessageListView.as_view(), name='chat-room-messages'),
]