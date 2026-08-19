"""subscriptions ilovasining BARCHA serializerlari shu faylda."""

from rest_framework import serializers

from subscriptions.models import PaymentLog, Subscription, SubscriptionPlan


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    business_type_display = serializers.CharField(source="get_business_type_display", read_only=True)

    class Meta:
        model = SubscriptionPlan
        fields = [
            "id", "business_type", "business_type_display",
            "monthly_price", "trial_days", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PaymentLogSerializer(serializers.ModelSerializer):
    confirmed_by_name = serializers.CharField(source="confirmed_by.full_name", read_only=True)

    class Meta:
        model = PaymentLog
        fields = [
            "id", "subscription", "amount", "confirmed_by",
            "confirmed_by_name", "note", "created_at",
        ]
        read_only_fields = ["id", "confirmed_by", "created_at"]


class SubscriptionSerializer(serializers.ModelSerializer):
    """
    Biznes egasining "Obuna" ekrani va admin panelidagi "Obunalar" jadvali
    uchun bir xil ko'rinish.
    """

    business_name = serializers.CharField(source="business.name", read_only=True)
    business_type = serializers.CharField(source="business.business_type", read_only=True)
    owner_name = serializers.CharField(source="business.owner.full_name", read_only=True)
    owner_phone = serializers.CharField(source="business.owner.phone_number", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    monthly_price = serializers.DecimalField(
        source="plan.monthly_price", max_digits=12, decimal_places=2, read_only=True
    )
    days_left = serializers.SerializerMethodField()
    payments = PaymentLogSerializer(many=True, read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id", "business", "business_name", "business_type", "owner_name", "owner_phone",
            "plan", "monthly_price", "status", "status_display",
            "trial_ends_at", "subscription_ends_at", "days_left",
            "approved_by", "payments", "created_at",
        ]
        read_only_fields = fields

    def get_days_left(self, obj) -> int | None:
        """Ekranda "6 kun qoldi" deb ko'rsatish uchun."""
        from django.utils import timezone

        deadline = obj.subscription_ends_at if obj.status == "active" else obj.trial_ends_at
        if deadline is None:
            return None
        delta = deadline - timezone.now()
        return max(delta.days, 0)


class SubscriptionActivateSerializer(serializers.Serializer):
    """Admin "To'lovni tasdiqlash" tugmasini bosganda yuboradigan ma'lumot."""

    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True)
