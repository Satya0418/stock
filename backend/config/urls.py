"""
==============================================================================
Main URL Configuration for Indian Stock Market Dashboard
==============================================================================

This file defines all HTTP URL routes for the Django application.
WebSocket routes are defined separately in apps/realtime/routing.py

URL Structure:
- /admin/          -> Django admin interface
- /api/market/     -> Market data REST API endpoints
- /api/health/     -> Health check endpoint

All API endpoints are prefixed with /api/ for clarity and future API versioning.
==============================================================================
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    """
    Health check endpoint for monitoring and load balancers.
    
    This endpoint is used by:
    - Load balancers to check if the server is healthy
    - Monitoring systems (Prometheus, DataDog, etc.)
    - Kubernetes liveness/readiness probes
    
    Returns:
        JsonResponse indicating server health status
    """
    return JsonResponse({
        'status': 'healthy',
        'service': 'market-dashboard-backend',
        'version': '1.0.0'
    })


urlpatterns = [
    # Django Admin Interface
    # Access at: http://localhost:8000/admin/
    # Create superuser with: python manage.py createsuperuser
    path('admin/', admin.site.urls),
    
    # Health Check Endpoint
    # Access at: http://localhost:8000/api/health/
    # Used by monitoring tools and load balancers
    path('api/health/', health_check, name='health_check'),
    
    # Auth API
    path('auth/', include('features.auth.urls')),

    # Stock Data API
    path('stocks/', include('features.stock_data.urls')),
]

# ==============================================================================
# URL Pattern Overview:
# ==============================================================================
#
# /admin/                    -> Django Admin (user management, debugging)
# /api/health/               -> Health check for monitoring
# /api/market/breadth/       -> Get current market breadth data
# /api/market/indices/       -> List all tracked indices
# /api/market/indices/<id>/  -> Get specific index details
#
# WebSocket endpoints (defined in apps/realtime/routing.py):
# ws://server/ws/market/     -> Real-time market data stream
#
# ==============================================================================
