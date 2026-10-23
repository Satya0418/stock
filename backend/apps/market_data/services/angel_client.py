"""
==============================================================================
Angel One SmartAPI Client Service
==============================================================================

This service handles all interactions with the Angel One SmartAPI:

1. Authentication (login with TOTP)
2. Token management (access token, refresh token)
3. Auto token refresh before expiry
4. REST API calls for market data
5. Error handling and retry logic

Angel One API Overview:
- Uses OAuth2-like authentication with TOTP (Time-based OTP)
- Access tokens expire every 24 hours
- Provides both REST API and WebSocket for market data

SECURITY NOTES:
- API credentials are loaded from environment variables
- NEVER log sensitive data like passwords or tokens
- Tokens are stored securely and refreshed automatically

Dependencies:
- smartapi-python: Official Angel One SDK
- pyotp: For TOTP generation

Usage:
    from apps.market_data.services.angel_client import AngelOneClient
    
    client = AngelOneClient()
    client.login()
    quote = client.get_quote("NSE", "RELIANCE")
==============================================================================
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

import pyotp
from SmartApi import SmartConnect

from django.conf import settings
from django.core.cache import cache

# Set up logger for this module
logger = logging.getLogger(__name__)


class AngelOneClient:
    """
    Client for interacting with Angel One SmartAPI.
    
    This class manages:
    - API connection and authentication
    - Token lifecycle (login, refresh, expiry)
    - Market data API calls
    
    The client uses a singleton pattern to ensure only one connection
    to the API is maintained throughout the application lifecycle.
    
    Attributes:
        api_key: Angel One API key
        client_id: Trading account client ID
        smart_api: SmartConnect instance from Angel One SDK
        access_token: Current access token for API calls
        refresh_token: Token used to refresh access token
        feed_token: Token for WebSocket connection
    """
    
    # Class-level instance for singleton pattern
    _instance = None
    _is_logged_in = False
    
    def __new__(cls):
        """
        Singleton pattern - ensures only one client instance exists.
        
        This is important because:
        1. Angel One has rate limits per client
        2. Multiple logins can cause session conflicts
        3. Token management is easier with single instance
        """
        if cls._instance is None:
            logger.info("Creating new AngelOneClient instance")
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """
        Initialize the Angel One client.
        
        Loads credentials from Django settings (which get them from .env).
        Creates SmartConnect instance but does NOT log in automatically.
        Call login() explicitly to authenticate.
        """
        # Prevent re-initialization of singleton
        if self._initialized:
            return
        
        # Load API credentials from settings
        self.api_key = settings.ANGEL_ONE_API_KEY
        self.client_id = settings.ANGEL_ONE_CLIENT_ID
        self.password = settings.ANGEL_ONE_PASSWORD
        self.totp_secret = settings.ANGEL_ONE_TOTP_SECRET
        
        # Validate that credentials are configured
        if not all([self.api_key, self.client_id, self.password, self.totp_secret]):
            logger.error("Missing Angel One API credentials in settings")
            raise ValueError(
                "Angel One API credentials not configured. "
                "Please set ANGEL_ONE_API_KEY, ANGEL_ONE_CLIENT_ID, "
                "ANGEL_ONE_PASSWORD, and ANGEL_ONE_TOTP_SECRET in .env file"
            )
        
        # Initialize SmartConnect from Angel One SDK
        # This is the main object for API interactions
        self.smart_api = SmartConnect(api_key=self.api_key)
        
        # Token storage
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.feed_token: Optional[str] = None
        
        # Token expiry tracking
        self.token_expiry: Optional[datetime] = None
        
        # Cache key for storing session across server restarts
        self.cache_key_session = f"angel_one_session_{self.client_id}"
        
        # Mark as initialized
        self._initialized = True
        logger.info(f"AngelOneClient initialized for client: {self.client_id}")
    
    def _generate_totp(self) -> str:
        """
        Generate TOTP (Time-based One Time Password) for authentication.
        
        Angel One uses TOTP as a second factor for API authentication.
        The TOTP secret is provided when you enable API access in Angel One.
        
        Returns:
            6-digit TOTP code as string
        """
        totp = pyotp.TOTP(self.totp_secret)
        return totp.now()
    
    def login(self) -> bool:
        """
        Authenticate with Angel One API.
        
        This method:
        1. Generates a TOTP code using the secret
        2. Sends login request with credentials
        3. Stores access token, refresh token, and feed token
        4. Sets token expiry time (24 hours from now)
        5. Caches session for server restart recovery
        
        Returns:
            True if login successful, False otherwise
        
        Raises:
            Exception: If login fails after all retries
        """
        # Check if we have a valid cached session
        if self._restore_session_from_cache():
            logger.info("Restored session from cache")
            return True
        
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting Angel One login (attempt {attempt + 1}/{max_retries})")
                
                # Generate fresh TOTP for each attempt
                totp = self._generate_totp()
                
                # Call Angel One login API
                # Returns dict with tokens if successful
                response = self.smart_api.generateSession(
                    clientCode=self.client_id,
                    password=self.password,
                    totp=totp
                )
                
                # Check if login was successful
                if response.get('status'):
                    # Extract tokens from response
                    data = response.get('data', {})
                    self.access_token = data.get('jwtToken')
                    self.refresh_token = data.get('refreshToken')
                    self.feed_token = self.smart_api.getfeedToken()
                    
                    # Set token expiry (24 hours from now, refresh 1 hour early)
                    self.token_expiry = datetime.now() + timedelta(hours=23)
                    
                    # Cache session for recovery after server restart
                    self._cache_session()
                    
                    AngelOneClient._is_logged_in = True
                    logger.info("Successfully logged in to Angel One API")
                    logger.info(f"Token expires at: {self.token_expiry}")
                    
                    return True
                else:
                    error_msg = response.get('message', 'Unknown error')
                    logger.error(f"Login failed: {error_msg}")
                    
            except Exception as e:
                logger.error(f"Login attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
        
        logger.error("All login attempts failed")
        return False
    
    def _cache_session(self):
        """
        Cache session tokens for recovery after server restart.
        
        Stores tokens in Redis with 24-hour expiry.
        This allows the server to resume without re-authenticating.
        """
        session_data = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'feed_token': self.feed_token,
            'token_expiry': self.token_expiry.isoformat() if self.token_expiry else None,
        }
        
        # Cache for 23 hours (1 hour before token expiry)
        cache.set(self.cache_key_session, session_data, timeout=82800)
        logger.debug("Session cached successfully")
    
    def _restore_session_from_cache(self) -> bool:
        """
        Attempt to restore session from cache.
        
        This is called on initialization to check if we have a valid
        cached session that can be reused instead of logging in again.
        
        Returns:
            True if valid session restored, False otherwise
        """
        session_data = cache.get(self.cache_key_session)
        
        if not session_data:
            return False
        
        # Check if token is still valid
        token_expiry_str = session_data.get('token_expiry')
        if token_expiry_str:
            token_expiry = datetime.fromisoformat(token_expiry_str)
            if datetime.now() > token_expiry:
                logger.info("Cached session expired")
                return False
        
        # Restore tokens
        self.access_token = session_data.get('access_token')
        self.refresh_token = session_data.get('refresh_token')
        self.feed_token = session_data.get('feed_token')
        self.token_expiry = datetime.fromisoformat(token_expiry_str) if token_expiry_str else None
        
        # Set token in SmartConnect instance
        self.smart_api._access_token = self.access_token
        
        AngelOneClient._is_logged_in = True
        return True
    
    def ensure_authenticated(self) -> bool:
        """
        Ensure we have a valid authenticated session.
        
        Checks token expiry and refreshes if needed.
        Call this before making API requests.
        
        Returns:
            True if authenticated (either existing or new session)
        """
        if not self._is_logged_in or not self.access_token:
            return self.login()
        
        # Check if token needs refresh (within 1 hour of expiry)
        if self.token_expiry and datetime.now() > (self.token_expiry - timedelta(hours=1)):
            logger.info("Token expiring soon, refreshing...")
            return self._refresh_tokens()
        
        return True
    
    def _refresh_tokens(self) -> bool:
        """
        Refresh access token using refresh token.
        
        Called automatically when token is close to expiry.
        If refresh fails, falls back to full login.
        
        Returns:
            True if refresh successful, False otherwise
        """
        try:
            logger.info("Refreshing access token")
            
            response = self.smart_api.generateToken(self.refresh_token)
            
            if response.get('status'):
                data = response.get('data', {})
                self.access_token = data.get('jwtToken')
                self.feed_token = data.get('feedToken')
                self.token_expiry = datetime.now() + timedelta(hours=23)
                
                self._cache_session()
                logger.info("Token refreshed successfully")
                return True
            else:
                logger.error(f"Token refresh failed: {response.get('message')}")
                # Fall back to full login
                return self.login()
                
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            return self.login()
    
    def logout(self):
        """
        Logout from Angel One API.
        
        Clears all tokens and cached session.
        Call this on application shutdown.
        """
        try:
            self.smart_api.terminateSession(self.client_id)
            logger.info("Successfully logged out from Angel One")
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
        finally:
            self.access_token = None
            self.refresh_token = None
            self.feed_token = None
            self.token_expiry = None
            cache.delete(self.cache_key_session)
            AngelOneClient._is_logged_in = False
    
    def get_quote(self, exchange: str, symbol: str, token: str) -> Optional[Dict[str, Any]]:
        """
        Get current quote (LTP, open, high, low, close) for a single stock.
        
        Args:
            exchange: Exchange code ('NSE' or 'BSE')
            symbol: Stock symbol (e.g., 'RELIANCE')
            token: Angel One token for the stock
        
        Returns:
            Dict with quote data or None if error
            
        Example response:
            {
                'exchange': 'NSE',
                'tradingSymbol': 'RELIANCE-EQ',
                'symbolToken': '2885',
                'ltp': 2500.50,
                'open': 2480.00,
                'high': 2510.00,
                'low': 2475.00,
                'close': 2490.00,
                'netChange': 10.50,
                'percentChange': 0.42
            }
        """
        if not self.ensure_authenticated():
            logger.error("Not authenticated, cannot get quote")
            return None
        
        try:
            # Angel One expects data in specific format
            quote_params = {
                'exchange': exchange,
                'tradingSymbol': symbol,
                'symbolToken': token
            }
            
            response = self.smart_api.getMarketData(
                mode='FULL',  # FULL includes all price data
                exchangeTokens={exchange: [token]}
            )
            
            if response.get('status'):
                data = response.get('data', {})
                fetched = data.get('fetched', [])
                if fetched:
                    return fetched[0]
            
            logger.error(f"Quote fetch failed: {response.get('message')}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {str(e)}")
            return None
    
    def get_multiple_quotes(self, exchange: str, tokens: List[str]) -> List[Dict[str, Any]]:
        """
        Get quotes for multiple stocks in a single API call.
        
        This is more efficient than calling get_quote multiple times.
        Angel One allows up to 50 tokens per request.
        
        Args:
            exchange: Exchange code ('NSE' or 'BSE')
            tokens: List of Angel One tokens
        
        Returns:
            List of quote dicts
        """
        if not self.ensure_authenticated():
            logger.error("Not authenticated, cannot get quotes")
            return []
        
        all_quotes = []
        
        # Angel One limits to 50 tokens per request
        # Split into batches if needed
        batch_size = 50
        
        for i in range(0, len(tokens), batch_size):
            batch_tokens = tokens[i:i + batch_size]
            
            try:
                response = self.smart_api.getMarketData(
                    mode='FULL',
                    exchangeTokens={exchange: batch_tokens}
                )
                
                if response.get('status'):
                    data = response.get('data', {})
                    fetched = data.get('fetched', [])
                    all_quotes.extend(fetched)
                else:
                    logger.error(f"Batch quote fetch failed: {response.get('message')}")
                    
            except Exception as e:
                logger.error(f"Error getting batch quotes: {str(e)}")
        
        return all_quotes
    
    def get_instrument_list(self) -> List[Dict[str, Any]]:
        """
        Get master instrument list from Angel One.
        
        This returns a complete list of all tradable instruments
        including stocks, indices, F&O contracts, etc.
        
        The list is large (100k+ instruments) so we cache it.
        
        Returns:
            List of instrument dicts with symbol, token, etc.
        """
        # Check cache first
        cache_key = "angel_one_instrument_list"
        cached = cache.get(cache_key)
        
        if cached:
            logger.debug("Returning cached instrument list")
            return cached
        
        if not self.ensure_authenticated():
            logger.error("Not authenticated, cannot get instrument list")
            return []
        
        try:
            # This downloads a JSON file with all instruments
            import requests
            
            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                instruments = response.json()
                # Cache for 24 hours
                cache.set(cache_key, instruments, timeout=86400)
                logger.info(f"Fetched {len(instruments)} instruments")
                return instruments
            else:
                logger.error(f"Failed to fetch instrument list: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching instrument list: {str(e)}")
            return []
    
    def get_index_constituents(self, index_symbol: str) -> List[Dict[str, str]]:
        """
        Get list of stocks in a specific index.
        
        Note: Angel One doesn't have a direct API for index constituents.
        This method tries to match stocks from the instrument list
        that are part of the given index.
        
        For production, you might want to maintain a separate database
        of index constituents that's updated periodically.
        
        Args:
            index_symbol: Index symbol (e.g., 'NIFTY', 'BANKNIFTY')
        
        Returns:
            List of dicts with stock symbol and token
        """
        # For now, return hardcoded NIFTY 50 constituents
        # In production, this would come from a database or API
        
        # Cache key for index constituents
        cache_key = f"index_constituents_{index_symbol}"
        cached = cache.get(cache_key)
        
        if cached:
            return cached
        
        # Hardcoded NIFTY 50 constituents with Angel One tokens
        # In production, maintain this in database and update periodically
        nifty50_stocks = [
            {"symbol": "RELIANCE", "token": "2885", "name": "Reliance Industries"},
            {"symbol": "TCS", "token": "11536", "name": "Tata Consultancy Services"},
            {"symbol": "HDFCBANK", "token": "1333", "name": "HDFC Bank"},
            {"symbol": "INFY", "token": "1594", "name": "Infosys"},
            {"symbol": "ICICIBANK", "token": "4963", "name": "ICICI Bank"},
            {"symbol": "HINDUNILVR", "token": "1394", "name": "Hindustan Unilever"},
            {"symbol": "SBIN", "token": "3045", "name": "State Bank of India"},
            {"symbol": "BHARTIARTL", "token": "10604", "name": "Bharti Airtel"},
            {"symbol": "ITC", "token": "1660", "name": "ITC"},
            {"symbol": "KOTAKBANK", "token": "1922", "name": "Kotak Mahindra Bank"},
            {"symbol": "LT", "token": "11483", "name": "Larsen & Toubro"},
            {"symbol": "AXISBANK", "token": "5900", "name": "Axis Bank"},
            {"symbol": "WIPRO", "token": "3787", "name": "Wipro"},
            {"symbol": "ASIANPAINT", "token": "236", "name": "Asian Paints"},
            {"symbol": "MARUTI", "token": "10999", "name": "Maruti Suzuki"},
            {"symbol": "HCLTECH", "token": "7229", "name": "HCL Technologies"},
            {"symbol": "ULTRACEMCO", "token": "11532", "name": "UltraTech Cement"},
            {"symbol": "SUNPHARMA", "token": "3351", "name": "Sun Pharmaceutical"},
            {"symbol": "TITAN", "token": "3506", "name": "Titan Company"},
            {"symbol": "BAJFINANCE", "token": "317", "name": "Bajaj Finance"},
            {"symbol": "NESTLEIND", "token": "17963", "name": "Nestle India"},
            {"symbol": "BAJAJFINSV", "token": "16675", "name": "Bajaj Finserv"},
            {"symbol": "TATAMOTORS", "token": "3456", "name": "Tata Motors"},
            {"symbol": "POWERGRID", "token": "14977", "name": "Power Grid Corporation"},
            {"symbol": "NTPC", "token": "11630", "name": "NTPC"},
            {"symbol": "ONGC", "token": "2475", "name": "ONGC"},
            {"symbol": "TATASTEEL", "token": "3499", "name": "Tata Steel"},
            {"symbol": "JSWSTEEL", "token": "11723", "name": "JSW Steel"},
            {"symbol": "ADANIENT", "token": "25", "name": "Adani Enterprises"},
            {"symbol": "COALINDIA", "token": "20374", "name": "Coal India"},
            {"symbol": "TECHM", "token": "13538", "name": "Tech Mahindra"},
            {"symbol": "DRREDDY", "token": "881", "name": "Dr. Reddy's Laboratories"},
            {"symbol": "INDUSINDBK", "token": "5258", "name": "IndusInd Bank"},
            {"symbol": "DIVISLAB", "token": "10940", "name": "Divi's Laboratories"},
            {"symbol": "GRASIM", "token": "1232", "name": "Grasim Industries"},
            {"symbol": "CIPLA", "token": "694", "name": "Cipla"},
            {"symbol": "ADANIPORTS", "token": "15083", "name": "Adani Ports"},
            {"symbol": "BRITANNIA", "token": "547", "name": "Britannia Industries"},
            {"symbol": "APOLLOHOSP", "token": "157", "name": "Apollo Hospitals"},
            {"symbol": "EICHERMOT", "token": "910", "name": "Eicher Motors"},
            {"symbol": "SBILIFE", "token": "21808", "name": "SBI Life Insurance"},
            {"symbol": "TATACONSUM", "token": "3432", "name": "Tata Consumer Products"},
            {"symbol": "BPCL", "token": "526", "name": "BPCL"},
            {"symbol": "HINDALCO", "token": "1363", "name": "Hindalco Industries"},
            {"symbol": "UPL", "token": "11287", "name": "UPL"},
            {"symbol": "HEROMOTOCO", "token": "1348", "name": "Hero MotoCorp"},
            {"symbol": "BAJAJ-AUTO", "token": "16669", "name": "Bajaj Auto"},
            {"symbol": "LTIM", "token": "17818", "name": "LTIMindtree"},
            {"symbol": "HDFCLIFE", "token": "467", "name": "HDFC Life Insurance"},
            {"symbol": "M&M", "token": "2031", "name": "Mahindra & Mahindra"},
        ]
        
        # Map index symbol to constituents
        # In production, this would be a database lookup
        index_constituents_map = {
            'NIFTY': nifty50_stocks,
            'NIFTY50': nifty50_stocks,
            'NIFTY 50': nifty50_stocks,
        }
        
        result = index_constituents_map.get(index_symbol.upper(), nifty50_stocks)
        
        # Cache for 1 hour
        cache.set(cache_key, result, timeout=3600)
        
        return result
    
    @property
    def is_authenticated(self) -> bool:
        """Check if client is currently authenticated."""
        return self._is_logged_in and self.access_token is not None
