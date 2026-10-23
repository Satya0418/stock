"""
==============================================================================
Database Models for Market Data App
==============================================================================

This file defines Django database models for storing market-related data.

For this real-time dashboard, we primarily use Redis for caching live data
rather than persistent database storage. However, we keep models for:

1. Index: Master list of indices being tracked
2. Stock: Stock information (symbol, name, sector)
3. IndexConstituent: Many-to-many relationship between Index and Stock

These models are useful for:
- Storing the master list of stocks in each index
- Historical data (if needed in the future)
- Admin interface for managing tracked indices

IMPORTANT: Live market data is NOT stored in the database.
           It's cached in Redis for speed (1-2 second updates).
==============================================================================
"""

from django.db import models
from django.utils import timezone


class Index(models.Model):
    """
    Represents a market index like NIFTY 50, NIFTY BANK, etc.
    
    Each index has:
    - A unique symbol (e.g., 'NIFTY')
    - A display name (e.g., 'NIFTY 50')
    - A token for Angel One API (e.g., '99926000')
    - Active status (can disable without deleting)
    """
    
    # Unique identifier used in API calls
    symbol = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique symbol for the index (e.g., 'NIFTY')"
    )
    
    # Human-readable name
    name = models.CharField(
        max_length=100,
        help_text="Display name (e.g., 'NIFTY 50')"
    )
    
    # Angel One specific token for this index
    angel_token = models.CharField(
        max_length=20,
        help_text="Angel One API token for this index"
    )
    
    # Exchange - NSE or BSE
    exchange = models.CharField(
        max_length=10,
        default='NSE',
        help_text="Exchange where this index is listed"
    )
    
    # Whether to track this index
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this index is currently being tracked"
    )
    
    # Number of constituent stocks
    constituent_count = models.IntegerField(
        default=0,
        help_text="Number of stocks in this index"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Indices"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.symbol})"


class Stock(models.Model):
    """
    Represents an individual stock that can be part of multiple indices.
    
    Stock information is relatively static and changes rarely.
    This is used to look up stock details by symbol/token.
    """
    
    # NSE symbol (e.g., 'RELIANCE', 'TCS')
    symbol = models.CharField(
        max_length=50,
        unique=True,
        help_text="NSE trading symbol"
    )
    
    # Angel One specific token for this stock
    angel_token = models.CharField(
        max_length=20,
        help_text="Angel One API token for this stock"
    )
    
    # Company name
    name = models.CharField(
        max_length=200,
        help_text="Full company name"
    )
    
    # Exchange - NSE or BSE
    exchange = models.CharField(
        max_length=10,
        default='NSE'
    )
    
    # ISIN (International Securities Identification Number)
    isin = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="ISIN code for the stock"
    )
    
    # Sector classification
    sector = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Industry sector (e.g., 'IT', 'Banking')"
    )
    
    # Whether the stock is actively traded
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['symbol']
    
    def __str__(self):
        return f"{self.symbol} - {self.name}"


class IndexConstituent(models.Model):
    """
    Many-to-many relationship between Index and Stock.
    
    A stock can belong to multiple indices (e.g., Reliance is in
    NIFTY 50, NIFTY 100, NIFTY 200, NIFTY 500).
    
    This separate model allows us to track:
    - Weightage of stock in index
    - When stock was added/removed
    """
    
    index = models.ForeignKey(
        Index,
        on_delete=models.CASCADE,
        related_name='constituents'
    )
    
    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name='index_memberships'
    )
    
    # Weightage of this stock in the index (percentage)
    weightage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Percentage weightage in the index"
    )
    
    # When this stock was added to the index
    added_date = models.DateField(
        default=timezone.now,
        help_text="Date when stock was added to index"
    )
    
    class Meta:
        # Ensure a stock can only be in an index once
        unique_together = ['index', 'stock']
        ordering = ['index', '-weightage']
    
    def __str__(self):
        return f"{self.stock.symbol} in {self.index.name}"


class MarketDataSnapshot(models.Model):
    """
    Optional: Store periodic snapshots of market breadth data.
    
    This can be useful for:
    - Historical analysis
    - Trend tracking
    - Debugging/auditing
    
    Each snapshot captures the market breadth at a specific moment.
    """
    
    index = models.ForeignKey(
        Index,
        on_delete=models.CASCADE,
        related_name='snapshots'
    )
    
    # Market breadth counts
    bullish_count = models.IntegerField(default=0)
    bearish_count = models.IntegerField(default=0)
    neutral_count = models.IntegerField(default=0)
    
    # Index-level data
    index_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    index_change_percent = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Timestamp of this snapshot
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['index', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.index.name} at {self.timestamp}"
    
    @property
    def sentiment_score(self):
        """
        Calculate sentiment score (0-100).
        100 = all bullish, 0 = all bearish, 50 = neutral
        """
        total = self.bullish_count + self.bearish_count + self.neutral_count
        if total == 0:
            return 50
        return round((self.bullish_count / total) * 100)
