"""
==============================================================================
Utility Functions for Real-time Features
==============================================================================

Helper functions for WebSocket and real-time communication.

Functions included:
- broadcast_to_group: Send message to all clients in a group
- get_connected_clients: Get count of connected WebSocket clients
- format_market_message: Format market data for WebSocket transmission

Usage:
    from apps.realtime.utils import broadcast_to_group
    
    await broadcast_to_group(
        'market_breadth_updates',
        {'type': 'market_breadth', 'data': [...]}
    )
==============================================================================
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# Set up logger
logger = logging.getLogger(__name__)


def broadcast_to_group(group_name: str, message: Dict[str, Any]) -> bool:
    """
    Broadcast a message to all clients in a Channels group.
    
    This is a synchronous wrapper around the async channel layer.
    Use this from non-async code (views, services, etc.)
    
    Args:
        group_name: Name of the Channels group
        message: Dict with message data
                Must include 'type' field matching consumer method name
    
    Returns:
        True if broadcast successful, False otherwise
    
    Example:
        broadcast_to_group('market_breadth_updates', {
            'type': 'market_breadth_update',  # Matches consumer method
            'data': [{'index': 'NIFTY 50', ...}],
            'timestamp': '2024-01-15T10:30:00'
        })
    """
    try:
        channel_layer = get_channel_layer()
        
        if channel_layer is None:
            logger.warning("No channel layer configured - broadcast skipped")
            return False
        
        # async_to_sync wraps the async method for use in sync code
        async_to_sync(channel_layer.group_send)(group_name, message)
        
        logger.debug(f"Broadcast to group '{group_name}' successful")
        return True
        
    except Exception as e:
        logger.error(f"Error broadcasting to group '{group_name}': {str(e)}")
        return False


def format_market_breadth_message(
    breadth_data: List[Dict[str, Any]],
    is_initial: bool = False
) -> Dict[str, Any]:
    """
    Format market breadth data for WebSocket transmission.
    
    Ensures consistent message structure for all broadcasts.
    
    Args:
        breadth_data: List of breadth data dicts
        is_initial: Whether this is initial data on connect
    
    Returns:
        Formatted message dict ready for broadcast
    """
    return {
        'type': 'market_breadth_update',  # Must match consumer method name
        'data': breadth_data,
        'timestamp': datetime.now().isoformat(),
        'is_initial': is_initial,
    }


def format_system_status_message(status_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format system status data for WebSocket transmission.
    
    Args:
        status_data: Dict with system status information
    
    Returns:
        Formatted message dict ready for broadcast
    """
    return {
        'type': 'system_status_update',  # Must match consumer method name
        'data': status_data,
        'timestamp': datetime.now().isoformat(),
    }


def broadcast_market_breadth(breadth_data: List[Dict[str, Any]]) -> bool:
    """
    Convenience function to broadcast market breadth data.
    
    Formats the data and sends to the market breadth group.
    
    Args:
        breadth_data: List of breadth data dicts
    
    Returns:
        True if broadcast successful
    """
    message = format_market_breadth_message(breadth_data)
    return broadcast_to_group('market_breadth_updates', message)


def broadcast_system_status(status_data: Dict[str, Any]) -> bool:
    """
    Convenience function to broadcast system status.
    
    Formats the data and sends to the system status group.
    
    Args:
        status_data: Dict with system status information
    
    Returns:
        True if broadcast successful
    """
    message = format_system_status_message(status_data)
    return broadcast_to_group('system_status_updates', message)


class WebSocketMetrics:
    """
    Track WebSocket connection metrics.
    
    Provides insights into:
    - Number of connected clients
    - Message counts
    - Error counts
    
    Note: This is a simple in-memory tracker.
    For production, use Redis or a proper metrics system.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.connections = 0
        self.total_connections = 0
        self.messages_sent = 0
        self.errors = 0
        
        self._initialized = True
    
    def connection_opened(self):
        """Record a new connection."""
        self.connections += 1
        self.total_connections += 1
    
    def connection_closed(self):
        """Record a connection close."""
        self.connections = max(0, self.connections - 1)
    
    def message_sent(self):
        """Record a message sent."""
        self.messages_sent += 1
    
    def error_occurred(self):
        """Record an error."""
        self.errors += 1
    
    @property
    def stats(self) -> Dict[str, int]:
        """Get current statistics."""
        return {
            'active_connections': self.connections,
            'total_connections': self.total_connections,
            'messages_sent': self.messages_sent,
            'errors': self.errors,
        }


# Global metrics instance
metrics = WebSocketMetrics()
