import json
import logging
from datetime import datetime

from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

from features.stock_data.services.cache import get_latest_prices_cache
from features.stock_data.services.streaming import STREAM_GROUP

logger = logging.getLogger(__name__)


class StockStreamConsumer(AsyncWebsocketConsumer):
    group_name = STREAM_GROUP

    async def connect(self):
        user = self.scope.get('user')
        if not user or not getattr(user, 'is_authenticated', False):
            await self.close(code=4401)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_initial_data()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_initial_data(self):
        data = await sync_to_async(get_latest_prices_cache)()
        await self.send_json({
            'type': 'stock_stream',
            'data': data,
            'timestamp': datetime.utcnow().isoformat(),
            'is_initial': True,
        })

    async def stock_stream_update(self, event):
        await self.send_json({
            'type': 'stock_stream',
            'data': event.get('data', []),
            'timestamp': event.get('timestamp'),
            'is_initial': False,
        })

    async def send_json(self, payload):
        await self.send(text_data=json.dumps(payload))
