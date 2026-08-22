"""notifications ilovasining BARCHA serializerlari shu faylda."""

from rest_framework import serializers

from notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Qo'ng'iroqcha ostidagi ro'yxat uchun."""

    kind_display = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id", "kind", "kind_display", "level",
            "title", "body", "link_url",
            "is_read", "read_at", "created_at",
        ]
        read_only_fields = fields


class UnreadCountSerializer(serializers.Serializer):
    """`/api/notifications/unread-count/` javobi."""

    unread = serializers.IntegerField(read_only=True)
