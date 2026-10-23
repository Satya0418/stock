from rest_framework import serializers


class AngelOneCredentialWriteSerializer(serializers.Serializer):
    api_key = serializers.CharField(min_length=6, max_length=128, write_only=True)
    client_id = serializers.CharField(min_length=2, max_length=64, write_only=True)
    password = serializers.CharField(min_length=6, max_length=128, write_only=True)
    totp_secret = serializers.CharField(min_length=16, max_length=64, write_only=True)


class AngelOneCredentialReadSerializer(serializers.Serializer):
    is_configured = serializers.BooleanField()
    api_key_last4 = serializers.CharField(allow_blank=True)
    client_id_last4 = serializers.CharField(allow_blank=True)
    updated_at = serializers.DateTimeField(allow_null=True)

    @staticmethod
    def mask_value(value: str) -> str:
        if not value:
            return ''
        return value[-4:]
