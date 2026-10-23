from datetime import timedelta
from django.core.cache import cache
from django.utils import timezone

SESSION_CACHE_KEY = 'angel_one_session'


def store_session(payload: dict, ttl_minutes: int = 60):
    payload = dict(payload)
    payload['stored_at'] = timezone.now().isoformat()
    cache.set(SESSION_CACHE_KEY, payload, ttl_minutes * 60)


def get_session() -> dict:
    return cache.get(SESSION_CACHE_KEY) or {}


def session_is_stale(max_age_minutes: int = 300) -> bool:
    session = get_session()
    stored_at = session.get('stored_at')
    if not stored_at:
        return True
    try:
        stored_time = timezone.datetime.fromisoformat(stored_at)
        if timezone.is_naive(stored_time):
            stored_time = timezone.make_aware(stored_time, timezone.get_current_timezone())
    except ValueError:
        return True
    return timezone.now() - stored_time > timedelta(minutes=max_age_minutes)
