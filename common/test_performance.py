"""
Unumdorlik testlari.

Bular tezlikni sekundlarda o'lchamaydi (u mashinaga bog'liq) — SO'ROVLAR
SONINI tekshiradi. N+1 muammosi aynan shu yerda tutiladi: ma'lumot
ko'paysa ham so'rovlar soni o'zgarmasligi kerak.
"""

import datetime
import threading

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connections
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.test import APIClient

from businesses.models import Business, Hall, Room
from businesses.services import submit_application
from catalog.models import RestaurantMenuItem
from reservations.models import Availability, Reservation

User = get_user_model()

# Kesh yoqilgan holda so'rovlar soni 0 bo'lib qolardi — testda uni o'chiramiz,
# chunki biz aynan BAZAGA tushadigan so'rovlarni sanamoqchimiz.
NO_CACHE = override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
)


def make_owner(i):
    return User.objects.create_user(
        username=f"owner{i}", password="StrongPass123!",
        full_name=f"Owner {i}", phone_number=f"+9989000{i:05d}",
        is_phone_verified=True,
    )


@NO_CACHE
class QueryCountTest(TestCase):
    """Ma'lumot ko'paysa ham so'rovlar soni o'sib ketmasligini tekshiradi."""

    @classmethod
    def setUpTestData(cls):
        for i in range(12):
            owner = make_owner(i)
            _, business, _ = submit_application(
                applicant=owner,
                business_type="restaurant" if i % 2 == 0 else "venue",
                business_name=f"Biznes {i}",
            )
            business.district = "Yunusobod"
            business.latitude, business.longitude = 41.3 + i * 0.001, 69.2 + i * 0.001
            business.save()

            if business.business_type == Business.TYPE_RESTAURANT:
                for r in range(3):
                    Room.objects.create(
                        business=business, name=f"Xona {r}", room_type="vip",
                        capacity=4 + r, deposit_tier="pro",
                    )
                for m in range(5):
                    RestaurantMenuItem.objects.create(
                        business=business, name=f"Taom {m}", price=50000
                    )
            else:
                for h in range(2):
                    Hall.objects.create(business=business, name=f"Zal {h}", people=200 + h)

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_business_list_query_count_is_constant(self):
        """
        Ro'yxatda 12 ta biznes bor. Agar N+1 bo'lsa, so'rovlar soni
        biznes soniga qarab o'sadi. Chegara — 10 ta so'rov.
        """
        with self.assertNumQueries(2):
            # 1) COUNT (paginatsiya uchun), 2) qatorlarning o'zi.
            response = self.client.get("/api/businesses/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 12)

    def test_business_list_with_filters_query_count(self):
        with self.assertNumQueries(2):
            response = self.client.get(
                "/api/businesses/?type=restaurant&district=Yunusobod&min_rating=0"
            )
        self.assertEqual(response.status_code, 200)

    def test_geo_search_uses_bounding_box(self):
        """
        Geo-qidiruvda ham so'rov soni o'zgarmasligi kerak: bounding box
        SQL darajasida kesadi, Haversine faqat qolganlar uchun ishlaydi.
        """
        # Geo-qidiruvda paginatsiya ro'yxat ustida ishlaydi (COUNT so'rovi yo'q).
        with self.assertNumQueries(1):
            response = self.client.get("/api/businesses/?lat=41.3&lng=69.2&radius_km=5")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all("distance_km" in r for r in response.data["results"]))

    def count_queries(self, url):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        # "Isitish" so'rovi: birinchi so'rov ulanish va sozlamalar bilan
        # bog'liq bir martalik so'rovlarni bajaradi, biz esa barqaror
        # holatdagi sonni o'lchamoqchimiz.
        self.client.get(url)

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # SAVEPOINT'lar test tranzaksiyasiga tegishli — ular haqiqiy
        # so'rov emas, shuning uchun sanamaymiz.
        real = [q for q in ctx.captured_queries if not q["sql"].startswith(("SAVEPOINT", "RELEASE"))]
        return len(real), response

    def test_business_detail_has_no_n_plus_one(self):
        """
        ASOSIY N+1 testi: kichik biznes (3 xona, 5 taom) va katta biznes
        (20 xona, 40 taom) uchun so'rovlar soni BIR XIL bo'lishi kerak.

        Aniq raqamni emas, o'sishni tekshiramiz — chunki aniq raqam
        muhitga (kesh yoqilganmi, savepoint bormi) bog'liq bo'lib qoladi.
        """
        small = Business.objects.filter(business_type="restaurant").first()

        big_owner = make_owner(80)
        _, big, _ = submit_application(
            applicant=big_owner, business_type="restaurant", business_name="Katta"
        )
        for r in range(20):
            Room.objects.create(
                business=big, name=f"Xona {r}", room_type="vip",
                capacity=4, deposit_tier="premium" if r % 2 else "pro",
            )
        for m in range(40):
            RestaurantMenuItem.objects.create(business=big, name=f"Taom {m}", price=50000)

        small_count, small_response = self.count_queries(f"/api/businesses/{small.id}/")
        big_count, big_response = self.count_queries(f"/api/businesses/{big.id}/")

        self.assertEqual(len(small_response.data["rooms"]), 3)
        self.assertEqual(len(big_response.data["rooms"]), 20)
        self.assertEqual(len(big_response.data["menu"]), 40)
        self.assertEqual(
            small_count, big_count,
            f"Ma'lumot 8 barobar ko'paydi, so'rov soni {small_count} -> {big_count} "
            f"ga o'zgardi — bu N+1 degani.",
        )
        self.assertLessEqual(big_count, 12, "Detal sahifasi 12 tadan ko'p so'rov yubormasligi kerak")

    def test_business_list_has_no_n_plus_one(self):
        """Ro'yxatda ham: 1 ta biznes va 12 ta biznes bir xil so'rov soni."""
        one, _ = self.count_queries("/api/businesses/?page_size=1")
        many, response = self.count_queries("/api/businesses/?page_size=50")
        self.assertEqual(len(response.data["results"]), 12)
        self.assertEqual(one, many, f"So'rov soni {one} -> {many}: ro'yxatda N+1 bor")

    def test_owner_reservation_list_query_count(self):
        owner = User.objects.get(username="owner0")
        business = Business.objects.get(owner=owner)
        room = business.rooms.first()
        customer = User.objects.create_user(
            username="qc_customer", password="StrongPass123!",
            full_name="QC", phone_number="+998911111111", is_phone_verified=True,
        )
        today = datetime.date.today()
        for i in range(8):
            availability = Availability.objects.create(
                business=business, room=room,
                date=today + datetime.timedelta(days=i + 1),
                start_time=datetime.time(8, 0), end_time=datetime.time(23, 0),
            )
            Reservation.objects.create(
                user=customer, business=business, room=room, availability=availability,
                start_time=datetime.time(19, 0), end_time=datetime.time(21, 0),
                guests_count=2, deposit_amount=49000,
            )

        client = APIClient()
        client.force_authenticate(user=owner)
        with self.assertNumQueries(3):
            # 1) owner business, 2) COUNT, 3) qatorlar (foydalanuvchi tokendan keladi)
            response = client.get("/api/owner/reservations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 8)


class CachingTest(TestCase):
    """Ommaviy ro'yxat keshlanadimi va o'zgarishda eskiradimi."""

    def setUp(self):
        cache.clear()
        owner = make_owner(90)
        _, self.business, _ = submit_application(
            applicant=owner, business_type="restaurant", business_name="Kesh Restorani"
        )
        self.owner = User.objects.get(pk=owner.pk)
        self.client = APIClient()

    def test_second_request_is_served_from_cache(self):
        self.client.get("/api/businesses/")
        with self.assertNumQueries(0):
            response = self.client.get("/api/businesses/")
        self.assertEqual(response.status_code, 200)

    def test_cache_is_invalidated_when_business_changes(self):
        response = self.client.get("/api/businesses/")
        self.assertEqual(response.data["results"][0]["name"], "Kesh Restorani")

        owner_client = APIClient()
        owner_client.force_authenticate(user=self.owner)
        owner_client.patch("/api/owner/business/", {"name": "Yangi nom"}, format="json")

        response = self.client.get("/api/businesses/")
        self.assertEqual(
            response.data["results"][0]["name"], "Yangi nom",
            "Biznes o'zgargach kesh eskirishi kerak",
        )


class ConcurrentBookingTest(TransactionTestCase):
    """
    Eng muhim poyga (race condition): ikki mijoz AYNI DAMDA bitta vaqtni
    band qilishga urinsa, faqat bittasi o'tishi kerak.

    `TransactionTestCase` kerak — oddiy `TestCase` hamma narsani bitta
    tranzaksiyaga o'raydi va `select_for_update` ning haqiqiy xatti-harakati
    ko'rinmay qoladi.
    """

    reset_sequences = True

    def setUp(self):
        cache.clear()
        owner = User.objects.create_user(
            username="race_owner", password="StrongPass123!",
            full_name="Race Owner", phone_number="+998921111111", is_phone_verified=True,
        )
        _, self.business, _ = submit_application(
            applicant=owner, business_type="restaurant", business_name="Race Restorani"
        )
        self.room = Room.objects.create(
            business=self.business, name="Yagona stol", room_type="vip",
            capacity=10, deposit_tier="pro",
        )
        self.date = datetime.date.today() + datetime.timedelta(days=2)
        Availability.objects.create(
            business=self.business, room=self.room, date=self.date,
            start_time=datetime.time(8, 0), end_time=datetime.time(23, 0),
        )
        self.customers = [
            User.objects.create_user(
                username=f"racer{i}", password="StrongPass123!",
                full_name=f"Racer {i}", phone_number=f"+99893000{i:04d}",
                is_phone_verified=True,
            )
            for i in range(6)
        ]

    def test_only_one_booking_wins_the_same_slot(self):
        payload = {
            "room": str(self.room.id), "date": str(self.date),
            "start_time": "19:00", "end_time": "21:00", "guests_count": 2,
        }
        results = []
        barrier = threading.Barrier(len(self.customers))

        def book(user):
            client = APIClient()
            client.force_authenticate(user=user)
            try:
                barrier.wait(timeout=10)  # hammasi bir vaqtda "otilsin"
                response = client.post("/api/reservations/", payload, format="json")
                results.append(response.status_code)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=book, args=(u,)) for u in self.customers]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        created = results.count(201)
        self.assertEqual(created, 1, f"Faqat bitta bron o'tishi kerak edi, natijalar: {results}")
        self.assertEqual(
            Reservation.objects.filter(
                room=self.room, status__in=["pending", "confirmed"]
            ).count(),
            1,
        )

    def test_venue_allows_only_one_wedding_per_day(self):
        owner = User.objects.create_user(
            username="venue_race_owner", password="StrongPass123!",
            full_name="Venue Owner", phone_number="+998922222222", is_phone_verified=True,
        )
        _, venue, _ = submit_application(
            applicant=owner, business_type="venue", business_name="Race To'yxonasi"
        )
        hall = Hall.objects.create(business=venue, name="Katta zal", people=500, all_price=9000000)
        date = datetime.date.today() + datetime.timedelta(days=3)
        Availability.objects.create(
            business=venue, room=None, date=date,
            start_time=datetime.time(8, 0), end_time=datetime.time(0, 0),
        )

        payload = {"hall": str(hall.id), "date": str(date), "guests_count": 100, "dish_count": 1}
        results = []
        barrier = threading.Barrier(len(self.customers))

        def book(user):
            client = APIClient()
            client.force_authenticate(user=user)
            try:
                barrier.wait(timeout=10)
                results.append(client.post("/api/reservations/", payload, format="json").status_code)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=book, args=(u,)) for u in self.customers]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        self.assertEqual(results.count(201), 1, f"Bir kunda bitta to'y bo'lishi kerak: {results}")
