"""
==============================================================================
Angel One WebSocket Manager Service
==============================================================================

This service manages the real-time WebSocket connection to Angel One API
for receiving live market data (tick-by-tick price updates).

How it works:
1. Connects to Angel One WebSocket server
2. Subscribes to desired stocks/indices
3. Receives tick data (price updates) in real-time
4. Passes tick data to BreadthCalculator for processing
5. Handles disconnections with automatic reconnection

WebSocket vs REST API:
- REST API: Request-response, good for occasional data fetches
- WebSocket: Persistent connection, receives data as it changes
- For live dashboard, WebSocket is essential for 1-2 second updates

Angel One WebSocket provides:
- LTP (Last Traded Price)
- Bid/Ask prices
- Volume
- Open/High/Low/Close

Threading Model:
- WebSocket runs on a background thread
- Main Django app thread handles HTTP requests
- Use Redis pub/sub to communicate between threads

Dependencies:
- smartapi-python: Angel One SDK with WebSocket support
- Redis: For publishing tick data to consumers

Usage:
    from apps.market_data.services.websocket_manager import WebSocketManager
    
    manager = WebSocketManager()
    manager.start()
    manager.subscribe(['2885', '11536'])  # Subscribe to RELIANCE, TCS
==============================================================================
"""

import json
import time
import logging
import threading
from typing import List, Dict, Callable, Optional, Any
from datetime import datetime

from django.conf import settings
from django.core.cache import cache

