# ==============================================================================
# Realtime App Initialization
# ==============================================================================
# This Django app handles real-time WebSocket communication with the frontend.
#
# Components:
# - consumers.py: WebSocket consumers (like views for WebSocket)
# - routing.py: WebSocket URL routing
# - utils.py: Helper functions
#
# How it works:
# 1. Frontend opens WebSocket connection to /ws/market/
# 2. Consumer handles connection, adds to broadcast group
# 3. BreadthCalculator broadcasts updates to the group
# 4. Consumer sends updates to the frontend
#
# Why Django Channels?
# - Native WebSocket support in Django
# - Uses Redis for message passing
# - Handles multiple connections efficiently
# - Integrates with Django authentication
# ==============================================================================
