"""
==============================================================================
DEVELOPMENT SETTINGS - Local development configuration
==============================================================================

This file extends base.py with settings optimized for local development:
- DEBUG mode enabled (detailed error pages)
- CORS allows all origins (for local React dev server)
- Less restrictive security settings

USAGE:
    Set environment variable: DJANGO_SETTINGS_MODULE=config.settings.development
    Or simply run: python manage.py runserver (uses this by default)

WARNING: Never use these settings in production!
==============================================================================
"""

# Import all base settings first
from .base import *  # noqa: F401, F403

# ==============================================================================
# DEBUG MODE
# ==============================================================================

# Enable debug mode - shows detailed error pages
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# ==============================================================================
# ALLOWED HOSTS
# ==============================================================================

# In development, allow all hosts
# This is the list of host/domain names that Django will serve
ALLOWED_HOSTS = ['*']

# ==============================================================================
# CORS CONFIGURATION (Cross-Origin Resource Sharing)
# ==============================================================================

# In development, allow all origins for easier frontend development
# The React dev server typically runs on localhost:5173 or localhost:3000
CORS_ALLOW_ALL_ORIGINS = True

# Allow credentials (cookies, auth headers) in cross-origin requests
CORS_ALLOW_CREDENTIALS = True

# ==============================================================================
# DJANGO DEBUG TOOLBAR (optional)
# ==============================================================================

# Uncomment to enable Django Debug Toolbar for SQL query analysis
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
# INTERNAL_IPS = ['127.0.0.1']

# ==============================================================================
# EMAIL BACKEND
# ==============================================================================

# In development, just print emails to console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ==============================================================================
# LOGGING OVERRIDE
# ==============================================================================

# More verbose logging in development
LOGGING['root']['level'] = 'DEBUG'
LOGGING['loggers']['features.stock_data']['level'] = 'DEBUG'
LOGGING['loggers']['features.websocket']['level'] = 'DEBUG'

# ==============================================================================
# CACHES (use in-memory for faster dev if Redis not available)
# ==============================================================================

# Uncomment to use local memory cache instead of Redis
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# ==============================================================================
# CHANNELS LAYER (use in-memory for dev if Redis not available)
# ==============================================================================

# Uncomment to use in-memory channel layer instead of Redis
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}

print("=" * 60)
print("DEVELOPMENT SETTINGS LOADED")
print("DEBUG =", DEBUG)
print("=" * 60)

# ---------------------------------------------------------------------------
# Celery development convenience
# - Run tasks eagerly (synchronously) so a running Redis broker is not required
# - Keep a memory broker/result backend as a fallback for local testing
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
