"""
==============================================================================
REST API Serializers for Market Data
==============================================================================

Serializers convert Django models and Python objects to JSON format
for API responses. They also validate incoming request data.

Django REST Framework serializers provide:
- Data validation
- Object to JSON conversion (serialization)
- JSON to object conversion (deserialization)

This file defines serializers for:
- Market breadth data
- Index information
- Stock details

Usage:
    from apps.market_data.serializers import MarketBreadthSerializer
    
    breadth_data = {'index': 'NIFTY 50', 'bullish': 32, ...}
    serializer = MarketBreadthSerializer(breadth_data)
    json_data = serializer.data
==============================================================================
"""

from rest_framework import serializers
from .models import Index, Stock, IndexConstituent


class StockSerializer(serializers.ModelSerializer):
    """
    Serializer for Stock model.
    
    Used for listing stocks and their basic information.
    """
    
    class Meta:
        model = Stock
        fields = [
            'id',
            'symbol',
            'name',
            'angel_token',
            'exchange',
            'sector',
            'is_active',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class IndexSerializer(serializers.ModelSerializer):
    """
    Serializer for Index model.
    
    Includes basic index information and constituent count.
    """
    
    class Meta:
        model = Index
        fields = [
            'id',
            'symbol',
            'name',
            'angel_token',
            'exchange',
            'constituent_count',
            'is_active',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MarketBreadthSerializer(serializers.Serializer):
    """
    Serializer for market breadth data.
    
    This is NOT a ModelSerializer because breadth data
    is computed in real-time, not stored in database.
    
    Fields:
        index: Index name (e.g., 'NIFTY 50')
        bullish: Count of stocks trading above previous close
        bearish: Count of stocks trading below previous close
        neutral: Count of stocks unchanged from previous close
        total: Total number of stocks in the index
        sentiment_score: 0-100 score (100 = all bullish)
        last_updated: Timestamp of last calculation
    """
    
    # Index identification
    index = serializers.CharField(
        help_text="Name of the index"
    )
    
    # Breadth counts
    bullish = serializers.IntegerField(
        help_text="Number of stocks trading above previous close"
    )
    bearish = serializers.IntegerField(
        help_text="Number of stocks trading below previous close"
    )
    neutral = serializers.IntegerField(
        help_text="Number of stocks unchanged from previous close"
    )
    total = serializers.IntegerField(
        help_text="Total number of stocks in the index"
    )
    
    # Derived metrics
    sentiment_score = serializers.IntegerField(
        help_text="Sentiment score from 0 (bearish) to 100 (bullish)"
    )
    
    # Timestamp
    last_updated = serializers.CharField(
        help_text="ISO timestamp of last update"
    )


class StockBreadthDetailSerializer(serializers.Serializer):
    """
    Serializer for individual stock breadth status.
    
    Used when drilling down into an index to see
    individual stock performance.
    """
    
    symbol = serializers.CharField()
    name = serializers.CharField()
    ltp = serializers.FloatField(
        help_text="Last Traded Price"
    )
    change = serializers.FloatField(
        help_text="Price change from previous close"
    )
    change_percent = serializers.FloatField(
        help_text="Percentage change from previous close"
    )
    status = serializers.ChoiceField(
        choices=['bullish', 'bearish', 'neutral'],
        help_text="Current status based on price vs close"
    )


class IndexDetailSerializer(serializers.Serializer):
    """
    Detailed index information including breadth and stock breakdown.
    
    Combines index metadata with current breadth data and stock list.
    """
    
    # Index info
    name = serializers.CharField()
    symbol = serializers.CharField()
    
    # Index-level price data (if available)
    ltp = serializers.FloatField(required=False, allow_null=True)
    change = serializers.FloatField(required=False, allow_null=True)
    change_percent = serializers.FloatField(required=False, allow_null=True)
    
    # Breadth summary
    breadth = MarketBreadthSerializer()
    
    # Individual stocks
    stocks = StockBreadthDetailSerializer(many=True)


class WebSocketStatusSerializer(serializers.Serializer):
    """
    Serializer for WebSocket connection status.
    
    Used by the status endpoint to report system health.
    """
    
    is_connected = serializers.BooleanField()
    is_connecting = serializers.BooleanField()
    subscribed_count = serializers.IntegerField()
    reconnect_attempts = serializers.IntegerField()


class SystemStatusSerializer(serializers.Serializer):
    """
    Serializer for overall system status.
    
    Aggregates status from all services.
    """
    
    angel_api_authenticated = serializers.BooleanField()
    websocket = WebSocketStatusSerializer()
    calculator_running = serializers.BooleanField()
    indices_tracked = serializers.IntegerField()
    total_stocks = serializers.IntegerField()
