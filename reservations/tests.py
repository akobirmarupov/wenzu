"""
Bron oqimining uchta yangi qoidasi uchun testlar:

  1. To'yxona summasi — ijara + IXTIYORIY taom paketi;
  2. bekor qilish oynasi — "teng yarim vaqt";
  3. ishonchlilik bali — bekor qilganda 5 Bit ayiriladi.
"""

import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from businesses.models import Business, BusinessApplication, Hall, VenuePricing
from catalog.models import VenueMenuItem
from reservations.models import Availability, Reservation

User = get_user_model()


def make_venue(owner, *, name="Olloyor To'yxonasi"):
    """
    Tasdiqlangan to'yxona — servis qatlamidan o'tmasdan, to'g'ridan-to'g'ri.

    Ariza/obuna oqimi bu testlarning mavzusi emas; u `common.tests` da
    alohida tekshiriladi. Bu yerda faqat NARX va BEKOR QILISH qoidasi
    sinaladi, shuning uchun kirish shartlarini eng qisqa yo'l bilan
    tayyorlaymiz.
    """
    application = BusinessApplication.objects.create(
        applicant=owner, business_type="venue", business_name=name,
        status=BusinessApplication.STATUS_APPROVED,
    )
    return Business.objects.create(
        owner=owner, application=application, name=name,
        business_type=Business.TYPE_VENUE, is_visible=True,
        district="Yunusobod", address="Amir Temur 12",
        latitude=41.311081, longitude=69.240562,
    )


def _give_trial_subscription(business):
    """Egasi ma'lumot yozishi uchun kerak bo'ladigan eng qisqa obuna."""
    from subscriptions.models import Subscription, SubscriptionPlan

    plan, _ = SubscriptionPlan.objects.get_or_create(
        business_type=business.business_type, duration_months=1,
        defaults={"price": Decimal(100000)},
    )
    return Subscription.objects.create(
        business=business, plan=plan, status="trial",
        trial_ends_at=timezone.now() + datetime.timedelta(days=7),
    )


class VenueCombinedPricingTest(TestCase):
    """
    Zal bir kunga ijaraga olinadi, ovqat esa IXTIYORIY qo'shimcha.

    To'y egasi zalni 15 000 000 so'mga oladi va shundan keyin ikki yo'ldan
    birini tanlaydi: ovqatni o'zi tashkil qiladi (qo'shimcha to'lov yo'q)
    yoki to'yxonadan 1/2/3 xil taom buyurtma qiladi (kishi boshiga).
    """

    def setUp(self):
        self.owner = User.objects.create_user(
            username="olloyor", password="StrongPass123!", full_name="Olloyor Aka",
            phone_number="+998901112233", is_phone_verified=True,
        )
        self.customer = User.objects.create_user(
            username="mijoz", password="StrongPass123!", full_name="Jasur Qodirov",
            phone_number="+998933334455", is_phone_verified=True,
        )
        self.business = make_venue(self.owner)
        self.hall = Hall.objects.create(
            business=self.business, name="Katta zal", people=500,
            all_price=Decimal(15000000),
        )
        self.date = timezone.localdate() + datetime.timedelta(days=10)
        Availability.objects.create(
            business=self.business, date=self.date,
            start_time=datetime.time(8, 0), end_time=datetime.time(0, 0),
        )
        self.dishes = [
            VenueMenuItem.objects.create(business=self.business, name=name)
            for name in ("Palov", "Norin", "Somsa", "Shashlik")
        ]

        self.client = APIClient()
        self.client.force_authenticate(user=self.customer)

    def _book(self, **extra):
        payload = {"hall": str(self.hall.id), "date": str(self.date), "guests_count": 300}
        payload.update(extra)
        return self.client.post("/api/reservations/", payload, format="json")

    def test_books_with_day_rent_only(self):
        """Hech nima tanlamasdan bron: faqat bir kunlik ijara to'lanadi."""
        response = self._book()
        self.assertEqual(response.status_code, 201, response.data)

        reservation = Reservation.objects.get(pk=response.data["id"])
        self.assertEqual(reservation.day_rent_price, Decimal("15000000.00"))
        self.assertEqual(reservation.total_price, Decimal("15000000.00"),
                         "Ijara mehmonlar soniga ko'paymasligi kerak")
        self.assertIsNone(reservation.dish_count)
        self.assertIsNone(reservation.price_per_person)

    def test_day_rent_and_dishes_add_up(self):
        """Ijara + (kishi boshiga narx x mehmonlar) — ikkalasi qo'shiladi."""
        VenuePricing.objects.create(
            business=self.business, dish_count=2, price_per_person=Decimal(120000)
        )

        response = self._book(
            dish_count=2,
            menu_items=[str(self.dishes[0].id), str(self.dishes[1].id)],
        )
        self.assertEqual(response.status_code, 201, response.data)

        reservation = Reservation.objects.get(pk=response.data["id"])
        self.assertEqual(reservation.day_rent_price, Decimal("15000000.00"))
        self.assertEqual(reservation.price_per_person, Decimal("120000.00"))
        # 15 000 000 + 300 x 120 000 = 51 000 000
        self.assertEqual(reservation.total_price, Decimal("51000000.00"))
        self.assertEqual(len(reservation.selected_menu), 2)

    def test_dish_count_without_menu_is_rejected(self):
        """
        "2 xil taom" tanlab, menyudan hech narsa belgilamagan bron
        o'tmasligi kerak — oshxona uni bajara olmasdi.
        """
        VenuePricing.objects.create(
            business=self.business, dish_count=2, price_per_person=Decimal(120000)
        )

        response = self._book(dish_count=2)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("menu_items", response.data["error"]["details"])

    def test_dish_count_with_wrong_number_of_dishes_is_rejected(self):
        """2 xil taom paketiga 3 ta taom belgilash ham xato."""
        VenuePricing.objects.create(
            business=self.business, dish_count=2, price_per_person=Decimal(120000)
        )

        response = self._book(
            dish_count=2,
            menu_items=[str(dish.id) for dish in self.dishes[:3]],
        )
        self.assertEqual(response.status_code, 400, response.data)

    def test_pricing_mode_is_combined_when_both_exist(self):
        """Ijara ham, paketlar ham bo'lsa — rejim `combined`."""
        VenuePricing.objects.create(
            business=self.business, dish_count=1, price_per_person=Decimal(90000)
        )
        detail = APIClient().get(f"/api/businesses/{self.business.id}/")
        self.assertEqual(detail.data["pricing_mode"], "combined")


