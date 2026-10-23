"""
==============================================================================
REST API Views for Market Data
==============================================================================

This file contains Django REST Framework views (endpoints) for:
- Market breadth data
- Index listing and details
- System status

Design Principles:
1. Views are thin - they handle HTTP request/response only
2. Business logic is in services/, not here
3. Views use serializers for data validation/formatting
4. Proper HTTP status codes and error messages

API Endpoints:
- GET /api/market/breadth/           - All indices breadth data
- GET /api/market/breadth/<index>/   - Single index breadth
- GET /api/market/indices/           - List all tracked indices
- GET /api/market/indices/<symbol>/  - Index details with stocks
- GET /api/market/status/            - System status

Authentication:
All endpoints are public (market data is not sensitive).
For internal status endpoints, consider adding auth in production.

Usage:
    curl http://localhost:8000/api/market/breadth/
==============================================================================
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.conf import settings

from .serializers import (
    MarketBreadthSerializer,
    IndexSerializer,
    IndexDetailSerializer,
    StockBreadthDetailSerializer,
    SystemStatusSerializer,
)

# Set up logger
logger = logging.getLogger(__name__)


class MarketBreadthListView(APIView):
    """
    API endpoint for market breadth data.
    
    GET /api/market/breadth/
    
    Returns breadth data for all tracked indices.
    Data is cached in Redis and updated every 1-2 seconds.
    
    Response:
        [
            {
                "index": "NIFTY 50",
                "bullish": 32,
                "bearish": 18,
                "neutral": 0,
                "total": 50,
                "sentiment_score": 64,
                "last_updated": "2024-01-15T10:30:00"
            },
            ...
        ]
    """
    
    def get(self, request):
        """
        Handle GET request for market breadth.
        
        Fetches data from BreadthCalculator service.
        Uses cached data if available.
        """
        try:
            # Import here to avoid circular imports at module load
            from .services.breadth_calculator import BreadthCalculator
            
            calculator = BreadthCalculator()
            breadth_data = calculator.get_breadth_data()
            
            # Serialize the response
            serializer = MarketBreadthSerializer(breadth_data, many=True)
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error fetching breadth data: {str(e)}")
            return Response(
                {'error': 'Failed to fetch market breadth data'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MarketBreadthDetailView(APIView):
    """
    API endpoint for single index breadth data.
    
    GET /api/market/breadth/<index_name>/
    
    Returns breadth data for a specific index.
    
    URL Parameters:
        index_name: Name of the index (URL encoded)
                   Example: NIFTY%2050 for "NIFTY 50"
    
    Response:
        {
            "index": "NIFTY 50",
            "bullish": 32,
            "bearish": 18,
            "neutral": 0,
            "total": 50,
            "sentiment_score": 64,
            "last_updated": "2024-01-15T10:30:00"
        }
    """
    
    def get(self, request, index_name):
        """
        Handle GET request for single index breadth.
        
        Args:
            request: HTTP request
            index_name: Name of the index from URL
        """
        try:
            from .services.breadth_calculator import BreadthCalculator
            
            calculator = BreadthCalculator()
            breadth_data = calculator.get_breadth_data(index_name)
            
            if not breadth_data or breadth_data.get('total', 0) == 0:
                return Response(
                    {'error': f'Index not found: {index_name}'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = MarketBreadthSerializer(breadth_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error fetching breadth for {index_name}: {str(e)}")
            return Response(
                {'error': 'Failed to fetch market breadth data'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class IndexListView(APIView):
    """
    API endpoint for listing tracked indices.
    
    GET /api/market/indices/
    
    Returns list of all indices being tracked by the system.
    
    Response:
        [
            {
                "name": "NIFTY 50",
                "symbol": "NIFTY",
                "token": "99926000",
                "constituent_count": 50
            },
            ...
        ]
    """
    
    def get(self, request):
        """
        Handle GET request for index list.
        """
        try:
            # Get tracked indices from settings
            indices = getattr(settings, 'TRACKED_INDICES', [])
            
            # Format response
            result = []
            for index in indices:
                result.append({
                    'name': index.get('name'),
                    'symbol': index.get('symbol'),
                    'token': index.get('token'),
                })
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error fetching indices: {str(e)}")
            return Response(
                {'error': 'Failed to fetch indices'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class IndexDetailView(APIView):
    """
    API endpoint for index details with stock breakdown.
    
    GET /api/market/indices/<index_name>/
    
    Returns detailed information about an index including:
    - Index metadata
    - Current breadth data
    - List of all constituent stocks with their status
    
    URL Parameters:
        index_name: Name of the index (URL encoded)
    
    Response:
        {
            "name": "NIFTY 50",
            "symbol": "NIFTY",
            "breadth": {...},
            "stocks": [
                {
                    "symbol": "RELIANCE",
                    "name": "Reliance Industries",
                    "ltp": 2505.50,
                    "change": 15.50,
                    "change_percent": 0.62,
                    "status": "bullish"
                },
                ...
            ]
        }
    """
    
    def get(self, request, index_name):
        """
        Handle GET request for index details.
        """
        try:
            from .services.breadth_calculator import BreadthCalculator
            
            calculator = BreadthCalculator()
            
            # Get breadth data
            breadth_data = calculator.get_breadth_data(index_name)
            
            if not breadth_data or breadth_data.get('total', 0) == 0:
                return Response(
                    {'error': f'Index not found: {index_name}'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get stock details
            stocks = calculator.get_stock_details(index_name)
            
            # Build response
            result = {
                'name': index_name,
                'symbol': index_name.replace(' ', ''),  # Simplified
                'breadth': breadth_data,
                'stocks': stocks,
            }
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error fetching index details for {index_name}: {str(e)}")
            return Response(
                {'error': 'Failed to fetch index details'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SystemStatusView(APIView):
    """
    API endpoint for system status.
    
    GET /api/market/status/
    
    Returns status of all system components:
    - Angel One API connection
    - WebSocket connection
    - Breadth calculator
    
    Useful for:
    - Health monitoring
    - Debugging connection issues
    - Admin dashboard
    
    Response:
        {
            "angel_api_authenticated": true,
            "websocket": {
                "is_connected": true,
                "subscribed_count": 150
            },
            "calculator_running": true,
            "indices_tracked": 10,
            "total_stocks": 500
        }
    """
    
    def get(self, request):
        """
        Handle GET request for system status.
        """
        try:
            from .services.angel_client import AngelOneClient
            from .services.websocket_manager import WebSocketManager
            from .services.breadth_calculator import BreadthCalculator
            
            # Get status from each service
            angel_client = AngelOneClient()
            ws_manager = WebSocketManager()
            calculator = BreadthCalculator()
            
            result = {
                'angel_api_authenticated': angel_client.is_authenticated,
                'websocket': ws_manager.status,
                'calculator_running': calculator.is_running,
                'indices_tracked': calculator.status.get('indices_tracked', 0),
                'total_stocks': calculator.status.get('total_stocks', 0),
                'tracked_indices': list(calculator.index_stocks.keys()),
            }
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error fetching system status: {str(e)}")
            return Response(
                {'error': 'Failed to fetch system status'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['POST'])
def start_market_data_service(request):
    """
    Start market data collection (admin endpoint).
    
    POST /api/market/start/
    
    Initializes:
    1. Angel One API authentication
    2. WebSocket connection
    3. Stock subscriptions
    4. Breadth calculator
    
    This is typically called once at application startup.
    Can also be used to restart after failures.
    
    In production, this would require authentication.
    """
    try:
        from .tasks import initialize_market_data_service
        
        success = initialize_market_data_service()
        
        if success:
            return Response(
                {'message': 'Market data service started successfully'},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'error': 'Failed to start market data service'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        logger.error(f"Error starting market data service: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def stop_market_data_service(request):
    """
    Stop market data collection (admin endpoint).
    
    POST /api/market/stop/
    
    Stops:
    1. WebSocket connection
    2. Breadth calculator
    3. Clears subscriptions
    
    In production, this would require authentication.
    """
    try:
        from .services.websocket_manager import WebSocketManager
        from .services.breadth_calculator import BreadthCalculator
        
        ws_manager = WebSocketManager()
        calculator = BreadthCalculator()
        
        ws_manager.stop()
        calculator.stop()
        
        return Response(
            {'message': 'Market data service stopped'},
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Error stopping market data service: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
