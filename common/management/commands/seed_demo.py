"""
Namoyish uchun demo ma'lumot.

Bu buyruq ISHLAB CHIQARISH bazasida ishlatilmasin — u faqat loyihani
ko'rsatish va lokal sinash uchun. Barcha yozuvlar `demo_` prefiksi bilan
yaratiladi, shuning uchun `--clear` ularni xavfsiz o'chira oladi va
haqiqiy ma'lumotga tegmaydi.

SURATLAR HAQIQIY. Ular Wikimedia Commons'dan olinadi (erkin litsenziya)
va MAVZUGA mos keladi: osh yozilgan taomda oshning surati, to'yxona
zalida to'yxona zali, restoranda restoran ichki ko'rinishi. Manba va
litsenziya `media/_demo_cache/manifest.json` da yozib boriladi.

Internet bo'lmasa buyruq baribir ishlaydi — shunchaki suratsiz.

NIMA YARATILADI:
  · 10 restoran va 10 to'yxona — har birining ismi-sharifi bor egasi,
    1 oylik FAOL obunasi, xonalari/zallari, menyusi va jadvali bilan
  · 10 ta TASDIQ KUTAYOTGAN ariza (5 restoran, 5 to'yxona; 1 va 3
    oylik tariflar aralash) — administrator ularni o'z panelidan
    tasdiqlab, oqimni boshidan oxirigacha ko'radi
  · 8 mijoz, ularning bronlari va sharhlari

Parol hamma demo hisobda bir xil (pastdagi `PASSWORD`).

Ishlatish:
    python manage.py seed_demo --clear
    python manage.py seed_demo --clear --no-photos    # tezroq, suratsiz
"""

import datetime
import io
import random
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from businesses.models import BusinessPhoto, Hall, Room, VenuePricing
from businesses.services import approve_application, submit_application
from catalog.models import RestaurantMenuItem, VenueMenuItem
from reservations.models import Availability, Reservation
from reviews.models import Review

User = get_user_model()
PASSWORD = "akobir2004"

# ===================================================================
# Xona shabloni.
#
# Har bir restoranda YETTI xil xona bo'ladi: ikki kishilik stoldan
# tortib katta zalgacha. Shunday qilingani — "yaqinimda 8 kishilik joy"
# kabi qidiruvlar haqiqiy ma'lumotda sinab ko'rilsin, bitta-ikkita
# xonada filtrlar amalda ishlamasdi.
#
# (nomi, turi, sig'imi, depozit tarifi)
# ===================================================================
ROOM_SET = [
    ("Stol №1 — 2 kishilik", "standard", 2, "pro"),
    ("Stol №2 — 4 kishilik", "standard", 4, "pro"),
    ("Oilaviy stol — 6 kishilik", "standard", 6, "pro"),
    ("Terrassa — 4 kishilik", "outdoor", 4, "pro"),
    ("Terrassa — 8 kishilik", "outdoor", 8, "premium"),
    ("VIP xona — 10 kishilik", "vip", 10, "premium"),
    ("Banket zali — 20 kishilik", "vip", 20, "premium"),
]

