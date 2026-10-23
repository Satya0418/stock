from typing import Iterable, List

from django.db import transaction
from .models import StockPrice


def bulk_insert_prices(rows: Iterable[StockPrice]) -> int:
    rows_list = list(rows)
    if not rows_list:
        return 0
    with transaction.atomic():
        created = StockPrice.objects.bulk_create(
            rows_list,
            ignore_conflicts=True,
            batch_size=500,
        )
    return len(created)


def get_latest_prices(symbols: List[str]) -> List[StockPrice]:
    latest_per_symbol = []
    for symbol in symbols:
        record = (
            StockPrice.objects.filter(symbol=symbol)
            .order_by('-timestamp')
            .first()
        )
        if record:
            latest_per_symbol.append(record)
    return latest_per_symbol


def get_history(symbol: str, start=None, end=None, limit: int = 1000):
    qs = StockPrice.objects.filter(symbol=symbol)
    if start:
        qs = qs.filter(timestamp__gte=start)
    if end:
        qs = qs.filter(timestamp__lte=end)
    return qs.order_by('-timestamp')[:limit]
