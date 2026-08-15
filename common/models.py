import uuid

from django.db import models


class BaseModel(models.Model):
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
    admin_telegram_username = models.CharField(
        max_length=32, default="uvente",
        help_text="@ belgisiz kiriting. Business ariza/to'lov oqimida foydalanuvchiga shu ko'rsatiladi.",
    )

    class Meta:
        verbose_name = "Platforma sozlamalari"
        verbose_name_plural = "Platforma sozlamalari"

    def __str__(self):
        return "Platforma sozlamalari"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls) -> "PlatformSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
 