# ===================================================================
# Restoranlar (10 ta)
#
# `menu` dagi uchinchi qiymat — SURAT MAVZUSI. Commons'da aynan shu
# so'z bo'yicha qidiriladi, shuning uchun taom nomi bilan surat mos
# tushadi.
# ===================================================================
RESTAURANTS = [
    {
        "name": "Choyxona Chinor", "district": "Chilonzor", "cuisine": "milliy",
        "open": "08:00", "close": "23:00", "lat": 41.2756, "lng": 69.2035,
        "description": "An'anaviy o'zbek milliy taomlari, keng hovli va sharqona muhit. "
                       "Oilaviy kechki ovqat va do'stlar davrasi uchun ideal joy.",
        "photos": "teahouse",
        "menu": [
            ("Osh (Toshkent usuli)", "main", 45000, "plov"),
            ("Shashlik (qo'y go'shti)", "main", 38000, "shashlik"),
            ("Norin", "main", 35000, "norin"),
            ("Somsa (3 dona)", "starter", 18000, "samsa"),
            ("Achchiq-chuchuk", "salad", 12000, "tomato-salad"),
            ("Ko'k choy (choynak)", "drink", 8000, "green-tea"),
        ],
    },
    {
        "name": "Shoxona Restorani", "district": "Yunusobod", "cuisine": "yevropa",
        "open": "09:00", "close": "23:00", "lat": 41.3641, "lng": 69.2871,
        "description": "Zamonaviy oshxona, VIP xonalar va tashqi terrassa. "
                       "Muhim uchrashuvlar va oilaviy kechki ovqat uchun mos.",
        "photos": "fine-dining",
        "menu": [
            ("Steyk Ribay", "main", 140000, "steak"),
            ("Losos grilda", "main", 120000, "salmon"),
            ("Sezar salat", "salad", 52000, "caesar-salad"),
            ("Qo'ziqorinli krem-sho'rva", "soup", 42000, "mushroom-soup"),
            ("Tiramisu", "dessert", 38000, "tiramisu"),
            ("Fresh sharbat", "drink", 22000, "orange-juice"),
        ],
    },
    {
        "name": "Osh Markazi", "district": "Mirzo Ulug'bek", "cuisine": "milliy",
        "open": "09:00", "close": "22:00", "lat": 41.3389, "lng": 69.3345,
        "description": "Shahardagi eng mashhur oshxonalardan biri. "
                       "Kunlik yangi tayyorlanadigan osh va tez xizmat.",
        "photos": "uzbek-restaurant",
        "menu": [
            ("Osh (katta lagan)", "main", 40000, "plov"),
            ("Kaklik osh", "main", 52000, "plov"),
            ("Manti (6 dona)", "main", 32000, "manti"),
            ("Achchiq-chuchuk", "salad", 10000, "tomato-salad"),
            ("Non (tandir)", "starter", 6000, "non-bread"),
            ("Ko'k choy", "drink", 6000, "green-tea"),
        ],
    },
    {
        "name": "Sky Lounge", "district": "Shayxontohur", "cuisine": "fusion",
        "open": "10:00", "close": "23:00", "lat": 41.3167, "lng": 69.2489,
        "description": "Shahar manzarasi ochiladigan tomdagi restoran. "
                       "Fusion taomlar, DJ kechalari va kokteyllar.",
        "photos": "rooftop-restaurant",
        "menu": [
            ("Wagyu burger", "main", 95000, "burger"),
            ("Tom Yum", "soup", 68000, "tom-yum"),
            ("Sushi to'plami", "main", 110000, "sushi"),
            ("Grilda pishirilgan tovuq", "main", 78000, "grilled-chicken"),
            ("Chizkeyk", "dessert", 42000, "cheesecake"),
            ("Limonad", "drink", 24000, "lemonade"),
        ],
    },
    {
        "name": "Registon Taomxonasi", "district": "Yakkasaroy", "cuisine": "milliy",
        "open": "08:30", "close": "22:30", "lat": 41.2861, "lng": 69.2452,
        "description": "Samarqand va Buxoro taomlari bir joyda. Katta oilaviy zallar "
                       "va tandirda pishirilgan non.",
        "photos": "uzbek-restaurant",
        "menu": [
            ("Samarqand oshi", "main", 48000, "plov"),
            ("Lag'mon (qo'l uzilgan)", "main", 34000, "lagman"),
            ("Chuchvara", "soup", 28000, "chuchvara"),
            ("Tandir go'sht", "main", 86000, "tandoor-meat"),
            ("Non (patir)", "starter", 8000, "non-bread"),
            ("Ayron", "drink", 9000, "ayran"),
        ],
    },
    {
        "name": "Bella Napoli", "district": "Mirobod", "cuisine": "yevropa",
        "open": "10:00", "close": "23:00", "lat": 41.2977, "lng": 69.2723,
        "description": "Haqiqiy italyan pitsasi o'tin pechida pishiriladi. "
                       "Pasta, risotto va uy sharoitidagi desertlar.",
        "photos": "pizzeria",
        "menu": [
            ("Margarita pitsa", "main", 62000, "pizza"),
            ("Pepperoni pitsa", "main", 78000, "pizza"),
            ("Karbonara pasta", "main", 68000, "pasta-carbonara"),
            ("Qo'ziqorinli risotto", "main", 72000, "risotto"),
            ("Kaprese salat", "salad", 46000, "caprese-salad"),
            ("Espresso", "drink", 18000, "espresso"),
        ],
    },
    {
        "name": "Anor Grill", "district": "Uchtepa", "cuisine": "sharqona",
        "open": "11:00", "close": "23:30", "lat": 41.2842, "lng": 69.1801,
        "description": "Ko'mirda pishirilgan kabob va sharqona ziravorlar. "
                       "Ochiq oshxona — pishirilishini o'zingiz ko'rasiz.",
        "photos": "grill-restaurant",
        "menu": [
            ("Lyulya-kabob", "main", 44000, "lyulya-kebab"),
            ("Tovuq kabob", "main", 38000, "chicken-kebab"),
            ("Qovurilgan kartoshka", "starter", 22000, "french-fries"),
            ("Xumus", "starter", 26000, "hummus"),
            ("Yashil salat", "salad", 18000, "green-salad"),
            ("Anor sharbati", "drink", 20000, "pomegranate-juice"),
        ],
    },
    {
        "name": "Bahor Kafe", "district": "Sergeli", "cuisine": "fastfood",
        "open": "09:00", "close": "22:00", "lat": 41.2298, "lng": 69.2263,
        "description": "Tez va arzon: burger, hot-dog va uyda tayyorlangan shirinliklar. "
                       "Talabalar va oilalar uchun qulay narxlar.",
        "photos": "cafe",
        "menu": [
            ("Klassik burger", "main", 32000, "burger"),
            ("Tovuqli sendvich", "main", 28000, "sandwich"),
            ("Frantsuz kartoshkasi", "starter", 16000, "french-fries"),
            ("Sabzavotli salat", "salad", 15000, "green-salad"),
            ("Shokoladli tort", "dessert", 24000, "chocolate-cake"),
            ("Kofe latte", "drink", 19000, "latte"),
        ],
    },
    {
        "name": "Marvarid Steak House", "district": "Mirobod", "cuisine": "yevropa",
        "open": "12:00", "close": "23:30", "lat": 41.2994, "lng": 69.2801,
        "description": "Quruq usulda yetiltirilgan go'sht va ochiq ko'mir gril. "
                       "Somelye tanlagan ichimliklar va tinch VIP xonalar.",
        "photos": "steakhouse",
        "menu": [
            ("Ribay steyk (300 g)", "main", 165000, "steak"),
            ("Tandirda qo'zi qovurg'asi", "main", 132000, "tandoor-meat"),
            ("Qo'ziqorinli krem-sho'rva", "soup", 46000, "mushroom-soup"),
            ("Sezar salat (tovuq bilan)", "salad", 58000, "caesar-salad"),
            ("Shokoladli tort", "dessert", 40000, "chocolate-cake"),
            ("Anor sharbati", "drink", 24000, "pomegranate-juice"),
        ],
    },
    {
        "name": "Sakura Sushi Bar", "district": "Yunusobod", "cuisine": "fusion",
        "open": "11:00", "close": "23:00", "lat": 41.3588, "lng": 69.2903,
        "description": "Yaponcha oshxona va sushi-bar. Har kuni yangi baliq, "
                       "ochiq oshxona va yakka mehmonlar uchun bar stollari.",
        "photos": "sushi-restaurant",
        "menu": [
            ("Filadelfiya to'plami", "main", 118000, "sushi"),
            ("Losos steyk", "main", 128000, "salmon"),
            ("Tom Yum sho'rvasi", "soup", 72000, "tom-yum"),
            ("Kaprese salat", "salad", 48000, "caprese-salad"),
            ("Chizkeyk", "dessert", 44000, "cheesecake"),
            ("Yashil choy", "drink", 14000, "green-tea"),
        ],
    },
]

