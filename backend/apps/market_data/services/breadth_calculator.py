"""
==============================================================================
Market Breadth Calculator Service
==============================================================================

This service calculates market breadth indicators for each index.

What is Market Breadth?
Market breadth measures the number of stocks advancing vs declining
in an index. It's a key sentiment indicator:
- Many advancing stocks = bullish sentiment
- Many declining stocks = bearish sentiment

Calculation Logic:
For each stock in an index:
- Compare LTP (Last Traded Price) vs Previous Close
- If LTP > Close: Bullish (stock is up)
- If LTP < Close: Bearish (stock is down)  
- If LTP = Close: Neutral (unchanged)

Data Flow:
1. WebSocketManager receives tick data from Angel One
2. This service aggregates ticks into breadth data
3. Results are cached in Redis
4. Periodically broadcasted to frontend via Django Channels

Output Format:
{
    "index": "NIFTY 50",
    "bullish": 32,
    "bearish": 18,
    "neutral": 0,
    "total": 50,
    "sentiment_score": 64,  # (bullish/total) * 100
    "last_updated": "2024-01-15T10:30:00"
}

Why This Service?
- Centralizes breadth calculation logic
- Can be used by both WebSocket stream and REST API
- Easy to test and modify calculation logic
- Separates data processing from API/WebSocket concerns

Usage:
    from apps.market_data.services.breadth_calculator import BreadthCalculator
    
    calculator = BreadthCalculator()
    calculator.start()  # Begin processing
    breadth = calculator.get_breadth_data("NIFTY 50")
==============================================================================
"""

import json
import time
import logging
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# Set up logger
logger = logging.getLogger(__name__)


