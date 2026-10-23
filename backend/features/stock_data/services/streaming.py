import logging
from typing import List, Dict
from datetime import datetime

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

STREAM_GROUP = 'stock_stream'


def broadcast_prices(rows: List[Dict[str, str]]):
    if not rows:
        return
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        STREAM_GROUP,
        {
            'type': 'stock_stream_update',
            'data': rows,
            'timestamp': datetime.utcnow().isoformat(),
        },
    )
