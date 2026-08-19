# WENZU — Backend

Restoran va to'yxonalarni onlayn qidirish, filtrlash va bron qilish platformasi.
Django 5 + DRF + PostgreSQL + Redis + Celery.

---

## Arxitektura

Loyiha 7 ta Django ilovasiga bo'lingan. Har bir ilovada API'lar **`routes/`**
paketida, har bir model uchun **alohida fayl** ko'rinishida turadi. Ilovaning
barcha serializerlari esa bitta **`routes/serializers.py`** faylida.

```
<app>/
├── routes/
│   ├── serializers.py     ← ilovaning BARCHA serializerlari
│   └── <model>.py         ← shu model uchun APIView'lar
├── filters.py             ← django-filter FilterSet'lari
├── services.py            ← biznes mantiq (view'dan ajratilgan)
├── tasks.py               ← Celery vazifalari
├── signals.py
└── urls.py
```

| Ilova | Modellar |
|---|---|
| `common` | `PlatformSettings` (singleton sozlamalar) |
| `account` | `User` |
| `businesses` | `BusinessApplication`, `Business`, `BusinessPhoto`, `Room`, `Hall`, `VenuePricing` |
| `catalog` | `RestaurantMenuItem`, `VenueMenuItem` |
| `reservations` | `Availability`, `Reservation` |
| `reviews` | `Review`, `ReviewPhoto` |
| `subscriptions` | `SubscriptionPlan`, `Subscription`, `PaymentLog` |

**Nega `services.py`:** ariza tasdiqlash, obuna faollashtirish kabi amallar
API'dan ham, Django admin panelidan ham, Celery'dan ham chaqiriladi. Mantiq
view ichida bo'lganida u uch joyda uch xil bo'lib ketardi.

---

## Rollar

Rasman **2 ta rol** (`user`, `business`) va Django'ning `is_staff` orqali
beriladigan super-admin huquqi.

Restoran egasi va to'yxona egasi **bitta rolda** — ular `business_type`
orqali ajraladi. Bu ataylab: kelajakda bitta odam ham restoran, ham to'yxona
ochsa, alohida rollar bilan tizim buzilardi.

Login javobida frontend uchun tayyor ma'lumot keladi:

```json
{
  "access": "...", "refresh": "...",
  "user": {
    "role": "business", "is_staff": false,
    "business": {"id": "...", "name": "Shoxona", "type": "restaurant"}
  }
}
```

Frontend shunga qarab panelni tanlaydi:
`is_staff` → admin paneli · `business.type == "restaurant"` → Xonalar paneli ·
`business.type == "venue"` → Zallar paneli · aks holda → oddiy foydalanuvchi.

---

## Ishga tushirish

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # qiymatlarni to'ldiring
python manage.py migrate
python manage.py seed_platform      # sozlamalar + tarif rejalari
python manage.py createsuperuser
python manage.py runserver
```

Celery (alohida terminallarda):

```bash
celery -A config worker -l info
celery -A config beat   -l info
```

Production:

```bash
python manage.py collectstatic --noinput
gunicorn config.wsgi:application -c gunicorn.conf.py
```

---

## Muhim endpointlar

| Bo'lim | Prefiks |
|---|---|
| Auth | `/api/auth/` — register, send-code, verify-phone, login, refresh, logout, me |
| Ommaviy | `/api/businesses/`, `/api/rooms/{id}/busy-hours/`, `/api/halls/{id}/busy-dates/`, `/api/settings/` |
| Mijoz | `/api/reservations/`, `/api/reviews/`, `/api/business-applications/` |
| Biznes egasi | `/api/owner/...` |
| Super-admin | `/api/admin/...` |
| Monitoring | `/api/health/` |

Hujjatlar: **`/swagger/`** va **`/redoc/`** (OpenAPI 3, drf-spectacular).

Biznes qidiruvi filtrlari birga ishlaydi:
`?type=restaurant&search=Shoxona&district=Yunusobod&cuisine=milliy&guests=6&lat=41.3&lng=69.2&radius_km=5&date=2026-09-01`

---

## Xavfsizlik

| Chora | Qayerda |
|---|---|
| Argon2 parol hashlash | `PASSWORD_HASHERS` |
| JWT rotatsiya + qora ro'yxat | `SIMPLE_JWT`, `/api/auth/logout/` |
| SMS kodi: `secrets`, 5 daqiqa TTL, 5 urinish chegarasi | `account/routes/user.py` |
| Foydalanuvchi enumeratsiyasidan himoya | `send-code` bir xil javob qaytaradi |
| Ikki qatlamli throttling (burst + kunlik) | `common/throttles.py` |
| Telefon raqami bo'yicha SMS cheklovi (IP emas) | `PhoneNumberThrottle` |
| IDOR himoyasi — biznes ID tokendan olinadi | `common/services.get_owner_business` |
| API orqali `is_staff` berib bo'lmaydi | `AdminUserDetailAPIView.EDITABLE_FIELDS` |
| Fayl yuklash: format + hajm chegarasi | `common/validators.py` |
| HSTS, secure cookie, SSL redirect, nosniff | `settings.py` (`if not DEBUG`) |
| CORS allowlist (production'da `*` emas) | `CORS_ALLOWED_ORIGINS` |
| So'rov ID + xavfsizlik loglari | `common/middleware.py`, `logs/security.log` |

`python manage.py check --deploy` production rejimida **toza** o'tadi.

---

## Unumdorlik (10 000+ foydalanuvchi uchun)

- **Kompozit indekslar** hot query yo'llarida — `is_visible+business_type+rating_avg`,
  `business+status+created_at`, `status+trial_ends_at` va h.k.
- **Geo-qidiruvda bounding box**: Haversine'dan oldin SQL darajasida
  to'rtburchak bilan kesiladi, shunda butun jadval Python'ga tortilmaydi.
- **Kesh**: ommaviy ro'yxat 60 s, detal 120 s. Kesh kalitida versiya raqami —
  biznes o'zgarganda versiya oshadi, `delete_pattern` kerak emas.
- **Denormalizatsiya**: `rating_avg` va `reviews_count` Business'da saqlanadi.
- **Subquery annotate** (JOIN emas) — qatorlar ko'payib ketmasligi uchun.
- **`CONN_MAX_AGE`** bilan ulanishni qayta ishlatish, `statement_timeout=15s`.
- **N+1 yo'q** — testlar buni ma'lumot hajmini 8 barobar oshirib tekshiradi.
- **Redis yiqilsa sayt o'lmaydi** (`IGNORE_EXCEPTIONS`), Telegram/SMS
  ishlamasa bron bekor bo'lmaydi.

---

## Testlar

```bash
python manage.py test
```

37 ta test, 3 ta faylda:

- `common/tests.py` — uchdan-uchgacha oqim: ro'yxatdan o'tish → SMS →
  ariza → trial → xona/menyu → bron → tasdiq → sharh → admin tasdig'i.
- `common/test_security.py` — IDOR, rol chegaralari, SMS brute-force,
  enumeratsiya, obuna bloklash, bron mantiqidagi teshiklar.
- `common/test_performance.py` — N+1 tekshiruvi, kesh, va eng muhimi
  **poyga holati**: 6 ta mijoz ayni damda bitta vaqtni band qilishga
  urinsa, faqat bittasi o'tadi (`select_for_update`).
