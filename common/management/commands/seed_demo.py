"""
Namoyish uchun demo ma'lumot.

Bu buyruq ISHLAB CHIQARISH bazasida ishlatilmasin — u faqat loyihani
ko'rsatish va lokal sinash uchun. Barcha yozuvlar `demo_` prefiksi bilan
yaratiladi, shuning uchun `--clear` ularni xavfsiz o'chira oladi va
haqiqiy ma'lumotga tegmaydi.
"""

import datetime
import random
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from businesses.models import Hall, Room, VenuePricing
from businesses.services import submit_application
from catalog.models import RestaurantMenuItem, VenueMenuItem
from reservations.models import Availability, Reservation
from reviews.models import Review

User = get_user_model()

RESTAURANTS = [
    {
        "name": "Choyxona Chinor", "district": "Chilonzor", "cuisine": "milliy",
        "open": "08:00", "close": "23:00", "lat": 41.2756, "lng": 69.2035,
        "description": "An'anaviy o'zbek milliy taomlari, keng hovli va sharqona muhit. "
                       "Oilaviy kechki ovqat va do'stlar davrasi uchun ideal joy.",
        "rooms": [("Hovli — 2 kishilik", "outdoor", 2, "pro"),
                  ("Hovli — 6 kishilik", "outdoor", 6, "pro"),
                  ("Zal — 4 kishilik", "standard", 4, "pro")],
        "menu": [("Osh (Toshkent usuli)", "main", 45000), ("Shashlik (qo'y go'shti)", "main", 38000),
                 ("Norin", "main", 35000), ("Ko'k choy (choynak)", "drink", 8000),
                 ("Somsa (3 dona)", "starter", 18000)],
    },
    {
        "name": "Shoxona Restorani", "district": "Yunusobod", "cuisine": "yevropa",
        "open": "08:00", "close": "23:00", "lat": 41.3641, "lng": 69.2871,
        "description": "Zamonaviy oshxona, VIP xonalar va tashqi terrassa. "
                       "Muhim uchrashuvlar va oilaviy kechki ovqat uchun mos.",
        "rooms": [("VIP xona — 6 kishilik", "vip", 6, "premium"),
                  ("Tashqi terrassa — 4 kishilik", "outdoor", 4, "pro"),
                  ("Tashqi terrassa — 10 kishilik", "outdoor", 10, "premium"),
                  ("Zal — 8 kishilik", "standard", 8, "pro")],
        "menu": [("Steyk Ribay", "main", 140000), ("Losos grilda", "main", 120000),
                 ("Sezar salat", "salad", 52000), ("Tiramisu", "dessert", 38000),
                 ("Fresh sharbat", "drink", 22000)],
    },
    {
        "name": "Osh Markazi", "district": "Mirzo Ulug'bek", "cuisine": "milliy",
        "open": "09:00", "close": "22:00", "lat": 41.3389, "lng": 69.3345,
        "description": "Shahardagi eng mashhur oshxonalardan biri. "
                       "Kunlik yangi tayyorlanadigan osh va tez xizmat.",
        "rooms": [("Umumiy zal — 4 kishilik", "standard", 4, "pro"),
                  ("Umumiy zal — 8 kishilik", "standard", 8, "pro")],
        "menu": [("Osh (katta lagan)", "main", 40000), ("Osh (kichik)", "main", 28000),
                 ("Achchiq-chuchuk", "salad", 10000), ("Ko'k choy", "drink", 6000)],
    },
    {
        "name": "Sky Lounge", "district": "Shayxontohur", "cuisine": "fusion",
        "open": "10:00", "close": "23:00", "lat": 41.3167, "lng": 69.2489,
        "description": "Shahar manzarasi ochiladigan tomdagi restoran. "
                       "Fusion taomlar, DJ kechalari va kokteyllar.",
        "rooms": [("Tom — panorama stol", "vip", 4, "premium"),
                  ("Bar zonasi", "standard", 2, "pro")],
        "menu": [("Wagyu burger", "main", 95000), ("Tom Yum", "soup", 68000),
                 ("Sushi to'plami", "main", 110000)],
    },
]

