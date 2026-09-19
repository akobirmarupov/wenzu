import datetime
from calendar import monthrange

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from businesses.models import Business, Hall, Room
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
        indexes = [
            # Mijoz "shu kunga bo'sh joyi bor" deb qidirganda ishlaydigan indeks.
            models.Index(fields=["business", "date", "is_booked"], name="idx_avail_biz_date_booked"),
            models.Index(fields=["room", "date"], name="idx_avail_room_date"),
            models.Index(fields=["date", "is_booked"], name="idx_avail_date_booked"),
        ]
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


# ===================================================================
# Bekor qilish oynasi — "TENG YARIM VAQT" qoidasi.
#
# Ilgari bu yerda qat'iy bir soat turardi va u ikki tomonga ham
# adolatsiz edi. Bugun bron qilib, to'yni bir oydan keyinga belgilagan
# odam bir soatdan keyin fikridan qayta olmasdi — holbuki joy egasiga
# hali hech qanday zarar yo'q, oldinda o'ttiz kun bor. Aksincha, ikki
# soatdan keyingi kechki ovqatni bron qilgan odam esa oxirgi daqiqagacha
# bekor qilib, stolni bo'sh qoldirib ketishi mumkin edi.
#
# Endi muddat BRON QILINGAN vaqt bilan TADBIR vaqti orasidagi masofaning
# yarmi. Ya'ni chegara har doim o'rtada turadi:
#
#   bron qilindi          yarim yo'l (oxirgi muddat)        tadbir
#   |---------------------------|---------------------------|
#   5-sentabr                 7-sentabr                  9-sentabr
#   soat 18:00                soat 20:00                 soat 22:00
#
# Mantiq oddiy: qancha erta bron qilsangiz, fikringizni o'zgartirishga
# shuncha ko'p vaqtingiz bor. Tadbirga yaqinlashgan sari esa joy egasi
# o'sha kunni boshqa mijozga sotish imkonini yo'qota boradi — shuning
# uchun bekor qilish huquqi ham qisqaradi.
#
# Muddat mijozga OLDINDAN aytiladi (`cancel_deadline`) — u tugmani
# bosgunicha emas, bronlar ro'yxatida turibdi.
# ===================================================================

# Tadbir vaqti noma'lum bo'lganda (jadval yozuvi o'chirilgan eski bron)
# ishlatiladigan zaxira oyna. Qoidasiz qolgan bronni butunlay ochiq
# qoldirish ham, butunlay yopish ham noto'g'ri bo'lardi.
CANCEL_FALLBACK_WINDOW = datetime.timedelta(hours=1)


