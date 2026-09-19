import re

from django.core.exceptions import ValidationError

USERNAME_PATTERN = re.compile(r"^[a-z0-9_]{3,30}$")


def validate_username(value):
    if not USERNAME_PATTERN.match(value):
        raise ValidationError(
            "Username faqat kichik lotin harflari, raqamlar va pastki "
            "chiziqcha (_) dan iborat bo'lishi kerak (3-30 belgi)."
        )

PHONE_PATTERN = re.compile(r"^\+998\d{9}$")


def validate_phone_number(value):
    """
    O'zbekiston raqami: +998 va 9 ta raqam.

    Format bir xil bo'lishi shart, chunki raqam SMS yuborishda ham,
    `unique` tekshiruvida ham ishlatiladi: "+998901234567" va
    "998901234567" bir xil odam bo'lsa-da, baza ularni ikki xil deb biladi.
    """
    if not PHONE_PATTERN.match(value or ""):
        raise ValidationError(
            "Telefon raqami +998XXXXXXXXX ko'rinishida bo'lishi kerak."
        )
