import asyncio

from channels_redis.core import RedisChannelLayer as BaseRedisChannelLayer
import redis.exceptions


class RedisChannelLayer(BaseRedisChannelLayer):
    """
    Resilient RedisChannelLayer that handles redis-py 5.x TimeoutError
    during idle receive polling, preventing ASGI consumer crashes.
    """

    async def receive(self, channel):
        while True:
            try:
                return await super().receive(channel)
            except (redis.exceptions.TimeoutError, TimeoutError):
                # redis-py 5.x raises TimeoutError when the socket read timeout
                # expires while waiting for blocking Redis operations. Catch it
                # and continue polling so the WebSocket connection remains alive.
                await asyncio.sleep(0.01)
                continue