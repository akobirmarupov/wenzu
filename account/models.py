from django.contrib.auth.models import AbstractUser
from django.db import models

from common.models import Role
from common.validators import validate_image_file

from .validators import validate_phone_number, validate_username


class User(AbstractUser):
    username = models.CharField(max_length=30, unique=True, validators=[validate_username])
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(
        max_length=13, unique=True, validators=[validate_phone_number]
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER, db_index=True)

    avatar = models.ImageField(
        upload_to="avatars/", null=True, blank=True, validators=[validate_image_file],
        verbose_name="Profil rasmi",
    )
    bio = models.CharField(max_length=200, blank=True, verbose_name="Qisqacha")
    birth_date = models.DateField(null=True, blank=True, verbose_name="Tug'ilgan sana")
    preferred_language = models.CharField(
        max_length=2, choices=(("uz", "O'zbekcha"), ("ru", "Русский"), ("en", "English")),
        default="uz", verbose_name="Interfeys tili",
    )

    is_phone_verified = models.BooleanField(default=False)
    is_confirmed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["phone_number", "full_name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["role", "is_active"], name="idx_user_role_active"),
            models.Index(fields=["phone_number"], name="idx_user_phone"),
        ]

    def __str__(self):
        return self.username

    @property
    def avatar_url(self) -> str | None:
        return self.avatar.url if self.avatar else None

    @property
    def initials(self) -> str:
        """Rasm bo'lmaganda ko'rsatiladigan bosh harflar."""
        parts = (self.full_name or self.username or "?").split()
        return "".join(word[0] for word in parts[:2]).upper()

    @property
    def is_platform_admin(self) -> bool:
        """Super-admin — TZ bo\'yicha alohida rol emas, Django huquqi orqali."""
        return self.is_staff or self.is_superuser