class CancelWindowTest(TestCase):
    """
    "Teng yarim vaqt" qoidasi: bekor qilish muddati bron qilingan payt
    bilan tadbir orasidagi masofaning o'rtasida turadi.
    """

    def setUp(self):
        self.owner = User.objects.create_user(
            username="ega2", password="StrongPass123!", full_name="Ega",
            phone_number="+998901112244",
        )
        self.customer = User.objects.create_user(
            username="mijoz2", password="StrongPass123!", full_name="Mijoz",
            phone_number="+998933334466", is_phone_verified=True,
        )
        self.business = make_venue(self.owner, name="Bahor To'yxonasi")
        self.hall = Hall.objects.create(business=self.business, name="Zal", people=300)

    def _reservation(self, *, created_at, event_date, event_time=datetime.time(8, 0)):
        availability = Availability.objects.create(
            business=self.business, date=event_date,
            start_time=event_time, end_time=datetime.time(0, 0),
        )
        reservation = Reservation.objects.create(
            user=self.customer, business=self.business, hall=self.hall,
            availability=availability, guests_count=100, status="confirmed",
        )
        # `created_at` — `auto_now_add`, shuning uchun yaratilgandan keyin
        # to'g'ridan-to'g'ri yoziladi.
        Reservation.objects.filter(pk=reservation.pk).update(created_at=created_at)
        return Reservation.objects.get(pk=reservation.pk)

    def test_deadline_is_the_midpoint(self):
        """
        Foydalanuvchi aytgan misol: soat 18:00 da bron qilinib, tadbir
        o'sha kuni 22:00 da — muddat 20:00 da tugaydi.
        """
        tz = timezone.get_current_timezone()
        event_date = timezone.localdate() + datetime.timedelta(days=1)
        booked_at = timezone.make_aware(
            datetime.datetime.combine(event_date, datetime.time(18, 0)), tz
        ) - datetime.timedelta(days=1)

        reservation = self._reservation(
            created_at=booked_at, event_date=event_date, event_time=datetime.time(22, 0),
        )
        # 5-sentabr 18:00 → 6-sentabr 22:00 = 28 soat, yarmi 14 soat.
        expected = booked_at + datetime.timedelta(hours=14)
        self.assertEqual(reservation.cancel_deadline(), expected)

    def test_can_cancel_before_the_midpoint(self):
        booked_at = timezone.now() - datetime.timedelta(hours=1)
        reservation = self._reservation(
            created_at=booked_at,
            event_date=timezone.localdate() + datetime.timedelta(days=10),
        )
        allowed, reason = reservation.cancel_check()
        self.assertTrue(allowed, reason)

    def test_cannot_cancel_after_the_midpoint(self):
        """Tadbirga 1 kun qolganda, 20 kun oldin qilingan bron — muddat o'tgan."""
        booked_at = timezone.now() - datetime.timedelta(days=20)
        reservation = self._reservation(
            created_at=booked_at,
            event_date=timezone.localdate() + datetime.timedelta(days=1),
        )
        allowed, reason = reservation.cancel_check()
        self.assertFalse(allowed)
        self.assertIn("muddati tugagan", reason)

    def test_api_reports_the_deadline_to_the_customer(self):
        """Muddat mijozga OLDINDAN, ro'yxatda ko'rinishi kerak."""
        reservation = self._reservation(
            created_at=timezone.now() - datetime.timedelta(hours=2),
            event_date=timezone.localdate() + datetime.timedelta(days=6),
        )
        client = APIClient()
        client.force_authenticate(user=self.customer)

        response = client.get(f"/api/reservations/{reservation.id}/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["can_cancel"])
        self.assertIsNotNone(response.data["cancel_deadline"])
        self.assertIsNotNone(response.data["event_starts_at"])


class TrustBitsTest(TestCase):
    """Ishonchlilik bali — bekor qilganda kamayadi, rad etilganda emas."""

    def setUp(self):
        self.owner = User.objects.create_user(
            username="ega3", password="StrongPass123!", full_name="Ega",
            phone_number="+998901112255",
        )
        self.customer = User.objects.create_user(
            username="mijoz3", password="StrongPass123!", full_name="Mijoz",
            phone_number="+998933334477", is_phone_verified=True,
        )
        self.business = make_venue(self.owner, name="Nur To'yxonasi")
        self.hall = Hall.objects.create(business=self.business, name="Zal", people=300)

    def _reservation(self):
        availability = Availability.objects.create(
            business=self.business,
            date=timezone.localdate() + datetime.timedelta(days=30),
            start_time=datetime.time(8, 0), end_time=datetime.time(0, 0),
        )
        return Reservation.objects.create(
            user=self.customer, business=self.business, hall=self.hall,
            availability=availability, guests_count=100, status="confirmed",
        )

    def test_new_user_starts_at_100_bits(self):
        self.assertEqual(self.customer.trust_bits, 100)
        self.assertEqual(self.customer.trust["level"], "excellent")
        self.assertEqual(self.customer.trust["level_display"], "A'lo")

    def test_customer_cancel_costs_five_bits(self):
        reservation = self._reservation()
        client = APIClient()
        client.force_authenticate(user=self.customer)

        response = client.patch(f"/api/reservations/{reservation.id}/cancel/")
        self.assertEqual(response.status_code, 200, response.data)

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.trust_bits, 95)
        self.assertEqual(self.customer.cancelled_reservations_count, 1)
        self.assertEqual(response.data["trust"]["bits"], 95)

    def test_owner_rejection_does_not_touch_the_bits(self):
        """Joy egasi rad etsa mijozning bali tegilmaydi — bu uning aybi emas."""
        self.owner.role = "business"
        self.owner.save(update_fields=["role"])
        reservation = self._reservation()

        client = APIClient()
        client.force_authenticate(user=self.owner)
        response = client.patch(
            f"/api/owner/reservations/{reservation.id}/status/",
            {"status": "cancelled"}, format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.trust_bits, 100)
        self.assertEqual(self.customer.cancelled_reservations_count, 0)

    def test_levels_cover_the_whole_scale(self):
        from account.trust import level_for

        cases = {
            100: "excellent", 80: "excellent",
            79: "good", 65: "good",
            64: "fair", 50: "fair",
            49: "poor", 30: "poor",
            29: "bad", 1: "bad",
        }
        for bits, expected in cases.items():
            self.assertEqual(level_for(bits)[0], expected, f"{bits} Bit")

    def test_bits_never_fall_below_one(self):
        self.customer.trust_bits = 3
        self.customer.save(update_fields=["trust_bits"])
        self.customer.penalize_trust()
        self.assertEqual(self.customer.trust_bits, 1)
        self.customer.penalize_trust()
        self.assertEqual(self.customer.trust_bits, 1)

    def test_owner_sees_the_customer_card(self):
        """Joy egasi bron ro'yxatida mijozning bali va ma'lumotini ko'radi."""
        self.owner.role = "business"
        self.owner.save(update_fields=["role"])
        self.customer.trust_bits = 70
        self.customer.save(update_fields=["trust_bits"])
        self._reservation()

        client = APIClient()
        client.force_authenticate(user=self.owner)
        response = client.get("/api/owner/reservations/")
        self.assertEqual(response.status_code, 200, response.data)

        customer = response.data["results"][0]["customer"]
        self.assertEqual(customer["full_name"], "Mijoz")
        self.assertEqual(customer["phone_number"], "+998933334477")
        self.assertEqual(customer["trust_bits"], 70)
        self.assertEqual(customer["trust_level"], "good")
        self.assertEqual(customer["trust_level_display"], "Yaxshi")


