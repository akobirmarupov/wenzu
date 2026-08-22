"""
Google orqali kirish.

TZ o'zgarishi: ro'yxatdan o'tish endi FAQAT Google orqali. SMS-kod
oqimi butunlay olib tashlandi.

Nega shunday qilindi:
  · SMS har bir yuborilishida pul turadi va Eskiz shlyuzi ishlamay
    qolsa hech kim ro'yxatdan o'ta olmasdi
  · kod kutish, terish, "kelmadi — qayta yuboring" — bu yerda odamning
    yarmi to'xtab qolardi
  · Google pochtani O'ZI tekshirgan, ya'ni tasdiq allaqachon bor

Bu modul ikki ish qiladi:
  1. Google bergan `id_token` ni TEKSHIRADI (imzo, muddat, kimga
     berilgani). Bu qadam majburiy: tekshirilmagan token — shunchaki
     brauzerdan kelgan matn, uni istalgan odam o'zi yozib yuborishi
     mumkin.
  2. Tekshiruvdan o'tgan ma'lumotdan foydalanuvchi topadi yoki yaratadi.
"""

import json
import logging
import re
import unicodedata
import urllib.parse
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from account.models import User

logger = logging.getLogger("account")

# Google bergan surat 96 px bo'ladi; `=s256-c` bilan kattaroq va
# kvadrat qilib so'raymiz — profil sahifasida kichigi xira ko'rinardi.
AVATAR_SIZE = 256
AVATAR_TIMEOUT = 10

# Google OAuth manzillari.
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = "openid email profile"


class GoogleAuthError(Exception):
    """Token yaroqsiz yoki Google sozlamalari yo'q."""


# ===================================================================
# QAYTA YO'NALTIRISH (redirect) OQIMI
#
# NEGA POPUP EMAS. Avval Google Identity Services (GSI) ishlatilgan
# edi: sahifada tugma chiziladi, bosilganda popup ochiladi va token
# `postMessage` orqali qaytadi. Amalda u ishlamadi —
#
#   [GSI_LOGGER]: The given origin is not allowed for the given client ID
#
# Manzil Google Console'ga qo'shilgan bo'lsa ham GSI uni qabul
# qilmadi ("Authorized JavaScript origins" o'zgarishi Google
# serverlariga soatlab tarqaladi va biz buni tezlashtira olmaymiz).
#
# Redirect oqimi bu to'siqni BUTUNLAY chetlab o'tadi:
#   · "JavaScript origins" ro'yxati umuman ishlatilmaydi — uning
#     o'rniga "Authorized redirect URIs" tekshiriladi
#   · popup yo'q → popup bloklagichlari, uchinchi tomon cookie
#     cheklovlari va `postMessage` uzilishlari ham yo'q
#   · telefonda ishonchliroq: popup o'rniga oddiy sahifa o'tishi
#
# Oqim: brauzer Google'ga o'tadi → odam hisobini tanlaydi →
# Google bizning `/api/auth/google/callback/` ga `code` bilan
# qaytaradi → server `code` ni token'ga almashtiradi.
# ===================================================================


