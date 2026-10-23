from rest_framework import serializers

from .models import StockPrice


class StockPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockPrice
        fields = ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume']


class StockHistoryQuerySerializer(serializers.Serializer):
    symbol = serializers.CharField(max_length=32)
    start = serializers.DateTimeField(required=False)
    end = serializers.DateTimeField(required=False)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=5000)

    def validate(self, attrs):
        start = attrs.get('start')
        end = attrs.get('end')
        if start and end and start > end:
            raise serializers.ValidationError('start must be before end')
        return attrs
