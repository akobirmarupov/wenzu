"""
Bildirishnomalar oqimi testlari.

Asosiy talab: bildirishnoma IKKINCHI DARAJALI. U to'g'ri yaratilishi
kerak, lekin xato bo'lsa ham bron yoki ariza jarayonini buzmasligi
shart — shuning uchun "signal yiqilsa nima bo'ladi" ham tekshiriladi.
"""

import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from businesses.models import Business, BusinessApplication, Room
from notifications.models import Notification
from reservations.models import Availability, Reservation

User = get_user_model()


class NotificationFlowTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.owner = User.objects.create_user(
            username="notif_owner", password="StrongPass123!",
            phone_number="+998900000101", full_name="Egasi Egayev", role="business",
        )
        self.customer = User.objects.create_user(
            username="notif_customer", password="StrongPass123!",
            phone_number="+998900000102", full_name="Mijoz Mijozov",
        )
        self.staff = User.objects.create_user(
            username="notif_staff", password="StrongPass123!",
            phone_number="+998900000103", full_name="Admin Adminov", is_staff=True,
        )

        # `Business.application` majburiy — biznes har doim tasdiqlangan
        # arizadan tug'iladi. Test ham shu yo'ldan boradi.
        self.application = BusinessApplication.objects.create(
            applicant=self.owner, business_type="restaurant", business_name="Test Restoran",
            status=BusinessApplication.STATUS_APPROVED,
        )
        self.business = Business.objects.create(
            owner=self.owner, application=self.application,
            name="Test Restoran", business_type=Business.TYPE_RESTAURANT,
            is_visible=True,
        )
        # setUp paytida yaratilgan ariza bildirishnomalari testga
        # aralashmasin — sanoq noldan boshlansin.
        Notification.objects.all().delete()
        self.room = Room.objects.create(business=self.business, name="VIP 1", capacity=6)
        self.availability = Availability.objects.create(
            business=self.business, room=self.room,
            date=datetime.date.today() + datetime.timedelta(days=2),
            start_time=datetime.time(10, 0), end_time=datetime.time(23, 0),
        )

    def _make_reservation(self):
        return Reservation.objects.create(
            user=self.customer, business=self.business, room=self.room,
            availability=self.availability,
            start_time=datetime.time(19, 0), end_time=datetime.time(21, 0),
            guests_count=4,
        )

    # ---------------- yaratilish ----------------
    def test_new_reservation_notifies_owner(self):
        """Yangi bron — joy egasiga xabar, mijozga emas."""
        self._make_reservation()

        owner_notifications = Notification.objects.filter(user=self.owner)
        self.assertEqual(owner_notifications.count(), 1)
        self.assertEqual(owner_notifications.first().kind, Notification.KIND_RESERVATION)
        self.assertEqual(Notification.objects.filter(user=self.customer).count(), 0)

    def test_status_change_notifies_customer(self):
        """Holat o'zgarganda — MIJOZGA xabar."""
        reservation = self._make_reservation()
        Notification.objects.all().delete()

        reservation.status = "confirmed"
        reservation.save()

        notification = Notification.objects.filter(user=self.customer).first()
        self.assertIsNotNone(notification)
        self.assertIn("tasdiqlandi", notification.title)
        self.assertEqual(notification.level, Notification.LEVEL_SUCCESS)

    def test_saving_without_status_change_is_silent(self):
        """
        Holat o'zgarmasa xabar YO'Q.

        Bu muhim: bron obyekti boshqa sabablarga ko'ra ham saqlanadi
        (masalan `deposit_amount` yangilanishi), va har safar mijozga
        "broningiz o'zgardi" deb yozib turish spam bo'lardi.
        """
        reservation = self._make_reservation()
        Notification.objects.all().delete()

        reservation.guests_count = 5
        reservation.save()

        self.assertEqual(Notification.objects.filter(user=self.customer).count(), 0)

    def test_application_notifies_applicant_and_staff(self):
        applicant = User.objects.create_user(
            username="notif_applicant", password="StrongPass123!",
            phone_number="+998900000104", full_name="Ariza Arizov",
        )
        BusinessApplication.objects.create(
            applicant=applicant, business_type="restaurant", business_name="Yangi Joy",
        )

        self.assertEqual(Notification.objects.filter(user=applicant).count(), 1)
        self.assertEqual(
            Notification.objects.filter(
                user=self.staff, kind=Notification.KIND_APPLICATION
            ).count(),
            1,
        )

    def test_notification_failure_does_not_break_reservation(self):
        """
        Bildirishnoma xatosi asosiy amalni YIQITMASLIGI kerak.

        Signal bron saqlanadigan tranzaksiya ichida ishlaydi — himoyasiz
        qolsa, oddiy matn xatosi butun bron oqimini 500 ga aylantirardi.
        """
        with patch("notifications.signals.notify", side_effect=RuntimeError("bo'ldi")):
            reservation = self._make_reservation()

        self.assertIsNotNone(reservation.pk)
        self.assertTrue(Reservation.objects.filter(pk=reservation.pk).exists())

    # ---------------- API ----------------
    def test_list_is_scoped_to_current_user(self):
        """Boshqa foydalanuvchining bildirishnomasi ko'rinmasligi shart."""
        self._make_reservation()  # egasiga xabar yaratadi

        self.client.force_authenticate(self.customer)
        response = self.client.get(reverse("notifications:list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    def test_unread_count_and_read_all(self):
        self._make_reservation()
        self.client.force_authenticate(self.owner)

        response = self.client.get(reverse("notifications:unread-count"))
        self.assertEqual(response.data["unread"], 1)

        response = self.client.post(reverse("notifications:read-all"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["unread"], 0)
        self.assertFalse(Notification.objects.filter(user=self.owner, is_read=False).exists())

    def test_cannot_read_someone_elses_notification(self):
        self._make_reservation()
        notification = Notification.objects.filter(user=self.owner).first()

        self.client.force_authenticate(self.customer)
        response = self.client.patch(
            reverse("notifications:read", args=[notification.id])
        )

        self.assertEqual(response.status_code, 404)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)

    def test_anonymous_cannot_list(self):
        response = self.client.get(reverse("notifications:list"))
        self.assertEqual(response.status_code, 401)


class ShowcaseEndpointTest(TestCase):
    """Bosh sahifa vitrinasi — ommaviy, kirish talab qilmaydi."""

    def setUp(self):
        self.client = APIClient()
        owner = User.objects.create_user(
            username="showcase_owner", password="StrongPass123!",
            phone_number="+998900000201", full_name="Vitrina Egasi", role="business",
        )
        def make(name, visible):
            application = BusinessApplication.objects.create(
                applicant=owner, business_type="restaurant", business_name=name,
                status=BusinessApplication.STATUS_APPROVED,
            )
            return Business.objects.create(
                owner=owner, application=application, name=name,
                business_type=Business.TYPE_RESTAURANT, is_visible=visible,
            )

        self.visible = make("Ko'rinadigan", True)
        self.hidden = make("Yashirin", False)

    def test_restaurant_menu_showcase_is_public(self):
        response = self.client.get(reverse("catalog:showcase-restaurant-menu"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)

    def test_venue_menu_showcase_is_public(self):
        response = self.client.get(reverse("catalog:showcase-venue-menu"))
        self.assertEqual(response.status_code, 200)

    def test_showcase_photos_skip_hidden_businesses(self):
        """Bloklangan biznes bosh sahifadagi lentaga TUSHMASLIGI kerak."""
        response = self.client.get(reverse("businesses:showcase-photos"))
        self.assertEqual(response.status_code, 200)
        names = {row["business_name"] for row in response.data}
        self.assertNotIn("Yashirin", names)


class AdminBusinessManagementTest(TestCase):
    """
    Admin panelidan biznesni to'liq boshqarish.

    Eng muhim qoida: o'chirish BILAN bloklash aralashib ketmasligi kerak.
    O'chirish biznes bilan birga bronlarni ham olib ketadi, shuning uchun
    faol bron bo'lsa server buni to'xtatadi.
    """

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="crud_admin", password="StrongPass123!",
            phone_number="+998900000301", full_name="Bosh Admin", is_staff=True,
        )
        self.candidate = User.objects.create_user(
            username="crud_candidate", password="StrongPass123!",
            phone_number="+998900000302", full_name="Nomzod Nomzodov",
        )
        self.client.force_authenticate(self.admin)

    def _create(self, **overrides):
        payload = {
            "owner": self.candidate.id,
            "business_type": "restaurant",
            "name": "Admin ochgan restoran",
            "district": "Chilonzor",
            "approve": True,
        } | overrides
        return self.client.post(reverse("businesses:admin-business-create"), payload)

    def test_admin_can_create_business(self):
        response = self._create()

        self.assertEqual(response.status_code, 201, response.data)
        business = Business.objects.get(pk=response.data["id"])
        self.assertEqual(business.owner, self.candidate)
        # Ariza yozuvi ham yaratilishi shart — `Business.application` majburiy
        # va biznes tarixi shu yozuvdan boshlanadi.
        self.assertIsNotNone(business.application)

        self.candidate.refresh_from_db()
        self.assertEqual(self.candidate.role, "business")

    def test_cannot_create_second_business_for_same_owner(self):
        self._create()
        response = self._create(name="Ikkinchi joy")

        self.assertEqual(response.status_code, 400)
        self.assertIn("owner", response.data["error"]["details"])

    def test_admin_can_edit_and_delete(self):
        business_id = self._create().data["id"]
        url = reverse("businesses:admin-business-detail", args=[business_id])

        response = self.client.patch(url, {"name": "Yangi nom", "district": "Yunusobod"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Yangi nom")

        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Business.objects.filter(pk=business_id).exists())

        # Egasida boshqa biznes qolmadi — roli oddiy foydalanuvchiga qaytadi.
        self.candidate.refresh_from_db()
        self.assertEqual(self.candidate.role, "user")

    def test_delete_is_blocked_while_bookings_are_active(self):
        business_id = self._create().data["id"]
        business = Business.objects.get(pk=business_id)

        room = Room.objects.create(business=business, name="Stol 1", capacity=4)
        availability = Availability.objects.create(
            business=business, room=room,
            date=datetime.date.today() + datetime.timedelta(days=3),
            start_time=datetime.time(10, 0), end_time=datetime.time(22, 0),
        )
        Reservation.objects.create(
            user=self.admin, business=business, room=room, availability=availability,
            start_time=datetime.time(18, 0), end_time=datetime.time(20, 0),
            guests_count=2, status="confirmed",
        )

        response = self.client.delete(
            reverse("businesses:admin-business-detail", args=[business_id])
        )

        self.assertEqual(response.status_code, 400)
        self.assertTrue(Business.objects.filter(pk=business_id).exists())

    def test_non_admin_cannot_manage(self):
        business_id = self._create().data["id"]
        self.client.force_authenticate(self.candidate)

        response = self.client.delete(
            reverse("businesses:admin-business-detail", args=[business_id])
        )
        self.assertIn(response.status_code, (403, 404))
        self.assertTrue(Business.objects.filter(pk=business_id).exists())


class CancelWindowTest(TestCase):
    """
    Bekor qilish oynasi: tasdiqlangandan keyin 1 soat.

    Nima uchun chegara bor: joy egasi bronni tasdiqlab, o'sha vaqtni
    band qilib qo'yadi va boshqa mijozlarni rad etadi. Oxirgi daqiqadagi
    bekor qilish uning uchun to'g'ridan-to'g'ri zarar.
    """

    def setUp(self):
        self.client = APIClient()
        owner = User.objects.create_user(
            username="cw_owner", password="StrongPass123!",
            phone_number="+998900000401", full_name="Egasi", role="business",
        )
        self.customer = User.objects.create_user(
            username="cw_customer", password="StrongPass123!",
            phone_number="+998900000402", full_name="Mijoz",
        )
        application = BusinessApplication.objects.create(
            applicant=owner, business_type="restaurant", business_name="Vaqt Restorani",
            status=BusinessApplication.STATUS_APPROVED,
        )
        self.business = Business.objects.create(
            owner=owner, application=application, name="Vaqt Restorani",
            business_type=Business.TYPE_RESTAURANT, is_visible=True,
        )
        self.room = Room.objects.create(business=self.business, name="Stol", capacity=4)
        self.availability = Availability.objects.create(
            business=self.business, room=self.room,
            date=datetime.date.today() + datetime.timedelta(days=5),
            start_time=datetime.time(10, 0), end_time=datetime.time(23, 0),
        )

    def _make(self, status="pending"):
        return Reservation.objects.create(
            user=self.customer, business=self.business, room=self.room,
            availability=self.availability,
            start_time=datetime.time(19, 0), end_time=datetime.time(21, 0),
            guests_count=2, status=status,
        )

    def _cancel(self, reservation):
        return self.client.patch(
            reverse("reservations:reservation-cancel", args=[reservation.id])
        )

    def test_confirmed_at_is_stamped_automatically(self):
        """
        Vaqt modelning o'zida yoziladi — qaysi joydan tasdiqlanishidan
        qat'i nazar (panel, adminka, buyruq).
        """
        reservation = self._make()
        self.assertIsNone(reservation.confirmed_at)

        reservation.status = "confirmed"
        reservation.save(update_fields=["status"])

        reservation.refresh_from_db()
        self.assertIsNotNone(reservation.confirmed_at)

    def test_pending_has_no_deadline(self):
        """Tasdiqlanmagan so'rovni istalgan paytda qaytarib olish mumkin."""
        reservation = self._make()

        self.assertIsNone(reservation.cancel_deadline())
        self.assertTrue(reservation.cancel_check()[0])

    def test_can_cancel_within_the_hour(self):
        reservation = self._make("confirmed")
        self.client.force_authenticate(self.customer)

        response = self._cancel(reservation)

        self.assertEqual(response.status_code, 200, response.data)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, "cancelled")

    def test_cannot_cancel_after_the_hour(self):
        reservation = self._make("confirmed")
        # Soat o'tib ketdi.
        Reservation.objects.filter(pk=reservation.pk).update(
            confirmed_at=timezone.now() - datetime.timedelta(hours=1, minutes=1)
        )
        self.client.force_authenticate(self.customer)

        response = self._cancel(reservation)

        self.assertEqual(response.status_code, 400)
        # Xabar mijozga aynan shu ko'rinishda yetadi (`http.js` `detail` ni o'qiydi).
        self.assertIn("muddat", response.data["detail"].lower())
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, "confirmed")

    def test_exactly_on_the_boundary_still_works(self):
        """59 daqiqa — hali mumkin. Chegara "keyin" tomonda yopiladi."""
        reservation = self._make("confirmed")
        Reservation.objects.filter(pk=reservation.pk).update(
            confirmed_at=timezone.now() - datetime.timedelta(minutes=59)
        )
        self.client.force_authenticate(self.customer)

        self.assertEqual(self._cancel(reservation).status_code, 200)

    def test_admin_can_cancel_after_the_deadline(self):
        """
        Administratorga chegara tegishli emas: nizoli holatni kimdir hal
        qila olishi kerak, aks holda har e'tiroz bazaga qo'lda kirishni
        talab qilardi.
        """
        reservation = self._make("confirmed")
        Reservation.objects.filter(pk=reservation.pk).update(
            confirmed_at=timezone.now() - datetime.timedelta(days=2)
        )
        staff = User.objects.create_user(
            username="cw_staff", password="StrongPass123!",
            phone_number="+998900000403", full_name="Admin", is_staff=True,
        )
        self.client.force_authenticate(staff)

        self.assertEqual(self._cancel(reservation).status_code, 200)

    def test_api_exposes_the_deadline(self):
        """Frontend qoidani qaytadan yozmasin — server aytib beradi."""
        reservation = self._make("confirmed")
        self.client.force_authenticate(self.customer)

        response = self.client.get(reverse("reservations:reservation-my"))
        row = next(r for r in response.data["results"] if r["id"] == str(reservation.id))

        self.assertTrue(row["can_cancel"])
        self.assertIsNotNone(row["cancel_deadline"])
        self.assertEqual(row["cancel_blocked_reason"], "")


class BusinessContactPrivacyTest(TestCase):
    """
    Aloqa ma'lumoti kirmagan foydalanuvchiga KO'RINMASLIGI kerak.

    Nega muhim: ochiq turgan telefon va Telegram bir kunda spam-botlar
    ro'yxatiga tushadi va joy egasi buni bizdan biladi. Bron qilish uchun
    baribir kirish kerak, ya'ni haqiqiy mijoz hech narsa yo'qotmaydi.

    Tekshiruv SERVER javobida — frontendda yashirish yetarli emas, chunki
    ma'lumot baribir javobda kelardi.
    """

    def setUp(self):
        self.client = APIClient()
        owner = User.objects.create_user(
            username="privacy_owner", password="StrongPass123!",
            phone_number="+998900000501", full_name="Egasi", role="business",
        )
        application = BusinessApplication.objects.create(
            applicant=owner, business_type="restaurant", business_name="Maxfiy Restoran",
            status=BusinessApplication.STATUS_APPROVED,
        )
        self.business = Business.objects.create(
            owner=owner, application=application, name="Maxfiy Restoran",
            business_type=Business.TYPE_RESTAURANT, is_visible=True,
            telegram_username="maxfiy_admin", phone_number="+998901234567",
        )
        # Egasi ma'lumot tahrirlay olishi uchun obuna kerak — tasdiqlangan
        # biznesda u avtomatik ochiladi, bu yerda esa qo'lda beramiz.
        from subscriptions.services import start_trial

        start_trial(business=self.business)

        self.customer = User.objects.create_user(
            username="privacy_customer", password="StrongPass123!",
            phone_number="+998900000502", full_name="Mijoz",
        )
        self.url = f"/api/businesses/{self.business.id}/"

    def test_anonymous_cannot_see_contacts(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["telegram_username"])
        self.assertIsNone(response.data["phone_number"])
        self.assertTrue(response.data["contacts_locked"])

        # Raqam javobning HECH QAYERIDA bo'lmasligi kerak — boshqa
        # maydonga tasodifan tushib qolmaganini ham tekshiramiz.
        self.assertNotIn("+998901234567", str(response.data))
        self.assertNotIn("maxfiy_admin", str(response.data))

    def test_authenticated_user_sees_contacts(self):
        self.client.force_authenticate(self.customer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["telegram_username"], "maxfiy_admin")
        self.assertEqual(response.data["phone_number"], "+998901234567")
        self.assertFalse(response.data["contacts_locked"])

    def test_public_list_never_exposes_contacts(self):
        """Ro'yxat javobida bu maydonlar umuman bo'lmasligi kerak."""
        response = self.client.get("/api/businesses/?type=restaurant")

        self.assertEqual(response.status_code, 200)
        row = response.data["results"][0]
        self.assertNotIn("telegram_username", row)
        self.assertNotIn("phone_number", row)

    def test_owner_sees_own_contacts_in_settings(self):
        """Egasi o'z ma'lumotini albatta ko'rishi va tahrirlashi kerak."""
        self.client.force_authenticate(self.business.owner)

        response = self.client.get("/api/owner/business/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["phone_number"], "+998901234567")

    def test_owner_can_update_phone(self):
        self.client.force_authenticate(self.business.owner)

        response = self.client.patch(
            "/api/owner/business/", {"phone_number": "+998907654321"}, format="json"
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.business.refresh_from_db()
        self.assertEqual(self.business.phone_number, "+998907654321")

    def test_invalid_phone_is_rejected(self):
        self.client.force_authenticate(self.business.owner)

        response = self.client.patch(
            "/api/owner/business/", {"phone_number": "12345"}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.business.refresh_from_db()
        self.assertEqual(self.business.phone_number, "+998901234567")

    def test_cache_does_not_leak_contacts_between_audiences(self):
        """
        Kesh mehmon va kirgan foydalanuvchini ARALASHTIRMASLIGI kerak.

        Detal javobi keshlanadi. Kalit kirgan/kirmaganni ajratmasa,
        keshni birinchi to'ldirgan so'rov hammaga xizmat qilardi va
        raqam mehmonga ham ketib qolardi — aynan shuning oldini
        olmoqchi edik.

        Tartib ataylab shunday: avval KIRGAN foydalanuvchi so'raydi
        (keshni to'ldiradi), keyin mehmon.
        """
        from django.core.cache import cache

        cache.clear()

        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get(self.url).data["phone_number"], "+998901234567")

        self.client.force_authenticate(None)
        anonymous = self.client.get(self.url)

        self.assertIsNone(anonymous.data["phone_number"])
        self.assertTrue(anonymous.data["contacts_locked"])
        self.assertNotIn("+998901234567", str(anonymous.data))


class PlatformOwnerBoundaryTest(TestCase):
    """
    Platforma egasi va biznes egasi — QAT'IY ajratilgan.

    Platforma egasi tizimni BOSHQARADI, undan foydalanmaydi:
      · bron qila olmaydi
      · biznes paneliga (xona, menyu, jadval) kira olmaydi
      · obuna sotib olmaydi — obunalarni tasdiqlaydi

    Nega muhim: aks holda u o'z platformasida o'zi mijoz bo'lib chiqardi,
    statistikasi buzilardi va "bu bronni kim tasdiqlaydi?" degan chalkash
    holat tug'ilardi.
    """

    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(
            username="boundary_admin", password="StrongPass123!",
            phone_number="+998900007001", full_name="Platforma Egasi",
            is_staff=True, is_phone_verified=True,
        )
        owner = User.objects.create_user(
            username="boundary_owner", password="StrongPass123!",
            phone_number="+998900007002", full_name="Biznes Egasi", role="business",
        )
        application = BusinessApplication.objects.create(
            applicant=owner, business_type="restaurant", business_name="Chegara",
            status=BusinessApplication.STATUS_APPROVED,
        )
        self.business = Business.objects.create(
            owner=owner, application=application, name="Chegara",
            business_type=Business.TYPE_RESTAURANT, is_visible=True,
        )
        self.room = Room.objects.create(business=self.business, name="Stol", capacity=4)
        self.availability = Availability.objects.create(
            business=self.business, room=self.room,
            date=datetime.date.today() + datetime.timedelta(days=3),
            start_time=datetime.time(10, 0), end_time=datetime.time(23, 0),
        )

    def test_staff_cannot_create_a_booking(self):
        self.client.force_authenticate(self.staff)

        response = self.client.post("/api/reservations/", {
            "room": str(self.room.id),
            "date": str(self.availability.date),
            "start_time": "19:00", "end_time": "21:00", "guests_count": 2,
        }, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Reservation.objects.count(), 0)

    def test_staff_cannot_use_owner_panel(self):
        """Biznes paneli endpointlari platforma egasiga yopiq."""
        self.client.force_authenticate(self.staff)

        for url in (
            "/api/owner/overview/",
            "/api/owner/rooms/",
            "/api/owner/business/",
            "/api/owner/subscription/",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_staff_cannot_create_rooms_even_with_a_business(self):
        """
        Xodim hisobida biznes ham bo'lsa — baribir yopiq.

        Eski ma'lumotda shunday holat uchraydi (bir odam ham admin, ham
        joy egasi bo'lgan). Ikki vazifani bir hisobda aralashtirmaslik
        kerak: buning uchun alohida hisob ochiladi.
        """
        self.business.owner = self.staff
        self.business.save(update_fields=["owner"])
        self.staff.role = "business"
        self.staff.save(update_fields=["role"])

        self.client.force_authenticate(self.staff)
        response = self.client.post("/api/owner/rooms/", {
            "name": "Yangi", "capacity": 4,
        }, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertIn("boshqaruv panel", response.data["error"]["message"].lower())

    def test_staff_keeps_full_admin_access(self):
        """Cheklov faqat "foydalanish"ga — boshqaruv to'liq ochiq qoladi."""
        self.client.force_authenticate(self.staff)

        for url in (
            "/api/admin/overview/",
            "/api/admin/businesses/",
            "/api/admin/subscriptions/",
            "/api/admin/subscription-requests/",
            "/api/admin/reservations/",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_customer_can_still_book(self):
        """Cheklov oddiy mijozga TEGMASLIGI kerak."""
        customer = User.objects.create_user(
            username="boundary_customer", password="StrongPass123!",
            phone_number="+998900007003", full_name="Mijoz", is_phone_verified=True,
        )
        self.client.force_authenticate(customer)

        response = self.client.post("/api/reservations/", {
            "room": str(self.room.id),
            "date": str(self.availability.date),
            "start_time": "19:00", "end_time": "21:00", "guests_count": 2,
        }, format="json")

        self.assertEqual(response.status_code, 201, response.data)


class OwnerPanelVisibilityTest(TestCase):
    """
    Biznes egasining paneli TASDIQDAN keyin ko'rinadi va TURIGA qarab
    nomlanadi.

    Frontend `business.is_approved` va `business.type` ga qarab hal
    qiladi — shuning uchun ikkalasi ham javobda to'g'ri kelishi shart.
    """

    def _make_owner(self, username, phone, business_type, approve):
        from businesses.services import approve_application, submit_application

        owner = User.objects.create_user(
            username=username, password="StrongPass123!",
            phone_number=phone, full_name=username.title(), is_phone_verified=True,
        )
        application, _, _ = submit_application(
            applicant=owner, business_type=business_type, business_name=f"{username} joyi",
        )
        if approve:
            approve_application(application=application, approved_by=self.admin)
        owner.refresh_from_db()
        return owner

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="panel_admin", password="StrongPass123!",
            phone_number="+998900008001", full_name="Admin", is_staff=True,
        )

    def _business_payload(self, owner):
        self.client.force_authenticate(owner)
        return self.client.get("/api/auth/me/").data["business"]

    def test_venue_owner_gets_venue_type(self):
        owner = self._make_owner("panel_venue", "+998900008002", "venue", approve=True)

        business = self._business_payload(owner)

        self.assertTrue(business["is_approved"])
        self.assertEqual(business["type"], "venue")

    def test_restaurant_owner_gets_restaurant_type(self):
        owner = self._make_owner("panel_rest", "+998900008003", "restaurant", approve=True)

        business = self._business_payload(owner)

        self.assertTrue(business["is_approved"])
        self.assertEqual(business["type"], "restaurant")

    def test_panel_stays_hidden_until_approval(self):
        owner = self._make_owner("panel_wait", "+998900008004", "venue", approve=False)

        business = self._business_payload(owner)

        self.assertFalse(business["is_approved"], "Tasdiqlanmaguncha panel ko'rinmasligi kerak")

    def test_deleting_a_business_resets_the_role(self):
        """
        Biznes o'chirilsa egasi "yarim holatda" qolmasligi kerak.

        Aks holda `role='business'`, lekin biznesi yo'q odam paydo
        bo'ladi: profilida panel yo'q, obuna bo'limi ham nima
        ko'rsatishni bilmaydi. Aynan shunday holat haqiqiy ma'lumotda
        uchragan edi.
        """
        owner = self._make_owner("panel_gone", "+998900008005", "restaurant", approve=True)
        self.assertEqual(owner.role, "business")

        Business.objects.filter(owner=owner).delete()

        owner.refresh_from_db()
        self.assertEqual(owner.role, "user")
        self.assertIsNone(self._business_payload(owner))


class OneBusinessPerUserTest(TestCase):
    """
    BITTA hisob — BITTA biznes.

    Restoran ochgan odam to'yxona ham ocha olmaydi va aksincha.

    Nega qat'iy: tizimning butun mantig'i shu farazga tayanadi —
    `user.businesses.first()` panel qaysi biznesniki ekanini shundan
    biladi, obuna biznesga OneToOne bog'langan, login javobidagi
    `business` maydoni bitta obyekt. Ikkinchi biznes paydo bo'lsa,
    egasi uni panelda umuman ko'rmasdi.
    """

    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username="one_owner", password="StrongPass123!",
            phone_number="+998900009001", full_name="Yagona Egasi",
            is_phone_verified=True,
        )
        self.admin = User.objects.create_user(
            username="one_admin", password="StrongPass123!",
            phone_number="+998900009002", full_name="Admin", is_staff=True,
        )
        self.client.force_authenticate(self.owner)

    def _apply(self, business_type, name):
        return self.client.post("/api/business-applications/", {
            "business_type": business_type, "business_name": name,
        }, format="json")

    def test_first_application_succeeds(self):
        self.assertEqual(self._apply("restaurant", "Birinchi Joy").status_code, 201)

    def test_restaurant_owner_cannot_open_a_venue(self):
        """
        Tasdiqlangan restoran egasi to'yxona ocholmaydi.

        Tasdiqlangunicha esa boshqa qoida ishlaydi — "ochiq arizangiz
        bor" (pastdagi testga qarang). Ikkalasi ham 400 qaytaradi,
        lekin sabablari boshqa.
        """
        from businesses.services import approve_application

        self._apply("restaurant", "Mening Restoranim")
        business = Business.objects.get(owner=self.owner)
        approve_application(application=business.application, approved_by=self.admin)

        response = self._apply("venue", "Mening To'yxonam")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get("code"), "business_limit")
        self.assertIn("Mening Restoranim", response.data["detail"])
        self.assertEqual(Business.objects.filter(owner=self.owner).count(), 1)

    def test_open_application_blocks_a_second_one(self):
        """Tasdiq kutilayotganda ikkinchi ariza qabul qilinmaydi."""
        self._apply("restaurant", "Birinchi")

        response = self._apply("venue", "Ikkinchi")

        self.assertEqual(response.status_code, 400)
        self.assertIn("ko'rib chiqilayotgan", response.data["detail"])

    def test_venue_owner_cannot_open_a_restaurant(self):
        from businesses.services import approve_application

        self._apply("venue", "Mening To'yxonam")
        business = Business.objects.get(owner=self.owner)
        approve_application(application=business.application, approved_by=self.admin)

        response = self._apply("restaurant", "Mening Restoranim")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get("code"), "business_limit")
        self.assertEqual(Business.objects.filter(owner=self.owner).count(), 1)

    def test_limit_holds_after_approval_too(self):
        """Tasdiqlangandan keyin ham ikkinchisiga ruxsat yo'q."""
        from businesses.services import approve_application

        self._apply("restaurant", "Tasdiqlangan Joy")
        business = Business.objects.get(owner=self.owner)
        approve_application(application=business.application, approved_by=self.admin)

        self.assertEqual(self._apply("venue", "Ikkinchi").status_code, 400)

    def test_a_new_business_is_allowed_after_deleting_the_old_one(self):
        """
        Biznesni o'chirgach yangisini ochish MUMKIN.

        Chegara "bir umrga bitta" emas, "bir vaqtda bitta" degani.

        Bu yerda ikkinchi narsa ham tekshiriladi: o'chirilgan biznesning
        YETIM arizasi yangi ariza berishni to'smasligi kerak. Ilgari
        to'sardi va odam bu holatdan chiqib ketolmasdi.
        """
        self._apply("restaurant", "Eski Joy")
        Business.objects.filter(owner=self.owner).delete()
        self.owner.refresh_from_db()

        self.assertEqual(self._apply("venue", "Yangi Joy").status_code, 201)

    def test_admin_cannot_bypass_it_either(self):
        """Admin panelidan qo'lda ochishda ham xuddi shu qoida."""
        self._apply("restaurant", "Mavjud Joy")

        self.client.force_authenticate(self.admin)
        response = self.client.post("/api/admin/businesses/create/", {
            "owner": self.owner.id, "business_type": "venue", "name": "Ikkinchi",
        }, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("owner", response.data["error"]["details"])
