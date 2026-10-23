#!/usr/bin/env python
"""
==============================================================================
Django's command-line utility for administrative tasks.
==============================================================================

This is the entry point for running Django management commands such as:
- runserver: Start the development server
- migrate: Apply database migrations
- createsuperuser: Create admin users
- shell: Open Django interactive shell

For production, we use ASGI server (Daphne/Uvicorn) for WebSocket support.
==============================================================================
"""
import os
import sys


def main():
    """
    Main entry point for Django management commands.
    
    Sets the default Django settings module to 'development' for local work.
    In production, this is overridden via environment variables.
    """
    # Default to development settings - override with DJANGO_SETTINGS_MODULE env var
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
