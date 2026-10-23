# ==============================================================================
# Config Package Initialization
# ==============================================================================
# This file makes the 'config' directory a Python package.
# The actual Django configuration is split into settings/ subdirectory.
# ==============================================================================

from .celery import app as celery_app

__all__ = ['celery_app']
