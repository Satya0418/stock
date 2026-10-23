import logging
from typing import List, Dict

import pyotp
from django.conf import settings

try:
    from SmartApi import SmartConnect
except ImportError:  # pragma: no cover
    SmartConnect = None

from features.auth.services.credentials import get_decrypted_credentials, get_any_active_credentials
from features.auth.services.crypto import CredentialCryptoError
from .session_store import store_session, get_session, session_is_stale

logger = logging.getLogger(__name__)


class AngelOneClient:
    def __init__(self):
        self.client = None
        self.session = {}

    def _build_client(self, api_key: str):
        if SmartConnect is None:
            raise RuntimeError('smartapi-python is not installed')
        self.client = SmartConnect(api_key=api_key)

    def _load_credentials(self) -> Dict[str, str]:
        service_user_id = getattr(settings, 'ANGEL_ONE_SERVICE_USER_ID', None)
        try:
            creds = get_decrypted_credentials(user_id=service_user_id)
            if not creds and not service_user_id:
                creds = get_any_active_credentials()
        except CredentialCryptoError:
            creds = {}
        if not creds:
            creds = {
                'api_key': settings.ANGEL_ONE_API_KEY,
                'client_id': settings.ANGEL_ONE_CLIENT_ID,
                'password': settings.ANGEL_ONE_PASSWORD,
                'totp_secret': settings.ANGEL_ONE_TOTP_SECRET,
            }
        return creds

    def login(self) -> Dict[str, str]:
        creds = self._load_credentials()
        if not creds.get('api_key'):
            raise RuntimeError('Angel One API credentials are not configured')

        self._build_client(creds['api_key'])
        totp = pyotp.TOTP(creds['totp_secret']).now()
        response = self.client.generateSession(creds['client_id'], creds['password'], totp)
        if not response or response.get('status') is False:
            raise RuntimeError('Angel One login failed')
        data = response.get('data') or {}
        session = {
            'jwt_token': data.get('jwtToken'),
            'refresh_token': data.get('refreshToken'),
            'feed_token': data.get('feedToken'),
            'client_id': creds['client_id'],
            'api_key': creds['api_key'],
        }
        if hasattr(self.client, 'setAccessToken') and session.get('jwt_token'):
            self.client.setAccessToken(session['jwt_token'])
        store_session(session, ttl_minutes=60)
        self.session = session
        return session

    def ensure_session(self) -> Dict[str, str]:
        if self.session and not session_is_stale():
            return self.session
        cached = get_session()
        if cached and not session_is_stale():
            self.session = cached
            self._build_client(cached.get('api_key'))
            if hasattr(self.client, 'setAccessToken') and cached.get('jwt_token'):
                self.client.setAccessToken(cached['jwt_token'])
            return cached
        return self.login()

    def _fetch_batch_once(self, instruments: List[Dict[str, str]]) -> List[Dict[str, str]]:
        results = []
        for instrument in instruments:
            exchange = instrument.get('exchange', 'NSE')
            symbol = instrument.get('symbol')
            token = instrument.get('token')
            if not symbol or not token:
                continue
            try:
                data = self.client.ltpData(exchange, symbol, token)
                payload = data.get('data') or {}
                ltp = payload.get('ltp') or payload.get('close')
                results.append({
                    'symbol': symbol,
                    'timestamp': payload.get('tradetime'),
                    'open': payload.get('open') or payload.get('open_price') or ltp,
                    'high': payload.get('high') or payload.get('high_price') or ltp,
                    'low': payload.get('low') or payload.get('low_price') or ltp,
                    'close': ltp,
                    'volume': payload.get('volume') or 0,
                })
            except Exception as exc:  # noqa: BLE001
                logger.warning('Angel One LTP fetch failed for %s: %s', symbol, exc)
        return results

    def fetch_ltp_batch(self, instruments: List[Dict[str, str]]) -> List[Dict[str, str]]:
        self.ensure_session()
        batch_size = getattr(settings, 'STOCK_MAX_BATCH_SIZE', 100)
        results = []
        for start in range(0, len(instruments), batch_size):
            batch = instruments[start:start + batch_size]
            results.extend(self._fetch_batch_once(batch))

        if results:
            return results

        logger.info('Empty batch result, attempting re-login')
        self.login()
        results = []
        for start in range(0, len(instruments), batch_size):
            batch = instruments[start:start + batch_size]
            results.extend(self._fetch_batch_once(batch))
        return results
