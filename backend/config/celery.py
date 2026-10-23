import os

from celery import Celery
from celery.schedules import crontab
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('stock_platform')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'fetch-market-data-every-minute': {
        'task': 'features.stock_data.tasks.fetch_market_data',
        'schedule': settings.STOCK_POLL_INTERVAL_SECONDS,
        'options': {'expires': max(5, settings.STOCK_POLL_INTERVAL_SECONDS - 5)},
    },
    'refresh-angel-one-session-daily': {
        'task': 'features.stock_data.tasks.refresh_angel_one_session',
        'schedule': crontab(hour=6, minute=0),
    },
}