# Set up logger
logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages Angel One WebSocket connection for live market data.
    
    This class:
    - Creates and maintains WebSocket connection
    - Handles subscription to stocks/indices
    - Processes incoming tick data
    - Implements automatic reconnection on failure
    - Thread-safe for use with Django
    
    Design Pattern: Singleton
    - Only one WebSocket connection should exist
    - Multiple connections could hit rate limits
    
    Attributes:
        angel_client: AngelOneClient instance for tokens
        sws: SmartWebSocket instance
        subscribed_tokens: List of currently subscribed tokens
        is_connected: Connection status flag
        on_tick_callback: Function to call when tick received
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """
        Singleton pattern with thread-safe locking.
        """
        with cls._lock:
            if cls._instance is None:
                logger.info("Creating new WebSocketManager instance")
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """
        Initialize WebSocket manager.
        
        Does NOT connect automatically - call start() to begin.
        """
        if self._initialized:
            return
        
        # Import here to avoid circular imports
        from apps.market_data.services.angel_client import AngelOneClient
        
        self.angel_client = AngelOneClient()
        
        # SmartWebSocket instance (created on start())
        self.sws = None
        
        # Currently subscribed tokens
        self.subscribed_tokens: List[str] = []
        
        # Connection state
        self.is_connected = False
        self.is_connecting = False
        self.should_run = False
        
        # Callback for tick data
        self._on_tick_callback: Optional[Callable] = None
        
        # Reconnection settings
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5  # seconds
        
        # Cache key for storing current prices
        self.cache_key_prefix = "stock_price_"
        
        # WebSocket thread
        self._ws_thread: Optional[threading.Thread] = None
        
        self._initialized = True
        logger.info("WebSocketManager initialized")
    
    def set_tick_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Set callback function for incoming tick data.
        
        The callback receives tick data dict with structure:
        {
            'token': '2885',
            'ltp': 2500.50,
            'open': 2480.00,
            'high': 2510.00,
            'low': 2475.00,
            'close': 2490.00,
            'volume': 1234567,
            'timestamp': datetime
        }
        
        Args:
            callback: Function that processes tick data
        """
        self._on_tick_callback = callback
        logger.debug("Tick callback registered")
    
    def start(self) -> bool:
        """
        Start WebSocket connection.
        
        1. Ensures Angel One client is authenticated
        2. Creates SmartWebSocket instance
        3. Sets up event handlers (open, tick, error, close)
        4. Starts connection in background thread
        
        Returns:
            True if connection started, False if error
        """
        if self.is_connected or self.is_connecting:
            logger.warning("WebSocket already connected or connecting")
            return True
        
        try:
            self.is_connecting = True
            self.should_run = True
            
            # Ensure we're authenticated with Angel One
            if not self.angel_client.ensure_authenticated():
                logger.error("Cannot start WebSocket: not authenticated")
                self.is_connecting = False
                return False
            
            # Import SmartWebSocket from Angel One SDK
            from SmartApi.smartWebSocketV2 import SmartWebSocketV2
            
            # Get tokens needed for WebSocket
            # Note: These come from the login session
            auth_token = self.angel_client.access_token
            feed_token = self.angel_client.feed_token
            api_key = self.angel_client.api_key
            client_code = self.angel_client.client_id
            
            # Create WebSocket instance
            self.sws = SmartWebSocketV2(
                auth_token=auth_token,
                api_key=api_key,
                client_code=client_code,
                feed_token=feed_token
            )
            
            # Register event handlers
            # These are callbacks that Angel One SDK will call
            self.sws.on_open = self._on_open
            self.sws.on_data = self._on_data
            self.sws.on_error = self._on_error
            self.sws.on_close = self._on_close
            
            # Start WebSocket in background thread
            self._ws_thread = threading.Thread(
                target=self._run_websocket,
                daemon=True,  # Thread dies when main program exits
                name="AngelOneWebSocket"
            )
            self._ws_thread.start()
            
            logger.info("WebSocket thread started")
            return True
            
        except Exception as e:
            logger.error(f"Error starting WebSocket: {str(e)}")
            self.is_connecting = False
            return False
    
    def _run_websocket(self):
        """
        Run WebSocket connection (called in background thread).
        
        This method runs continuously while should_run is True.
        Handles reconnection on failure.
        """
        while self.should_run:
            try:
                logger.info("Connecting to Angel One WebSocket...")
                
                # This is blocking - runs until connection closes
                self.sws.connect()
                
            except Exception as e:
                logger.error(f"WebSocket error: {str(e)}")
            
            # If we get here, connection was lost
            if self.should_run:
                self._handle_reconnect()
    
    def _handle_reconnect(self):
        """
        Handle WebSocket reconnection with exponential backoff.
        
        Called when connection is lost unexpectedly.
        Implements exponential backoff to avoid hammering server.
        """
        self.is_connected = False
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > self.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts ({self.max_reconnect_attempts}) reached")
            self.should_run = False
            return
        
        # Exponential backoff: 5s, 10s, 20s, 40s, etc.
        delay = self.reconnect_delay * (2 ** (self.reconnect_attempts - 1))
        delay = min(delay, 300)  # Cap at 5 minutes
        
        logger.info(f"Reconnecting in {delay} seconds (attempt {self.reconnect_attempts})")
        time.sleep(delay)
        
        # Refresh authentication before reconnecting
        self.angel_client.ensure_authenticated()
    
    def _on_open(self, wsapp):
        """
        Called when WebSocket connection is established.
        
        This is a callback from Angel One SDK.
        Re-subscribes to previously subscribed tokens.
        """
        logger.info("WebSocket connection opened")
        self.is_connected = True
        self.is_connecting = False
        self.reconnect_attempts = 0  # Reset on successful connection
        
        # Re-subscribe to tokens if we had subscriptions
        if self.subscribed_tokens:
            logger.info(f"Re-subscribing to {len(self.subscribed_tokens)} tokens")
            self._do_subscribe(self.subscribed_tokens)
    
    def _on_data(self, wsapp, message):
        """
        Called when tick data is received from WebSocket.
        
        This is a callback from Angel One SDK.
        Processes the raw message and calls our tick callback.
        
        Args:
            wsapp: WebSocket app instance
            message: Raw message from WebSocket (binary or JSON)
        """
        try:
            # Parse the tick data
            tick_data = self._parse_tick(message)
            
            if tick_data:
                # Cache the latest price
                self._cache_price(tick_data)
                
                # Call user-defined callback if registered
                if self._on_tick_callback:
                    self._on_tick_callback(tick_data)
                    
        except Exception as e:
            logger.error(f"Error processing tick data: {str(e)}")
    
    def _parse_tick(self, message: Any) -> Optional[Dict[str, Any]]:
        """
        Parse raw WebSocket message into structured tick data.
        
        Angel One WebSocket sends data in specific format.
        This method extracts the fields we need.
        
        Args:
            message: Raw message (could be binary or dict)
        
        Returns:
            Parsed tick data dict or None if parsing fails
        """
        try:
            # Message format depends on subscription mode
            # For FULL mode, we get complete OHLC data
            
            if isinstance(message, dict):
                data = message
            elif isinstance(message, (bytes, str)):
                data = json.loads(message)
            else:
                logger.warning(f"Unknown message type: {type(message)}")
                return None
            
            # Extract relevant fields
            # Field names vary by Angel One API version
            tick = {
                'token': str(data.get('token', '')),
                'symbol': data.get('symbol', ''),
                'ltp': float(data.get('ltp', 0)),
                'open': float(data.get('open', data.get('open_price_of_the_day', 0))),
                'high': float(data.get('high', data.get('high_price_of_the_day', 0))),
                'low': float(data.get('low', data.get('low_price_of_the_day', 0))),
                'close': float(data.get('close', data.get('close_price', 0))),
                'volume': int(data.get('volume', data.get('volume_trade_for_the_day', 0))),
                'timestamp': datetime.now(),
                'exchange': data.get('exchange', 'NSE'),
            }
            
            # Calculate change from previous close
            if tick['close'] > 0:
                tick['change'] = tick['ltp'] - tick['close']
                tick['change_percent'] = (tick['change'] / tick['close']) * 100
            else:
                tick['change'] = 0
                tick['change_percent'] = 0
            
            return tick
            
        except Exception as e:
            logger.error(f"Error parsing tick: {str(e)}, message: {message}")
            return None
    
    def _cache_price(self, tick_data: Dict[str, Any]):
        """
        Cache latest price data in Redis.
        
        Prices are cached with short TTL (60 seconds) since they're
        updated frequently and we need fresh data.
        
        Args:
            tick_data: Processed tick data dict
        """
        token = tick_data.get('token')
        if not token:
            return
        
        cache_key = f"{self.cache_key_prefix}{token}"
        
        # Store full tick data
        cache.set(cache_key, tick_data, timeout=60)
    
    def get_cached_price(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get cached price data for a token.
        
        Args:
            token: Stock token
        
        Returns:
            Cached tick data or None if not found
        """
        cache_key = f"{self.cache_key_prefix}{token}"
        return cache.get(cache_key)
    
    def _on_error(self, wsapp, error):
        """
        Called when WebSocket error occurs.
        
        This is a callback from Angel One SDK.
        Logs the error for debugging.
        """
        logger.error(f"WebSocket error: {error}")
    
    def _on_close(self, wsapp):
        """
        Called when WebSocket connection is closed.
        
        This is a callback from Angel One SDK.
        The _run_websocket method will handle reconnection.
        """
        logger.warning("WebSocket connection closed")
        self.is_connected = False
    
    def subscribe(self, tokens: List[str], exchange: str = 'nse_cm'):
        """
        Subscribe to receive tick data for given tokens.
        
        Angel One WebSocket subscription modes:
        - 1 (LTP): Only last traded price
        - 2 (Quote): LTP + bid/ask
        - 3 (Snap Quote): Full market depth
        
        Args:
            tokens: List of stock tokens to subscribe
            exchange: Exchange segment ('nse_cm' for NSE Cash Market)
        """
        if not self.is_connected:
            logger.warning("Cannot subscribe: WebSocket not connected")
            # Store for subscription when connected
            self.subscribed_tokens.extend(tokens)
            self.subscribed_tokens = list(set(self.subscribed_tokens))  # Deduplicate
            return
        
        self._do_subscribe(tokens, exchange)
    
    def _do_subscribe(self, tokens: List[str], exchange: str = 'nse_cm'):
        """
        Actually perform the subscription (internal method).
        
        Args:
            tokens: List of stock tokens to subscribe
            exchange: Exchange segment
        """
        try:
            # Build subscription list
            # Format depends on Angel One SDK version
            token_list = [
                {
                    'exchangeType': 1,  # NSE = 1, BSE = 2
                    'tokens': tokens
                }
            ]
            
            # Subscribe with mode 3 (Snap Quote) for full data
            # Mode options: 1=LTP, 2=Quote, 3=Snap Quote
            self.sws.subscribe(
                correlation_id='market_breadth',
                mode=3,  # Snap Quote mode for full OHLC
                token_list=token_list
            )
            
            # Track subscribed tokens
            self.subscribed_tokens.extend(tokens)
            self.subscribed_tokens = list(set(self.subscribed_tokens))
            
            logger.info(f"Subscribed to {len(tokens)} tokens")
            
        except Exception as e:
            logger.error(f"Subscription error: {str(e)}")
    
    def unsubscribe(self, tokens: List[str]):
        """
        Unsubscribe from tick data for given tokens.
        
        Args:
            tokens: List of stock tokens to unsubscribe
        """
        if not self.is_connected or not self.sws:
            logger.warning("Cannot unsubscribe: WebSocket not connected")
            return
        
        try:
            token_list = [
                {
                    'exchangeType': 1,
                    'tokens': tokens
                }
            ]
            
            self.sws.unsubscribe(
                correlation_id='market_breadth',
                mode=3,
                token_list=token_list
            )
            
            # Remove from tracked subscriptions
            self.subscribed_tokens = [t for t in self.subscribed_tokens if t not in tokens]
            
            logger.info(f"Unsubscribed from {len(tokens)} tokens")
            
        except Exception as e:
            logger.error(f"Unsubscription error: {str(e)}")
    
    def stop(self):
        """
        Stop WebSocket connection and cleanup.
        
        Call this on application shutdown or when connection is no longer needed.
        """
        logger.info("Stopping WebSocket connection")
        self.should_run = False
        
        if self.sws:
            try:
                self.sws.close_connection()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {str(e)}")
        
        self.is_connected = False
        self.is_connecting = False
        self.subscribed_tokens = []
        
        logger.info("WebSocket stopped")
    
    @property
    def status(self) -> Dict[str, Any]:
        """
        Get current WebSocket status.
        
        Returns:
            Dict with connection status info
        """
        return {
            'is_connected': self.is_connected,
            'is_connecting': self.is_connecting,
            'subscribed_count': len(self.subscribed_tokens),
            'reconnect_attempts': self.reconnect_attempts,
        }
