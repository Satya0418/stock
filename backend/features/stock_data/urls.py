from django.urls import path

from .views import LatestStockPriceView, StockHistoryView


urlpatterns = [
    path('latest/', LatestStockPriceView.as_view(), name='stocks-latest'),
    path('history/', StockHistoryView.as_view(), name='stocks-history'),
]
