"""
WENZU — Django sozlamalari.

Barcha muhitga bog'liq qiymatlar `.env` orqali beriladi. Standart qiymatlar
XAVFSIZ tomonga og'ib turadi: `.env` unutilsa loyiha production rejimida
ochilib qolmaydi, balki DEBUG=False bilan qattiq sozlamalarda ishlaydi.
"""

from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

from .unfold_config import UNFOLD  # noqa: F401  (Django shu nom bo'yicha o'qiydi)

BASE_DIR = Path(__file__).resolve().parent.parent


# ===================================================================
# Asosiy
# ===================================================================
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)

# Production'da aniq domenlar ko'rsatilishi SHART — '*' faqat DEBUG uchun.
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())
if DEBUG:
    ALLOWED_HOSTS = ALLOWED_HOSTS + ["*"]

AUTH_USER_MODEL = "account.User"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

GEMINI_API_KEY = config("GEMINI_API_KEY", default="")


# ===================================================================
# Ilovalar
# ===================================================================
DJANGO_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

EXTERNAL_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
    "corsheaders",
]

LOCAL_APPS = [
    "common",
    "web",
    "account",
    "businesses",
    "catalog",
    "reservations",
    "reviews",
    "subscriptions",
    "content",
]

INSTALLED_APPS = DJANGO_APPS + EXTERNAL_APPS + LOCAL_APPS


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "common.middleware.RequestIDMiddleware",
]


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ===================================================================
# Ma'lumotlar bazasi
# ===================================================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT"),
        # Ulanishni qayta ishlatish: 10k+ foydalanuvchida har so'rovga yangi
        # PostgreSQL ulanishi ochish eng qimmat qismlardan biri bo'lib qoladi.
        "CONN_MAX_AGE": config("DB_CONN_MAX_AGE", default=60, cast=int),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            # Bitta so'rov bazani abadiy band qilib turmasligi uchun.
            "connect_timeout": 10,
            "options": "-c statement_timeout=15000",
        },
    }
}


# ===================================================================
# Parol va autentifikatsiya
# ===================================================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Argon2 — Django tavsiya qiladigan eng kuchli hasher. bcrypt/PBKDF2 zaxira
# sifatida qoladi, shunda eski parollar birinchi kirishda avtomatik yangilanadi.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=config("JWT_ACCESS_MINUTES", default=60, cast=int)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=config("JWT_REFRESH_DAYS", default=30, cast=int)),
    # Refresh ishlatilganda yangisi beriladi va eskisi qora ro'yxatga tushadi —
    # o'g'irlangan refresh token cheksiz ishlatilmasligi uchun.
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}


# ===================================================================
# REST Framework
# ===================================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardResultsPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "common.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": (
        "common.throttles.BurstUserThrottle",
        "common.throttles.SustainedUserThrottle",
        "common.throttles.BurstAnonThrottle",
        "common.throttles.SustainedAnonThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        # Ikki qatlamli cheklov: qisqa portlash (bot/skript) alohida,
        # kunlik umumiy hajm alohida ushlanadi.
        "burst_user": "120/min",
        "sustained_user": "5000/day",
        "burst_anon": "40/min",
        "sustained_anon": "1000/day",

        # Og'ir yoki xavfli amallar uchun aniq cheklovlar
        "register": "5/hour",
        "login": "10/min",
        "sms_send": "3/hour",
        "sms_verify": "10/hour",
        "reservation_create": "10/hour",
        "business_application": "3/day",
        "review_create": "20/day",
    },
    # DEBUG'da brauzerdan sinash qulay, productionda faqat JSON.
    "DEFAULT_RENDERER_CLASSES": (
        ("rest_framework.renderers.JSONRenderer",)
        if not DEBUG
        else (
            "rest_framework.renderers.JSONRenderer",
            "rest_framework.renderers.BrowsableAPIRenderer",
        )
    ),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "WENZU API",
    "DESCRIPTION": "Restoran va to'yxonalarni onlayn qidirish va bron qilish platformasi",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api",
    # `category` nomi ikki joyda (menyu turkumi va yangilik turkumi) uchraydi —
    # schema'da avtomatik nom to'qnashmasligi uchun aniq nom beramiz.
    "ENUM_NAME_OVERRIDES": {
        "MenuCategoryEnum": "catalog.models.MenuCategory.choices",
        "NewsCategoryEnum": "content.models.News.CATEGORY_CHOICES",
    },
}


