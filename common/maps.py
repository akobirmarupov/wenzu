"""
Xarita havolalari — koordinatadan Google/Yandex manzillarini yasash va
egasi joylashtirgan havoladan koordinatani ajratib olish.

Nega alohida modul: havola matni uch joyda kerak — biznes serializerida
(mijoz ko'radigan tugmalar) va egasining sozlamalar oqimida (kiritilgan
havoladan koordinatani chiqarish). Ikki joyda qaytadan yozilsa, bir kuni
ular bir-biridan farq qila boshlardi.
"""

import re
from urllib.parse import quote

# Koordinata "bor" deb hisoblanishi uchun chegara.
#
# `latitude`/`longitude` maydonlari `default=0` bilan yaratiladi, ya'ni
# egasi hech narsa kiritmagan joyda ular NOL bo'lib turadi. Nol-nol esa
# Atlantika okeanining o'rtasidagi nuqta — u yerga havola berish mijozni
# chalg'itardi. Shuning uchun "kiritilmagan" degani aynan shu holat.
_MIN_COORD = 0.000001


def has_coordinates(latitude, longitude) -> bool:
    try:
        return abs(float(latitude or 0)) > _MIN_COORD and abs(float(longitude or 0)) > _MIN_COORD
    except (TypeError, ValueError):
        return False


def build_map_links(*, latitude=None, longitude=None, address="", name="") -> dict:
    """
    Mijoz bosadigan havolalar to'plami.

    Koordinata bo'lsa — aniq nuqta. Bo'lmasa — matnli qidiruv (nom +
    manzil): noaniq bo'lsa ham "hech narsa" dan yaxshi, xaritada joy
    baribir topiladi. Ikkalasi ham bo'lmasa — bo'sh lug'at qaytadi va
    frontend blokni umuman chizmaydi.
    """
    if has_coordinates(latitude, longitude):
        point = f"{float(latitude):.6f},{float(longitude):.6f}"
        lng_lat = f"{float(longitude):.6f},{float(latitude):.6f}"
        return {
            "google": f"https://www.google.com/maps/search/?api=1&query={point}",
            "google_directions": f"https://www.google.com/maps/dir/?api=1&destination={point}",
            # Yandex koordinatani LNG,LAT tartibida kutadi — Google'ning
            # teskarisi. Almashtirib qo'yilsa nuqta boshqa qit'aga tushadi.
            "yandex": f"https://yandex.uz/maps/?pt={lng_lat},pm2rdm&z=17&l=map",
            "yandex_directions": f"https://yandex.uz/maps/?rtext=~{point}&rtt=auto",
        }

    query = " ".join(part for part in (name, address) if part).strip()
    if not query:
        return {}

    encoded = quote(query)
    return {
        "google": f"https://www.google.com/maps/search/?api=1&query={encoded}",
        "google_directions": f"https://www.google.com/maps/dir/?api=1&destination={encoded}",
        "yandex": f"https://yandex.uz/maps/?text={encoded}",
        "yandex_directions": f"https://yandex.uz/maps/?text={encoded}&rtt=auto",
    }


# ===================================================================
# Havoladan koordinatani ajratib olish
#
# Joy egasidan "kenglik" va "uzunlik" ni qo'lda so'rash amalda ishlamaydi:
# u telefonida Google Maps'ni ochib, "ulashish" tugmasini bosadi va bizga
# HAVOLA tashlaydi. Shuning uchun havolani ham qabul qilamiz va sonlarni
# o'zimiz chiqarib olamiz — shunda "yaqinimda" qidiruvi ishlab ketadi.
# ===================================================================
_NUM = r"(-?\d{1,3}\.\d{3,})"

_PATTERNS = (
    # Google: .../@41.311081,69.240562,17z
    (re.compile(rf"@{_NUM},{_NUM}"), False),
    # Google: !3d41.311081!4d69.240562
    (re.compile(rf"!3d{_NUM}!4d{_NUM}"), False),
    # Yandex: ?ll=69.240562,41.311081  /  &pt=69.240562,41.311081
    (re.compile(rf"[?&](?:ll|pt|whatshere%5Bpoint%5D)={_NUM}(?:%2C|,){_NUM}"), True),
    # Yandex marshrut: ?rtext=~41.311081,69.240562
    (re.compile(rf"rtext=[^&]*?{_NUM}(?:%2C|,){_NUM}"), False),
    # Google: ?q=41.311081,69.240562  /  ?query=...  /  ?destination=...
    (re.compile(rf"[?&](?:q|query|daddr|destination|center)={_NUM}(?:%2C|,)\s*{_NUM}"), False),
    # 2GIS: /geo/.../69.240562,41.311081
    (re.compile(rf"2gis\.[a-z]+/.*?/{_NUM},{_NUM}"), True),
    # Oddiy matn: "41.311081, 69.240562"
    (re.compile(rf"^\s*{_NUM}\s*,\s*{_NUM}\s*$"), False),
)


def coordinates_from_link(value: str):
    """
    Havola (yoki oddiy "lat, lng" matni) ichidan koordinatani chiqaradi.

    Qaytaradi `(latitude, longitude)` yoki topilmasa `None`. Qisqartirilgan
    havolalar (`maps.app.goo.gl/...`) ichida koordinata BO'LMAYDI — ularni
    ochish uchun tashqi so'rov kerak bo'lardi, shuning uchun ular jimgina
    `None` qaytaradi va havolaning o'zi baribir saqlanadi.
    """
    if not value:
        return None

    text = str(value).strip()
    for pattern, lng_first in _PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        first, second = float(match.group(1)), float(match.group(2))
        latitude, longitude = (second, first) if lng_first else (first, second)
        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            return latitude, longitude
    return None
