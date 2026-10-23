from django.db import models
from django.utils import timezone


class StockPrice(models.Model):
    symbol = models.CharField(max_length=32)
    timestamp = models.DateTimeField(db_index=True)
    open = models.DecimalField(max_digits=14, decimal_places=4)
    high = models.DecimalField(max_digits=14, decimal_places=4)
    low = models.DecimalField(max_digits=14, decimal_places=4)
    close = models.DecimalField(max_digits=14, decimal_places=4)
    volume = models.BigIntegerField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'stock_prices'
        indexes = [
            models.Index(fields=['symbol', 'timestamp']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['symbol', 'timestamp'], name='unique_symbol_timestamp'),
        ]

    def __str__(self):
        return f"{self.symbol} @ {self.timestamp.isoformat()}"
