"""
==============================================================================
PRODUCTION SETTINGS - Secure configuration for deployment
==============================================================================

This file extends base.py with security-hardened settings for production:
- DEBUG disabled
- HTTPS enforced
- Strict CORS policy
- Security headers enabled

USAGE:
    Set environment variable: DJANGO_SETTINGS_MODULE=config.settings.production
    Then run with Uvicorn/Daphne ASGI server

SECURITY: All secrets MUST come from environment variables!
==============================================================================
"""

import os
from .base import *  # noqa: F401, F403

# ==============================================================================
# DEBUG MODE - MUST BE FALSE IN PRODUCTION
# ==============================================================================

DEBUG = False

# ==============================================================================
# SECRET KEY - MUST BE SET VIA ENVIRONMENT VARIABLE
# ==============================================================================

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError('DJANGO_SECRET_KEY environment variable is required in production!')

# ==============================================================================
# ALLOWED HOSTS - Only allow your actual domain(s)
# ==============================================================================

# Get allowed hosts from environment variable (comma-separated)
# Example: ALLOWED_HOSTS=example.com,www.example.com
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
    raise ValueError('ALLOWED_HOSTS environment variable is required in production!')

# ==============================================================================
# CORS CONFIGURATION - Strict policy for production
# ==============================================================================

# Only allow specific origins in production
CORS_ALLOW_ALL_ORIGINS = False

# Set allowed origins from environment variable
# Example: CORS_ORIGINS=https://example.com,https://www.example.com
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',')

# Allow credentials in cross-origin requests
CORS_ALLOW_CREDENTIALS = True

# ==============================================================================
# SECURITY SETTINGS - All security features enabled
# ==============================================================================

# HTTPS/SSL Settings
SECURE_SSL_REDIRECT = True  # Redirect all HTTP to HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Cookie Security
SESSION_COOKIE_SECURE = True  # Only send cookies over HTTPS
CSRF_COOKIE_SECURE = True     # Only send CSRF cookie over HTTPS
SESSION_COOKIE_HTTPONLY = True  # JavaScript can't access session cookie

# HSTS (HTTP Strict Transport Security)
# Tell browsers to only use HTTPS for this domain
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Content Security
SECURE_CONTENT_TYPE_NOSNIFF = True  # Prevent MIME type sniffing
X_FRAME_OPTIONS = 'DENY'  # Prevent clickjacking

# ==============================================================================
# DATABASE - Use PostgreSQL in production
# ==============================================================================

# Uncomment and configure for PostgreSQL
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': os.environ.get('DB_NAME'),
#         'USER': os.environ.get('DB_USER'),
#         'PASSWORD': os.environ.get('DB_PASSWORD'),
#         'HOST': os.environ.get('DB_HOST', 'localhost'),
#         'PORT': os.environ.get('DB_PORT', '5432'),
#         'CONN_MAX_AGE': 60,  # Connection pooling
#     }
# }

# ==============================================================================
# STATIC FILES - Use CDN or storage service in production
# ==============================================================================

# Uncomment for whitenoise (static file serving middleware)
# MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ==============================================================================
# LOGGING - More structured for production monitoring
# ==============================================================================

LOGGING['handlers']['file']['level'] = 'WARNING'
LOGGING['root']['level'] = 'WARNING'

# ==============================================================================
# CACHE - Ensure Redis is properly configured
# ==============================================================================

# Production cache should have longer timeouts
CACHES['default']['TIMEOUT'] = 600  # 10 minutes

print("=" * 60)
print("PRODUCTION SETTINGS LOADED")
print("DEBUG =", DEBUG)
print("=" * 60)
