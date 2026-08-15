from django.contrib.auth.models import AbstractUser
from django.db import models

from common.models import Role
from .validators import validate_username


class User(AbstractUser):
    username = models.CharField(max_length=30, unique=True, validators=[validate_username])
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=13, unique=True)
    role = models.CharField( max_length=10, choices=Role.choices, default=Role.USER, db_index=True)
    is_phone_verified = models.BooleanField(default=False)
    is_confirmed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["phone_number", "full_name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.username