# ===================================================================
# To'yxonalar (10 ta)
# ===================================================================
VENUES = [
    {
        "name": "Grand Palace To'yxonasi", "district": "Yunusobod",
        "lat": 41.3701, "lng": 69.2854, "photos": "wedding-hall",
        "description": "Shaharning eng nufuzli to'yxonalaridan biri. Zamonaviy zal, "
                       "katta parking va professional dekoratsiya xizmati.",
        "halls": [("Katta zal", 500), ("Kichik zal (nikoh marosimi)", 120)],
        "pricing": {1: 100000, 2: 120000, 3: 150000},
        "menu": [
            ("Palov (to'y oshi)", "main", "plov"),
            ("Manti", "main", "manti"),
            ("Lag'mon", "main", "lagman"),
            ("Salatlar to'plami", "salad", "salad-platter"),
            ("Shirinliklar stoli", "dessert", "dessert-table"),
            ("Ichimliklar", "drink", "soft-drinks"),
        ],
    },
    {
        "name": "Bog'i Rayhon", "district": "Sergeli", "lat": 41.2234, "lng": 69.2201,
        "photos": "garden-wedding",
        "description": "Ochiq havoda va yopiq zalda o'tkaziladigan tadbirlar uchun qulay maskan. "
                       "Bog' hududi fotosessiya uchun ajoyib.",
        "halls": [("Yopiq zal", 300), ("Ochiq bog' maydoni", 400)],
        "pricing": {1: 90000, 2: 110000, 3: 140000},
        "menu": [
            ("Palov", "main", "plov"),
            ("Kabob", "main", "shashlik"),
            ("Salatlar", "salad", "salad-platter"),
            ("Tandir non", "starter", "non-bread"),
            ("Mevalar", "dessert", "fruit-platter"),
        ],
    },
    {
        "name": "Diyor Saroyi", "district": "Mirzo Ulug'bek", "lat": 41.3412, "lng": 69.3390,
        "photos": "banquet-hall",
        "description": "Katta tadbirlar uchun mo'ljallangan ulkan zal. "
                       "Zamonaviy yorug'lik va tovush tizimi bilan jihozlangan.",
        "halls": [("Asosiy zal", 800), ("Bo'lim zali", 200)],
        "pricing": {1: 110000, 2: 135000, 3: 165000},
        "menu": [
            ("Osh", "main", "plov"),
            ("Manti", "main", "manti"),
            ("Shashlik", "main", "shashlik"),
            ("Sabzavotli salat", "salad", "green-salad"),
            ("Shirinliklar", "dessert", "dessert-table"),
        ],
    },
    {
        "name": "Navro'z Saroyi", "district": "Chilonzor", "lat": 41.2718, "lng": 69.2043,
        "photos": "wedding-hall",
        "description": "Milliy uslubdagi bezaklar va zamonaviy qulayliklar. "
                       "Nikoh to'yi, uzatish marosimi va yubileylar uchun.",
        "halls": [("Navro'z zali", 600), ("Kichik marosim zali", 150)],
        "pricing": {1: 95000, 2: 118000, 3: 145000},
        "menu": [
            ("To'y oshi", "main", "plov"),
            ("Norin", "main", "norin"),
            ("Chuchvara", "soup", "chuchvara"),
            ("Achchiq-chuchuk", "salad", "tomato-salad"),
            ("Shirinliklar", "dessert", "dessert-table"),
            ("Choy va ichimliklar", "drink", "green-tea"),
        ],
    },
    {
        "name": "Zilol Zamon", "district": "Olmazor", "lat": 41.3488, "lng": 69.2032,
        "photos": "banquet-hall",
        "description": "Yorug' va keng zal, katta sahna va professional videosuratga olish "
                       "xizmati. Mehmonlar uchun alohida kirish.",
        "halls": [("Zilol zali", 450), ("Yosh-kelin zali", 100)],
        "pricing": {1: 88000, 2: 105000, 3: 132000},
        "menu": [
            ("Palov", "main", "plov"),
            ("Tovuq kabob", "main", "chicken-kebab"),
            ("Mevali stol", "dessert", "fruit-platter"),
            ("Salatlar", "salad", "salad-platter"),
            ("Ichimliklar", "drink", "soft-drinks"),
        ],
    },
    {
        "name": "Oq Saroy", "district": "Bektemir", "lat": 41.2113, "lng": 69.3350,
        "photos": "garden-wedding",
        "description": "Shahar chetidagi tinch hudud, katta parking va bog'. "
                       "Yozgi to'ylar uchun ochiq maydon ham bor.",
        "halls": [("Oq zal", 350), ("Yozgi maydon", 500)],
        "pricing": {1: 85000, 2: 102000, 3: 128000},
        "menu": [
            ("To'y palovi", "main", "plov"),
            ("Lag'mon", "main", "lagman"),
            ("Somsa", "starter", "samsa"),
            ("Salatlar", "salad", "salad-platter"),
            ("Tort", "dessert", "chocolate-cake"),
        ],
    },
    {
        "name": "Shodlik Saroyi", "district": "Yashnobod", "lat": 41.2887, "lng": 69.3121,
        "photos": "wedding-reception",
        "description": "Ikki qavatli zamonaviy to'yxona: pastda nikoh marosimi, "
                       "yuqorida katta to'y zali. Liftli kirish va issiq yo'lak.",
        "halls": [("Shodlik zali", 550), ("Nikoh zali", 140)],
        "pricing": {1: 105000, 2: 125000, 3: 155000},
        "menu": [
            ("To'y oshi", "main", "plov"),
            ("Tovuq kabob", "main", "chicken-kebab"),
            ("Manti", "main", "manti"),
            ("Salatlar to'plami", "salad", "salad-platter"),
            ("Shirinliklar stoli", "dessert", "dessert-table"),
            ("Ichimliklar", "drink", "soft-drinks"),
        ],
    },
    {
        "name": "Malika To'yxonasi", "district": "Uchtepa", "lat": 41.2809, "lng": 69.1774,
        "photos": "wedding-decor",
        "description": "O'z dekoratsiya jamoasi bor to'yxona: sahna bezagi, gullar va "
                       "yorug'lik narxga kiritilgan. Kelin-kuyov uchun alohida xona.",
        "halls": [("Malika zali", 400), ("Kichik zal", 130)],
        "pricing": {1: 98000, 2: 120000, 3: 148000},
        "menu": [
            ("Palov", "main", "plov"),
            ("Norin", "main", "norin"),
            ("Chuchvara", "soup", "chuchvara"),
            ("Achchiq-chuchuk", "salad", "tomato-salad"),
            ("Mevali stol", "dessert", "fruit-platter"),
            ("Choy", "drink", "green-tea"),
        ],
    },
    {
        "name": "Anhor Bog'i", "district": "Shayxontohur", "lat": 41.3243, "lng": 69.2384,
        "photos": "garden-wedding",
        "description": "Anhor bo'yidagi bog' maskani. Yozda ochiq maydonda, qishda "
                       "issiq zalda tadbir o'tkaziladi. Fotosessiya uchun ko'prik va soyabon.",
        "halls": [("Bog' maydoni", 450), ("Qishki zal", 250)],
        "pricing": {1: 92000, 2: 112000, 3: 138000},
        "menu": [
            ("To'y palovi", "main", "plov"),
            ("Shashlik", "main", "shashlik"),
            ("Somsa", "starter", "samsa"),
            ("Yashil salat", "salad", "green-salad"),
            ("Mevalar", "dessert", "fruit-platter"),
        ],
    },
    {
        "name": "Sitora Palace", "district": "Mirobod", "lat": 41.3012, "lng": 69.2846,
        "photos": "ballroom",
        "description": "Shahar markazidagi nufuzli marosimlar zali. Qandil, sahna va "
                       "professional tovush tizimi. Mehmonlar uchun yopiq parking.",
        "halls": [("Sitora zali", 700), ("Yulduz zali", 180)],
        "pricing": {1: 125000, 2: 148000, 3: 178000},
        "menu": [
            ("To'y oshi", "main", "plov"),
            ("Lyulya-kabob", "main", "lyulya-kebab"),
            ("Lag'mon", "main", "lagman"),
            ("Salatlar to'plami", "salad", "salad-platter"),
            ("Shirinliklar stoli", "dessert", "dessert-table"),
            ("Ichimliklar", "drink", "soft-drinks"),
        ],
    },
]