class Reservation(BaseModel):
    STATUS_CHOICES = (
        ("pending", "Kutilmoqda"),
        ("confirmed", "Tasdiqlangan"),
        ("cancelled", "Bekor qilingan"),
        ("completed", "Yakunlangan"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservations")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="reservations")
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name="reservations", null=True, blank=True,
        help_text="Faqat restoran broni uchun.",
    )
    hall = models.ForeignKey(
        Hall, on_delete=models.CASCADE, related_name="reservations", null=True, blank=True,
        help_text="Faqat to'yxona broni uchun — qaysi zal band qilingani.",
    )
    availability = models.ForeignKey(
        Availability, on_delete=models.CASCADE, related_name="reservations",
        null=True, blank=True,
        help_text="Bron tegishli bo'lgan kunlik bo'sh vaqt yozuvi.",
    )

    # Restoran broni kun ichidagi soatlik oraliqqa tegishli (masalan 19:00-21:00).
    # To'yxona broni butun kunga bo'lgani uchun bu maydonlar bo'sh qoladi.
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    guests_count = models.PositiveIntegerField()
    special_request = models.TextField(blank=True)

    # To'yxona uchun: nechta xil taom tanlangani va shundan kelib chiqqan summa.
    dish_count = models.PositiveSmallIntegerField(null=True, blank=True)
    price_per_person = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Zalning bir kunlik ijarasi — bron paytidagi narx bilan MUZLATILADI.
    #
    # `total_price` ning ichida turgani yetmaydi: to'yxonada summa ikki
    # qismdan yig'iladi (ijara + kishi boshiga taom) va mijoz ham, joy
    # egasi ham qaysi qism qancha ekanini ko'rishi kerak. Aks holda
    # "18 000 000" degan yagona raqamdan nima uchun to'lanayotgani
    # bilinmasdi.
    day_rent_price = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        verbose_name="Bir kunlik ijara",
    )
    total_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    # Mijoz bron paytida tanlagan taomlar — nom va narx bilan MUZLATIB
    # saqlanadi. FK bo'lganida, restoran keyin taomni o'chirsa yoki narxini
    # o'zgartirsa, eski bronning tarkibi ham "o'zgarib" ketardi.
    selected_menu = models.JSONField(default=list, blank=True)

    # Depozit summasi ham bron YARATILGAN paytdagi narx bilan muzlatiladi.
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="pending", db_index=True)

    # Bron QACHON tasdiqlangani — joy egasi javob bergan payt.
    # Bekor qilish oynasi bunga bog'liq EMAS: u bron yaratilgan payt
    # bilan tadbir orasidagi vaqtdan hisoblanadi (`cancel_deadline`).
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name="Tasdiqlangan vaqti")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # Biznes egasining "Bronlar" ekrani — eng ko'p so'raladigan so'rov.
            models.Index(fields=["business", "status", "-created_at"], name="idx_resv_biz_status_created"),
            # Mijozning "Mening bronlarim" ekrani.
            models.Index(fields=["user", "-created_at"], name="idx_resv_user_created"),
            # Vaqt kesishishini tekshirish (bron yaratishdagi qulflangan so'rov).
            models.Index(fields=["room", "availability", "status"], name="idx_resv_room_avail_status"),
            models.Index(fields=["hall", "availability", "status"], name="idx_resv_hall_avail_status"),
        ]

    def __str__(self):
        return f"{self.user} — {self.business} ({self.status})"

    def save(self, *args, **kwargs):
        """
        Tasdiqlangan vaqtni AVTOMATIK yozadi.

        Nega view'da emas, shu yerda: bron holati bir necha joydan
        o'zgaradi — biznes egasining paneli, Django adminkasi, demo
        to'ldirgich. Har birida qo'lda yozish bitta joyni unutishga
        olib kelardi va o'sha bronni keyin bekor qilib bo'lmay qolardi.

        `update_fields` bilan saqlanganda uni ham to'ldiramiz, aks holda
        yangi qiymat bazaga yozilmasdi.
        """
        if self.status == "confirmed" and self.confirmed_at is None:
            self.confirmed_at = timezone.now()
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"confirmed_at"}
        super().save(*args, **kwargs)

    # ---------------- bekor qilish qoidasi ----------------
    def event_starts_at(self):
        """
        Tadbirning boshlanish payti — to'liq sana va vaqt.

        Restoranda bu mijoz tanlagan soat (masalan 19:00). To'yxonada
        soat tanlanmaydi, shuning uchun jadvaldagi kun boshlanishi
        olinadi (odatda 08:00) — to'y ertalabdan boshlanadi.

        Jadval yozuvi bo'lmasa `None`. Bunday bron eskirgan yoki qo'lda
        yaratilgan bo'ladi; muddatni `CANCEL_FALLBACK_WINDOW` hisoblaydi.
        """
        availability = self.availability
        if availability is None:
            return None

        start = self.start_time or availability.start_time or datetime.time(0, 0)
        naive = datetime.datetime.combine(availability.date, start)
        if timezone.is_naive(naive):
            return timezone.make_aware(naive, timezone.get_current_timezone())
        return naive

    def cancel_deadline(self):
        """
        Bekor qilishning oxirgi muddati — bron qilingan payt bilan tadbir
        orasidagi masofaning TENG YARMI.

        Misol: 5-sentabr 18:00 da bron qilinib, tadbir 9-sentabr 22:00 ga
        belgilangan bo'lsa, oraliq 4 kun-u 4 soat, yarmi esa 2 kun-u
        2 soat — ya'ni muddat 7-sentabr soat 20:00.

        Nima uchun `created_at`, `confirmed_at` emas: hisob mijoz uchun
        oldindan bilinadigan bo'lishi kerak. Tasdiq vaqti esa joy egasiga
        bog'liq — u kechqurun javob bersa, mijozning oynasi o'zi sezmagan
        holda siljib ketardi.
        """
        event_at = self.event_starts_at()
        if event_at is None:
            # Tadbir vaqti noma'lum — zaxira oyna bron yaratilgan
            # paytdan boshlanadi.
            return self.created_at + CANCEL_FALLBACK_WINDOW if self.created_at else None

        if self.created_at is None:
            # Hali bazaga yozilmagan obyekt (masalan formadagi tekshiruv).
            return event_at

        # Tadbir bron qilingan paytdan oldin bo'lsa (eskirgan yozuv) —
        # o'rtacha nuqta orqada qoladi va shart baribir "muddat o'tgan"
        # deb ishlaydi. Alohida hol qilib ajratish shart emas.
        return self.created_at + (event_at - self.created_at) / 2

    def cancel_check(self):
        """
        Mijoz bu bronni hozir bekor qila oladimi?

        Qaytaradi: (mumkinmi, sabab). Sabab foydalanuvchiga ko'rsatiladi,
        shuning uchun "nima qilish kerak"ligi ham yozilgan.
        """
        if self.status in ("cancelled", "completed"):
            return False, f'Bu bron allaqachon "{self.get_status_display()}" holatida.'

        deadline = self.cancel_deadline()
        if deadline is None:
            return True, ""

        if timezone.now() > deadline:
            return False, (
                "Bekor qilish muddati tugagan — u "
                f"{timezone.localtime(deadline).strftime('%d.%m.%Y %H:%M')} da yopilgan. "
                "Bekor qilish uchun bron qilingan payt bilan tadbir orasidagi "
                "vaqtning teng yarmi beriladi. Endi joy egasi bilan bevosita "
                "bog'laning."
            )
        return True, ""

    def clean(self):
        is_restaurant = self.business.business_type == Business.TYPE_RESTAURANT
        if is_restaurant and not self.room_id:
            raise ValidationError({"room": "Restoran broni uchun xona tanlanishi shart."})
        if not is_restaurant and not self.hall_id:
            raise ValidationError({"hall": "To'yxona broni uchun zal tanlanishi shart."})
        if self.room_id and self.room.business_id != self.business_id:
            raise ValidationError({"room": "Bu xona ushbu businessga tegishli emas."})
        if self.hall_id and self.hall.business_id != self.business_id:
            raise ValidationError({"hall": "Bu zal ushbu businessga tegishli emas."})

    def resolve_deposit_amount(self):
        """
        Depozit narxi — tranzaksiya emas, faqat ko'rsatkich. Foydalanuvchiga
        bron ekranida "shuncha depozit to'lang, @admin bilan bog'laning"
        deb ko'rsatish uchun. Haqiqiy to'lov/tasdiq Telegram + admin panel
        orqali (Reservation.status) qo'lda amalga oshiriladi.
        """
        if self.room_id:
            return self.room.deposit_amount
        if self.hall_id:
            return self.hall.deposit_amount
        return 0