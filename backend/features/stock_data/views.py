from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .repositories import get_latest_prices, get_history
from .serializers import StockPriceSerializer, StockHistoryQuerySerializer
from .services.cache import get_latest_prices_cache
from .services.symbol_registry import load_symbol_config


class LatestStockPriceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        symbols_param = request.query_params.get('symbols', '')
        symbols = [s.strip().upper() for s in symbols_param.split(',') if s.strip()]
        if not symbols:
            symbols = [entry['symbol'].upper() for entry in load_symbol_config()]

        cached = get_latest_prices_cache()
        if cached:
            filtered = [row for row in cached if row.get('symbol') in symbols]
            if filtered:
                return Response(filtered, status=status.HTTP_200_OK)

        latest = get_latest_prices(symbols)
        serializer = StockPriceSerializer(latest, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StockHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = StockHistoryQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data

        history = get_history(
            params['symbol'].upper(),
            start=params.get('start'),
            end=params.get('end'),
            limit=params.get('limit', 1000),
        )
        output = StockPriceSerializer(history, many=True)
        return Response(output.data, status=status.HTTP_200_OK)
