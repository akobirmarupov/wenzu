import uuid
from contextvars import ContextVar
from decimal import Decimal

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
        max_length=32, default="uvente",
        help_text="@ belgisiz kiriting. Business ariza/to'lov oqimida foydalanuvchiga shu ko'rsatiladi.",
    )
    support_phone = models.CharField(max_length=20, blank=True)

    # --- depozit narxlari ---
    room_deposit_premium = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("99000"),
        help_text="Restoran Premium xonasi uchun oldindan to'lov.",
    )
    room_deposit_pro = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("49000"),
        help_text="Restoran Pro xonasi uchun oldindan to'lov.",
    )
    venue_deposit = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("599000"),
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