VENUES = [
    {
        "name": "Grand Palace To'yxonasi", "district": "Yunusobod",
        "lat": 41.3701, "lng": 69.2854,
        "description": "Shaharning eng nufuzli to'yxonalaridan biri. Zamonaviy zal, "
                       "katta parking va professional dekoratsiya xizmati.",
        "halls": [("Katta zal", 500), ("Kichik zal (nikoh marosimi)", 120)],
        "pricing": {1: 100000, 2: 120000, 3: 150000},
        "menu": [("Palov (to'y oshi)", "main"), ("Manti", "main"), ("Lag'mon", "main"),
                 ("Salatlar to'plami", "salad"), ("Shirinliklar stoli", "dessert"),
                 ("Ichimliklar", "drink")],
    },
    {
        "name": "Bog'i Rayhon", "district": "Sergeli", "lat": 41.2234, "lng": 69.2201,
        "description": "Ochiq havoda va yopiq zalda o'tkaziladigan tadbirlar uchun qulay maskan. "
                       "Bog' hududi fotosessiya uchun ajoyib.",
        "halls": [("Yopiq zal", 300), ("Ochiq bog' maydoni", 400)],
        "pricing": {1: 90000, 2: 110000, 3: 140000},
        "menu": [("Palov", "main"), ("Kabob", "main"), ("Salatlar", "salad")],
    },
    {
        "name": "Diyor Saroyi", "district": "Mirzo Ulug'bek", "lat": 41.3412, "lng": 69.3390,
        "description": "Katta tadbirlar uchun mo'ljallangan ulkan zal. "
                       "Zamonaviy yorug'lik va tovush tizimi bilan jihozlangan.",
        "halls": [("Asosiy zal", 800), ("Bo'lim zali", 200)],
        "pricing": {1: 110000, 2: 135000, 3: 165000},
        "menu": [("Osh", "main"), ("Manti", "main"), ("Shashlik", "main"),
                 ("Shirinliklar", "dessert")],
    },
]

CUSTOMERS = [
    ("demo_dilshod", "Dilshod Aliyev", "+998901112233"),
    ("demo_nodira", "Nodira Karimova", "+998907778899"),
    ("demo_javohir", "Javohir Rasulov", "+998903334455"),
]

COMMENTS = [
    "Xizmat a'lo darajada, ovqatlar juda mazali. Albatta yana boraman!",
    "Interyer chiroyli, xodimlar xushmuomala. Tavsiya qilaman.",
    "Joy toza va shinam, narxlar ham o'rtacha. Oila bilan bordik.",
    "Buyurtma tez keldi, hammasi issiq va yangi edi.",
    "To'yimiz juda chiroyli o'tdi, xodimlar diqqat bilan yordam berishdi.",
]

PASSWORD = "DemoPass123!"


