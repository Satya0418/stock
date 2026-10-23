# ==============================================================================
# Market Data App Initialization
# ==============================================================================
# This Django app handles all market data functionality:
#
# 1. Angel One API Integration
#    - Authentication and token management
#    - WebSocket connection for live market data
#    - REST API calls for historical data
#
# 2. Market Breadth Calculation
#    - Processes live price data for each index
#    - Calculates bullish/bearish/neutral counts
#    - Caches results in Redis for fast access
#
# 3. REST API Endpoints
#    - GET /api/market/breadth/ - Current market breadth
#    - GET /api/market/indices/ - List of tracked indices
#
# Key Files:
# - services/angel_client.py: Angel One API client
# - services/websocket_manager.py: Manages Angel One WebSocket
# - services/breadth_calculator.py: Market breadth calculations
# - models.py: Database models for indices and stocks
# - views.py: REST API views
# ==============================================================================