# ===================================================================
# Surat qidiruvlari.
#
# Chapda — kod ichidagi belgi, o'ngda Commons uchun so'rov. Ajratib
# yozilgani: so'rovni yaxshilash uchun ma'lumotlar jadvaliga tegish
# shart emas, hammasi shu yerda.
#
# So'rovlar ATAYLAB QISQA. Commons qidiruvi barcha so'zlarni VA bilan
# birlashtiradi, shuning uchun "shashlik kebab grilled meat skewers"
# kabi uzun ibora nol natija berardi — "shashlik" esa o'nlab.
# ===================================================================
# Commons'dagi qidiruv so'zlari.
#
# So'z ANIQ bo'lishi kerak: "lemonade" so'rovi XIX asr rasmini,
# "plov" esa oshxona jarayonini chiqarib qo'yadi — Commons'da san'at
# asarlari ham, hujjatli kadrlar ham bir xil teglangan. "plate",
# "glass", "cup" kabi so'zlar natijani tayyor taom tomonga suradi.
PHOTO_TERMS = {
    # --- joy ko'rinishlari ---
    "teahouse": "chaikhana",
    "fine-dining": "restaurant dining room",
    "uzbek-restaurant": "Uzbek restaurant",
    "rooftop-restaurant": "rooftop restaurant",
    "pizzeria": "pizzeria",
    "grill-restaurant": "grill restaurant",
    "cafe": "cafe interior",
    "wedding-hall": "wedding hall",
    "garden-wedding": "outdoor wedding venue",
    "banquet-hall": "banquet hall",
    "steakhouse": "steakhouse interior",
    "sushi-restaurant": "sushi restaurant interior",
    "wedding-reception": "wedding reception hall",
    "wedding-decor": "wedding hall decoration",
    "ballroom": "ballroom interior",
    # --- taomlar ---
    "plov": "uzbek pilaf",
    "shashlik": "shashlik",
    "norin": "naryn dish",
    "samsa": "samsa pastry",
    "tomato-salad": "tomato salad",
    "green-tea": "green tea teapot",
    "steak": "ribeye steak",
    "salmon": "grilled salmon",
    "caesar-salad": "caesar salad",
    "mushroom-soup": "mushroom soup",
    "tiramisu": "tiramisu",
    "orange-juice": "orange juice glass",
    "manti": "manti dumplings",
    "non-bread": "Uzbek non bread",
    "burger": "hamburger plate",
    "tom-yum": "tom yum",
    "sushi": "sushi platter",
    "grilled-chicken": "roast chicken plate",
    "cheesecake": "cheesecake slice",
    "lemonade": "homemade lemonade",
    "lagman": "lagman",
    "chuchvara": "dumpling soup",
    "tandoor-meat": "roast lamb meat",
    "ayran": "yogurt drink glass",
    "pizza": "pizza margherita",
    "pasta-carbonara": "spaghetti carbonara",
    "risotto": "risotto",
    "caprese-salad": "caprese salad",
    "espresso": "espresso shot",
    "lyulya-kebab": "lula kebab",
    "chicken-kebab": "chicken kebab",
    "french-fries": "french fries",
    "hummus": "hummus",
    "green-salad": "green salad",
    "pomegranate-juice": "pomegranate juice bottle",
    "sandwich": "chicken sandwich",
    "chocolate-cake": "chocolate cake",
    "latte": "caffe latte",
    "salad-platter": "salad buffet",
    "dessert-table": "dessert buffet",
    "fruit-platter": "fruit platter",
    "soft-drinks": "soft drinks bottles",
}

