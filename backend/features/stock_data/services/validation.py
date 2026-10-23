from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

from django.utils import timezone


@dataclass
class ValidatedPrice:
    symbol: str
    timestamp: timezone.datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


def _to_decimal(value) -> Optional[Decimal]:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def validate_price_row(payload: dict) -> Optional[ValidatedPrice]:
    symbol = (payload.get('symbol') or '').strip().upper()
    if not symbol:
        return None

    timestamp = payload.get('timestamp') or timezone.now()
    if isinstance(timestamp, str):
        try:
            timestamp = timezone.datetime.fromisoformat(timestamp)
        except ValueError:
            timestamp = timezone.now()
    if timezone.is_naive(timestamp):
        timestamp = timezone.make_aware(timestamp, timezone.get_current_timezone())

    now = timezone.now()
    if timestamp > now:
        timestamp = now
    timestamp = timestamp.replace(second=0, microsecond=0)

    open_price = _to_decimal(payload.get('open'))
    high_price = _to_decimal(payload.get('high'))
    low_price = _to_decimal(payload.get('low'))
    close_price = _to_decimal(payload.get('close'))

    if None in (open_price, high_price, low_price, close_price):
        return None

    if open_price < 0 or high_price < 0 or low_price < 0 or close_price < 0:
        return None

    if high_price < low_price:
        return None

    volume = payload.get('volume')
    try:
        volume = int(volume)
    except (TypeError, ValueError):
        volume = 0

    if volume < 0:
        return None

    return ValidatedPrice(
        symbol=symbol,
        timestamp=timestamp,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
    )
