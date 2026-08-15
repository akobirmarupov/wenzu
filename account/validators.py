import re

from django.core.exceptions import ValidationError

USERNAME_PATTERN = re.compile(r"^[a-z0-9_]{3,30}$")


def validate_username(value):
    if not USERNAME_PATTERN.match(value):
        raise ValidationError(
            "Username faqat kichik lotin harflari, raqamlar va pastki "
            "chiziqcha (_) dan iborat bo'lishi kerak (3-30 belgi)."
        )