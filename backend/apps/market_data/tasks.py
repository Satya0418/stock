"""
==============================================================================
Background Tasks and Initialization for Market Data
==============================================================================

This file contains background tasks and initialization functions:

1. Application startup initialization
2. Market data service startup
3. Periodic tasks (if using Celery/APScheduler)
4. Cleanup tasks

Startup Flow:
When Django application starts, these tasks:
1. Authenticate with Angel One API
2. Load index constituent lists
3. Start WebSocket connection
4. Subscribe to all stocks
5. Start breadth calculator

The initialization can be triggered:
- Automatically on server start (via Django AppConfig.ready())
- Manually via REST API endpoint (/api/market/start/)
- Via management command

Why Separate Tasks File?
- Keeps views clean (no initialization logic)
- Can be reused by management commands, signals, etc.
- Easier to test initialization in isolation
- Clear separation of startup vs request handling

Notes:
- Tasks run in a thread pool to not block HTTP requests
- Uses singleton services to ensure single connection
- Handles failures with retry logic
==============================================================================
"""

import logging
import threading
import time
from typing import List, Dict, Any

from django.conf import settings

# Set up logger
logger = logging.getLogger(__name__)


def initialize_market_data_service() -> bool:
    """
    Initialize the complete market data service.
    
    This is the main entry point for starting market data collection.
    
    Steps:
    1. Login to Angel One API
    2. Load stock lists for all tracked indices
    3. Configure breadth calculator with stock mappings
    4. Start WebSocket connection
    5. Subscribe to all stocks
    6. Start breadth calculation and broadcasting
    
    Returns:
        True if initialization successful, False otherwise
    
    Called by:
    - AppConfig.ready() on server startup
    - REST API endpoint for manual restart
    - Management command
    """
    logger.info("=" * 60)
    logger.info("Initializing Market Data Service")
    logger.info("=" * 60)
    
    try:
        # Step 1: Authenticate with Angel One
        logger.info("Step 1: Authenticating with Angel One API...")
        from .services.angel_client import AngelOneClient
        
        client = AngelOneClient()
        if not client.login():
            logger.error("Failed to authenticate with Angel One")
            return False
        logger.info("✓ Angel One authentication successful")
        
        # Step 2: Load index constituents
        logger.info("Step 2: Loading index constituents...")
        indices_config = load_index_configurations(client)
        if not indices_config:
            logger.error("Failed to load index configurations")
            return False
        logger.info(f"✓ Loaded {len(indices_config)} indices")
        
        # Step 3: Configure breadth calculator
        logger.info("Step 3: Configuring breadth calculator...")
        from .services.breadth_calculator import BreadthCalculator
        
        calculator = BreadthCalculator()
        calculator.setup_indices(indices_config)
        logger.info("✓ Breadth calculator configured")
        
        # Step 4: Start WebSocket connection
        logger.info("Step 4: Starting WebSocket connection...")
        from .services.websocket_manager import WebSocketManager
        
        ws_manager = WebSocketManager()
        
        # Register tick callback to process incoming data
        ws_manager.set_tick_callback(calculator.process_tick)
        
        if not ws_manager.start():
            logger.error("Failed to start WebSocket connection")
            return False
        logger.info("✓ WebSocket connection starting...")
        
        # Wait for WebSocket connection
        time.sleep(3)
        
        # Step 5: Subscribe to all stocks
        logger.info("Step 5: Subscribing to stocks...")
        all_tokens = collect_all_tokens(indices_config)
        ws_manager.subscribe(all_tokens)
        logger.info(f"✓ Subscribed to {len(all_tokens)} stocks")
        
        # Step 6: Start breadth calculator
        logger.info("Step 6: Starting breadth calculator...")
        calculator.start()
        logger.info("✓ Breadth calculator started")
        
        logger.info("=" * 60)
        logger.info("Market Data Service initialized successfully!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Error initializing market data service: {str(e)}")
        logger.exception(e)
        return False


def load_index_configurations(client) -> List[Dict[str, Any]]:
    """
    Load stock lists for all tracked indices.
    
    For each index defined in settings.TRACKED_INDICES:
    1. Get list of constituent stocks
    2. Get previous close for each stock (for breadth calculation)
    
    Args:
        client: Authenticated AngelOneClient
    
    Returns:
        List of index configurations with stocks
        [
            {
                'name': 'NIFTY 50',
                'symbol': 'NIFTY',
                'token': '99926000',
                'stocks': [
                    {'symbol': 'RELIANCE', 'token': '2885', 'close': 2500.0},
                    ...
                ]
            },
            ...
        ]
    """
    indices_config = []
    tracked_indices = getattr(settings, 'TRACKED_INDICES', [])
    
    for index in tracked_indices:
        index_name = index.get('name')
        index_symbol = index.get('symbol')
        
        logger.info(f"Loading constituents for {index_name}...")
        
        try:
            # Get constituent stocks for this index
            # Note: Angel One doesn't provide index constituents directly
            # We use a predefined list or external data source
            stocks = client.get_index_constituents(index_symbol)
            
            if stocks:
                # Get current prices (for previous close)
                tokens = [s.get('token') for s in stocks if s.get('token')]
                
                if tokens:
                    quotes = client.get_multiple_quotes('NSE', tokens)
                    
                    # Map quotes to stocks
                    quote_map = {str(q.get('symbolToken', '')): q for q in quotes}
                    
                    for stock in stocks:
                        token = stock.get('token')
                        quote = quote_map.get(token, {})
                        
                        # Get previous close from quote
                        stock['close'] = float(quote.get('close', quote.get('ltp', 0)))
                        stock['ltp'] = float(quote.get('ltp', stock['close']))
                
                indices_config.append({
                    'name': index_name,
                    'symbol': index_symbol,
                    'token': index.get('token'),
                    'stocks': stocks,
                })
                
                logger.info(f"  - {index_name}: {len(stocks)} stocks loaded")
            else:
                logger.warning(f"  - {index_name}: No stocks found")
                
        except Exception as e:
            logger.error(f"Error loading {index_name}: {str(e)}")
    
    return indices_config


