"""
So'rov chastotasini cheklash.

Ikki qatlamli yondashuv: `burst_*` qisqa vaqtdagi portlashni (skript, bot)
ushlaydi, `sustained_*` esa kunlik umumiy hajmni cheklaydi. Bittasi
bo'lganda — yo oddiy foydalanuvchi qiynaladi, yo hujumchi bemalol ishlaydi.
"""

from rest_framework.throttling import (
    AnonRateThrottle,
    SimpleRateThrottle,
    UserRateThrottle,
)


class BurstUserThrottle(UserRateThrottle):
    scope = "burst_user"


class SustainedUserThrottle(UserRateThrottle):
    scope = "sustained_user"


class BurstAnonThrottle(AnonRateThrottle):
    scope = "burst_anon"


class SustainedAnonThrottle(AnonRateThrottle):
    scope = "sustained_anon"


class LoginThrottle(SimpleRateThrottle):
    """
    IP + username juftligi bo'yicha — bitta hisobga parol terishni ham,
    bitta IP'dan ko'p hisobni sinashni ham cheklaydi.
    """

    scope = "login"

    def get_cache_key(self, request, view):
        username = request.data.get("username", "anonymous")
        ident = f"{self.get_ident(request)}:{username}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


# DIQQAT: bular `ScopedRateThrottle` emas, `UserRateThrottle` — chunki
# ScopedRateThrottle view'da `throttle_scope` atributini qidiradi va u
# bo'lmasa cheklovni JIMGINA o'tkazib yuboradi (ya'ni himoya ishlamaydi).
class ReservationCreateThrottle(UserRateThrottle):
    scope = "reservation_create"


class BusinessApplicationThrottle(UserRateThrottle):
    scope = "business_application"


class ReviewCreateThrottle(UserRateThrottle):
    scope = "review_create"