class BreadthCalculator:
    """
    Calculates and broadcasts market breadth data for all tracked indices.
    
    This class:
    - Receives tick data from WebSocketManager
    - Maintains current price state for all subscribed stocks
    - Calculates bullish/bearish/neutral counts per index
    - Caches results in Redis for fast API access
    - Broadcasts updates via Django Channels WebSocket
    
    Design Pattern: Singleton
    - One calculator instance processes all market data
    - Ensures consistent state across the application
    
    Attributes:
        stock_prices: Dict mapping token -> current price data
        index_stocks: Dict mapping index -> list of stock tokens
        is_running: Whether calculator is active
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern with thread-safe locking."""
        with cls._lock:
            if cls._instance is None:
                logger.info("Creating new BreadthCalculator instance")
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """
        Initialize the breadth calculator.
        
        Sets up data structures but doesn't start processing.
        Call start() to begin calculations.
        """
        if self._initialized:
            return
        
        # Current price data for all stocks
        # Key: stock token (str), Value: dict with ltp, close, etc.
        self.stock_prices: Dict[str, Dict[str, Any]] = {}
        
        # Mapping of index to its constituent stock tokens
        # Key: index name, Value: list of stock tokens
        self.index_stocks: Dict[str, List[str]] = {}
        
        # Mapping of stock token to index names
        # A stock can belong to multiple indices
        self.token_to_indices: Dict[str, List[str]] = {}
        
        # Control flags
        self.is_running = False
        self._stop_event = threading.Event()
        
        # Broadcast thread
        self._broadcast_thread: Optional[threading.Thread] = None
        
        # Update interval (how often to broadcast breadth data)
        self.update_interval = getattr(settings, 'MARKET_BREADTH_UPDATE_INTERVAL', 2)
        
        # Cache keys
        self.cache_key_breadth = "market_breadth_all"
        self.cache_key_prefix = "market_breadth_"
        
        # Django Channels group name for WebSocket broadcast
        self.ws_group_name = "market_breadth_updates"
        
        self._initialized = True
        logger.info("BreadthCalculator initialized")
    
    def setup_indices(self, indices: List[Dict[str, Any]]):
        """
        Configure which indices and their stocks to track.
        
        Must be called before start() to set up stock-index mappings.
        
        Args:
            indices: List of index configurations
                [
                    {
                        'name': 'NIFTY 50',
                        'symbol': 'NIFTY',
                        'stocks': [
                            {'symbol': 'RELIANCE', 'token': '2885', 'close': 2500.0},
                            ...
                        ]
                    },
                    ...
                ]
        """
        logger.info(f"Setting up tracking for {len(indices)} indices")
        
        self.index_stocks.clear()
        self.token_to_indices.clear()
        
        for index_config in indices:
            index_name = index_config['name']
            stocks = index_config.get('stocks', [])
            
            # Store stock tokens for this index
            stock_tokens = []
            
            for stock in stocks:
                token = stock.get('token')
                if not token:
                    continue
                
                stock_tokens.append(token)
                
                # Initialize price data with previous close
                self.stock_prices[token] = {
                    'symbol': stock.get('symbol', ''),
                    'name': stock.get('name', ''),
                    'token': token,
                    'ltp': stock.get('close', 0),  # Default to close
                    'close': stock.get('close', 0),
                    'change': 0,
                    'change_percent': 0,
                    'status': 'neutral',  # bullish, bearish, neutral
                }
                
                # Map token to indices (a stock can be in multiple indices)
                if token not in self.token_to_indices:
                    self.token_to_indices[token] = []
                self.token_to_indices[token].append(index_name)
            
            self.index_stocks[index_name] = stock_tokens
            logger.info(f"Configured {index_name} with {len(stock_tokens)} stocks")
    
    def process_tick(self, tick_data: Dict[str, Any]):
        """
        Process a single tick (price update) from WebSocket.
        
        This is the callback function registered with WebSocketManager.
        Called every time a new price update is received.
        
        Args:
            tick_data: Dict with price data
                {
                    'token': '2885',
                    'ltp': 2505.50,
                    'close': 2500.00,
                    ...
                }
        """
        token = str(tick_data.get('token', ''))
        
        if not token:
            return
        
        # Get current stored data for this token
        current_data = self.stock_prices.get(token)
        
        if current_data is None:
            # Unknown token, not tracking this stock
            return
        
        # Update price data
        ltp = float(tick_data.get('ltp', 0))
        close = float(tick_data.get('close', current_data.get('close', 0)))
        
        # Use stored close if not provided in tick
        if close == 0:
            close = current_data.get('close', ltp)
        
        # Calculate change
        if close > 0:
            change = ltp - close
            change_percent = (change / close) * 100
        else:
            change = 0
            change_percent = 0
        
        # Determine bullish/bearish/neutral status
        if ltp > close:
            status = 'bullish'
        elif ltp < close:
            status = 'bearish'
        else:
            status = 'neutral'
        
        # Update stored data
        self.stock_prices[token].update({
            'ltp': ltp,
            'close': close,
            'change': round(change, 2),
            'change_percent': round(change_percent, 2),
            'status': status,
            'last_updated': datetime.now().isoformat(),
        })
    
    def calculate_breadth(self, index_name: str) -> Dict[str, Any]:
        """
        Calculate market breadth for a specific index.
        
        Counts stocks that are bullish, bearish, and neutral
        based on current price vs previous close.
        
        Args:
            index_name: Name of the index (e.g., 'NIFTY 50')
        
        Returns:
            Dict with breadth data:
            {
                'index': 'NIFTY 50',
                'bullish': 32,
                'bearish': 18,
                'neutral': 0,
                'total': 50,
                'sentiment_score': 64,
                'last_updated': '2024-01-15T10:30:00'
            }
        """
        stock_tokens = self.index_stocks.get(index_name, [])
        
        if not stock_tokens:
            logger.warning(f"No stocks configured for index: {index_name}")
            return {
                'index': index_name,
                'bullish': 0,
                'bearish': 0,
                'neutral': 0,
                'total': 0,
                'sentiment_score': 50,
                'last_updated': datetime.now().isoformat(),
            }
        
        # Count by status
        bullish = 0
        bearish = 0
        neutral = 0
        
        for token in stock_tokens:
            stock_data = self.stock_prices.get(token, {})
            status = stock_data.get('status', 'neutral')
            
            if status == 'bullish':
                bullish += 1
            elif status == 'bearish':
                bearish += 1
            else:
                neutral += 1
        
        total = len(stock_tokens)
        
        # Calculate sentiment score (0-100)
        # 100 = all bullish, 0 = all bearish, 50 = balanced
        if total > 0:
            sentiment_score = round((bullish / total) * 100)
        else:
            sentiment_score = 50
        
        return {
            'index': index_name,
            'bullish': bullish,
            'bearish': bearish,
            'neutral': neutral,
            'total': total,
            'sentiment_score': sentiment_score,
            'last_updated': datetime.now().isoformat(),
        }
    
    def calculate_all_breadth(self) -> List[Dict[str, Any]]:
        """
        Calculate market breadth for all configured indices.
        
        Returns:
            List of breadth data dicts for all indices
        """
        results = []
        
        for index_name in self.index_stocks.keys():
            breadth = self.calculate_breadth(index_name)
            results.append(breadth)
        
        return results
    
    def get_breadth_data(self, index_name: Optional[str] = None) -> Any:
        """
        Get cached or fresh market breadth data.
        
        Tries cache first, falls back to calculation if cache miss.
        
        Args:
            index_name: Optional index name. If None, returns all indices.
        
        Returns:
            Breadth data dict or list of dicts
        """
        if index_name:
            # Get single index
            cache_key = f"{self.cache_key_prefix}{index_name}"
            cached = cache.get(cache_key)
            
            if cached:
                return cached
            
            return self.calculate_breadth(index_name)
        else:
            # Get all indices
            cached = cache.get(self.cache_key_breadth)
            
            if cached:
                return cached
            
            return self.calculate_all_breadth()
    
    def start(self):
        """
        Start the breadth calculator.
        
        Begins the background thread that:
        1. Periodically calculates breadth for all indices
        2. Caches results in Redis
        3. Broadcasts updates via WebSocket
        """
        if self.is_running:
            logger.warning("BreadthCalculator already running")
            return
        
        self.is_running = True
        self._stop_event.clear()
        
        # Start broadcast thread
        self._broadcast_thread = threading.Thread(
            target=self._broadcast_loop,
            daemon=True,
            name="BreadthBroadcast"
        )
        self._broadcast_thread.start()
        
        logger.info(f"BreadthCalculator started (interval: {self.update_interval}s)")
    
    def _broadcast_loop(self):
        """
        Background loop that calculates and broadcasts breadth data.
        
        Runs every update_interval seconds while is_running is True.
        """
        logger.info("Broadcast loop started")
        
        while not self._stop_event.is_set():
            try:
                # Calculate breadth for all indices
                breadth_data = self.calculate_all_breadth()
                
                # Cache the results
                self._cache_results(breadth_data)
                
                # Broadcast via WebSocket
                self._broadcast_to_websocket(breadth_data)
                
            except Exception as e:
                logger.error(f"Error in broadcast loop: {str(e)}")
            
            # Wait for next interval
            self._stop_event.wait(self.update_interval)
        
        logger.info("Broadcast loop stopped")
    
    def _cache_results(self, breadth_data: List[Dict[str, Any]]):
        """
        Cache breadth results in Redis.
        
        Caches both:
        1. All breadth data together (for list endpoint)
        2. Individual index data (for detail endpoint)
        
        Args:
            breadth_data: List of breadth data dicts
        """
        # Cache all data
        cache.set(self.cache_key_breadth, breadth_data, timeout=60)
        
        # Cache individual indices
        for data in breadth_data:
            index_name = data.get('index')
            if index_name:
                cache_key = f"{self.cache_key_prefix}{index_name}"
                cache.set(cache_key, data, timeout=60)
    
    def _broadcast_to_websocket(self, breadth_data: List[Dict[str, Any]]):
        """
        Broadcast breadth data to connected WebSocket clients.
        
        Uses Django Channels to send data to all clients
        subscribed to the 'market_breadth_updates' group.
        
        Args:
            breadth_data: List of breadth data dicts to broadcast
        """
        try:
            # Get Django Channels layer
            channel_layer = get_channel_layer()
            
            if channel_layer is None:
                logger.warning("No channel layer configured")
                return
            
            # Prepare message
            message = {
                'type': 'market_breadth_update',  # Must match handler method name
                'data': breadth_data,
                'timestamp': datetime.now().isoformat(),
            }
            
            # Send to group (all connected clients)
            # async_to_sync wraps the async channel layer method
            async_to_sync(channel_layer.group_send)(
                self.ws_group_name,
                message
            )
            
            logger.debug(f"Broadcasted breadth data for {len(breadth_data)} indices")
            
        except Exception as e:
            logger.error(f"Error broadcasting to WebSocket: {str(e)}")
    
    def stop(self):
        """
        Stop the breadth calculator.
        
        Stops the broadcast thread and cleans up.
        """
        logger.info("Stopping BreadthCalculator")
        self.is_running = False
        self._stop_event.set()
        
        if self._broadcast_thread and self._broadcast_thread.is_alive():
            self._broadcast_thread.join(timeout=5)
        
        logger.info("BreadthCalculator stopped")
    
    def get_stock_details(self, index_name: str) -> List[Dict[str, Any]]:
        """
        Get detailed stock-level data for an index.
        
        Returns all stocks with their current status.
        Useful for drill-down views.
        
        Args:
            index_name: Index name
        
        Returns:
            List of stock details
        """
        stock_tokens = self.index_stocks.get(index_name, [])
        
        result = []
        for token in stock_tokens:
            stock_data = self.stock_prices.get(token, {})
            if stock_data:
                result.append({
                    'symbol': stock_data.get('symbol'),
                    'name': stock_data.get('name'),
                    'ltp': stock_data.get('ltp'),
                    'change': stock_data.get('change'),
                    'change_percent': stock_data.get('change_percent'),
                    'status': stock_data.get('status'),
                })
        
        # Sort by change percent (most bullish first)
        result.sort(key=lambda x: x.get('change_percent', 0), reverse=True)
        
        return result
    
    @property
    def status(self) -> Dict[str, Any]:
        """
        Get calculator status.
        
        Returns:
            Dict with status information
        """
        return {
            'is_running': self.is_running,
            'indices_tracked': len(self.index_stocks),
            'total_stocks': len(self.stock_prices),
            'update_interval': self.update_interval,
        }
