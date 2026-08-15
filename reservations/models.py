import datetime
from calendar import monthrange

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from businesses.models import Business, Room
from common.models import BaseModel


class Availability(BaseModel):
    """
    Bitta kunga tegishli "bo'sh vaqt" yozuvi.

    Restoran: har bir Room o'zining alohida Availability qatoriga ega
    (room to'ldirilgan). Bitta kunda bir nechta room bo'lishi mumkin.

    To'yxona: Room/Hall TANLANMAYDI — bitta to'yxonada bir kunda faqat
    bitta to'y bo'lishi mumkin, shuning uchun bu yerda `room = None`,
    va yozuv to'g'ridan-to'g'ri `business` + `date` darajasida yagona
    bo'ladi (butun kun uchun bitta oraliq).
    """

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="availabilities")
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name="availabilities",
        null=True, blank=True,
        help_text="Faqat restoran uchun. To'yxona uchun bo'sh qoldiriladi — "
                   "to'yxonada bo'sh vaqt Room emas, butun business darajasida hisoblanadi.",
    )
    date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_booked = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name_plural = "Availabilities"
        ordering = ["date", "start_time"]
        constraints = [
            # Restoran: bitta room bitta kunda bitta start_time'ga faqat bitta yozuvga ega bo'lishi mumkin
            models.UniqueConstraint(
                fields=["room", "date", "start_time"],
                condition=Q(room__isnull=False),
                name="uniq_room_date_start_time",
            ),
            # To'yxona: room yo'q, shuning uchun business + date + start_time darajasida yagona
            models.UniqueConstraint(
                fields=["business", "date", "start_time"],
                condition=Q(room__isnull=True),
                name="uniq_business_date_start_time_no_room",
            ),
        ]

    def __str__(self):
        target = self.room.name if self.room_id else self.business.name
        return f"{target} — {self.date} ({self.start_time}-{self.end_time})"

    def clean(self):
        if self.business.business_type == Business.TYPE_RESTAURANT and not self.room_id:
            raise ValidationError({"room": "Restoran uchun room ko'rsatilishi shart."})
        if self.business.business_type == Business.TYPE_VENUE and self.room_id:
            raise ValidationError({"room": "To'yxona uchun room tanlanmaydi — bo'sh qoldiring."})
        if self.room_id and self.room.business_id != self.business_id:
            raise ValidationError({"room": "Bu room ushbu businessga tegishli emas."})

    # ------------------------------------------------------------------
    # Oylar bo'yicha avtomatik generatsiya
    # ------------------------------------------------------------------
    # Eslatma: start/end vaqti hech qanday biznes turi uchun qattiq
    # belgilanmagan — har bir restoran/to'yxona o'z ish vaqtini o'zi
    # kiritadi (masalan 07:00 yoki 09:00 dan). Faqat mantiqiy tekshiruv
    # bor: end_time > start_time (serializer'da tekshiriladi).
    # Istisno: to'yxona uchun end_time == 00:00 "yarim tungacha" (butun
    # kun) degan maxsus holat sifatida qabul qilinadi.

    @classmethod
    def generate_for_months(cls, *, business: Business, start_time, end_time, months: list[datetime.date], room: Room | None = None):
        """
        Berilgan oylarning (har biri shu oyning 1-kuni sifatida keladi) BARCHA
        kunlari uchun bitta shablon (start_time/end_time) bo'yicha Availability
        yozuvlarini yaratadi.

        - Restoran uchun `room` majburiy.
        - To'yxona uchun `room` berilmaydi (None) — business darajasida bitta
          kunlik yozuv yaratiladi.
        - Allaqachon mavjud (masalan band qilingan) kunlar qayta yozilmaydi —
          faqat yo'q bo'lgan kunlar uchun yangi qator qo'shiladi.

        Qaytaradi: (created_count, skipped_count)
        """
        is_restaurant = business.business_type == Business.TYPE_RESTAURANT

        if is_restaurant and room is None:
            raise ValidationError("Restoran uchun room tanlanishi shart.")
        if not is_restaurant and room is not None:
            raise ValidationError("To'yxona uchun room tanlanmaydi.")
        if room is not None and room.business_id != business.id:
            raise ValidationError("Bu room ushbu businessga tegishli emas.")

        to_create = []
        existing_filter_base = Q(business=business)
        existing_filter_base &= Q(room=room) if room is not None else Q(room__isnull=True)

        for month_start in months:
            days_in_month = monthrange(month_start.year, month_start.month)[1]
            all_dates = [
                datetime.date(month_start.year, month_start.month, day)
                for day in range(1, days_in_month + 1)
            ]

            existing_dates = set(
                cls.objects.filter(existing_filter_base, date__in=all_dates)
                .values_list("date", flat=True)
            )

            for day in all_dates:
                if day in existing_dates:
                    continue
                to_create.append(
                    cls(
                        business=business,
                        room=room,
                        date=day,
                        start_time=start_time,
                        end_time=end_time,
                        is_booked=False,
                    )
                )

        created = cls.objects.bulk_create(to_create)
        skipped = sum(
            monthrange(m.year, m.month)[1] for m in months
        ) - len(created)
        return len(created), skipped


class Reservation(BaseModel):
    STATUS_CHOICES = (
        ("pending", "Kutilmoqda"),
        ("confirmed", "Tasdiqlangan"),
        ("cancelled", "Bekor qilingan"),
        ("completed", "Yakunlangan"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservations")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="reservations")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="reservations", null=True, blank=True)
    availability = models.OneToOneField(Availability, on_delete=models.CASCADE, related_name="reservation")
    guests_count = models.PositiveIntegerField()
    special_request = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="pending", db_index=True)

    def __str__(self):
        return f"{self.user} — {self.business} ({self.status})"

    @property
    def deposit_amount(self):
        """
        Depozit narxi — tranzaksiya emas, faqat ko'rsatkich. Foydalanuvchiga
        bron ekranida "shuncha depozit to'lang, @admin bilan bog'laning"
        deb ko'rsatish uchun. Haqiqiy to'lov/tasdiq Telegram + admin panel
        orqali (Reservation.status) qo'lda amalga oshiriladi.
        """
        if self.room_id:
            return self.room.deposit_amount
        return self.business.deposit_amount