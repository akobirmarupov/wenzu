from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from common.models import BaseModel


class BusinessApplication(BaseModel):
    STATUS_CHOICES = (
        ("pending_payment", "To'lov kutilmoqda"),
        ("approved", "Tasdiqlangan"),
        ("rejected", "Rad etilgan"),
    )
    BUSINESS_TYPE_CHOICES = (
        ("restaurant", "Restoran"),
        ("venue", "To'yxona"),
    )

    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications")
    business_type = models.CharField(max_length=15, choices=BUSINESS_TYPE_CHOICES)
    business_name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending_payment", db_index=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_applications")

    class Meta:
        verbose_name = "Business Application"
        verbose_name_plural = "Business Applications"


class Business(BaseModel):
    TYPE_RESTAURANT = "restaurant"
    TYPE_VENUE = "venue"
    TYPE_CHOICES = (
        (TYPE_RESTAURANT, "Restoran"),
        (TYPE_VENUE, "To'yxona"),
    )

    VENUE_DEPOSIT_AMOUNT = Decimal("699000")

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="businesses")
    application = models.OneToOneField(BusinessApplication, on_delete=models.CASCADE, related_name="business")
    name = models.CharField(max_length=200)
    business_type = models.CharField(max_length=15, choices=TYPE_CHOICES)
    address = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    description = models.TextField(blank=True)
    cover_photo = models.ImageField(upload_to="business_covers/", null=True, blank=True)
    is_visible = models.BooleanField(default=True, db_index=True)
    rating_avg = models.FloatField(default=0)
    telegram_username = models.CharField(max_length=32, blank=False,)

    class Meta:
        verbose_name_plural = "Businesses"
        indexes = [models.Index(fields=["latitude", "longitude"])]

    def __str__(self):
        return self.name

    @property
    def deposit_amount(self) -> Decimal:
        if self.business_type == self.TYPE_VENUE:
            return self.VENUE_DEPOSIT_AMOUNT
        return Decimal("0")


class Room(BaseModel):
    ROOM_TYPE_CHOICES = (
        ("vip", "VIP xona"),
        ("standard", "Oddiy zal"),
        ("outdoor", "Tashqi terrasa"),
        ("hall", "Katta zal (to'yxona)"),
    )

    DEPOSIT_TIER_PREMIUM = "premium"
    DEPOSIT_TIER_PRO = "pro"
    DEPOSIT_TIER_CHOICES = (
        (DEPOSIT_TIER_PREMIUM, "Premium — 99 000 so'm"),
        (DEPOSIT_TIER_PRO, "Pro — 49 000 so'm"),
    )
    DEPOSIT_TIER_AMOUNTS = {
        DEPOSIT_TIER_PREMIUM: Decimal("99000"),
        DEPOSIT_TIER_PRO: Decimal("49000"),
    }

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="rooms")
    name = models.CharField(max_length=100)
    room_type = models.CharField(max_length=15, choices=ROOM_TYPE_CHOICES)
    capacity = models.PositiveIntegerField()
    price_per_slot = models.DecimalField(max_digits=12, decimal_places=2)
    deposit_tier = models.CharField(
        max_length=10, choices=DEPOSIT_TIER_CHOICES, null=True, blank=True,
        help_text="Faqat restoranlar uchun. To'yxona xonalarida bo'sh qoldiring.",
    )

    def __str__(self):
        return f"{self.business.name} — {self.name}"

    def clean(self):
        if self.business.business_type == Business.TYPE_RESTAURANT and not self.deposit_tier:
            raise ValidationError(
                {"deposit_tier": "Restoran xonasi uchun deposit tarifi (Premium/Pro) tanlanishi shart."}
            )
        if self.business.business_type == Business.TYPE_VENUE and self.deposit_tier:
            raise ValidationError(
                {"deposit_tier": "To'yxona xonasi uchun tarif tanlanmaydi — narx qat'iy belgilangan."}
            )

    @property
    def deposit_amount(self) -> Decimal:
        if self.business.business_type == Business.TYPE_VENUE:
            return self.business.VENUE_DEPOSIT_AMOUNT
        return self.DEPOSIT_TIER_AMOUNTS.get(
            self.deposit_tier, self.DEPOSIT_TIER_AMOUNTS[self.DEPOSIT_TIER_PRO]
        )