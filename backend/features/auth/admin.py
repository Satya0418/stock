from django.contrib import admin

from .models import AngelOneCredential


@admin.register(AngelOneCredential)
class AngelOneCredentialAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('user__username', 'user__email')