# ===================================================================
# JOY EGALARI — har bir joyning o'z hisobi.
#
# Nega alohida jadval: ilgari egalar `demo_owner_<joy nomi>` ko'rinishida
# avtomatik yaratilardi. Bunday hisob namoyish paytida darhol sun'iy
# ko'rinardi — kirish oynasiga "demo_owner_grand" deb yozish haqiqiy
# ishlatishga o'xshamaydi. Endi har bir joyning ismi-sharifi bor odami
# bor, telefon raqami bilan: ro'yxatni ochib, kimning qaysi joy egasi
# ekanini ko'rish mumkin.
#
# `demo_` prefiksi ATAYLAB saqlanadi: `--clear` aynan shu prefiksga
# qarab tozalaydi va haqiqiy foydalanuvchilarga tegmaydi.
#
# joy nomi: (username, ism-familiya, telefon)
# ===================================================================
OWNERS = {
    # --- restoranlar ---
    "Choyxona Chinor":      ("demo_akmal_tursunov", "Akmal Tursunov", "+998901010101"),
    "Shoxona Restorani":    ("demo_bekzod_aliyev", "Bekzod Aliyev", "+998901010102"),
    "Osh Markazi":          ("demo_sardor_yoqubov", "Sardor Yoqubov", "+998901010103"),
    "Sky Lounge":           ("demo_temur_saidov", "Temur Saidov", "+998901010104"),
    "Registon Taomxonasi":  ("demo_ulugbek_nazarov", "Ulug'bek Nazarov", "+998901010105"),
    "Bella Napoli":         ("demo_farrux_qodirov", "Farrux Qodirov", "+998901010106"),
    "Anor Grill":           ("demo_jasur_ergashev", "Jasur Ergashev", "+998901010107"),
    "Bahor Kafe":           ("demo_dilnoza_ismoilova", "Dilnoza Ismoilova", "+998901010108"),
    "Marvarid Steak House": ("demo_shohruh_umarov", "Shohruh Umarov", "+998901010109"),
    "Sakura Sushi Bar":     ("demo_aziza_rahimova", "Aziza Rahimova", "+998901010110"),
    # --- to'yxonalar ---
    "Grand Palace To'yxonasi": ("demo_rustam_xolmatov", "Rustam Xolmatov", "+998901010201"),
    "Bog'i Rayhon":            ("demo_gulnora_sattorova", "Gulnora Sattorova", "+998901010202"),
    "Diyor Saroyi":            ("demo_ilhom_yusupov", "Ilhom Yusupov", "+998901010203"),
    "Navro'z Saroyi":          ("demo_qahramon_toshev", "Qahramon Toshev", "+998901010204"),
    "Zilol Zamon":             ("demo_mavluda_ochilova", "Mavluda Ochilova", "+998901010205"),
    "Oq Saroy":                ("demo_botir_hasanov", "Botir Hasanov", "+998901010206"),
    "Shodlik Saroyi":          ("demo_anvar_mirzayev", "Anvar Mirzayev", "+998901010207"),
    "Malika To'yxonasi":       ("demo_nigora_abdullayeva", "Nigora Abdullayeva", "+998901010208"),
    "Anhor Bog'i":             ("demo_shavkat_normatov", "Shavkat Normatov", "+998901010209"),
    "Sitora Palace":           ("demo_zafar_karimov", "Zafar Karimov", "+998901010210"),
}

# ===================================================================
# KUTILAYOTGAN ARIZALAR — administrator uchun ish stoli.
#
# Bular hali TASDIQLANMAGAN: odam ro'yxatdan o'tgan, tarif tanlab ariza
# yuborgan va javob kutmoqda. Joyi bazada bor, lekin `is_visible=False`
# — qidiruvda chiqmaydi, obunasi ochilmagan, egasi panelga ma'lumot
# kirita olmaydi.
#
# Nega kerak: tasdiqlash oqimini HAQIQIY ma'lumotda sinash uchun. Faqat
# tasdiqlangan joylar bo'lsa, admin panelidagi "Arizalar" bo'limi bo'sh
# turadi va uni bosib ko'rib bo'lmaydi.
#
# Tariflar ATAYLAB aralash — 1 oylik va 3 oylik. Tasdiqlangandan keyin
# obuna aynan tanlangan muddatga ochiladi, ya'ni farqi darhol ko'rinadi.
#
# (username, ism-familiya, telefon, biznes turi, joy nomi, oy)
# ===================================================================
PENDING_APPLICANTS = [
    ("demo_muzaffar_sobirov", "Muzaffar Sobirov", "+998901010301",
     "restaurant", "Lazzat Milliy Taomlar", 1),
    ("demo_shahnoza_yuldash", "Shahnoza Yo'ldosheva", "+998901010302",
     "restaurant", "Shirin Kafe", 3),
    ("demo_otabek_rasulov", "Otabek Rasulov", "+998901010303",
     "restaurant", "Baraka Osh Uyi", 1),
    ("demo_kamron_alimov", "Kamronbek Alimov", "+998901010304",
     "restaurant", "Gril Master", 3),
    ("demo_madina_xudoyberdi", "Madina Xudoyberdiyeva", "+998901010305",
     "restaurant", "Sitora Pitsa", 1),
    ("demo_sanjar_ochilov", "Sanjar Ochilov", "+998901010306",
     "venue", "Yangi Asr To'yxonasi", 3),
    ("demo_zulfiya_nematova", "Zulfiya Ne'matova", "+998901010307",
     "venue", "Guliston Saroyi", 1),
    ("demo_doniyor_xasanov", "Doniyor Xasanov", "+998901010308",
     "venue", "Marvarid To'yxonasi", 3),
    ("demo_feruza_bekmurod", "Feruza Bekmurodova", "+998901010309",
     "venue", "Zarafshon Bog'i", 1),
    ("demo_ergash_qurbonov", "Ergash Qurbonov", "+998901010310",
     "venue", "Chinor Saroyi", 3),
]

# Bron qiladigan va sharh qoldiradigan oddiy mijozlar.
CUSTOMERS = [
    ("demo_dilshod", "Dilshod Aliyev", "+998901112233"),
    ("demo_nodira", "Nodira Karimova", "+998907778899"),
    ("demo_javohir", "Javohir Rasulov", "+998903334455"),
    ("demo_kamola", "Kamola Yusupova", "+998905556677"),
    ("demo_bobur", "Bobur Ergashev", "+998901112244"),
    ("demo_zarina", "Zarina Umarova", "+998907778811"),
    ("demo_islom", "Islom Toshpo'latov", "+998903334466"),
    ("demo_malika", "Malika Sobirova", "+998905556688"),
]

