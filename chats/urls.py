from django.urls import path
from chats.views import (
    ChatRoomListCreateView,
    ChatRoomJoinView,
    ChatRoomMessageListView,
    ChatRoomReadStateView,
    DirectMessageRoomView,
)

urlpatterns = [
    path("rooms/", ChatRoomListCreateView.as_view(), name="chat-room-list-create"),
    path(
        "rooms/<uuid:room_id>/join/", ChatRoomJoinView.as_view(), name="chat-room-join"
    ),
    path(
        "rooms/<uuid:room_id>/messages/",
        ChatRoomMessageListView.as_view(),
        name="chat-room-messages",
    ),
    path(
        "rooms/<uuid:room_id>/read-states/",
        ChatRoomReadStateView.as_view(),
        name="chat-room-read-states",
    ),
    path(
        "dm/<uuid:target_user_id>/",
        DirectMessageRoomView.as_view(),
        name="direct-message",
    ),
]