class Command(BaseCommand):
    help = "Namoyish uchun demo restoran, to'yxona, bron va sharhlar yaratadi."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true",
                            help="Avval eski demo ma'lumotni o'chiradi")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"]:
            deleted = User.objects.filter(username__startswith="demo_").delete()
            self.stdout.write(self.style.WARNING(f"Eski demo ma'lumot o'chirildi: {deleted[0]} yozuv"))

        if User.objects.filter(username__startswith="demo_").exists():
            self.stdout.write(self.style.WARNING(
                "Demo ma'lumot allaqachon mavjud. Qayta yaratish uchun --clear bilan ishga tushiring."))
            return

        random.seed(42)  # har safar bir xil natija — namoyish barqaror bo'lsin

        customers = [self._user(u, n, p) for u, n, p in CUSTOMERS]
        businesses = []

        for index, data in enumerate(RESTAURANTS):
            businesses.append(self._restaurant(data, index))
        for index, data in enumerate(VENUES):
            businesses.append(self._venue(data, index))

        self._reservations_and_reviews(businesses, customers)

        self.stdout.write(self.style.SUCCESS(f"""
Demo ma'lumot tayyor.

  Restoranlar : {len(RESTAURANTS)}
  To'yxonalar : {len(VENUES)}
  Mijozlar    : {len(customers)}

Kirish uchun (parol hammasida: {PASSWORD}):

  Restoran egasi : demo_owner_shoxona
  To'yxona egasi : demo_owner_grand
  Mijoz          : demo_dilshod

Super-admin uchun:  python manage.py createsuperuser
"""))

    # ---------------- yordamchilar ----------------
    def _user(self, username, full_name, phone, **extra):
        user = User.objects.create_user(
            username=username, password=PASSWORD, full_name=full_name,
            phone_number=phone, is_phone_verified=True, is_confirmed=True, **extra,
        )
        return user

    def _slug(self, name):
        return (name.lower().replace("'", "").replace(" ", "_").split("_")[0])[:12]

    def _restaurant(self, data, index):
        owner = self._user(
            f"demo_owner_{self._slug(data['name'])}",
            f"{data['name']} egasi",
            f"+9989011{index:05d}",
        )
        _, business, _ = submit_application(
            applicant=owner, business_type="restaurant", business_name=data["name"]
        )

        business.district = data["district"]
        business.cuisine = data["cuisine"]
        business.address = f"{data['district']} tumani, Toshkent"
        business.latitude, business.longitude = data["lat"], data["lng"]
        business.description = data["description"]
        business.open_time = data["open"]
        business.close_time = data["close"]
        business.telegram_username = f"{self._slug(data['name'])}_admin"
        business.save()

        rooms = [
            Room.objects.create(business=business, name=name, room_type=room_type,
                                capacity=capacity, deposit_tier=tier)
            for name, room_type, capacity, tier in data["rooms"]
        ]
        for name, category, price in data["menu"]:
            RestaurantMenuItem.objects.create(
                business=business, name=name, category=category, price=Decimal(price)
            )

        self._availability(business, rooms, data["open"], data["close"])
        self.stdout.write(f"  ✓ {data['name']} ({len(rooms)} xona)")
        return business

    def _venue(self, data, index):
        owner = self._user(
            f"demo_owner_{self._slug(data['name'])}",
            f"{data['name']} egasi",
            f"+9989022{index:05d}",
        )
        _, business, _ = submit_application(
            applicant=owner, business_type="venue", business_name=data["name"]
        )

        business.district = data["district"]
        business.address = f"{data['district']} tumani, Toshkent"
        business.latitude, business.longitude = data["lat"], data["lng"]
        business.description = data["description"]
        business.telegram_username = f"{self._slug(data['name'])}_admin"
        business.save()

        for name, people in data["halls"]:
            Hall.objects.create(business=business, name=name, people=people)
        for dish_count, price in data["pricing"].items():
            VenuePricing.objects.create(
                business=business, dish_count=dish_count, price_per_person=Decimal(price)
            )
        for name, category in data["menu"]:
            VenueMenuItem.objects.create(business=business, name=name, category=category)

        self._availability(business, [None], "08:00", "00:00")
        self.stdout.write(f"  ✓ {data['name']} ({len(data['halls'])} zal)")
        return business

    def _availability(self, business, targets, start, end):
        """Joriy oy va keyingi oy uchun jadval ochadi."""
        today = datetime.date.today()
        months = [today.replace(day=1)]
        next_month = (today.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        months.append(next_month)

        for room in targets:
            Availability.generate_for_months(
                business=business, room=room,
                start_time=datetime.time(*map(int, start.split(":"))),
                end_time=datetime.time(*map(int, end.split(":"))),
                months=months,
            )

    def _reservations_and_reviews(self, businesses, customers):
        """Yaqin o'tmish uchun yakunlangan bronlar + sharhlar, kelajak uchun kutilayotganlar."""
        today = datetime.date.today()
        created_reservations = 0
        created_reviews = 0

        for business in businesses:
            is_venue = business.business_type == "venue"
            rooms = list(business.rooms.all())
            halls = list(business.halls.all())
            if not rooms and not halls:
                continue

            for offset, status in ((-6, "completed"), (-3, "completed"), (2, "confirmed"), (5, "pending")):
                date = today + datetime.timedelta(days=offset)
                availability = Availability.objects.filter(
                    business=business, date=date,
                    room__isnull=is_venue,
                ).first()
                if availability is None:
                    continue
                if is_venue and Reservation.objects.filter(availability=availability).exists():
                    continue

                customer = random.choice(customers)
                if is_venue:
                    hall = random.choice(halls)
                    pricing = business.pricings.filter(dish_count=2).first()
                    guests = random.choice([150, 200, 250])
                    reservation = Reservation(
                        user=customer, business=business, hall=hall, availability=availability,
                        guests_count=guests, dish_count=2,
                        price_per_person=pricing.price_per_person if pricing else None,
                        total_price=(pricing.price_per_person * guests) if pricing else None,
                        status=status,
                    )
                else:
                    room = random.choice(rooms)
                    start = random.choice([13, 17, 19])
                    reservation = Reservation(
                        user=customer, business=business, room=room, availability=availability,
                        start_time=datetime.time(start), end_time=datetime.time(start + 2),
                        guests_count=min(random.choice([2, 3, 4]), room.capacity),
                        status=status,
                    )

                reservation.deposit_amount = reservation.resolve_deposit_amount()
                reservation.save()
                created_reservations += 1

                if status == "completed":
                    Review.objects.create(
                        user=customer, business=business, reservation=reservation,
                        rating=random.choice([4, 5, 5, 5]),
                        comment=random.choice(COMMENTS),
                    )
                    created_reviews += 1

        self.stdout.write(f"  ✓ {created_reservations} ta bron, {created_reviews} ta sharh")
