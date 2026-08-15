from django.contrib import admin

from .models import PlatformSettings


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    """Faqat bitta yozuv bo'lishi kerak (singleton) — qo'shish/o'chirish tugmalari yashiriladi."""

    list_display = ("admin_telegram_username",)

    def has_add_permission(self, request):
        return not PlatformSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False