class MapLinkTest(TestCase):
    """Joylashuv havolalari — mijoz xaritada ochib, yo'nalish ola bilsin."""

    def setUp(self):
        self.owner = User.objects.create_user(
            username="ega4", password="StrongPass123!", full_name="Ega",
            phone_number="+998901112266",
        )
        self.business = make_venue(self.owner, name="Saroy To'yxonasi")

    def test_detail_returns_google_and_yandex_links(self):
        response = APIClient().get(f"/api/businesses/{self.business.id}/")
        links = response.data["map_links"]
        self.assertIn("41.311081,69.240562", links["google"])
        # Yandex koordinatani teskari tartibda kutadi.
        self.assertIn("69.240562,41.311081", links["yandex"])
        self.assertIn("google_directions", links)
        self.assertIn("yandex_directions", links)

    def test_falls_back_to_a_text_search_without_coordinates(self):
        self.business.latitude = 0
        self.business.longitude = 0
        self.business.save(update_fields=["latitude", "longitude"])

        links = self.business.map_links
        self.assertIn("Amir%20Temur", links["google"])

    def test_owner_link_produces_coordinates(self):
        """
        Egasi xaritadan havola tashlaydi — koordinatani o'zimiz chiqaramiz,
        shunda joy "yaqinimda" qidiruvida chiqadi.
        """
        self.owner.role = "business"
        self.owner.save(update_fields=["role"])
        # Sozlamalar ekrani faol obuna talab qiladi (`HasActiveSubscription`).
        _give_trial_subscription(self.business)
        self.business.latitude = 0
        self.business.longitude = 0
        self.business.save(update_fields=["latitude", "longitude"])

        client = APIClient()
        client.force_authenticate(user=self.owner)
        response = client.patch("/api/owner/business/", {
            "map_link": "https://www.google.com/maps/place/Feasto/@41.326500,69.281000,17z",
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)

        self.business.refresh_from_db()
        self.assertAlmostEqual(self.business.latitude, 41.3265, places=4)
        self.assertAlmostEqual(self.business.longitude, 69.281, places=4)

    def test_new_link_moves_the_pin(self):
        """
        Egasi joyni ko'chirsa va yangi havola qo'ysa, nuqta ham ko'chishi
        kerak — eski koordinatada qotib qolmasligi kerak.
        """
        self.owner.role = "business"
        self.owner.save(update_fields=["role"])
        _give_trial_subscription(self.business)

        client = APIClient()
        client.force_authenticate(user=self.owner)
        response = client.patch("/api/owner/business/", {
            "map_link": "https://yandex.uz/maps/?ll=69.350000%2C41.400000&z=17",
            # Forma har saqlashda joriy koordinatani ham yuboradi —
            # bu "egasi qo'lda yozdi" degani emas.
            "latitude": self.business.latitude,
            "longitude": self.business.longitude,
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)

        self.business.refresh_from_db()
        self.assertAlmostEqual(self.business.latitude, 41.4, places=4)
        self.assertAlmostEqual(self.business.longitude, 69.35, places=4)

    def test_hand_typed_coordinates_win(self):
        """Egasi nuqtani qo'lda aniqlashtirsa, havola uni bosib ketmaydi."""
        self.owner.role = "business"
        self.owner.save(update_fields=["role"])
        _give_trial_subscription(self.business)

        client = APIClient()
        client.force_authenticate(user=self.owner)
        response = client.patch("/api/owner/business/", {
            "map_link": "https://yandex.uz/maps/?ll=69.350000%2C41.400000&z=17",
            "latitude": 41.500000,
            "longitude": 69.500000,
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)

        self.business.refresh_from_db()
        self.assertAlmostEqual(self.business.latitude, 41.5, places=4)
        self.assertAlmostEqual(self.business.longitude, 69.5, places=4)
