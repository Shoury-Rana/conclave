import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django_redis import get_redis_connection

from chats.models import ChatRooms, Messages, RoomMembers
from chats.utils import rls_db_sync_to_async
from core.contexts import _current_tenant_id
from core.models import Profile


@rls_db_sync_to_async
def get_or_create_room_member(chat_room, user):
    profile = Profile.objects.filter(tenant=chat_room.tenant, user=user).first()
    if not profile:
        profile = Profile.objects.create(
            user=user,
            tenant=chat_room.tenant,
            username=(user.name.lower().replace(" ", "_") or user.email.split("@")[0])[
                :50
            ],
            role="member",
        )
    member, _ = RoomMembers.objects.get_or_create(room=chat_room, profile=profile)
    return member


@rls_db_sync_to_async
def persist_message(chat_room_id, user_id, message_content):
    member = (
        RoomMembers.objects.select_related("profile__user")
        .filter(room_id=chat_room_id, profile__user_id=user_id)
        .first()
    )
    if not member:
        profile = Profile.objects.filter(
            user_id=user_id, tenant__chat_rooms__id=chat_room_id
        ).first()
        if profile:
            member, _ = RoomMembers.objects.get_or_create(
                room_id=chat_room_id, profile=profile
            )

    msg = Messages.objects.create(
        room_id=chat_room_id, sender=member, content=message_content
    )
    return {
        "id": str(msg.id),
        "room_id": str(msg.room_id),
        "sender_id": str(member.profile.user.id),
        "sender_name": member.profile.user.name,
        "sender_username": member.profile.username,
        "content": msg.content,
        "sent_at": msg.sent_at.isoformat(),
    }


@rls_db_sync_to_async
def update_last_read(chat_room_id, user_id, message_id):
    try:
        member = RoomMembers.objects.filter(
            room_id=chat_room_id, profile__user_id=user_id
        ).first()
        message = Messages.objects.filter(id=message_id, room_id=chat_room_id).first()
        if member and message:
            member.last_read_at = message.sent_at
            member.save(update_fields=["last_read_at"])
    except Exception:
        pass


@rls_db_sync_to_async
def find_chat_room(room_id=None, room_name=None, tenant_id=None):
    if room_id:
        room = ChatRooms.objects.filter(id=room_id).select_related("tenant").first()
        if room and tenant_id and str(room.tenant_id) != str(tenant_id):
            return None
        return room
    if room_name and tenant_id:
        return (
            ChatRooms.objects.filter(name=room_name, tenant_id=tenant_id)
            .select_related("tenant")
            .first()
        )
    return None


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        self.tenant_id = self.scope.get("tenant_id")
        self.room_name = self.scope.get("room_name")

        self.room_id = self.scope.get("room_id") or self.scope.get(
            "url_route", {}
        ).get("kwargs", {}).get("room_id")

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        # Default to workspace #general room when no explicit room is targeted
        if not self.room_id and not self.room_name:
            self.room_name = "general"

        self.chat_room = await find_chat_room(
            room_id=self.room_id, room_name=self.room_name, tenant_id=self.tenant_id
        )
        if not self.chat_room:
            await self.close(code=4004)
            return

        if not self.tenant_id:
            self.tenant_id = str(self.chat_room.tenant_id)
            _current_tenant_id.set(self.chat_room.tenant_id)

        self.member = await get_or_create_room_member(self.chat_room, self.user)

        self.group_name = f"chat_{self.chat_room.id}"

        subprotocols = self.scope.get("subprotocols", [])
        if subprotocols:
            await self.accept(subprotocol=subprotocols[0])
        else:
            await self.accept()

        await self.channel_layer.group_add(self.group_name, self.channel_name)

        try:
            redis_conn = get_redis_connection("default")
            await sync_to_async(redis_conn.set)(
                f"room:{self.chat_room.id}:user:{self.user.id}:online",
                "true",
                ex=86400,
            )
            await sync_to_async(redis_conn.set)(
                f"user:{self.user.id}:is_online", "true", ex=86400
            )
        except Exception:
            pass

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "user.presence",
                "user_id": str(self.user.id),
                "user_name": self.user.name,
                "status": "online",
            },
        )

    async def disconnect(self, code):
        if (
            hasattr(self, "group_name")
            and hasattr(self, "user")
            and self.user
            and self.user.is_authenticated
        ):
            try:
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "user.presence",
                        "user_id": str(self.user.id),
                        "user_name": self.user.name,
                        "status": "offline",
                    },
                )
            except Exception:
                pass

            try:
                await self.channel_layer.group_discard(
                    self.group_name, self.channel_name
                )
            except Exception:
                pass

        if hasattr(self, "chat_room") and hasattr(self, "user") and self.user:
            try:
                redis_conn = get_redis_connection("default")
                await sync_to_async(redis_conn.delete)(
                    f"room:{self.chat_room.id}:user:{self.user.id}:online"
                )
            except Exception:
                pass

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        message_type = data.get("type")

        match message_type:
            case "message_send" | "chat_message" | "message":
                message_content = data.get("message") or data.get("content", "")
                if isinstance(message_content, str) and message_content.strip():
                    msg_payload = await persist_message(
                        self.chat_room.id, self.user.id, message_content.strip()
                    )
                    await self.channel_layer.group_send(
                        self.group_name,
                        {"type": "chat.message", "payload": msg_payload},
                    )

            case "mark_read":
                message_id = data.get("message_id")
                if message_id:
                    await update_last_read(self.chat_room.id, self.user.id, message_id)

            case "typing_start":
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "user.typing",
                        "user_id": str(self.user.id),
                        "user_name": self.user.name,
                        "typing": True,
                    },
                )

            case "typing_stop":
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "user.typing",
                        "user_id": str(self.user.id),
                        "user_name": self.user.name,
                        "typing": False,
                    },
                )

            case _:
                pass

    async def chat_message(self, event):
        payload = event["payload"]
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message_send",
                    "id": payload["id"],
                    "room_id": payload["room_id"],
                    "sender_id": payload["sender_id"],
                    "sender_name": payload["sender_name"],
                    "sender_username": payload["sender_username"],
                    "message": payload["content"],
                    "content": payload["content"],
                    "sent_at": payload["sent_at"],
                }
            )
        )

    async def user_presence(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "presence",
                    "user_id": event["user_id"],
                    "user_name": event.get("user_name", ""),
                    "status": event["status"],
                }
            )
        )

    async def user_typing(self, event):
        if event["user_id"] != str(self.user.id):
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "typing",
                        "user_id": event["user_id"],
                        "user_name": event.get("user_name", ""),
                        "typing": event["typing"],
                    }
                )
            )