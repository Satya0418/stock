from django.urls import path

from .consumers import StockStreamConsumer


websocket_urlpatterns = [
    path('stocks/stream/', StockStreamConsumer.as_asgi()),
]
