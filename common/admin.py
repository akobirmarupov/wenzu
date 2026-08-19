from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import PlatformSettings


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(ModelAdmin):
    """Faqat bitta yozuv bo'lishi kerak (singleton) — qo'shish/o'chirish tugmalari yashiriladi."""

    list_display = ("admin_telegram_username", "trial_days", "subscription_days", "venue_deposit")

    fieldsets = (
        ("Aloqa", {"fields": ("admin_telegram_username", "support_phone")}),
        ("Depozit narxlari", {
            "fields": ("room_deposit_premium", "room_deposit_pro", "venue_deposit"),
            "description": "Bron qilishda mijoz oldindan to'laydigan summalar.",
        }),
        ("Obuna", {"fields": ("trial_days", "subscription_days")}),
    )

    def has_add_permission(self, request):
        return not PlatformSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
