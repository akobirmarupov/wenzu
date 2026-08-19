"""common ilovasining BARCHA serializerlari shu faylda."""

from rest_framework import serializers

from common.models import PlatformSettings


class PlatformSettingsSerializer(serializers.ModelSerializer):
    """Admin panelidagi "Platforma sozlamalari" ekrani."""

    admin_telegram = serializers.SerializerMethodField()

    class Meta:
        model = PlatformSettings
        fields = [
            "admin_telegram_username", "admin_telegram", "support_phone",
            "room_deposit_premium", "room_deposit_pro", "venue_deposit",
            "trial_days", "subscription_days",
        ]

    def get_admin_telegram(self, obj) -> str:
        return f"@{obj.admin_telegram_username}"


class PublicSettingsSerializer(serializers.Serializer):
    """
    Mobil ilovaga ochiq sozlamalar — "Biznes ochish" ekranida oylik narx,
    bepul sinov muddati va admin Telegram'ini ko'rsatish uchun.
    """

    admin_telegram = serializers.CharField(read_only=True)
    trial_days = serializers.IntegerField(read_only=True)
    plans = serializers.ListField(read_only=True)
