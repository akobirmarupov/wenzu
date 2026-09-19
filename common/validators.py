"""Fayl va matn validatorlari — yuklanadigan kontentni chegaralash uchun."""

import os

from django.core.exceptions import ValidationError

MAX_IMAGE_SIZE_MB = 5
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def validate_image_file(value):
    """
    Yuklangan rasmni tekshiradi.

    Nega kerak: `ImageField` faqat "bu rasmmi" degan savolga javob beradi.
    Hajm chegarasi bo'lmasa, bitta foydalanuvchi 200 MB'lik fayl yuklab
    diskni va trafikni yeb qo'yishi mumkin; kengaytma chegarasi bo'lmasa
    esa SVG ichida JavaScript bilan XSS qilish yo'li ochiq qoladi.
    """
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f"Faqat {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))} formatdagi rasmlar qabul qilinadi."
        )

    size_mb = value.size / (1024 * 1024)
    if size_mb > MAX_IMAGE_SIZE_MB:
        raise ValidationError(
            f"Rasm hajmi {MAX_IMAGE_SIZE_MB} MB dan oshmasligi kerak "
            f"(yuklangani: {size_mb:.1f} MB)."
        )


def validate_latitude(value):
    if not -90 <= value <= 90:
        raise ValidationError("Kenglik (latitude) -90 va 90 orasida bo'lishi kerak.")


def validate_longitude(value):
    if not -180 <= value <= 180:
        raise ValidationError("Uzunlik (longitude) -180 va 180 orasida bo'lishi kerak.")
