"""
==============================================================================
Realtime App Configuration
==============================================================================

Django AppConfig for the realtime application.

This app handles WebSocket connections for real-time data streaming.
No special initialization needed - the consumers are loaded via routing.py.
==============================================================================
"""

from django.apps import AppConfig


class RealtimeConfig(AppConfig):
    """Configuration class for realtime app."""
    
    name = 'apps.realtime'
    verbose_name = 'Real-time WebSocket'
    default_auto_field = 'django.db.models.BigAutoField'
