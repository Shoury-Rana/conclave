import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django_redis import get_redis_connection

from chats.utilts import rls_db_sync_to_async
from chats.models import Messages, ChatRooms, RoomMembers

redis_conn = get_redis_connection()     # TODO: instead of this, redis-py's native aioredis should be used.


@rls_db_sync_to_async
def create_message(room_id, sender_id, message):
    Messages.objects.create(room_id=room_id, sender_id=sender_id, content=message)


@rls_db_sync_to_async
def mark_message_as_read(room_id, user_id, message_id):
    try:
        member = RoomMembers.objects.get(room_id=room_id, profile__user_id=user_id)
        member.last_read_message_id = message_id
        member.save(update_fields=['last_read_message'])
    except RoomMembers.DoesNotExist:
        pass


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

        await self.channel_layer.group_send(self.room_name, {
            'type': 'user.presence',
            'user_id': str(self.user.id),
            'status': 'online',
        })

    async def disconnect(self, code):
        if getattr(self, 'room_name', None):
            if getattr(self, 'user', None):
                await self.channel_layer.group_send(self.room_name, {
                    'type': 'user.presence',
                    'user_id': str(self.user.id),
                    'status': 'offline',
                })

            try:
                await self.channel_layer.group_discard(self.room_name, self.channel_name)
            except Exception:
                pass

        if getattr(self, 'chat_room', None) and getattr(self, 'user', None):
            try:
                await sync_to_async(redis_conn.delete)(f'room:{self.chat_room.id}::member:{self.user.id}::is_online')
            except Exception:
                pass

    async def receive(self, text_data=None, bytes_data=None):
        text_data_json = json.loads(text_data or '{}')
        message_type = text_data_json.get('type', None)

        match message_type:
            case 'message_send':
                message = text_data_json.get('message', None)
                sender = text_data_json.get('sender', None)

                if message and sender:
                    await self.channel_layer.group_send(self.room_name, {
                        'type': 'message.send',
                        'message': message,
                        'sender': sender,
                    })
                    await create_message(self.chat_room.id, sender, message)

            case 'mark_read':
                message_id = text_data_json.get('message_id')
                if message_id:
                    await mark_message_as_read(self.chat_room.id, self.user.id, message_id)

            case 'typing_start':
                await self.channel_layer.group_send(self.room_name, {
                    'type': 'user.typing',
                    'user_id': str(self.user.id),
                    'typing': True,
                })

            case 'typing_stop':
                await self.channel_layer.group_send(self.room_name, {
                    'type': 'user.typing',
                    'user_id': str(self.user.id),
                    'typing': False,
                })

            case _:
                return

    async def message_send(self, event):
        await self.send(json.dumps({
            'type': 'message_send',
            'message': event['message'],
            'sender': event['sender'],
        }))

    async def user_presence(self, event):
        await self.send(json.dumps({
            'type': 'presence',
            'user_id': event['user_id'],
            'status': event['status'],
        }))

    async def user_typing(self, event):
        if event['user_id'] != str(self.user.id):
            await self.send(json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'typing': event['typing'],
            }))