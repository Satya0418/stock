"""
==============================================================================
URL Configuration for Market Data API
==============================================================================

This file maps URLs to views for the market data API.

URL Patterns:
    GET  /api/market/breadth/              - All indices breadth
    GET  /api/market/breadth/<index>/      - Single index breadth
    GET  /api/market/indices/              - List tracked indices
    GET  /api/market/indices/<index>/      - Index details with stocks
    GET  /api/market/status/               - System status
    POST /api/market/start/                - Start market data service
    POST /api/market/stop/                 - Stop market data service

Notes:
- All URLs are relative to /api/market/ (prefix defined in main urls.py)
- Index names in URLs should be URL-encoded (spaces become %20)
- POST endpoints are for admin use and should be protected in production

Usage:
    # Fetch all breadth data
    curl http://localhost:8000/api/market/breadth/
    
    # Fetch NIFTY 50 breadth
    curl http://localhost:8000/api/market/breadth/NIFTY%2050/
==============================================================================
"""

from django.urls import path
from . import views

# App name for namespacing
app_name = 'market_data'

urlpatterns = [
    # ===========================================================================
    # Market Breadth Endpoints
    # ===========================================================================
    
    # List breadth for all indices
    # GET /api/market/breadth/
    path(
        'breadth/',
        views.MarketBreadthListView.as_view(),
        name='breadth-list'
    ),
    
    # Get breadth for specific index
    # GET /api/market/breadth/<index_name>/
    path(
        'breadth/<str:index_name>/',
        views.MarketBreadthDetailView.as_view(),
        name='breadth-detail'
    ),
    
    # ===========================================================================
    # Index Endpoints
    # ===========================================================================
    
    # List all tracked indices
    # GET /api/market/indices/
    path(
        'indices/',
        views.IndexListView.as_view(),
        name='index-list'
    ),
    
    # Get specific index with stock breakdown
    # GET /api/market/indices/<index_name>/
    path(
        'indices/<str:index_name>/',
        views.IndexDetailView.as_view(),
        name='index-detail'
    ),
    
    # ===========================================================================
    # System Status Endpoints
    # ===========================================================================
    
    # Get system status
    # GET /api/market/status/
    path(
        'status/',
        views.SystemStatusView.as_view(),
        name='system-status'
    ),
    
    # ===========================================================================
    # Admin Control Endpoints
    # ===========================================================================
    
    # Start market data service
    # POST /api/market/start/
    path(
        'start/',
        views.start_market_data_service,
        name='start-service'
    ),
    
    # Stop market data service  
    # POST /api/market/stop/
    path(
        'stop/',
        views.stop_market_data_service,
        name='stop-service'
    ),
]
