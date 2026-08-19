"""
SMS yuborish — Eskiz.uz shlyuzi orqali.

Sozlamalar berilmagan bo'lsa (masalan lokal ishlab chiqishda), SMS
yuborilmaydi va kod faqat logda ko'rinadi — shunda ishlab chiquvchi
haqiqiy SMS pulini sarflamasdan oqimni sinab ko'ra oladi.
"""

import logging

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("common")

ESKIZ_AUTH_URL = "https://notify.eskiz.uz/api/auth/login"
ESKIZ_SEND_URL = "https://notify.eskiz.uz/api/message/sms/send"
TOKEN_CACHE_KEY = "eskiz_token"
TOKEN_TTL = 60 * 60 * 24 * 25  # Eskiz tokeni ~30 kun yashaydi
TIMEOUT_SECONDS = 10


def _get_token():
    token = cache.get(TOKEN_CACHE_KEY)
    if token:
        return token
    try:
        response = requests.post(
            ESKIZ_AUTH_URL,
            data={"email": settings.ESKIZ_EMAIL, "password": settings.ESKIZ_PASSWORD},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        token = response.json()["data"]["token"]
        cache.set(TOKEN_CACHE_KEY, token, TOKEN_TTL)
        return token
    except (requests.RequestException, KeyError) as exc:
        logger.error(f"Eskiz tokenini olib bo'lmadi: {exc}")
        return None


def send_sms(phone_number, message):
    """Qaytaradi: yuborildi (True) / yuborilmadi (False)."""
    if not settings.ESKIZ_EMAIL or not settings.ESKIZ_PASSWORD:
        logger.warning(f"SMS shlyuzi sozlanmagan. {phone_number} uchun xabar: {message}")
        return False

    token = _get_token()
    if not token:
        return False

    try:
        response = requests.post(
            ESKIZ_SEND_URL,
            headers={"Authorization": f"Bearer {token}"},
            data={
                "mobile_phone": phone_number.lstrip("+"),
                "message": message,
                "from": settings.ESKIZ_FROM,
            },
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        logger.info(f"SMS yuborildi: phone={phone_number}")
        return True
    except requests.RequestException as exc:
        logger.error(f"SMS yuborib bo'lmadi ({phone_number}): {exc}")
        return False


def send_verification_code(phone_number, code):
    return send_sms(phone_number, f"WENZU tasdiqlash kodi: {code}. Hech kimga bermang.")
