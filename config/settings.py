from pathlib import Path
from datetime import timedelta
from decouple import config


from dotenv import load_dotenv

load_dotenv()


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


GEMINI_API_KEY = config('GEMINI_API_KEY')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = []


# Application definition

DJANGO_APPS = [
    'unfold',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

# config/settings.py
AUTH_USER_MODEL = "account.User"
# config/settings.py
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOCAL_APPS = [
    'account',
    'common',
    'businesses',
    'subscriptions',
    'reviews',
    'reservations',
    'catalog',
]


EXTERNAL_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_yasg',
    'corsheaders',
]


INSTALLED_APPS = DJANGO_APPS + EXTERNAL_APPS + LOCAL_APPS


MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
    }
}



# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'




SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
}



REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "common.pagination.DefaultPagination",
    "PAGE_SIZE": 20,

    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        # umumiy fallback (throttle klass scope belgilamagan holatlar uchun)
        "user": "1000/day",
        "anon": "100/day",

        # common/throttles.py dagi maxsus scope'lar
        "sms_verify": "5/hour",
        "login": "10/min",
        "reservation_create": "10/hour",
        "business_application": "3/day",
        "review_create": "20/day",
    },
}



CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}


UNFOLD = {
    "SITE_TITLE": "WENZU Admin",
    "SITE_HEADER": "WENZU",
    "SITE_SUBHEADER": "WENZU boshqaruv paneli",
    "SITE_URL": "/",
    "SITE_SYMBOL": "school",
    "BORDER_RADIUS": "16px",
    "THEME": "dark",
    "SITE_LOGO": {
        "light": "/static/images/logo.png",
        "dark": "/static/images/logo.png",
    },
    "STYLES": {
    "css": [
        lambda request: """
            /* ===== LOGO (sidebar / navbar) ===== */
            html body div.flex.items-center.gap-4 img.unfold-logo,
            html body .unfold-sidebar header img,
            html body a[href="/admin/"] img {
                width: 70px !important;
                height: 70px !important;
                object-fit: cover !important;
                border-radius: 50% !important;
                border: 3px solid #10b981 !important;
                box-shadow: 0 0 15px rgba(16, 185, 129, 0.4) !important;
                margin: 15px auto !important;
                display: block !important;
            }
            html body div.flex.items-center.gap-4 .material-symbols-outlined {
                display: none !important;
            }

            /* ===== LOGO (login sahifasi) ===== */
            html body div[class*="login"] img,
            html body .unfold-login-box img {
                width: 130px !important;
                height: 130px !important;
                border-radius: 50% !important;
                border: 4px solid #10b981 !important;
                box-shadow: 0 0 25px rgba(16, 185, 129, 0.5) !important;
                margin: 0 auto 30px auto !important;
            }

            /* ===== SIDEBAR ===== */
            html body .unfold-sidebar {
                background-color: #0f141c !important;
                border-right: 1px solid #1e293b !important;
            }
            html .unfold-sidebar-section-title {
                color: #10b981 !important;
                font-weight: 700 !important;
                text-transform: uppercase !important;
                letter-spacing: 0.05em !important;
                border-left: 3px solid #10b981 !important;
                padding-left: 10px !important;
            }

            /* ===== FAQAT DASHBOARD KARTALARI (bosh sahifadagi statistika bloklari) =====
               DIQQAT: bu endi juda tor — faqat bosh sahifa "grid" ichidagi to'g'ridan-to'g'ri
               bolalarga tegadi, forma inputlariga UMUMAN tegmaydi. */
            html body main > div.grid > div.rounded-default,
            html body main > div.grid > div[class*="border"][class*="p-"] {
                background-color: #1a2333 !important;
                border: 2px solid #2e3b52 !important;
                border-radius: 20px !important;
                box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3) !important;
            }

            /* ===== JADVAL (list ko'rinishi) ===== */
            html body table {
                background: #151c2c !important;
                border-radius: 12px !important;
                border: 1px solid #243146 !important;
                border-collapse: separate !important;
                border-spacing: 0 !important;
                overflow: hidden !important;
                width: 100% !important;
            }
            html body table thead th {
                background-color: #202b40 !important;
                color: #e2e8f0 !important;
                font-weight: 700 !important;
                text-transform: uppercase !important;
                letter-spacing: 0.04em !important;
                font-size: 12px !important;
                border-bottom: 2px solid #10b981 !important;
            }
            html body table th,
            html body table td {
                border: 1px solid #2e3b52 !important;
                padding: 12px 16px !important;
                color: #cbd5e1 !important;
            }
            html body table tbody tr {
                background-color: #151c2c !important;
            }
            html body table tbody tr:nth-child(even) {
                background-color: #182031 !important;
            }
            html body table tbody tr:hover {
                background-color: #1f2c40 !important;
            }
            html body table td a {
                color: #34d399 !important;
                font-weight: 600 !important;
                text-decoration: none !important;
            }
            html body table td a:hover {
                color: #6ee7b7 !important;
                text-decoration: underline !important;
            }

            /* ===== FORMA MAYDONLARI — endi ANIQ va aloha ko'rinadi =====
               Unfold har bir input/select/textarea uchun o'zining klasslarini
               beradi, biz ularning ustidan aniq fon/chegara/soya qo'yamiz. */
            html body input:not([type="checkbox"]):not([type="radio"]):not([type="submit"]):not([type="hidden"]),
            html body select,
            html body textarea,
            html body .unfold-input,
            html body [class*="AdminTextInput"] {
                background-color: #151c2c !important;
                border: 1px solid #3a4a63 !important;
                border-radius: 10px !important;
                color: #e2e8f0 !important;
                padding: 10px 14px !important;
                box-shadow: none !important;
            }
            html body input:not([type="checkbox"]):not([type="radio"]):focus,
            html body select:focus,
            html body textarea:focus {
                border-color: #10b981 !important;
                box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.35) !important;
                outline: none !important;
            }

            /* Har bir forma qatorini (label + input) bir oz ajratib turish */
            html body form .flex.flex-col.gap-2,
            html body form div[class*="mb-"] {
                margin-bottom: 16px !important;
            }

            /* ===== INLINE JADVALLAR (Room / Hall inline) ===== */
            html body .inline-group table th,
            html body .inline-group table td {
                border: 1px solid #243146 !important;
                padding: 10px 14px !important;
            }
        """
    ],
},
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Asosiy",
                "separator": True,
                "items": [
                    {"title": "Bosh sahifa", "icon": "space_dashboard", "link": "/admin/"},
                ],
            },
            {
                "title": "Foydalanuvchilar",
                "separator": True,
                "collapsible": False,
                "items": [
                    {"title": "Foydalanuvchilar", "icon": "group", "link": "/admin/account/user/"},
                ],
            },
            {
                # app: businesses
                "title": "Bizneslar",
                "separator": True,
                "collapsible": True,
                "items": [
                    {"title": "Biznes arizalari", "icon": "assignment", "link": "/admin/businesses/businessapplication/"},
                    {"title": "Bizneslar", "icon": "storefront", "link": "/admin/businesses/business/"},
                    {"title": "Xonalar", "icon": "meeting_room", "link": "/admin/businesses/room/"},
                    {"title": "Zallar", "icon": "celebration", "link": "/admin/businesses/hall/"},
                ],
            },
            {
                # app: catalog
                "title": "Katalog",
                "separator": True,
                "collapsible": True,
                "items": [
                    {"title": "Restoran menyusi", "icon": "restaurant_menu", "link": "/admin/catalog/restaurantmenuitem/"},
                    {"title": "To'yxona menyusi", "icon": "restaurant", "link": "/admin/catalog/venuemenuitem/"},
                ],
            },
            {
                # app: reservations
                "title": "Bronlar",
                "separator": True,
                "collapsible": True,
                "items": [
                    {"title": "Bo'sh vaqtlar", "icon": "event_available", "link": "/admin/reservations/availability/"},
                    {"title": "Bronlar", "icon": "event", "link": "/admin/reservations/reservation/"},
                ],
            },
            {
                # app: reviews
                "title": "Sharhlar",
                "separator": True,
                "collapsible": True,
                "items": [
                    {"title": "Sharhlar", "icon": "rate_review", "link": "/admin/reviews/review/"},
                    {"title": "Sharh rasmlari", "icon": "photo_library", "link": "/admin/reviews/reviewphoto/"},
                ],
            },
            {
                # app: subscriptions
                "title": "Obunalar",
                "separator": True,
                "collapsible": True,
                "items": [
                    {"title": "Tarif rejalari", "icon": "workspace_premium", "link": "/admin/subscriptions/subscriptionplan/"},
                    {"title": "Obunalar", "icon": "subscriptions", "link": "/admin/subscriptions/subscription/"},
                    {"title": "To'lov jurnali", "icon": "receipt_long", "link": "/admin/subscriptions/paymentlog/"},
                ],
            },
            {
                # app: common
                "title": "Sozlamalar",
                "separator": True,
                "collapsible": True,
                "items": [
                    {"title": "Platforma sozlamalari", "icon": "settings", "link": "/admin/common/platformsettings/"},
                ],
            },
        ],
    },
}