COMMENTS = [
    "Xizmat a'lo darajada, ovqatlar juda mazali. Albatta yana boraman!",
    "Interyer chiroyli, xodimlar xushmuomala. Tavsiya qilaman.",
    "Joy toza va shinam, narxlar ham o'rtacha. Oila bilan bordik.",
    "Buyurtma tez keldi, hammasi issiq va yangi edi.",
    "To'yimiz juda chiroyli o'tdi, xodimlar diqqat bilan yordam berishdi.",
    "Bron qilish oson bo'ldi, kelganimizda stol tayyor turgan edi.",
    "Narx-sifat nisbati yaxshi. Do'stlarimga ham aytdim.",
]


class Command(BaseCommand):
    help = "Namoyish uchun 10 restoran, 10 to'yxona, kutilayotgan arizalar, bron va sharhlar yaratadi."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true",
                            help="Avval eski demo ma'lumotni o'chiradi")
        parser.add_argument("--no-photos", action="store_true",
                            help="Suratlarsiz — tezroq, internet talab qilmaydi")

    def handle(self, *args, **options):
        if options["clear"]:
            deleted = User.objects.filter(username__startswith="demo_").delete()
            self.stdout.write(self.style.WARNING(
                f"Eski demo ma'lumot o'chirildi: {deleted[0]} yozuv"))

        if User.objects.filter(username__startswith="demo_").exists():
            self.stdout.write(self.style.WARNING(
                "Demo ma'lumot allaqachon mavjud. Qayta yaratish uchun --clear bilan ishga tushiring."))
            return

        random.seed(42)  # har safar bir xil natija — namoyish barqaror bo'lsin
        self.use_photos = not options["no_photos"]
        self.photo_cache = {}
        self.plans = self._plans()

        # Bir surat mavzusini bir nechta joy baham ko'radi (masalan uchta
        # bog' to'yxonasi). Har biriga keshdagi kadrlar ro'yxatining
        # BOSHQA qismidan beriladi — aks holda uchalasi bosh sahifada
        # bir xil rasm bilan chiqib, ma'lumot soxta ekani darrov
        # bilinardi. Bu yerda har bir joyga o'z "boshlanish nuqtasi"
        # hisoblanadi.
        self.photo_slot = {}
        used = {}
        for data in RESTAURANTS + VENUES:
            key = data["photos"]
            self.photo_slot[data["name"]] = used.get(key, 0) * 4
            used[key] = used.get(key, 0) + 1

        # Suratlar TRANZAKSIYADAN TASHQARIDA yuklanadi: tarmoq sekin
        # bo'lsa, ochiq tranzaksiya bazani daqiqalab qulflab turardi.
        if self.use_photos:
            self._download_photos()

        with transaction.atomic():
            # Arizalarni tasdiqlaydigan hisob. Haqiqiy tizimda buni
            # administrator qiladi; demoda esa tasdiqlovchi yo'q, shuning
            # uchun mavjud super-admin (yoki demo admini) ishlatiladi.
            self.approver = (
                User.objects.filter(is_staff=True, is_active=True).order_by("id").first()
                or self._user("demo_admin", "Demo Administrator", "+998900000001", is_staff=True)
            )

            customers = [self._user(u, n, p) for u, n, p in CUSTOMERS]
            businesses = []
            for index, data in enumerate(RESTAURANTS):
                businesses.append(self._restaurant(data, index))
            for index, data in enumerate(VENUES):
                businesses.append(self._venue(data, index))
            self._reservations_and_reviews(businesses, customers)
            self._pending_applications()

        self._report(customers)

    # ---------------- tariflar ----------------
    def _plans(self):
        """
        Tarif rejalarini tayyorlaydi: {(biznes turi, oy): reja}.

        `seed_platform` ularni yaratadi, lekin demo undan oldin ham
        ishga tushishi mumkin. Yo'q bo'lsa shu yerda ochiladi —
        seeder boshqa buyruqning tartibiga bog'liq bo'lmasin.
        """
        from common.management.commands.seed_platform import PLAN_PRICES
        from subscriptions.models import SubscriptionPlan

        plans = {}
        for business_type, durations in PLAN_PRICES.items():
            for months, price in durations.items():
                plans[(business_type, months)], _ = SubscriptionPlan.objects.get_or_create(
                    business_type=business_type, duration_months=months,
                    defaults={"price": price, "trial_days": 7},
                )
        return plans

    # ---------------- suratlar ----------------
    def _download_photos(self):
        """Barcha kerakli mavzularni oldindan yuklab, keshga soladi."""
        from common.management.commands._commons import collect

        place_keys = {data["photos"] for data in RESTAURANTS + VENUES}
        food_keys = {item[3] for data in RESTAURANTS for item in data["menu"]}
        food_keys |= {item[2] for data in VENUES for item in data["menu"]}

        self.stdout.write("Suratlar yuklanmoqda (Wikimedia Commons)...")
        for key in sorted(place_keys):
            # Joy uchun ko'proq kadr kerak: muqova + galereya + xona/zal.
            # O'nta — chunki bitta mavzuni uchtagacha joy baham ko'radi
            # va har biriga o'z kadrlari tegishi kerak (`photo_slot`).
            self.photo_cache[key] = collect(PHOTO_TERMS[key], 10, cache_key=key)
            self.stdout.write(f"  {key}: {len(self.photo_cache[key])} ta")
        for key in sorted(food_keys):
            self.photo_cache[key] = collect(PHOTO_TERMS[key], 2, cache_key=key)

        total = sum(len(v) for v in self.photo_cache.values())
        self.stdout.write(self.style.SUCCESS(f"  jami {total} ta surat tayyor\n"))

    def _picture(self, key, index=0, *, width=1400):
        """
        Keshdan bitta suratni Django fayli sifatida beradi.

        Surat qayta siqiladi: Commons'dan kelgan kadr 1-2 MB bo'lishi
        mumkin, bu esa demo uchun ortiqcha. Kenglik cheklanadi va JPEG
        sifat 82 ga tushiriladi — ko'z bilan farqi bilinmaydi, hajmi
        esa bir necha barobar kichrayadi.
        """
        files = self.photo_cache.get(key) or []
        if not files:
            return None

        path = files[index % len(files)]
        try:
            from PIL import Image

            image = Image.open(path)
            image = image.convert("RGB")
            if image.width > width:
                height = round(image.height * width / image.width)
                image = image.resize((width, height), Image.LANCZOS)

            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=82, optimize=True)
            return ContentFile(buffer.getvalue())
        except Exception:  # noqa: BLE001 — buzuq fayl demoni to'xtatmasin
            return None

    def _attach(self, field, key, index=0, *, name, width=1400):
        picture = self._picture(key, index, width=width)
        if picture is None:
            return False
        field.save(name, picture, save=True)
        return True

    # ---------------- yordamchilar ----------------
    def _user(self, username, full_name, phone, **extra):
        return User.objects.create_user(
            username=username, password=PASSWORD, full_name=full_name,
            phone_number=phone, is_phone_verified=True, is_confirmed=True, **extra,
        )

    def _slug(self, name):
        return (name.lower().replace("'", "").replace(" ", "_").split("_")[0])[:12]

    # ---------------- restoran ----------------
    def _restaurant(self, data, index):
        username, full_name, phone = OWNERS[data["name"]]
        owner = self._user(username, full_name, phone)

        # Demo joylar DARHOL tasdiqlanadi.
        #
        # Haqiqiy oqimda ariza yuborilgach admin uni tekshiradi va ana
        # shunda biznes ko'rinadigan bo'ladi. Demoda tasdiqlovchi yo'q,
        # shuning uchun buni seeder o'zi bajaradi — aks holda barcha
        # namoyish joylari yashirin qolib, sayt bo'sh ko'rinardi.
        #
        # Tarif ariza bosqichidayoq tanlanadi (1 oylik), ya'ni bu PULLIK
        # ariza: tasdiqlangach obuna bepul sinovsiz, darhol 'active'
        # holatda 30 kunga ochiladi. Sinov yo'li alohida — uni
        # kutilayotgan arizalarda ko'rish mumkin.
        application, business, _ = submit_application(
            applicant=owner, business_type="restaurant", business_name=data["name"],
            plan=self.plans[("restaurant", 1)],
        )
        approve_application(application=application, approved_by=self.approver)

        business.district = data["district"]
        business.cuisine = data["cuisine"]
        business.address = f"{data['district']} tumani, Toshkent"
        business.latitude, business.longitude = data["lat"], data["lng"]
        business.description = data["description"]
        business.open_time = data["open"]
        business.close_time = data["close"]
        business.telegram_username = f"{self._slug(data['name'])}_admin"
        # Aloqa raqami joyning O'ZINIKI (egasinikidan boshqa) — mijoz
        # shu raqamga qo'ng'iroq qiladi. Restoran va to'yxona raqamlari
        # turli oraliqdan olinadi, aks holda ikki xil joy bir xil raqam
        # bilan chiqib qolardi.
        business.phone_number = f"+99871200{index:03d}"
        business.save()

        photos = data["photos"]
        slot = self.photo_slot[data["name"]]
        self._attach(business.cover_photo, photos, slot,
                     name=f"{business.id}-cover.jpg")

        # Galereya — uchta qo'shimcha kadr (muqovadan boshqa).
        for order in range(3):
            picture = self._picture(photos, slot + order + 1, width=1200)
            if picture is None:
                break
            photo = BusinessPhoto(business=business, order=order)
            photo.image.save(f"{business.id}-{order}.jpg", picture, save=True)

        rooms = []
        for position, (name, room_type, capacity, tier) in enumerate(ROOM_SET):
            room = Room.objects.create(
                business=business, name=name, room_type=room_type,
                capacity=capacity, deposit_tier=tier,
            )
            self._attach(room.photo, photos, slot + position,
                         name=f"{room.id}.jpg", width=900)
            rooms.append(room)

        for name, category, price, photo_key in data["menu"]:
            item = RestaurantMenuItem.objects.create(
                business=business, name=name, category=category,
                price=Decimal(price), is_available=True,
                description=f"{name} — {business.name} oshxonasidan.",
            )
            self._attach(item.photo, photo_key, 0, name=f"{item.id}.jpg", width=900)

        self._availability(business, rooms=rooms)
        return business

    # ---------------- to'yxona ----------------
    def _venue(self, data, index):
        username, full_name, phone = OWNERS[data["name"]]
        owner = self._user(username, full_name, phone)

        application, business, _ = submit_application(
            applicant=owner, business_type="venue", business_name=data["name"],
            plan=self.plans[("venue", 1)],
        )
        approve_application(application=application, approved_by=self.approver)

        business.district = data["district"]
        business.address = f"{data['district']} tumani, Toshkent"
        business.latitude, business.longitude = data["lat"], data["lng"]
        business.description = data["description"]
        business.telegram_username = f"{self._slug(data['name'])}_admin"
        business.phone_number = f"+99871210{index:03d}"
        business.save()

        photos = data["photos"]
        slot = self.photo_slot[data["name"]]
        self._attach(business.cover_photo, photos, slot, name=f"{business.id}-cover.jpg")

        for order in range(3):
            picture = self._picture(photos, slot + order + 1, width=1200)
            if picture is None:
                break
            photo = BusinessPhoto(business=business, order=order)
            photo.image.save(f"{business.id}-{order}.jpg", picture, save=True)

        for position, (name, people) in enumerate(data["halls"]):
            hall = Hall.objects.create(business=business, name=name, people=people)
            self._attach(hall.photo, photos, slot + position + 1,
                         name=f"{hall.id}.jpg", width=1200)

        for dish_count, price in data["pricing"].items():
            VenuePricing.objects.create(
                business=business, dish_count=dish_count,
                price_per_person=Decimal(price),
            )

        for name, category, photo_key in data["menu"]:
            item = VenueMenuItem.objects.create(
                business=business, name=name, category=category,
                description=f"{name} — {business.name} to'y dasturxonidan.",
            )
            self._attach(item.photo, photo_key, 0, name=f"{item.id}.jpg", width=900)

        self._availability(business, rooms=None)
        return business

    # ---------------- bo'sh vaqtlar ----------------
    def _availability(self, business, *, rooms):
        """Kelgusi 45 kunga jadval ochadi."""
        today = datetime.date.today()
        rows = []
        for offset in range(45):
            day = today + datetime.timedelta(days=offset)
            if rooms:
                for room in rooms:
                    rows.append(Availability(
                        business=business, room=room, date=day,
                        start_time=business.open_time or datetime.time(9, 0),
                        end_time=business.close_time or datetime.time(23, 0),
                    ))
            else:
                rows.append(Availability(
                    business=business, room=None, date=day,
                    start_time=datetime.time(0, 0), end_time=datetime.time(23, 59),
                ))
        Availability.objects.bulk_create(rows, ignore_conflicts=True)

    # ---------------- bron va sharhlar ----------------
    def _reservations_and_reviews(self, businesses, customers):
        # Holatlar TAQSIMOTI ataylab nomutanosib: yakunlangan bron ko'p
        # bo'lsin. Sababi — sharh faqat yakunlangan bronga yoziladi,
        # reyting esa sharhdan hisoblanadi. Ilgari yakunlangani beshdan
        # bir edi va ko'pchilik joy reytingsiz, "0.0" bilan turardi;
        # bosh sahifa yarim tayyor ko'rinardi.
        statuses = [
            "pending", "confirmed", "confirmed", "confirmed",
            "completed", "completed", "completed", "cancelled",
        ]

        for business in businesses:
            for _ in range(random.randint(8, 14)):
                customer = random.choice(customers)
                status = random.choice(statuses)
                availability = (
                    Availability.objects.filter(business=business)
                    .order_by("?")
                    .first()
                )
                if availability is None:
                    continue

                if business.business_type == "restaurant":
                    room = availability.room
                    if room is None:
                        continue
                    start = random.choice([12, 14, 18, 19, 20])
                    reservation = Reservation.objects.create(
                        user=customer, business=business, room=room,
                        availability=availability,
                        start_time=datetime.time(start, 0),
                        end_time=datetime.time(min(start + 2, 23), 0),
                        guests_count=random.randint(2, room.capacity),
                        status=status,
                        deposit_amount=room.deposit_amount,
                    )
                else:
                    hall = business.halls.order_by("?").first()
                    pricing = business.pricings.order_by("?").first()
                    if hall is None or pricing is None:
                        continue
                    guests = random.randint(80, min(hall.people, 400))
                    reservation = Reservation.objects.create(
                        user=customer, business=business, hall=hall,
                        availability=availability,
                        guests_count=guests, status=status,
                        dish_count=pricing.dish_count,
                        price_per_person=pricing.price_per_person,
                        total_price=pricing.price_per_person * guests,
                        deposit_amount=hall.deposit_amount,
                    )

                # Sharh faqat yakunlangan bronga — TZ qoidasi shunday.
                if status == "completed" and random.random() < 0.75:
                    Review.objects.create(
                        user=customer, business=business, reservation=reservation,
                        rating=random.choice([4, 5, 5, 5, 3]),
                        comment=random.choice(COMMENTS),
                    )

    # ---------------- kutilayotgan arizalar ----------------
    def _pending_applications(self):
        """
        Tasdiqlanmagan arizalar — admin panelida ko'rib chiqish uchun.

        Bu yerda `approve_application` ATAYLAB chaqirilmaydi: arizani
        administrator o'z panelidan tasdiqlaydi. Ana shunda obuna
        tanlangan muddatga ochiladi va joy qidiruvda paydo bo'ladi —
        oqimning butun ma'nosi shu qadamda ko'rinadi.
        """
        for username, full_name, phone, business_type, business_name, months in PENDING_APPLICANTS:
            applicant = self._user(username, full_name, phone)
            submit_application(
                applicant=applicant,
                business_type=business_type,
                business_name=business_name,
                plan=self.plans[(business_type, months)],
            )

    # ---------------- xulosa ----------------
    def _report(self, customers):
        from businesses.models import BusinessApplication

        photos = BusinessPhoto.objects.filter(
            business__owner__username__startswith="demo_"
        ).count()
        pending = BusinessApplication.objects.filter(
            applicant__username__startswith="demo_", status="pending_payment",
        ).count()

        restaurant_owners = "\n".join(
            f"    {OWNERS[data['name']][0]:<24} — {data['name']}"
            for data in RESTAURANTS
        )
        venue_owners = "\n".join(
            f"    {OWNERS[data['name']][0]:<24} — {data['name']}"
            for data in VENUES
        )
        applicants = "\n".join(
            f"    {username:<24} — {name} ({months} oylik)"
            for username, _, _, _, name, months in PENDING_APPLICANTS
        )

        self.stdout.write(self.style.SUCCESS(f"""
Demo ma'lumot tayyor. PAROL HAMMASIDA BIR XIL: {PASSWORD}

  Restoranlar : {len(RESTAURANTS)} ta (har birida {len(ROOM_SET)} xona)
  To'yxonalar : {len(VENUES)} ta
  Obuna       : hammasi 1 oylik, 'active' holatda
  Galereya    : {photos} ta surat
  Bronlar     : {Reservation.objects.filter(user__username__startswith='demo_').count()}
  Sharhlar    : {Review.objects.filter(user__username__startswith='demo_').count()}
  Mijozlar    : {len(customers)}
  Kutayotgan arizalar : {pending} ta

RESTORAN EGALARI (obunasi faol, panelga kiradi)
{restaurant_owners}

TO'YXONA EGALARI (obunasi faol, panelga kiradi)
{venue_owners}

TASDIQ KUTAYOTGAN ARIZALAR (siz admin sifatida ko'rib chiqasiz)
{applicants}

  Ular hozir panelga KIRA OLMAYDI va joylari qidiruvda YO'Q.
  Admin panelidagi "Arizalar" bo'limidan tasdiqlang — obuna
  tanlangan muddatga ochiladi va joy darhol saytda paydo bo'ladi.

MIJOZLAR (bron qiladi, sharh yozadi)
    demo_dilshod, demo_nodira, demo_javohir, demo_kamola,
    demo_bobur, demo_zarina, demo_islom, demo_malika

Suratlar Wikimedia Commons'dan (erkin litsenziya).
Manba va mualliflar: media/_demo_cache/manifest.json
"""))