def collect_all_tokens(indices_config: List[Dict[str, Any]]) -> List[str]:
    """
    Collect all unique stock tokens from all indices.
    
    A stock can belong to multiple indices (e.g., Reliance is in
    NIFTY 50, 100, 200, 500). We only need to subscribe once.
    
    Args:
        indices_config: List of index configurations
    
    Returns:
        List of unique stock tokens
    """
    all_tokens = set()
    
    for index in indices_config:
        for stock in index.get('stocks', []):
            token = stock.get('token')
            if token:
                all_tokens.add(token)
    
    return list(all_tokens)


def shutdown_market_data_service():
    """
    Gracefully shutdown market data service.
    
    Called on application shutdown to cleanup resources.
    
    Steps:
    1. Stop breadth calculator
    2. Close WebSocket connection
    3. Logout from Angel One
    """
    logger.info("Shutting down market data service...")
    
    try:
        from .services.breadth_calculator import BreadthCalculator
        from .services.websocket_manager import WebSocketManager
        from .services.angel_client import AngelOneClient
        
        # Stop calculator
        calculator = BreadthCalculator()
        calculator.stop()
        
        # Stop WebSocket
        ws_manager = WebSocketManager()
        ws_manager.stop()
        
        # Logout from Angel One
        client = AngelOneClient()
        client.logout()
        
        logger.info("Market data service shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


def start_initialization_thread():
    """
    Start market data initialization in background thread.
    
    This allows Django to start quickly while initialization
    happens in the background.
    
    Used by AppConfig.ready() to avoid blocking server startup.
    """
    def run_initialization():
        # Wait a bit for Django to fully start
        time.sleep(5)
        initialize_market_data_service()
    
    thread = threading.Thread(
        target=run_initialization,
        daemon=True,
        name="MarketDataInit"
    )
    thread.start()
    logger.info("Market data initialization thread started")


# ==============================================================================
# Simulated Data Functions (for development/testing without Angel One)
# ==============================================================================

def generate_mock_breadth_data() -> List[Dict[str, Any]]:
    """
    Generate mock market breadth data for development.
    
    Useful when:
    - Testing without Angel One credentials
    - Frontend development
    - Unit testing
    
    Returns:
        List of mock breadth data for all tracked indices
    """
    import random
    from datetime import datetime
    
    indices = getattr(settings, 'TRACKED_INDICES', [])
    result = []
    
    for index in indices:
        # Random but plausible counts
        total = int(index.get('name', '').split()[-1]) if index.get('name', '').split()[-1].isdigit() else 50
        bullish = random.randint(int(total * 0.3), int(total * 0.7))
        bearish = total - bullish - random.randint(0, 5)
        neutral = total - bullish - bearish
        
        result.append({
            'index': index.get('name'),
            'bullish': max(0, bullish),
            'bearish': max(0, bearish),
            'neutral': max(0, neutral),
            'total': total,
            'sentiment_score': round((bullish / total) * 100) if total > 0 else 50,
            'last_updated': datetime.now().isoformat(),
        })
    
    return result


def start_mock_service():
    """
    Start mock market data service.
    
    For development without Angel One credentials.
    Generates random data and broadcasts it.
    """
    from .services.breadth_calculator import BreadthCalculator
    from django.core.cache import cache
    
    logger.info("Starting MOCK market data service...")
    
    calculator = BreadthCalculator()
    
    # Setup with mock data
    tracked_indices = getattr(settings, 'TRACKED_INDICES', [])
    mock_indices = []
    
    for index in tracked_indices:
        mock_stocks = []
        # Generate some mock stocks
        for i in range(50):
            mock_stocks.append({
                'symbol': f'STOCK{i}',
                'token': str(10000 + i),
                'name': f'Mock Stock {i}',
                'close': 1000 + (i * 10),
            })
        
        mock_indices.append({
            'name': index.get('name'),
            'symbol': index.get('symbol'),
            'token': index.get('token'),
            'stocks': mock_stocks,
        })
    
    calculator.setup_indices(mock_indices)
    
    # Simulate random price changes
    import random
    for token, stock_data in calculator.stock_prices.items():
        close = stock_data.get('close', 1000)
        change_pct = random.uniform(-5, 5)
        ltp = close * (1 + change_pct / 100)
        
        stock_data['ltp'] = round(ltp, 2)
        stock_data['change'] = round(ltp - close, 2)
        stock_data['change_percent'] = round(change_pct, 2)
        stock_data['status'] = 'bullish' if ltp > close else ('bearish' if ltp < close else 'neutral')
    
    # Start broadcasting
    calculator.start()
    
    logger.info("Mock market data service started")
