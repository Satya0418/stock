import logging
from typing import List, Dict

from django.conf import settings
from features.scheduler.locks import RedisLock
from ..models import StockPrice
from ..repositories import bulk_insert_prices
from .angel_one_client import AngelOneClient
from .symbol_registry import load_symbol_config
from .validation import validate_price_row
from .cache import set_latest_prices
from .streaming import broadcast_prices

logger = logging.getLogger(__name__)


class StockDataPipeline:
    def __init__(self):
        self.client = AngelOneClient()
        self.lock = RedisLock('stock_data_pipeline', timeout=settings.STOCK_PIPELINE_LOCK_TIMEOUT)

    def run(self) -> Dict[str, int]:
        if not self.lock.acquire():
            logger.info('stock data pipeline skipped due to active lock')
            return {'fetched': 0, 'stored': 0}

        try:
            symbols = load_symbol_config()
            if not symbols:
                logger.warning('No symbol config found for stock data pipeline')
                return {'fetched': 0, 'stored': 0}

            raw_rows = self.client.fetch_ltp_batch(symbols)
            validated = []
            output_rows = []

            for row in raw_rows:
                validated_row = validate_price_row(row)
                if not validated_row:
                    continue
                validated.append(StockPrice(
                    symbol=validated_row.symbol,
                    timestamp=validated_row.timestamp,
                    open=validated_row.open,
                    high=validated_row.high,
                    low=validated_row.low,
                    close=validated_row.close,
                    volume=validated_row.volume,
                ))
                output_rows.append({
                    'symbol': validated_row.symbol,
                    'timestamp': validated_row.timestamp.isoformat(),
                    'open': str(validated_row.open),
                    'high': str(validated_row.high),
                    'low': str(validated_row.low),
                    'close': str(validated_row.close),
                    'volume': validated_row.volume,
                })

            stored = bulk_insert_prices(validated)
            set_latest_prices(output_rows, ttl_seconds=settings.STOCK_LATEST_CACHE_TTL)
            broadcast_prices(output_rows)

            return {'fetched': len(raw_rows), 'stored': stored}
        finally:
            self.lock.release()