# ===================================================================
# Kesh (Redis)
# ===================================================================
REDIS_URL = config("REDIS_URL", default="redis://127.0.0.1:6379/1")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100, "retry_on_timeout": True},
            "SOCKET_CONNECT_TIMEOUT": 3,
            "SOCKET_TIMEOUT": 3,
            # Redis o'chib qolsa sayt ham o'lmasin — kesh shunchaki
            # "bo'sh" bo'lib qoladi va so'rovlar bazaga tushadi.
            "IGNORE_EXCEPTIONS": True,
        },
        "KEY_PREFIX": "wenzu",
    }
}
DJANGO_REDIS_IGNORE_EXCEPTIONS = True

# Sessiya ham Redis'da — bir nechta server orasida bo'lishish uchun.
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Ommaviy ro'yxat/detal javoblarining kesh muddati (sekund).
CACHE_TTL_BUSINESS_LIST = config("CACHE_TTL_BUSINESS_LIST", default=60, cast=int)
CACHE_TTL_BUSINESS_DETAIL = config("CACHE_TTL_BUSINESS_DETAIL", default=120, cast=int)


# ===================================================================
# Celery
# ===================================================================
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Tashkent"
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 240
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True


# ===================================================================
# Xavfsizlik
# ===================================================================
# CORS: productionda aniq domenlar ro'yxati. '*' faqat DEBUG'da.
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="", cast=Csv())
CORS_ALLOW_ALL_ORIGINS = DEBUG and not CORS_ALLOWED_ORIGINS
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

# Yuklanadigan ma'lumot hajmi — xotira bilan DoS qilishning oldini oladi.
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024    # 5 MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

if not DEBUG:
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = 31536000  # 1 yil
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SAMESITE = "Lax"


# ===================================================================
# Biznes qoidalari (PlatformSettings'da yo'q, kod darajasidagi standartlar)
# ===================================================================
TRIAL_DAYS = config("TRIAL_DAYS", default=7, cast=int)
SUBSCRIPTION_DAYS = config("SUBSCRIPTION_DAYS", default=30, cast=int)
SMS_CODE_TTL_SECONDS = config("SMS_CODE_TTL_SECONDS", default=300, cast=int)
SMS_MAX_VERIFY_ATTEMPTS = config("SMS_MAX_VERIFY_ATTEMPTS", default=5, cast=int)

TELEGRAM_BOT_TOKEN = config("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_ADMIN_CHAT_ID = config("TELEGRAM_ADMIN_CHAT_ID", default="")

ESKIZ_EMAIL = config("ESKIZ_EMAIL", default="")
ESKIZ_PASSWORD = config("ESKIZ_PASSWORD", default="")
ESKIZ_FROM = config("ESKIZ_FROM", default="4546")


# ===================================================================
# Xalqarolashtirish va statik fayllar
# ===================================================================
LANGUAGE_CODE = "uz"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# S3-mos ombor (MinIO / AWS) yoqilgan bo'lsa, media fayllar o'sha yerga boradi.
if config("USE_S3", default=False, cast=bool):
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage"}
    AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL = config("AWS_S3_ENDPOINT_URL", default=None)
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False


# ===================================================================
# Loglar
# ===================================================================
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_LEVEL = config("LOG_LEVEL", default="INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {"()": "common.middleware.RequestIDFilter"},
    },
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} req={request_id} — {message}",
            "style": "{",
        },
        "simple": {"format": "{levelname} {message}", "style": "{"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "filters": ["request_id"],
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "wenzu.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "verbose",
            "filters": ["request_id"],
            "encoding": "utf-8",
        },
        "security_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "security.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 20,
            "formatter": "verbose",
            "filters": ["request_id"],
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "django": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        "django.security": {"handlers": ["security_file", "console"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["file", "console"], "level": "ERROR", "propagate": False},
        # Loyihaning o'z ilovalari
        "account": {"handlers": ["console", "file"], "level": LOG_LEVEL, "propagate": False},
        "businesses": {"handlers": ["console", "file"], "level": LOG_LEVEL, "propagate": False},
        "catalog": {"handlers": ["console", "file"], "level": LOG_LEVEL, "propagate": False},
        "reservations": {"handlers": ["console", "file"], "level": LOG_LEVEL, "propagate": False},
        "reviews": {"handlers": ["console", "file"], "level": LOG_LEVEL, "propagate": False},
        "subscriptions": {"handlers": ["console", "file"], "level": LOG_LEVEL, "propagate": False},
        "common": {"handlers": ["console", "file"], "level": LOG_LEVEL, "propagate": False},
        "content": {"handlers": ["console", "file"], "level": LOG_LEVEL, "propagate": False},
    },
}
