"""
Shablonlarga uzatiladigan umumiy qiymatlar.

Bu yerda faqat BITTA narsa bor: statik fayllar versiyasi. Sababi past
tushuntirilgan — muammo mayda ko'rinsa ham, ishlab chiqishni sezilarli
sekinlashtiradi.
"""

import hashlib
from pathlib import Path

from django.conf import settings

# ===================================================================
# Uslublar ro'yxati.
#
# Ilgari bu ro'yxat `static/css/main.css` ichida `@import` bo'lib turardi.
# Ikki jiddiy kamchiligi bor edi:
#
#   1. KESH. `@import` qilingan fayllar brauzerda sahifadan ALOHIDA
#      keshlanadi va `main.css` ga qo'yilgan versiya belgisi ularga
#      o'tmaydi. Natijada JS yangilanib, CSS eski qolib ketardi —
#      sahifa "buzilgan" ko'rinardi va Ctrl+Shift+R bosilmaguncha
#      shunday turardi.
#
#   2. TEZLIK. `@import` ketma-ket yuklanadi: brauzer avval `main.css`
#      ni oladi, o'qiydi, keyin ichidagilarni birma-bir so'raydi.
#      Alohida `<link>` teglari esa parallel yuklanadi.
#
# Tartib MUHIM: tokenlar birinchi (qolgan hammasi ularga tayanadi),
# keyin reset va tartib, oxirida komponent va sahifalar — shunda
# kaskadda keyingi qatlam oldingisini xotirjam ustidan yoza oladi.
# ===================================================================
STYLESHEETS = [
    # 1. Asos
    "css/base/_tokens.css",
    "css/base/_reset.css",
    "css/base/_typography.css",
    "css/base/_layout.css",
    # 2. Komponentlar
    "css/components/_button.css",
    "css/components/_badge.css",
    "css/components/_avatar.css",
    "css/components/_card.css",
    "css/components/_form.css",
    "css/components/_table.css",
    "css/components/_modal.css",
    "css/components/_toast.css",
    "css/components/_state.css",
    "css/components/_shell.css",
    "css/components/_topbar.css",
    "css/components/_footer.css",
    "css/components/_sidebar.css",
    "css/components/_banner.css",
    "css/components/_marquee.css",
    "css/components/_showcase.css",
    "css/components/_pricing.css",
    "css/components/_news.css",
    # 3. Sahifalar
    "css/pages/_home.css",
    "css/pages/_catalog.css",
    "css/pages/_detail.css",
    "css/pages/_auth.css",
    "css/pages/_profile.css",
    "css/pages/_premium.css",
    # 4. Telefon ko'rinishi — ENG OXIRIDA.
    #
    # Kaskadda oxirgi qatlam ustun turadi, shuning uchun mobil qoidalar
    # `!important` siz ham ishlaydi. Ro'yxat o'rtasiga qo'yilsa, keyingi
    # sahifa uslublari ularni bosib ketardi.
    "css/base/_mobile.css",
]

_cached_version = None


def _compute_version():
    """
    Statik fayllarning eng so'nggi o'zgarish vaqtidan qisqa belgi yasaydi.

    Fayl o'zgarsa belgi ham o'zgaradi, ya'ni brauzer yangi manzilni
    ko'radi va faylni qaytadan yuklaydi. O'zgarmasa — eski keshdan oladi.
    """
    newest = 0.0
    for folder in ("css", "js"):
        root = Path(settings.BASE_DIR) / "static" / folder
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file():
                newest = max(newest, path.stat().st_mtime)
    return hashlib.md5(str(newest).encode()).hexdigest()[:10]


def asset_version(request):
    """
    `{{ asset_version }}` — CSS va JS manzillariga qo'shiladigan belgi.

    DEBUG'da har so'rovda qaytadan hisoblanadi: fayl saqlangan zahoti
    sahifani yangilash kifoya, server qayta ishga tushirish shart emas.

    Productionda bir marta hisoblanadi va xotirada qoladi — bu yerda
    fayllar deploy paytida o'zgaradi, so'rov paytida emas, shuning uchun
    har so'rovda diskni aylanib chiqish ortiqcha yuk bo'lardi.
    """
    global _cached_version

    if settings.DEBUG:
        version = _compute_version()
    else:
        if _cached_version is None:
            _cached_version = _compute_version()
        version = _cached_version

    return {
        "asset_version": version,
        "stylesheets": STYLESHEETS,
    }
