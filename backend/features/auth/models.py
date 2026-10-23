from django.conf import settings
from django.db import models
from django.utils import timezone


class AngelOneCredential(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    api_key_encrypted = models.TextField()
    client_id_encrypted = models.TextField()
    password_encrypted = models.TextField()
    totp_secret_encrypted = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'auth_angel_one_credentials'

    def __str__(self):
        return f"AngelOneCredential(user={self.user_id}, active={self.is_active})"
