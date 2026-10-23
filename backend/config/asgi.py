"""
==============================================================================
ASGI Configuration for Indian Stock Market Dashboard
==============================================================================

ASGI (Asynchronous Server Gateway Interface) configuration for Django.

This file sets up the application to handle:
1. Regular HTTP requests (via Django's standard handling)
2. WebSocket connections (via Django Channels)

The ProtocolTypeRouter routes requests based on their protocol:
- HTTP requests -> Django ASGI application  
- WebSocket requests -> Django Channels routing

This is the entry point for production ASGI servers like:
- Uvicorn: uvicorn config.asgi:application
- Daphne: daphne config.asgi:application

WebSocket connections are critical for this dashboard as they provide
real-time market data updates without polling.
==============================================================================
"""

import os
import django

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Setup Django BEFORE importing anything that uses Django models
# This is required for Django Channels to work properly
django.setup()

# Now we can safely import Django components
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from features.websocket.middleware import JwtAuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

# Import WebSocket URL routing from our realtime app
from features.websocket.routing import websocket_urlpatterns

# Get the standard Django ASGI application for HTTP requests
django_asgi_app = get_asgi_application()

# ==============================================================================
# Main ASGI Application
# ==============================================================================

# ProtocolTypeRouter routes connections based on the protocol type:
# - 'http': Standard HTTP requests handled by Django
# - 'websocket': WebSocket connections handled by Channels

application = ProtocolTypeRouter({
    # HTTP requests are handled by standard Django ASGI application
    # This handles regular REST API calls, admin interface, etc.
    'http': django_asgi_app,
    
    # WebSocket connections go through our custom routing
    # The middleware stack provides:
    # 1. AllowedHostsOriginValidator - validates the Origin header
    # 2. AuthMiddlewareStack - populates scope['user'] from session
    # 3. URLRouter - routes to the appropriate consumer based on URL
    'websocket': AllowedHostsOriginValidator(
        JwtAuthMiddlewareStack(
            URLRouter(
                websocket_urlpatterns
            )
        )
    ),
})

# ==============================================================================
# How WebSocket connections work in this application:
# ==============================================================================
#
# 1. Client (React frontend) opens WebSocket connection to ws://server/ws/market/
#
# 2. ProtocolTypeRouter sees it's a WebSocket and routes to websocket handler
#
# 3. AllowedHostsOriginValidator checks Origin header against ALLOWED_HOSTS
#
# 4. AuthMiddlewareStack authenticates the user (if logged in)
#
# 5. URLRouter matches the URL pattern and routes to MarketDataConsumer
#
# 6. MarketDataConsumer handles the connection in apps/realtime/consumers.py
#
# 7. Consumer joins a broadcast group to receive market data updates
#
# 8. When market data changes, backend broadcasts to all connected clients
#
# ==============================================================================
