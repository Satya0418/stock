"""
==============================================================================
WebSocket URL Routing for Real-time Features
==============================================================================

This file maps WebSocket URLs to consumers (like urls.py for HTTP).

WebSocket URL Format:
- ws://localhost:8000/ws/market/     (development, no SSL)
- wss://example.com/ws/market/        (production, with SSL)

URL Patterns:
- /ws/market/      -> MarketDataConsumer (market breadth updates)
- /ws/status/      -> SystemStatusConsumer (system health)

How it integrates:
1. Client opens WebSocket to ws://server/ws/market/
2. Django sees it's a WebSocket (not HTTP)
3. ASGI ProtocolTypeRouter routes to 'websocket' handler
4. URLRouter matches URL to MarketDataConsumer
5. Consumer handles the connection

Note: WebSocket URLs are prefixed with /ws/ to distinguish from HTTP URLs.
This is a convention, not required by Django.

The routing is imported by config/asgi.py which sets up the ASGI application.

Example Frontend Connection:
    const socket = new WebSocket('ws://localhost:8000/ws/market/');
    
    socket.onopen = () => console.log('Connected!');
    socket.onmessage = (e) => console.log('Data:', JSON.parse(e.data));
    socket.onerror = (e) => console.error('Error:', e);
    socket.onclose = () => console.log('Disconnected');
==============================================================================
"""

from django.urls import re_path, path
from . import consumers

# WebSocket URL patterns
# These are matched against the WebSocket connection URL

websocket_urlpatterns = [
    # Market data WebSocket
    # Connect to: ws://localhost:8000/ws/market/
    # Receives: Real-time market breadth updates
    path(
        'ws/market/',
        consumers.MarketDataConsumer.as_asgi(),
    ),
    
    # System status WebSocket
    # Connect to: ws://localhost:8000/ws/status/
    # Receives: System health updates (for admin dashboard)
    path(
        'ws/status/',
        consumers.SystemStatusConsumer.as_asgi(),
    ),
    
    # Alternative pattern with regex (if needed for parameters)
    # Example: ws://localhost:8000/ws/index/NIFTY%2050/
    # re_path(
    #     r'ws/index/(?P<index_name>\w+)/$',
    #     consumers.IndexDataConsumer.as_asgi(),
    # ),
]

# ==============================================================================
# URL Pattern Explanation:
# ==============================================================================
#
# path() vs re_path():
# - path(): Simple string matching (recommended for most cases)
# - re_path(): Regex pattern matching (for complex URLs)
#
# .as_asgi():
# - Converts consumer class to ASGI application
# - Required for Django Channels routing
# - Similar to .as_view() for class-based views
#
# Trailing slash:
# - Include trailing slash for consistency
# - Configure APPEND_SLASH in settings if needed
#
# ==============================================================================
