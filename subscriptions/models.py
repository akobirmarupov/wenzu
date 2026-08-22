from django.conf import settings
from django.db import models

from businesses.models import Business
from common.models import BaseModel


class SubscriptionPlan(BaseModel):
    """
    Tarif rejasi: biznes turi + muddat.

    Har bir tur uchun bir nechta reja bo'ladi (1 oylik, 3 oylik...), shuning
    uchun kalit — (`business_type`, `duration_months`) juftligi.

    `price` — SHU MUDDAT uchun to'liq summa, oylik emas. Ilgari maydon
    `price` deb atalardi va bir oylik rejadan boshqasi paydo
    bo'lishi bilan nomi yolg'onga aylanardi: 3 oylik reja uchun 600 000
    "oylik narx" emas. Oylikka keltirilgani `price_per_month` da.
    """

    business_type = models.CharField(max_length=15, choices=Business.TYPE_CHOICES)
    duration_months = models.PositiveSmallIntegerField(
        default=1, verbose_name="Muddat (oy)",
        help_text="Reja necha oyga amal qiladi. 1 = oylik, 3 = choraklik.",
    )
    price = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name="Narx", help_text="Shu muddat uchun TO'LIQ summa.",
    )
    trial_days = models.PositiveIntegerField(default=7)

    class Meta:
        ordering = ["business_type", "duration_months"]
        verbose_name = "Tarif rejasi"
        verbose_name_plural = "Tarif rejalari"
        constraints = [
            models.UniqueConstraint(
                fields=["business_type", "duration_months"],
                name="uniq_plan_type_duration",
            )
        ]

    def __str__(self):
        return f"{self.get_business_type_display()} — {self.duration_months} oy — {self.price}"

    @property
    def price_per_month(self):
        """Taqqoslash uchun: uzoq muddatli reja qanchaga arzonligi ko'rinsin."""
        return self.price / self.duration_months

    @property
    def duration_label(self):
        return f"{self.duration_months} oy"

    @property
    def days(self):
        """Obuna necha kunga uzayadi. Oy = 30 kun deb olinadi."""
        return self.duration_months * 30


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

    # Qaysi eslatmalar YUBORILGAN: [5, 3, 2] kabi.
    #
    # Kerak bo'lish sababi: eslatma vazifasi kuniga bir marta emas, bir
    # necha marta ishga tushishi mumkin (qayta urinish, qo'lda chaqirish).
    # Ro'yxat bo'lmasa foydalanuvchi bir xil xabarni bir kunda bir necha
    # marta olardi.
    reminded_days = models.JSONField(default=list, blank=True, verbose_name="Yuborilgan eslatmalar")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # Celery job'i har kuni "muddati o'tganlar"ni shu indeks bilan topadi.
            models.Index(fields=["status", "trial_ends_at"], name="idx_sub_status_trial_end"),
            models.Index(fields=["status", "subscription_ends_at"], name="idx_sub_status_sub_end"),
        ]

    def __str__(self):
        return f"{self.business} — {self.status}"


class PaymentLog(BaseModel):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["subscription", "-created_at"], name="idx_payment_sub_created")]

class SubscriptionRequest(BaseModel):
    """
    Obunani uzaytirish/faollashtirish arizasi.

    Nega alohida model: `BusinessApplication` — biznesni OCHISH arizasi,
    u bir marta beriladi va biznes bilan bir umrga bog'lanadi. Obuna esa
    har oy yangilanadi, ya'ni bitta biznesda o'nlab ariza bo'ladi.
    Ikkalasini bitta jadvalga tiqish tarixni chalkashtirardi.

    Oqim biznes ochish bilan BIR XIL — egasi shunga o'rgangan:
      ariza yuboriladi → Telegram orqali to'lov → admin tasdiqlaydi →
      obuna reja muddatiga uzayadi.
    """

    STATUS_PENDING = "pending_payment"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = (
        (STATUS_PENDING, "To'lov kutilmoqda"),
        (STATUS_APPROVED, "Tasdiqlangan"),
        (STATUS_REJECTED, "Rad etilgan"),
    )

    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="subscription_requests"
    )
    plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.PROTECT, related_name="requests",
        help_text="Egasi qaysi muddatni tanlagani.",
    )
    # Narx ariza berilgan paytdagi holida MUZLATILADI: admin ertaga
    # tarifni oshirsa, kecha ariza bergan odam eski narxda to'laydi.
    price = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    note = models.CharField(max_length=255, blank=True, verbose_name="Egasining izohi")
    admin_note = models.CharField(max_length=255, blank=True, verbose_name="Admin izohi")

    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="reviewed_subscription_requests",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Obuna arizasi"
        verbose_name_plural = "Obuna arizalari"
        indexes = [
            # Admin panelidagi "kutilayotgan arizalar" ro'yxati.
            models.Index(fields=["status", "-created_at"], name="idx_subreq_status_created"),
            models.Index(fields=["business", "-created_at"], name="idx_subreq_biz_created"),
        ]

    def __str__(self):
        return f"{self.business} — {self.plan.duration_label} ({self.get_status_display()})"
