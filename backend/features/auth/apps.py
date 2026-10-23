from django.apps import AppConfig


class AuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'features.auth'
    # Use a non-conflicting label to avoid clashing with Django's built-in "auth" app
    label = 'features_auth'
