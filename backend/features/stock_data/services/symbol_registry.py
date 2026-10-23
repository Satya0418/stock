import json
import logging
from typing import List, Dict

from django.conf import settings

logger = logging.getLogger(__name__)


def load_symbol_config() -> List[Dict[str, str]]:
    raw = settings.STOCK_TOKEN_MAP
    if raw:
        try:
            data = json.loads(raw)
            return [item for item in data if item.get('symbol') and item.get('token')]
        except json.JSONDecodeError:
            logger.error('Invalid STOCK_TOKEN_MAP JSON')
    return []
