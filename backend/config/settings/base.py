"""
==============================================================================
BASE SETTINGS - Common configuration for all environments
==============================================================================

This file contains Django settings that are shared across:
- Development environment (local machine)
- Production environment (server/cloud)

Environment-specific settings are in development.py and production.py
which import and override these base settings.

IMPORTANT: Never put secrets here. Use environment variables via .env file.
==============================================================================
"""

import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

# ==============================================================================
# PATH CONFIGURATION
# ==============================================================================

# Build paths inside the project
# BASE_DIR points to the 'backend' folder (parent of 'config')
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env file
# This MUST be done before accessing any os.environ.get() calls
load_dotenv(BASE_DIR / '.env')

# ==============================================================================
# SECURITY SETTINGS (overridden in production.py)
# ==============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
# This default is only for development - production uses env variable
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-secret-key-change-in-production')

# ==============================================================================
# APPLICATION DEFINITION
# ==============================================================================

# Django built-in apps
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

# Third-party packages
THIRD_PARTY_APPS = [
    'rest_framework',       # Django REST Framework for API endpoints
    'corsheaders',          # CORS support for cross-origin requests
    'channels',             # WebSocket support via Django Channels
    'django_celery_beat',    # Celery beat scheduler
    'django_celery_results', # Celery task results
    'rest_framework_simplejwt.token_blacklist',
]

# Our custom applications
LOCAL_APPS = [
    'features.auth',        # Authentication and credentials
    'features.stock_data',  # Stock data pipeline and APIs
    'features.websocket',   # WebSocket streaming
    'features.scheduler',   # Task scheduling and locks
    'features.ml_engine',   # ML feature entry point
]

# Combine all apps - order matters for middleware and template loading
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ==============================================================================
# MIDDLEWARE CONFIGURATION
# ==============================================================================

# Middleware process requests/responses in order (top to bottom for requests)
MIDDLEWARE = [
    # CORS must be as high as possible, before any response-modifying middleware
    'corsheaders.middleware.CorsMiddleware',
    
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# URL configuration module
ROOT_URLCONF = 'config.urls'

# ==============================================================================
# TEMPLATES CONFIGURATION
# ==============================================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Custom templates directory
        'APP_DIRS': True,  # Look for templates in app directories
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ==============================================================================
# ASGI APPLICATION (for WebSocket support)
# ==============================================================================

# ASGI (Asynchronous Server Gateway Interface) is required for:
# - WebSocket connections
# - Server-Sent Events
# - Long-polling
# We use Django Channels as the ASGI implementation
ASGI_APPLICATION = 'config.asgi.application'

# ==============================================================================
# DATABASE CONFIGURATION
# ==============================================================================

# Using SQLite for simplicity - in production, use PostgreSQL
# For this dashboard, we mainly use Redis for caching, not heavy DB usage
USE_SQLITE = os.environ.get('USE_SQLITE', '').lower() in ('1', 'true', 'yes')

if USE_SQLITE or not os.environ.get('DB_NAME'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME'),
            'USER': os.environ.get('DB_USER'),
            'PASSWORD': os.environ.get('DB_PASSWORD'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '60')),
        }
    }

# ==============================================================================
# REDIS CONFIGURATION
# ==============================================================================

# Redis is used for:
# 1. Django Channels layer (WebSocket message passing between consumers)
# 2. Caching market data (fast access, no DB hits)
# 3. Session storage (optional)

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}'

# Django Channels layer configuration
# This tells Channels how to communicate between different consumers
CHANNEL_LAYERS = {
    'default': {
        # Use Redis as the backing store for Channels
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(REDIS_HOST, REDIS_PORT)],
            # Expire groups after 1 day (for cleanup)
            'group_expiry': 86400,
        },
    },
}

# Django Cache configuration using Redis
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        # Do not pass `CLIENT_CLASS` here - that option is specific to
        # `django-redis` and will be forwarded into redis-py's connection
        # constructor causing unexpected keyword args. Keep OPTIONS empty
        # unless using `django_redis.cache.RedisCache`.
        'KEY_PREFIX': 'market_dashboard',  # Prefix all keys to avoid collisions
        'TIMEOUT': 300,  # Default cache timeout: 5 minutes
    }
}

# ==============================================================================
# REST FRAMEWORK CONFIGURATION
# ==============================================================================

REST_FRAMEWORK = {
    # Default permission - allow any for public market data
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    # JSON renderer for API responses
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    # Pagination for large data sets
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    # Throttling to prevent API abuse
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/minute',  # Allow 100 requests per minute for anonymous users
        'user': '300/minute',
    },
}

