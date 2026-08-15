from django.conf import settings
from django.db import models

from businesses.models import Business
from common.models import BaseModel


class SubscriptionPlan(BaseModel):
    business_type = models.CharField(max_length=15, choices=Business.TYPE_CHOICES)
    monthly_price = models.DecimalField(max_digits=12, decimal_places=2)
    trial_days = models.PositiveIntegerField(default=7)

    def __str__(self):
        return f"{self.get_business_type_display()} — {self.monthly_price}"


class Subscription(BaseModel):
    STATUS_CHOICES = (
        ("trial", "Trial (bepul)"),
        ("active", "Faol"),
        ("expired", "Muddati tugagan"),
    )

    business = models.OneToOneField(Business, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="trial", db_index=True)
    trial_ends_at = models.DateTimeField()
    subscription_ends_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.business} — {self.status}"


class PaymentLog(BaseModel):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    note = models.CharField(max_length=255, blank=True)