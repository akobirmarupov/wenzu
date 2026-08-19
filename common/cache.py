"""
Ommaviy (auth talab qilmaydigan) javoblarni keshlash.

Nega kerak: bosh sahifadagi biznes ro'yxati eng ko'p so'raladigan endpoint.
10 000 foydalanuvchi bir vaqtda ochsa, har biri uchun JOIN va COUNT bilan
so'rov yuborish bazani cho'ktiradi. Javob 60 sekund eskirsa ham hech narsa
buzilmaydi — restoran ro'yxati sekundiga o'zgarmaydi.

Kesh kalitida VERSIYA raqami bor: biznes o'zgarganda versiyani bittaga
oshirish kifoya — eski kalitlar o'z-o'zidan "yetim" bo'lib qoladi va
Redis ularni TTL bo'yicha o'chiradi. Bu `delete_pattern` (butun Redis'ni
skanerlaydigan qimmat amal) dan ancha tez.
"""

import hashlib
import logging

from django.core.cache import cache

logger = logging.getLogger("common")

BUSINESS_VERSION_KEY = "business:version"
DEFAULT_VERSION = 1


def get_business_version() -> int:
    version = cache.get(BUSINESS_VERSION_KEY)
    if version is None:
        cache.set(BUSINESS_VERSION_KEY, DEFAULT_VERSION, None)
        return DEFAULT_VERSION
    return version


def invalidate_business_cache():
    """Biznes ma'lumoti o'zgardi — barcha keshlangan ro'yxat/detal javoblari eskiradi."""
    try:
        cache.incr(BUSINESS_VERSION_KEY)
    except ValueError:
        # Kalit hali yo'q edi (yoki Redis qayta ishga tushgan).
        cache.set(BUSINESS_VERSION_KEY, DEFAULT_VERSION + 1, None)
    logger.debug("Business kesh versiyasi oshirildi")


def build_cache_key(prefix: str, *parts) -> str:
    """
    Uzun va tartibsiz so'rov parametrlaridan qisqa, barqaror kalit yasaydi.
    Xesh ishlatiladi, chunki Redis kaliti uzun bo'lishi ham, ichida bo'sh
    joy/maxsus belgi bo'lishi ham nomaqbul.
    """
    raw = "|".join(str(p) for p in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}:v{get_business_version()}:{digest}"


def cached_response(key: str, ttl: int, producer):
    """
    Keshda bo'lsa — o'shani, bo'lmasa `producer()` natijasini qaytaradi
    va keshga yozadi.
    """
    cached = cache.get(key)
    if cached is not None:
        return cached
    value = producer()
    cache.set(key, value, ttl)
    return value