# ============================================================================== 
# JWT AUTH SETTINGS
# ==============================================================================

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# ==============================================================================
# PASSWORD VALIDATION
# ==============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ==============================================================================
# INTERNATIONALIZATION
# ==============================================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'  # Indian Standard Time for stock market
USE_I18N = True
USE_TZ = True

# ==============================================================================
# STATIC FILES (CSS, JavaScript, Images)
# ==============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# ==============================================================================
# PRIMARY KEY FIELD TYPE
# ==============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==============================================================================
# ANGEL ONE API CONFIGURATION
# ==============================================================================

# All Angel One credentials MUST be in .env file
# Never hardcode these values!
ANGEL_ONE_API_KEY = os.environ.get('ANGEL_ONE_API_KEY', '')
ANGEL_ONE_CLIENT_ID = os.environ.get('ANGEL_ONE_CLIENT_ID', '')
ANGEL_ONE_PASSWORD = os.environ.get('ANGEL_ONE_PASSWORD', '')
ANGEL_ONE_TOTP_SECRET = os.environ.get('ANGEL_ONE_TOTP_SECRET', '')
ANGEL_ONE_SERVICE_USER_ID = os.environ.get('ANGEL_ONE_SERVICE_USER_ID')

# ============================================================================== 
# CREDENTIAL ENCRYPTION
# ==============================================================================

# Base64-encoded 32-byte key for Fernet
CREDENTIAL_ENCRYPTION_KEY = os.environ.get('CREDENTIAL_ENCRYPTION_KEY', '')

# ============================================================================== 
# STOCK DATA PIPELINE CONFIG
# ==============================================================================

# JSON array string with objects: {"symbol": "RELIANCE", "token": "2885", "exchange": "NSE"}
STOCK_TOKEN_MAP = os.environ.get('STOCK_TOKEN_MAP', '')

# Polling interval for live data ingestion
STOCK_POLL_INTERVAL_SECONDS = int(os.environ.get('STOCK_POLL_INTERVAL_SECONDS', '60'))

# Cache TTL for latest prices
STOCK_LATEST_CACHE_TTL = int(os.environ.get('STOCK_LATEST_CACHE_TTL', '120'))

# Max number of instruments per request
STOCK_MAX_BATCH_SIZE = int(os.environ.get('STOCK_MAX_BATCH_SIZE', '100'))

# Redis lock timeout to avoid overlapping jobs
STOCK_PIPELINE_LOCK_TIMEOUT = int(os.environ.get('STOCK_PIPELINE_LOCK_TIMEOUT', '55'))

# ============================================================================== 
# CELERY CONFIGURATION
# ==============================================================================

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', REDIS_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TIME_LIMIT = 60
CELERY_TASK_SOFT_TIME_LIMIT = 55

# ==============================================================================
# LOGGING CONFIGURATION
# ==============================================================================

LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': LOG_DIR / 'django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'features.auth': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'features.stock_data': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'features.websocket': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'features.scheduler': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# ==============================================================================
# MARKET DATA CONFIGURATION
# ==============================================================================

# Update interval for market breadth calculations (in seconds)
MARKET_BREADTH_UPDATE_INTERVAL = 2

# Indices to track - these are the major Indian market indices
# Each index has a unique symbol/token in Angel One system
TRACKED_INDICES = [
    {'name': 'NIFTY 50', 'symbol': 'NIFTY', 'token': '99926000'},
    {'name': 'NIFTY BANK', 'symbol': 'BANKNIFTY', 'token': '99926009'},
    {'name': 'NIFTY MIDCAP 100', 'symbol': 'NIFTY MIDCAP 100', 'token': '99926013'},
    {'name': 'NIFTY NEXT 50', 'symbol': 'NIFTY NEXT 50', 'token': '99926012'},
    {'name': 'NIFTY 100', 'symbol': 'NIFTY 100', 'token': '99926011'},
    {'name': 'NIFTY 200', 'symbol': 'NIFTY 200', 'token': '99926014'},
    {'name': 'NIFTY 500', 'symbol': 'NIFTY 500', 'token': '99926004'},
    {'name': 'NIFTY SMALLCAP 100', 'symbol': 'NIFTY SMLCAP 100', 'token': '99926015'},
    {'name': 'NIFTY MIDCAP 50', 'symbol': 'NIFTY MIDCAP 50', 'token': '99926016'},
    {'name': 'NIFTY SMALLCAP 50', 'symbol': 'NIFTY SMLCAP 50', 'token': '99926017'},
]
