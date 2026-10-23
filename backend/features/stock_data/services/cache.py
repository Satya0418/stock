import json
from typing import List, Dict

from django.core.cache import cache

LATEST_CACHE_KEY = 'stock_latest_prices'


def set_latest_prices(rows: List[Dict[str, str]], ttl_seconds: int = 120):
    cache.set(LATEST_CACHE_KEY, json.dumps(rows), ttl_seconds)


def get_latest_prices_cache() -> List[Dict[str, str]]:
    raw = cache.get(LATEST_CACHE_KEY)
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []
