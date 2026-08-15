from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from businesses.models import Business, Room
from common.models import BaseModel


DEPOSIT_REFUND_WINDOW = timedelta(hours=1)


class Availability(BaseModel):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="availabilities")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="availabilities")
    date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_booked = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name_plural = "Availabilities"
        unique_together = ("room", "date", "start_time")


class Reservation(BaseModel):
    STATUS_CHOICES = (
        ("pending", "Kutilmoqda"),
        ("confirmed", "Tasdiqlangan"),
        ("cancelled", "Bekor qilingan"),
        ("completed", "Yakunlangan"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservations")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="reservations")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="reservations")
    availability = models.OneToOneField(Availability, on_delete=models.CASCADE, related_name="reservation")
    guests_count = models.PositiveIntegerField()
    special_request = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="pending", db_index=True)

    def __str__(self):
        return f"{self.user} — {self.business} ({self.status})"


class DepositTransaction(BaseModel):

    STATUS_HELD = "held"
    STATUS_REFUNDED = "refunded"
    STATUS_FORFEITED = "forfeited"
    STATUS_CHOICES = (
        (STATUS_HELD, "Ushlab turilgan"),
        (STATUS_REFUNDED, "Qaytarilgan (1 soat ichida bekor qilingan)"),
        (STATUS_FORFEITED, "Qaytarilmaydi"),
    )

    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name="deposit")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_HELD, db_index=True)
    refund_deadline = models.DateTimeField(help_text="Reservation yaratilgan payt + 1 soat. Shu vaqtgacha bekor qilinsa deposit qaytariladi.")
    refunded_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,related_name="confirmed_deposit_refunds",)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Deposit Transaction"

    def __str__(self):
        return f"{self.reservation} — {self.amount} ({self.status})"

    def is_refundable(self) -> bool:
        return self.status == self.STATUS_HELD and timezone.now() <= self.refund_deadline

    @classmethod
    def create_for_reservation(cls, reservation: Reservation) -> "DepositTransaction":
        return cls.objects.create(
            reservation=reservation,
            amount=reservation.business.deposit_amount,
            refund_deadline=timezone.now() + DEPOSIT_REFUND_WINDOW,
        )