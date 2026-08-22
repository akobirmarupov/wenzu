"""
Xavfsizlik testlari — har biri aniq bir hujum stsenariysini tekshiradi.

Bular "ishlaydimi" emas, "buzib bo'ladimi" degan savolga javob beradi.
"""

import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from businesses.models import Room
from common.test_utils import make_business
from reservations.models import Availability

User = get_user_model()


def make_user(username, phone, **extra):
    return User.objects.create_user(
        username=username, password="StrongPass123!",
        full_name=username.title(), phone_number=phone,
        is_phone_verified=True, **extra,
    )


class AuthorizationTest(TestCase):
    """Boshqa birovning ma'lumotiga tegib bo'ladimi (IDOR)."""

    def setUp(self):
        cache.clear()
        self.owner_a = make_user("owner_a", "+998900000001")
        self.owner_b = make_user("owner_b", "+998900000002")
        _, self.biz_a, _ = make_business(
            applicant=self.owner_a, business_type="restaurant", business_name="Restoran A"
        )
        _, self.biz_b, _ = make_business(
            applicant=self.owner_b, business_type="restaurant", business_name="Restoran B"
        )
        self.room_a = Room.objects.create(
            business=self.biz_a, name="A xona", room_type="vip",
            capacity=4, deposit_tier="pro",
        )
        self.owner_a.refresh_from_db()
        self.owner_b.refresh_from_db()

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_owner_cannot_touch_other_business_room(self):
        """B egasi A ning xonasini ko'ra ham, o'zgartira ham, o'chira ham olmasligi kerak."""
        client = self.client_for(self.owner_b)
        url = f"/api/owner/rooms/{self.room_a.id}/"

        self.assertEqual(client.get(url).status_code, 404)
        self.assertEqual(client.patch(url, {"name": "O'g'irlandi"}, format="json").status_code, 404)
        self.assertEqual(client.delete(url).status_code, 404)

        self.room_a.refresh_from_db()
        self.assertEqual(self.room_a.name, "A xona")

    def test_owner_business_endpoint_is_scoped_to_token(self):
        """/api/owner/business/ har doim SO'ROVCHINING biznesini qaytaradi."""
        response = self.client_for(self.owner_b).get("/api/owner/business/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(self.biz_b.id))

    def test_regular_user_cannot_reach_admin_endpoints(self):
        customer = make_user("plain_user", "+998900000003")
        client = self.client_for(customer)
        for url in [
            "/api/admin/overview/", "/api/admin/users/", "/api/admin/businesses/",
            "/api/admin/applications/", "/api/admin/subscriptions/", "/api/admin/settings/",
        ]:
            self.assertEqual(client.get(url).status_code, 403, url)

    def test_business_owner_cannot_reach_admin_endpoints(self):
        """Biznes egasi ham admin emas — rol chalkashib ketmasligi kerak."""
        response = self.client_for(self.owner_a).get("/api/admin/users/")
        self.assertEqual(response.status_code, 403)

    def test_admin_api_cannot_grant_staff_rights(self):
        """
        Admin API orqali `is_staff` berib bo'lmasligi kerak — aks holda
        bitta admin tokeni o'g'irlansa, hujumchi o'ziga doimiy
        super-admin huquqi yozib qo'yardi.
        """
        admin = make_user("root_admin", "+998900000009", is_staff=True, is_superuser=True)
        victim = make_user("victim", "+998900000010")

        response = self.client_for(admin).patch(
            f"/api/admin/users/{victim.pk}/",
            {"is_staff": True, "is_superuser": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        victim.refresh_from_db()
        self.assertFalse(victim.is_staff)
        self.assertFalse(victim.is_superuser)

    def test_anonymous_cannot_reach_protected_endpoints(self):
        client = APIClient()
        for url in ["/api/auth/me/", "/api/owner/business/", "/api/reservations/my/"]:
            self.assertEqual(client.get(url).status_code, 401, url)


class GoogleAuthSecurityTest(TestCase):
    """
    Google orqali kirishning zaif joylari.

    Eng muhimi bitta: token TEKSHIRILMASDAN ishlatilmasin. Aks holda
    istalgan odam o'zi yozgan "token" bilan boshqa birov bo'lib kirib
    olardi — bu butun tizimni ochib qo'yardi.
    """

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_forged_token_is_rejected(self):
        """O'zi yozilgan token qabul qilinmasin."""
        response = self.client.post("/api/auth/google/", {
            "credential": "men.ozim.yozdim",
        }, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 0, "Yaroqsiz token hisob yaratmasin")

    def test_credential_is_required(self):
        response = self.client.post("/api/auth/google/", {}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("success", response.data)

    def test_blocked_account_cannot_get_in(self):
        """
        Bloklangan hisob Google orqali ham kira olmasligi kerak.

        Bu oson unutiladigan joy: administrator hisobni bloklaydi,
        lekin kirishning YANGI yo'li bu bayroqni tekshirmasa, blok
        hech qanday kuchga ega bo'lmaydi.
        """
        user = make_user("blocked_g", "+998901111222")
        user.email = "blocked@gmail.com"
        user.is_active = False
        user.save(update_fields=["email", "is_active"])

        with patch("account.routes.user.verify_google_token") as verify:
            verify.return_value = {
                "sub": "g-blocked", "email": "blocked@gmail.com",
                "name": "Blocked", "picture": "",
            }
            response = self.client.post("/api/auth/google/", {
                "credential": "token",
            }, format="json")

        self.assertEqual(response.status_code, 403)

    def test_username_is_derived_and_never_collides(self):
        """
        Ikki xil pochtaning @ gacha qismi bir xil bo'lishi mumkin
        (ali@gmail.com va ali@mail.ru). Ikkinchisiga boshqa username
        berilishi kerak, aks holda hisob yaratilmay xato bo'lardi.
        """
        for index, email in enumerate(["ali@gmail.com", "ali@mail.ru"]):
            with patch("account.routes.user.verify_google_token") as verify:
                verify.return_value = {
                    "sub": f"g-{index}", "email": email, "name": "Ali", "picture": "",
                }
                response = self.client.post("/api/auth/google/", {
                    "credential": "token",
                }, format="json")
            self.assertEqual(response.status_code, 200, response.data)

        names = set(User.objects.values_list("username", flat=True))
        self.assertEqual(len(names), 2, f"Username takrorlanmasin: {names}")
        self.assertIn("ali", names)

    def test_phone_cannot_be_changed_once_set(self):
        """
        Raqam bir marta yoziladi. Aks holda mehmon bron yuborib, keyin
        raqamni almashtirib qo'yardi va joy egasi bog'lana olmasdi.
        """
        user = make_user("phoneowner", "+998903333444")
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.patch("/api/auth/me/", {
            "phone_number": "+998904444555",
        }, format="json")

        self.assertEqual(response.status_code, 400)
        user.refresh_from_db()
        self.assertEqual(user.phone_number, "+998903333444")


class ValidationSecurityTest(TestCase):
    """Kirish ma'lumotlarini tekshirish."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_invalid_phone_rejected(self):
        """Bron uchun kiritiladigan raqam formati tekshirilsin."""
        user = make_user("phonevalid", "+998902222225")
        user.phone_number = None
        user.save(update_fields=["phone_number"])

        client = APIClient()
        client.force_authenticate(user=user)

        for bad in ["901234567", "+7901234567", "+99890123", "salom"]:
            response = client.patch("/api/auth/me/", {"phone_number": bad}, format="json")
            self.assertEqual(response.status_code, 400, f"'{bad}' qabul qilinmasligi kerak")

    def test_error_response_has_consistent_shape(self):
        response = self.client.post("/api/auth/google/", {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("success", response.data)
        self.assertFalse(response.data["success"])
        self.assertIn("code", response.data["error"])
        self.assertIn("request_id", response.data)


class SubscriptionGateTest(TestCase):
    """Obunasi tugagan biznes egasi nima qila oladi."""

    def setUp(self):
        cache.clear()
        self.owner = make_user("expired_owner", "+998903333333")
        _, self.business, self.subscription = make_business(
            applicant=self.owner, business_type="restaurant", business_name="Muddati tugagan"
        )
        self.owner.refresh_from_db()
        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)

    def expire(self):
        self.subscription.status = "expired"
        self.subscription.trial_ends_at = timezone.now() - datetime.timedelta(days=1)
        self.subscription.save(update_fields=["status", "trial_ends_at"])

    def test_can_still_read_dashboard_after_expiry(self):
        """
        O'qish ochiq qolishi kerak — aks holda egasi "obunangiz tugadi,
        to'lov qiling" ekranini ham ko'rmasdi.
        """
        self.expire()
        self.assertEqual(self.client.get("/api/owner/overview/").status_code, 200)
        self.assertEqual(self.client.get("/api/owner/rooms/").status_code, 200)
        self.assertEqual(self.client.get("/api/owner/subscription/").status_code, 200)

    def test_cannot_write_after_expiry(self):
        self.expire()
        response = self.client.post("/api/owner/rooms/", {
            "name": "Yangi xona", "room_type": "vip", "capacity": 4, "deposit_tier": "pro",
        }, format="json")
        self.assertEqual(response.status_code, 403)

    def test_can_write_during_trial(self):
        response = self.client.post("/api/owner/rooms/", {
            "name": "Trial xona", "room_type": "vip", "capacity": 4, "deposit_tier": "pro",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)

    def test_expired_business_hidden_from_public_search(self):
        from subscriptions.services import check_expired_subscriptions

        self.subscription.trial_ends_at = timezone.now() - datetime.timedelta(days=1)
        self.subscription.save(update_fields=["trial_ends_at"])
        check_expired_subscriptions()

        self.business.refresh_from_db()
        self.assertFalse(self.business.is_visible)

        response = APIClient().get("/api/businesses/?search=Muddati")
        self.assertEqual(response.data["count"], 0)


class BookingIntegrityTest(TestCase):
    """Bron qilishdagi mantiqiy teshiklarni tekshirish."""

    def setUp(self):
        cache.clear()
        self.owner = make_user("book_owner", "+998904444444")
        _, self.business, _ = make_business(
            applicant=self.owner, business_type="restaurant", business_name="Bron Restorani"
        )
        self.room = Room.objects.create(
            business=self.business, name="Stol", room_type="standard",
            capacity=4, deposit_tier="pro",
        )
        self.tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        Availability.objects.create(
            business=self.business, room=self.room, date=self.tomorrow,
            start_time=datetime.time(8, 0), end_time=datetime.time(23, 0),
        )
        self.customer = make_user("booker", "+998905555555")
        self.client = APIClient()
        self.client.force_authenticate(user=self.customer)

    def payload(self, **overrides):
        base = {
            "room": str(self.room.id), "date": str(self.tomorrow),
            "start_time": "19:00", "end_time": "21:00", "guests_count": 4,
        }
        base.update(overrides)
        return base

    def test_cannot_exceed_room_capacity(self):
        response = self.client.post("/api/reservations/", self.payload(guests_count=50), format="json")
        self.assertEqual(response.status_code, 400)

    def test_cannot_book_in_the_past(self):
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        response = self.client.post("/api/reservations/", self.payload(date=str(yesterday)), format="json")
        self.assertEqual(response.status_code, 400)

    def test_cannot_book_too_far_ahead(self):
        far = datetime.date.today() + datetime.timedelta(days=400)
        response = self.client.post("/api/reservations/", self.payload(date=str(far)), format="json")
        self.assertEqual(response.status_code, 400)

    def test_cannot_book_outside_working_hours(self):
        response = self.client.post(
            "/api/reservations/", self.payload(start_time="03:00", end_time="05:00"), format="json"
        )
        self.assertEqual(response.status_code, 409)

    def test_cannot_attach_menu_item_from_another_restaurant(self):
        """Boshqa restoranning taomini o'z broniga tirkab bo'lmasligi kerak."""
        from catalog.models import RestaurantMenuItem

        other_owner = make_user("other_rest", "+998906666666")
        _, other_business, _ = make_business(
            applicant=other_owner, business_type="restaurant", business_name="Boshqa"
        )
        alien = RestaurantMenuItem.objects.create(
            business=other_business, name="Begona taom", price=10000
        )

        response = self.client.post(
            "/api/reservations/", self.payload(menu_items=[str(alien.id)]), format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_cannot_cancel_someone_elses_reservation(self):
        response = self.client.post("/api/reservations/", self.payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        reservation_id = response.data["id"]

        stranger = make_user("stranger", "+998907777777")
        other_client = APIClient()
        other_client.force_authenticate(user=stranger)

        self.assertEqual(
            other_client.patch(f"/api/reservations/{reservation_id}/cancel/").status_code, 403
        )
        self.assertEqual(
            other_client.get(f"/api/reservations/{reservation_id}/").status_code, 403
        )

    def test_user_without_phone_cannot_book(self):
        """
        Aloqa raqamisiz bron qabul qilinmasligi kerak.

        Google orqali kirgan yangi foydalanuvchida raqam bo'lmaydi —
        u birinchi bron paytida so'raladi. Server shu talabni ushlab
        turmasa, joy egasi bog'lana olmaydigan bron kelib qolardi.
        """
        no_phone = make_user("nophone", "+998908888888")
        no_phone.phone_number = None
        no_phone.save(update_fields=["phone_number"])

        client = APIClient()
        client.force_authenticate(user=no_phone)
        self.assertEqual(
            client.post("/api/reservations/", self.payload(), format="json").status_code, 403
        )

    def test_booking_works_once_the_phone_is_added(self):
        """Raqam kiritilgach o'sha odam bron qila olsin."""
        guest = make_user("withphone", "+998908888777")
        guest.phone_number = None
        guest.save(update_fields=["phone_number"])

        client = APIClient()
        client.force_authenticate(user=guest)

        added = client.patch("/api/auth/me/", {"phone_number": "+998908888777"}, format="json")
        self.assertEqual(added.status_code, 200, added.data)

        response = client.post("/api/reservations/", self.payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)


class PhoneRequiredEverywhereTest(TestCase):
    """
    Aloqa raqami qayerda SHART.

    Google orqali kirgan odam raqamsiz keladi va u saytni bemalol
    KO'RADI. Lekin administrator yoki joy egasi u bilan BOG'LANISHI
    kerak bo'lgan har bir amal raqamni talab qiladi:

      · bron           — joy egasi mehmonga qo'ng'iroq qiladi
      · biznes arizasi — admin joyni tekshirib, egasi bilan gaplashadi
      · obuna so'rovi  — admin to'lovni kelishadi

    Bu ro'yxat frontendda ham takrorlanadi (kichik oyna ochiladi),
    lekin ASOSIY to'siq shu yerda: frontend chetlab o'tilsa ham
    raqamsiz o'tmasin.
    """

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = make_user("nophone_gate", "+998900123400")
        self.user.phone_number = None
        self.user.save(update_fields=["phone_number"])
        self.client.force_authenticate(self.user)

    def test_business_application_needs_a_phone(self):
        response = self.client.post("/api/business-applications/", {
            "business_type": "restaurant", "business_name": "Raqamsiz joy",
        }, format="json")

        self.assertEqual(response.status_code, 403, response.data)

    def test_application_works_once_the_phone_is_added(self):
        self.client.patch("/api/auth/me/", {"phone_number": "+998900123400"}, format="json")

        response = self.client.post("/api/business-applications/", {
            "business_type": "restaurant", "business_name": "Raqamli joy",
        }, format="json")

        self.assertEqual(response.status_code, 201, response.data)

    def test_browsing_stays_open_without_a_phone(self):
        """
        Raqam faqat AMALLARNI to'sadi. Ko'rish — restoranlar ro'yxati,
        joy sahifasi, menyu — hamma uchun ochiq qoladi, aks holda
        odam saytni umuman ko'ra olmay, raqam so'ralganda ham nima
        uchun kerakligini bilmasdi.
        """
        for url in ["/api/businesses/", "/api/auth/me/"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)
