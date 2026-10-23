from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import AngelOneCredentialWriteSerializer, AngelOneCredentialReadSerializer
from .services.credentials import upsert_credentials, get_decrypted_credentials
from .services.crypto import CredentialCryptoError
from .models import AngelOneCredential


class AngelOneCredentialView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        instance = AngelOneCredential.objects.filter(user=request.user, is_active=True).first()
        if not instance:
            serializer = AngelOneCredentialReadSerializer({
                'is_configured': False,
                'api_key_last4': '',
                'client_id_last4': '',
                'updated_at': None,
            })
            return Response(serializer.data, status=status.HTTP_200_OK)

        try:
            creds = get_decrypted_credentials(request.user)
        except CredentialCryptoError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = AngelOneCredentialReadSerializer({
            'is_configured': True,
            'api_key_last4': creds.get('api_key', '')[-4:],
            'client_id_last4': creds.get('client_id', '')[-4:],
            'updated_at': instance.updated_at,
        })
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        serializer = AngelOneCredentialWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            upsert_credentials(request.user, serializer.validated_data)
        except CredentialCryptoError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'refresh token required'}, status=status.HTTP_400_BAD_REQUEST)
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'status': 'logged_out'}, status=status.HTTP_200_OK)
