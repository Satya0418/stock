import logging

from celery import shared_task

from .services.data_pipeline import StockDataPipeline
from .services.angel_one_client import AngelOneClient

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 5})
def fetch_market_data(self):
    pipeline = StockDataPipeline()
    result = pipeline.run()
    logger.info('market data pipeline run result: %s', result)
    return result


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def refresh_angel_one_session(self):
    client = AngelOneClient()
    client.login()
    logger.info('angel one session refreshed')
    return {'status': 'refreshed'}
