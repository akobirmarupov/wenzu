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
PASSWORD = "DemoPass123!"

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
# Restoranlar (8 ta)
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
]

# ===================================================================
# To'yxonalar (6 ta)
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

CUSTOMERS = [
    ("demo_dilshod", "Dilshod Aliyev", "+998901112233"),
    ("demo_nodira", "Nodira Karimova", "+998907778899"),
    ("demo_javohir", "Javohir Rasulov", "+998903334455"),
    ("demo_kamola", "Kamola Yusupova", "+998905556677"),
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
    help = "Namoyish uchun 8 restoran, 6 to'yxona, bron va sharhlar yaratadi (haqiqiy suratlar bilan)."

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

        self._report(customers)

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
            self.photo_cache[key] = collect(PHOTO_TERMS[key], 6, cache_key=key)
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
        owner = self._user(
            f"demo_owner_{self._slug(data['name'])}",
            f"{data['name']} egasi",
            f"+9989011{index:05d}",
        )
        # Demo joylar DARHOL tasdiqlanadi.
        #
        # Haqiqiy oqimda ariza yuborilgach admin uni tekshiradi va ana
        # shunda biznes ko'rinadigan bo'ladi. Demoda tasdiqlovchi yo'q,
        # shuning uchun buni seeder o'zi bajaradi — aks holda barcha
        # namoyish joylari yashirin qolib, sayt bo'sh ko'rinardi.
        application, business, _ = submit_application(
            applicant=owner, business_type="restaurant", business_name=data["name"]
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
        business.phone_number = f"+9987112{index:05d}"
        business.save()

        photos = data["photos"]
        self._attach(business.cover_photo, photos, 0,
                     name=f"{business.id}-cover.jpg")

        # Galereya — uchta qo'shimcha kadr (muqovadan boshqa).
        for order in range(3):
            picture = self._picture(photos, order + 1, width=1200)
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
            self._attach(room.photo, photos, position % 6,
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
        owner = self._user(
            f"demo_owner_{self._slug(data['name'])}",
            f"{data['name']} egasi",
            f"+9989022{index:05d}",
        )
        application, business, _ = submit_application(
            applicant=owner, business_type="venue", business_name=data["name"]
        )
        approve_application(application=application, approved_by=self.approver)

        business.district = data["district"]
        business.address = f"{data['district']} tumani, Toshkent"
        business.latitude, business.longitude = data["lat"], data["lng"]
        business.description = data["description"]
        business.telegram_username = f"{self._slug(data['name'])}_admin"
        business.phone_number = f"+9987112{index:05d}"
        business.save()

        photos = data["photos"]
        self._attach(business.cover_photo, photos, 0, name=f"{business.id}-cover.jpg")

        for order in range(3):
            picture = self._picture(photos, order + 1, width=1200)
            if picture is None:
                break
            photo = BusinessPhoto(business=business, order=order)
            photo.image.save(f"{business.id}-{order}.jpg", picture, save=True)

        for position, (name, people) in enumerate(data["halls"]):
            hall = Hall.objects.create(business=business, name=name, people=people)
            self._attach(hall.photo, photos, position + 1,
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
        statuses = ["pending", "confirmed", "confirmed", "completed", "cancelled"]

        for business in businesses:
            for _ in range(random.randint(3, 6)):
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

    # ---------------- xulosa ----------------
    def _report(self, customers):
        from businesses.models import Business

        photos = BusinessPhoto.objects.count()
        self.stdout.write(self.style.SUCCESS(f"""
Demo ma'lumot tayyor.

  Restoranlar : {len(RESTAURANTS)} ta (har birida {len(ROOM_SET)} xona)
  To'yxonalar : {len(VENUES)} ta
  Bizneslar   : {Business.objects.filter(owner__username__startswith='demo_').count()}
  Galereya    : {photos} ta surat
  Bronlar     : {Reservation.objects.count()}
  Sharhlar    : {Review.objects.count()}
  Mijozlar    : {len(customers)}

Kirish uchun (parol hammasida: {PASSWORD}):

  Restoran egasi : demo_owner_shoxona
  To'yxona egasi : demo_owner_grand
  Mijoz          : demo_dilshod

Suratlar Wikimedia Commons'dan (erkin litsenziya).
Manba va mualliflar: media/_demo_cache/manifest.json
"""))
