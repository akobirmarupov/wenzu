import uuid
from contextvars import ContextVar
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.db import models

# Bitta so'rov davomida sozlamalarni qayta-qayta o'qimaslik uchun xotira.
# Redis o'chib qolsa ham (IGNORE_EXCEPTIONS) bu bazaga N marta bormaslikni
# kafolatlaydi: `Room.deposit_amount` har bir xona uchun chaqiriladi va
# detal sahifasida ular o'nlab bo'lishi mumkin.
_solo_memo: ContextVar = ContextVar("platform_settings_memo", default=None)


class BaseModel(models.Model):
    """
    Barcha modellar uchun umumiy asos.

    UUID birlamchi kalit: ketma-ket ID'lar tashqi API'da biznes/bron sonini
    oshkor qiladi va begona yozuvni taxmin qilib so'rashni osonlashtiradi.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class Role(models.TextChoices):
    USER = "user", "Oddiy foydalanuvchi"
    BUSINESS = "business", "Biznes admin"
    ADMIN = "admin", "Platforma admini"


class PlatformSettings(models.Model):
    """
    Butun platforma uchun bitta sozlamalar yozuvi (singleton).

    Narxlar kodga qattiq yozilmaydi — admin ularni panelda o'zgartiradi va
    deploy qilish shart emas. Yozuv har so'rovda o'qilgani uchun cache'lanadi.
    """

    CACHE_KEY = "platform_settings"
    CACHE_TTL = 300

    admin_telegram_username = models.CharField(
        max_length=32, default="akobir_marupov",
        help_text="@ belgisiz kiriting. Business ariza/to'lov oqimida foydalanuvchiga shu ko'rsatiladi.",
    )
    support_phone = models.CharField(max_length=20, blank=True, default="+998771210418")

    # --- depozit narxlari ---
    room_deposit_premium = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal(99000),
        help_text="Restoran Premium xonasi uchun oldindan to'lov.",
    )
    room_deposit_pro = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal(49000),
        help_text="Restoran Pro xonasi uchun oldindan to'lov.",
    )
    venue_deposit = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal(599000),
        help_text="To'yxona zalini bron qilishda oldindan to'lov.",
    )

    # --- obuna ---
    trial_days = models.PositiveSmallIntegerField(default=7)
    subscription_days = models.PositiveSmallIntegerField(default=30)

    class Meta:
        verbose_name = "Platforma sozlamalari"
        verbose_name_plural = "Platforma sozlamalari"

    def __str__(self):
        return "Platforma sozlamalari"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(self.CACHE_KEY)
        _solo_memo.set(None)

    @classmethod
    def get_solo(cls) -> "PlatformSettings":
        memo = _solo_memo.get()
        if memo is not None:
            return memo

        obj = cache.get(cls.CACHE_KEY)
        if obj is None:
            obj, _ = cls.objects.get_or_create(pk=1)
            cache.set(cls.CACHE_KEY, obj, cls.CACHE_TTL)

        _solo_memo.set(obj)
        return obj


class Feedback(BaseModel):
    """
    Platforma haqidagi taklif yoki shikoyat.

    ===================================================================
    NEGA KERAK
    ===================================================================
    Sinov davrida eng qimmat ma'lumot — foydalanuvchi nimadan
    qiynalayotgani. Uni faqat bitta yo'l bilan bilish mumkin: so'rash.

    Shuning uchun forma menyuning eng pastida, jimgina turadi: kerak
    bo'lganda topiladi, lekin ishlayotgan odamning e'tiborini tortmaydi.

    ===================================================================
    NEGA KIRISH TALAB QILINMAYDI
    ===================================================================
    `user` bo'sh bo'lishi MUMKIN.

    Eng qimmatli fikr ko'pincha ro'yxatdan O'TMAGAN odamdan keladi:
    "tushunmadim", "qidirganimni topolmadim" — ya'ni aynan shu odam
    saytni tashlab ketgan. Kirishni talab qilsak, u fikrini yozmasdan
    ketardi va biz sababni hech qachon bilmasdik.

    Spam xavfi cheklov bilan ushlanadi (`FeedbackThrottle`), mazmunni
    esa administrator o'zi o'qib chiqadi — sinov davrida ular ko'p
    bo'lmaydi.

    `on_delete=SET_NULL`: foydalanuvchi hisobini o'chirsa ham taklif
    qoladi. U shaxsga emas, MAHSULOTGA tegishli fikr.
    """

    KIND_IDEA = "idea"
    KIND_PROBLEM = "problem"
    KIND_OTHER = "other"
    KIND_CHOICES = (
        (KIND_IDEA, "Taklif"),
        (KIND_PROBLEM, "Muammo"),
        (KIND_OTHER, "Boshqa"),
    )

    STATUS_NEW = "new"
    STATUS_SEEN = "seen"
    STATUS_DONE = "done"
    STATUS_CHOICES = (
        (STATUS_NEW, "Yangi"),
        (STATUS_SEEN, "O'qilgan"),
        (STATUS_DONE, "Hal qilingan"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="feedbacks",
        verbose_name="Kim yozgan",
        help_text="Bo'sh — kirmagan foydalanuvchi yozgan.",
    )
    kind = models.CharField(
        max_length=10, choices=KIND_CHOICES, default=KIND_IDEA, db_index=True,
        verbose_name="Turi",
    )
    message = models.TextField(max_length=1000, verbose_name="Matn")

    # QAYSI SAHIFADAN yozilgani.
    #
    # "tugma ishlamadi" degan fikr o'z-o'zicha deyarli foydasiz —
    # qaysi ekranda ekani ma'lum bo'lsa, muammoni izlash daqiqalar
    # ishiga aylanadi. Shuning uchun manzil avtomatik qo'shiladi va
    # foydalanuvchidan hech narsa so'ralmaydi.
    page = models.CharField(
        max_length=200, blank=True, verbose_name="Qaysi sahifadan",
    )

    # Kirmagan odam javob olishni xohlasa qoldiradigan aloqa.
    # Majburiy emas: talab qilsak, aynan qisqa va foydali fikrlar
    # yozilmay qolardi.
    contact = models.CharField(
        max_length=120, blank=True, verbose_name="Aloqa (ixtiyoriy)",
        help_text="Telefon yoki Telegram — javob kerak bo'lsa.",
    )

    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_NEW, db_index=True,
        verbose_name="Holati",
    )
    admin_note = models.TextField(
        blank=True, verbose_name="Administrator izohi",
        help_text="Faqat ichki foydalanish uchun — foydalanuvchiga ko'rinmaydi.",
    )

    class Meta:
        verbose_name = "Taklif"
        verbose_name_plural = "Takliflar"
        ordering = ["-created_at"]
        indexes = [
            # Administratorning asosiy ekrani: "yangi takliflar, yangisi tepada".
            models.Index(fields=["status", "-created_at"], name="idx_feedback_status_created"),
        ]

    def __str__(self):
        author = self.user.username if self.user_id else "mehmon"
        return f"{self.get_kind_display()} — {author}"

    @property
    def short(self) -> str:
        """Ro'yxatda ko'rsatish uchun qisqartirilgan matn."""
        text = self.message.strip().replace("\n", " ")
        return text if len(text) <= 80 else text[:77] + "…"