def build_auth_url(*, redirect_uri, state):
    """Foydalanuvchi yo'naltiriladigan Google manzilini yig'adi."""
    if not settings.GOOGLE_CLIENT_ID:
        raise GoogleAuthError(
            "Google orqali kirish sozlanmagan. GOOGLE_CLIENT_ID ni .env ga qo'shing."
        )
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        # Hisob tanlash oynasi HAR SAFAR ko'rsatilsin: bitta
        # qurilmadan bir necha hisob ishlatiladi (masalan joy egasi
        # o'z hisobi va mijoz hisobini sinaydi).
        "prompt": "select_account",
    }
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_code(*, code, redirect_uri):
    """
    Google bergan bir martalik `code` ni `id_token` ga almashtiradi.

    Bu qadam SERVERDA bajariladi va `client_secret` talab qiladi —
    shuning uchun brauzerdan qalbaki `code` yuborib bo'lmaydi.
    """
    if not settings.GOOGLE_CLIENT_SECRET:
        raise GoogleAuthError(
            "GOOGLE_CLIENT_SECRET .env da yo'q. Google Console → Clients → "
            "OAuth client → Client secrets → Add secret."
        )

    payload = urllib.parse.urlencode({
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).encode()

    request = Request(
        TOKEN_URL, data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urlopen(request, timeout=15) as response:
            data = json.loads(response.read())
    except Exception as error:
        logger.warning(f"Google token almashinuvi ishlamadi: {error}")
        raise GoogleAuthError(
            "Google bilan bog'lanib bo'lmadi. Qaytadan urinib ko'ring."
        ) from error

    id_token_value = data.get("id_token")
    if not id_token_value:
        raise GoogleAuthError("Google javobida id_token yo'q.")
    return id_token_value


def verify_google_token(credential):
    """
    Google `id_token` ni tekshirib, ichidagi ma'lumotni qaytaradi.

    Kutubxona bir necha narsani birdaniga tekshiradi: imzo Google
    kalitiga mos keladimi, muddati o'tmaganmi va token AYNAN BIZNING
    ilovamiz uchun berilganmi (`aud`). Oxirgisi eng muhimi: usiz
    boshqa saytga berilgan token bilan bizga kirib olish mumkin
    bo'lardi.
    """
    client_id = settings.GOOGLE_CLIENT_ID
    if not client_id:
        raise GoogleAuthError(
            "Google orqali kirish sozlanmagan. GOOGLE_CLIENT_ID ni .env ga qo'shing."
        )

    try:
        payload = google_id_token.verify_oauth2_token(
            credential, google_requests.Request(), client_id
        )
    except ValueError as error:
        logger.warning(f"Google token rad etildi: {error}")
        raise GoogleAuthError("Google tasdig'i qabul qilinmadi. Qaytadan urinib ko'ring.") from error

    if payload.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise GoogleAuthError("Token Google tomonidan berilmagan.")
    if not payload.get("email"):
        raise GoogleAuthError("Google hisobida pochta manzili topilmadi.")

    return payload


def username_from_email(email):
    """
    Pochtaning @ belgisigacha bo'lgan qismidan username yasaydi.

    Bizning qoidamiz: kichik lotin harflari, raqam va pastki chiziqcha,
    3–30 belgi (`validate_username`). Google pochtasida esa nuqta va
    tire uchraydi ("ali.valiyev@gmail.com"), shuning uchun tozalanadi.

    Band bo'lsa oxiriga raqam qo'shiladi: ali, ali2, ali3...
    """
    local = (email or "").split("@")[0]

    # Lotin bo'lmagan harflarni yaqin lotin muqobiliga aylantiramiz,
    # aks holda "тест@..." dan bo'sh nom chiqardi.
    local = unicodedata.normalize("NFKD", local).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9_]", "_", local.lower()).strip("_")
    base = re.sub(r"_{2,}", "_", base)[:24] or "user"
    if len(base) < 3:
        base = f"{base}_user"[:24]

    candidate = base
    suffix = 2
    while User.objects.filter(username=candidate).exists():
        tail = str(suffix)
        candidate = f"{base[:24 - len(tail)]}{tail}"
        suffix += 1
    return candidate


def _download_avatar(url):
    """
    Google profil suratini yuklab oladi.

    Xato bo'lsa `None` qaytaradi va kirish TO'XTAMAYDI: surat —
    qulaylik, uning yuklanmagani odamni saytga kiritmaslik uchun
    sabab emas. Rasmi yo'q foydalanuvchida bosh harflari ko'rinadi.
    """
    if not url:
        return None
    try:
        # Google surat manzilida o'lcham `=s96-c` ko'rinishida yoziladi.
        sized = re.sub(r"=s\d+(-c)?$", f"=s{AVATAR_SIZE}-c", url)
        request = Request(sized, headers={"User-Agent": "WENZU/1.0"})
        with urlopen(request, timeout=AVATAR_TIMEOUT) as response:
            return ContentFile(response.read())
    except Exception as error:  # noqa: BLE001 — tarmoq xatosi kirishni to'xtatmasin
        logger.warning(f"Google avatarini yuklab bo'lmadi: {error}")
        return None


@transaction.atomic
def get_or_create_google_user(payload):
    """
    Google ma'lumotidan foydalanuvchi topadi yoki yaratadi.

    @returns: (user, created)

    Uch bosqichda qidiriladi va tartib MUHIM:
      1. `google_sub` — o'zgarmas identifikator, eng ishonchlisi
      2. `email` — hisob ilgari parol bilan ochilgan bo'lsa, o'sha
         odamning o'zi. Yangi hisob yaratib, eski bronlarini yo'qotib
         qo'ymaymiz — mavjudini Google'ga BOG'LAYMIZ.
      3. topilmasa — yangi hisob
    """
    sub = payload["sub"]
    email = payload["email"].lower()

    user = User.objects.filter(google_sub=sub).first()
    created = False

    if user is None:
        user = User.objects.filter(email__iexact=email).first()
        if user is not None:
            # Eski hisob — endi Google bilan ham kiradi.
            user.google_sub = sub
            user.save(update_fields=["google_sub"])
            logger.info(f"Existing account linked to Google: user_id={user.id}")

    if user is None:
        user = User(
            username=username_from_email(email),
            email=email,
            google_sub=sub,
            full_name=(payload.get("name") or "").strip() or email.split("@")[0],
            # Pochtani Google tekshirgan — bizga qo'shimcha tasdiq kerak emas.
            is_confirmed=True,
        )
        # Parol bilan kirish yo'li yopiladi: bu hisob Google'niki.
        user.set_unusable_password()
        user.save()
        created = True
        logger.info(f"User created via Google: id={user.id}, username={user.username}")

    # --- har kirishda yangilanadigan maydonlar ---
    fields = []
    if not user.is_confirmed:
        user.is_confirmed = True
        fields.append("is_confirmed")
    if not user.email:
        user.email = email
        fields.append("email")
    # Ism-familiya faqat BO'SH bo'lsa olinadi: odam profilida o'zi
    # yozgan nomni Google'niki bilan almashtirib qo'ymaymiz.
    if not user.full_name and payload.get("name"):
        user.full_name = payload["name"].strip()
        fields.append("full_name")
    if fields:
        user.save(update_fields=fields)

    # Surat ham faqat bir marta — foydalanuvchi keyin o'zinikini yuklasa,
    # har kirishda Google'niki uni bosib ketmasligi kerak.
    if not user.avatar:
        picture = _download_avatar(payload.get("picture"))
        if picture is not None:
            user.avatar.save(f"google-{user.pk}.jpg", picture, save=True)

    return user, created
