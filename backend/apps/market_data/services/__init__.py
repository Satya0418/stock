# ==============================================================================
# Services Package Initialization
# ==============================================================================
# This package contains all business logic for market data processing.
# Following clean architecture principles, services are separated from views.
#
# Service Files:
# 1. angel_client.py - Angel One API authentication and REST calls
# 2. websocket_manager.py - Manages Angel One WebSocket connection
# 3. breadth_calculator.py - Calculates market breadth from tick data
#
# Why Separate Services?
# - Views handle HTTP request/response only
# - Services contain reusable business logic
# - Easier to test services in isolation
# - Services can be used by both views and background tasks
# ==============================================================================
