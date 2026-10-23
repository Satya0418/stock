from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class CredentialCryptoError(RuntimeError):
    pass


def _get_fernet():
    key = settings.CREDENTIAL_ENCRYPTION_KEY
    if not key:
        raise CredentialCryptoError('CREDENTIAL_ENCRYPTION_KEY is not set')
    if isinstance(key, str):
        key_bytes = key.encode('utf-8')
    else:
        key_bytes = key
    return Fernet(key_bytes)


def encrypt_value(value: str) -> str:
    if value is None:
        return ''
    fernet = _get_fernet()
    return fernet.encrypt(value.encode('utf-8')).decode('utf-8')


def decrypt_value(value: str) -> str:
    if not value:
        return ''
    fernet = _get_fernet()
    try:
        return fernet.decrypt(value.encode('utf-8')).decode('utf-8')
    except InvalidToken as exc:
        raise CredentialCryptoError('Invalid credential encryption key') from exc
