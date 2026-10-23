# ==============================================================================
# Apps Package Initialization
# ==============================================================================
# This directory contains all custom Django applications for the project.
# Each app is a self-contained module with specific functionality:
#
# - market_data: Angel One API integration, market breadth calculations
# - realtime: Django Channels WebSocket consumers for live updates
#
# Apps follow Django's app structure:
# - models.py: Database models
# - views.py: API views/endpoints
# - serializers.py: Data serialization for REST API
# - services/: Business logic (separated from views)
# - urls.py: URL routing for this app
# ==============================================================================
