"""
==============================================================================
WebSocket Consumers for Real-time Market Data
==============================================================================

Consumers are like Django views but for WebSocket connections.
Instead of handling HTTP requests, they handle WebSocket events:
- connect: Client opens connection
- disconnect: Client closes connection
- receive: Client sends a message

How Data Flows:
1. Client connects to ws://server/ws/market/
2. Consumer adds client to "market_breadth_updates" group
3. BreadthCalculator sends updates to the group
4. Consumer receives group message and forwards to client

Groups:
Django Channels uses "groups" to broadcast to multiple clients.
All clients interested in market data join the same group.
When we send to the group, all connected clients receive it.

Example Client Connection (JavaScript):
    const ws = new WebSocket('ws://localhost:8000/ws/market/');
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Market update:', data);
    };

Message Format (Server to Client):
{
    "type": "market_breadth",
    "data": [
        {"index": "NIFTY 50", "bullish": 32, ...},
        ...
    ],
    "timestamp": "2024-01-15T10:30:00"
}

Dependencies:
- channels: Django Channels library
- channels_redis: Redis backend for Channels

Usage:
    This file is imported by routing.py which maps URLs to consumers.
    The consumer is instantiated for each WebSocket connection.
==============================================================================
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async

# Set up logger
logger = logging.getLogger(__name__)


class MarketDataConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time market breadth data.
    
    This consumer:
    - Accepts WebSocket connections from frontend clients
    - Adds clients to broadcast group for market updates
    - Sends initial data when client connects
    - Forwards broadcast updates to connected clients
    - Handles client disconnect and cleanup
    
    Attributes:
        room_group_name: Name of the Channels group for broadcasting
    """
    
    # Group name must match what BreadthCalculator uses
    room_group_name = "market_breadth_updates"
    
    async def connect(self):
        """
        Handle WebSocket connection.
        
        Called when a client opens a WebSocket connection.
        
        Steps:
        1. Accept the connection
        2. Add client to broadcast group
        3. Send initial market data
        
        Note: This method must accept() the connection or the client
        will get a connection refused error.
        """
        # Get connection info for logging
        # self.scope is like request object for WebSocket
        user = self.scope.get('user', None)
        client_ip = self.scope.get('client', ['unknown'])[0]
        
        logger.info(f"WebSocket connect from {client_ip}")
        
        # Join market updates group
        # channel_name is unique identifier for this connection
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Accept the WebSocket connection
        # Must be called to establish the connection
        await self.accept()
        
        logger.info(f"WebSocket accepted, channel: {self.channel_name}")
        
        # Send initial data immediately on connect
        await self.send_initial_data()
    
    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.
        
        Called when client closes connection or connection is lost.
        
        Args:
            close_code: WebSocket close code (1000 = normal, etc.)
        """
        logger.info(f"WebSocket disconnect, channel: {self.channel_name}, code: {close_code}")
        
        # Leave broadcast group
        # This ensures we don't try to send to closed connections
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data=None, bytes_data=None):
        """
        Handle message received from client.
        
        For this application, client mainly receives data.
        But we could support commands like:
        - subscribe: Subscribe to specific index
        - unsubscribe: Unsubscribe from index
        - ping: Heartbeat
        
        Args:
            text_data: Text message from client (JSON string)
            bytes_data: Binary message from client
        """
        if text_data:
            try:
                message = json.loads(text_data)
                message_type = message.get('type', '')
                
                logger.debug(f"Received message: {message_type}")
                
                if message_type == 'ping':
                    # Respond to ping with pong (heartbeat)
                    await self.send_json({
                        'type': 'pong',
                        'timestamp': datetime.now().isoformat()
                    })
                    
                elif message_type == 'subscribe':
                    # Client requesting specific data
                    # Could be used to subscribe to specific indices
                    indices = message.get('indices', [])
                    await self.handle_subscribe(indices)
                    
                elif message_type == 'refresh':
                    # Client requesting fresh data
                    await self.send_initial_data()
                    
                else:
                    logger.warning(f"Unknown message type: {message_type}")
                    
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {text_data[:100]}")
    
    async def send_initial_data(self):
        """
        Send current market breadth data to newly connected client.
        
        Called immediately after connection is accepted.
        Provides instant data so client doesn't wait for next broadcast.
        """
        try:
            # Fetch current breadth data from calculator
            breadth_data = await self.get_current_breadth()
            
            # Send to this client only
            await self.send_json({
                'type': 'market_breadth',
                'data': breadth_data,
                'timestamp': datetime.now().isoformat(),
                'is_initial': True,  # Flag indicating this is initial data
            })
            
            logger.debug(f"Sent initial data with {len(breadth_data)} indices")
            
        except Exception as e:
            logger.error(f"Error sending initial data: {str(e)}")
    
    @database_sync_to_async
    def get_current_breadth(self):
        """
        Get current market breadth data from BreadthCalculator.
        
        Uses database_sync_to_async because BreadthCalculator
        is not async-aware (uses Redis sync client).
        
        Returns:
            List of breadth data dicts
        """
        from apps.market_data.services.breadth_calculator import BreadthCalculator
        
        calculator = BreadthCalculator()
        return calculator.get_breadth_data()
    
    async def handle_subscribe(self, indices: list):
        """
        Handle client subscription request.
        
        For now, all clients receive all index data.
        This could be extended to filter data per client.
        
        Args:
            indices: List of index names to subscribe to
        """
        # Acknowledge subscription
        await self.send_json({
            'type': 'subscribed',
            'indices': indices,
            'message': f'Subscribed to {len(indices)} indices'
        })
    
    async def market_breadth_update(self, event):
        """
        Handle broadcast messages from BreadthCalculator.
        
        This method is called when BreadthCalculator sends a message
        to the 'market_breadth_updates' group.
        
        The method name MUST match the 'type' field in the message.
        BreadthCalculator sends: {'type': 'market_breadth_update', ...}
        So this method must be named: market_breadth_update
        
        Args:
            event: Dict with broadcast message data
                {
                    'type': 'market_breadth_update',
                    'data': [breadth_data...],
                    'timestamp': '2024-01-15T10:30:00'
                }
        """
        # Extract data from event
        data = event.get('data', [])
        timestamp = event.get('timestamp', datetime.now().isoformat())
        
        # Forward to client
        await self.send_json({
            'type': 'market_breadth',
            'data': data,
            'timestamp': timestamp,
            'is_initial': False,
        })
    
    async def send_json(self, content: Dict[str, Any]):
        """
        Send JSON data to the client.
        
        Convenience method that serializes dict to JSON string.
        
        Args:
            content: Dict to send as JSON
        """
        await self.send(text_data=json.dumps(content))


class SystemStatusConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for system status updates.
    
    Provides real-time system health information:
    - WebSocket connection status
    - API authentication status
    - Data service status
    
    Useful for admin dashboard to monitor system health.
    """
    
    room_group_name = "system_status_updates"
    
    async def connect(self):
        """Accept connection and join status group."""
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        await self.send_status()
    
    async def disconnect(self, close_code):
        """Leave status group on disconnect."""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data=None, bytes_data=None):
        """Handle status request from client."""
        if text_data:
            try:
                message = json.loads(text_data)
                if message.get('type') == 'refresh':
                    await self.send_status()
            except json.JSONDecodeError:
                pass
    
    async def send_status(self):
        """Send current system status to client."""
        status = await self.get_system_status()
        await self.send(text_data=json.dumps({
            'type': 'system_status',
            'data': status,
            'timestamp': datetime.now().isoformat()
        }))
    
    @database_sync_to_async
    def get_system_status(self):
        """Fetch status from all services."""
        from apps.market_data.services.angel_client import AngelOneClient
        from apps.market_data.services.websocket_manager import WebSocketManager
        from apps.market_data.services.breadth_calculator import BreadthCalculator
        
        try:
            angel_client = AngelOneClient()
            ws_manager = WebSocketManager()
            calculator = BreadthCalculator()
            
            return {
                'angel_api_authenticated': angel_client.is_authenticated,
                'websocket': ws_manager.status,
                'calculator': calculator.status,
            }
        except Exception as e:
            return {'error': str(e)}
    
    async def system_status_update(self, event):
        """Handle broadcast status updates."""
        await self.send(text_data=json.dumps({
            'type': 'system_status',
            'data': event.get('data', {}),
            'timestamp': event.get('timestamp', datetime.now().isoformat())
        }))
