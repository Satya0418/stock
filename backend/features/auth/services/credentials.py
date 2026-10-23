from typing import Dict

from django.db import transaction

from .crypto import encrypt_value, decrypt_value
from django.contrib.auth import get_user_model

from ..models import AngelOneCredential


def upsert_credentials(user, payload: Dict[str, str]) -> AngelOneCredential:
    with transaction.atomic():
        instance, _ = AngelOneCredential.objects.select_for_update().get_or_create(user=user)
        instance.api_key_encrypted = encrypt_value(payload['api_key'])
        instance.client_id_encrypted = encrypt_value(payload['client_id'])
        instance.password_encrypted = encrypt_value(payload['password'])
        instance.totp_secret_encrypted = encrypt_value(payload['totp_secret'])
        instance.is_active = True
        instance.save()
    return instance


def get_decrypted_credentials(user=None, user_id=None) -> Dict[str, str]:
    if user is None and user_id is not None:
        User = get_user_model()
        user = User.objects.filter(id=user_id).first()
    if user is None:
        return {}
    instance = AngelOneCredential.objects.filter(user=user, is_active=True).first()
    if not instance:
        return {}
    return {
        'api_key': decrypt_value(instance.api_key_encrypted),
        'client_id': decrypt_value(instance.client_id_encrypted),
        'password': decrypt_value(instance.password_encrypted),
        'totp_secret': decrypt_value(instance.totp_secret_encrypted),
    }


def get_any_active_credentials() -> Dict[str, str]:
    instance = AngelOneCredential.objects.filter(is_active=True).first()
    if not instance:
        return {}
    return {
        'api_key': decrypt_value(instance.api_key_encrypted),
        'client_id': decrypt_value(instance.client_id_encrypted),
        'password': decrypt_value(instance.password_encrypted),
        'totp_secret': decrypt_value(instance.totp_secret_encrypted),
    }
