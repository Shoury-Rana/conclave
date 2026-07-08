import json

from asgiref.sync import sync_to_async
from chats.utilts import rls_db_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django_redis import get_redis_connection
from chats.models import Messages
from chats.models import ChatRooms

redis_conn = get_redis_connection()     # TODO: instead of this, redis-py's native aioredis should be used.


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        self.room_name = self.scope.get('room_name')

        if not self.user or not self.room_name:
            await self.close()
            return

        self.chat_room = await rls_db_sync_to_async(ChatRooms.objects.filter(name=self.room_name).first)()
        if not self.chat_room:       # No need to check for tenant specific as it will be handled via RLS
            await self.close()
            return

        await self.accept()

        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await sync_to_async(redis_conn.set)(f'room:{self.chat_room.id}::member:{self.user.id}::is_online', 'true')

    async def disconnect(self, code):
        if getattr(self, 'room_name', None):
            try:
                await self.channel_layer.group_discard(self.room_name, self.channel_name)
            except Exception:
                pass

        if getattr(self, 'chat_room', None) and getattr(self, 'user', None):
            try:
                await sync_to_async(redis_conn.delete)(f'room:{self.chat_room.id}::member:{self.user.id}::is_online')
            except Exception:
                pass

    async def receive(self, text_data = None, bytes_data = None):
        text_data_json = json.loads(text_data or '')
        message = text_data_json.get('message', None)
        message_type = text_data_json.get('type', None)
        sender = text_data_json.get('sender', None)

        match message_type:
            case 'message_send':
                self.event_type = 'message.send'
            case _:
                return

        await self.channel_layer.group_send(self.room_name, {
            'type': self.event_type,
            'message': message,
            'sender': sender,
        })
        rls_db_sync_to_async(Messages.objects.create)(room=self.room_name, sender=sender, content=message)

    async def message_send(self, event):
        await self.send(json.dumps({
            'message': event['message']
        }))
