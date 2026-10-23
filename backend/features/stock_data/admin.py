from django.contrib import admin

from .models import StockPrice


@admin.register(StockPrice)
class StockPriceAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'timestamp', 'close', 'volume')
    list_filter = ('symbol',)
    search_fields = ('symbol',)
    ordering = ('-timestamp',)
