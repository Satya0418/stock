"""
==============================================================================
Market Data App Configuration
==============================================================================

Django AppConfig for the market_data application.

This file:
1. Defines app metadata (name, verbose name)
2. Contains the ready() hook for startup tasks
3. Initializes market data service on server start

The ready() method is called once when Django starts.
We use it to start the market data collection service.

Auto-start Behavior:
- When Django starts, ready() is called
- We start initialization in a background thread
- This allows Django to start quickly
- Market data begins streaming after ~5 seconds

Disable Auto-start:
Set environment variable: DISABLE_MARKET_DATA_AUTOSTART=true
This is useful for:
- Running migrations
- Testing
- Development without Angel One credentials
==============================================================================
"""

import os
import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class MarketDataConfig(AppConfig):
    """
    Configuration class for market_data app.
    """
    
    # Full Python path to the app
    name = 'apps.market_data'
    
    # Human-readable name for admin
    verbose_name = 'Market Data'
    
    # Use BigAutoField for primary keys
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        """
        Called when Django app is ready.
        
        This is where we initialize the market data service.
        Uses a background thread to not block server startup.
        
        Note: ready() can be called twice in development
        due to Django's auto-reloader. We handle this by
        checking an environment variable.
        """
        # Check for RUN_MAIN to handle Django's auto-reloader
        # Without this, initialization runs twice in development
        run_main = os.environ.get('RUN_MAIN')
        
        # In development (with runserver), RUN_MAIN is 'true' on the reloaded process
        # We only want to run initialization once
        if run_main == 'true' or not self._is_dev_server():
            self._initialize_service()
    
    def _is_dev_server(self) -> bool:
        """
        Check if running with Django development server.
        
        Returns:
            True if using runserver command
        """
        import sys
        return 'runserver' in sys.argv
    
    def _initialize_service(self):
        """
        Start market data service initialization.
        
        Checks for disable flag and starts in background thread.
        """
        # Check if auto-start is disabled
        if os.environ.get('DISABLE_MARKET_DATA_AUTOSTART', '').lower() == 'true':
            logger.info("Market data auto-start disabled via environment variable")
            return
        
        # Check if running management commands that shouldn't start service
        import sys
        skip_commands = ['migrate', 'makemigrations', 'collectstatic', 'createsuperuser', 'shell']
        if any(cmd in sys.argv for cmd in skip_commands):
            logger.info(f"Skipping market data service for management command")
            return
        
        logger.info("Starting market data service initialization...")
        
        try:
            # Import and start in background thread
            from .tasks import start_initialization_thread
            start_initialization_thread()
            
        except Exception as e:
            logger.error(f"Error starting market data initialization: {str(e)}")
            # Don't raise - let Django continue starting
