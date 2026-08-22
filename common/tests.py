"""
Uchdan-uchgacha (end-to-end) smoke test: ro'yxatdan o'tishdan tortib
sharh qoldirishgacha bo'lgan butun biznes oqimi.

Bu test alohida metodlarga bo'linmagan — chunki bosqichlar bir-biriga
ketma-ket bog'liq (ariza bo'lmasa biznes yo'q, biznes bo'lmasa bron yo'q).
"""

import datetime

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from account.routes.user import SMS_CACHE_KEY
from businesses.models import Business, Room
from businesses.services import approve_application
from reservations.models import Availability, Reservation

User = get_user_model()


class FullFlowTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def auth(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_full_flow(self):
        # --- 1. Ro'yxatdan o'tish -------------------------------------
        response = self.client.post("/api/auth/register/", {
            "full_name": "Sardor Yusupov",
            "phone_number": "+998901234567",
            "username": "sardor_y",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)

        owner = User.objects.get(username="sardor_y")
        self.assertEqual(owner.role, "user")

        # --- 2. Telefonni tasdiqlash (SMS kodi cache'dan) -------------
        response = self.client.post("/api/auth/send-code/", {
            "phone_number": "+998901234567",
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        # Test rejimida DEBUG=False, shuning uchun kod javobda emas —
        # uni to'g'ridan-to'g'ri cache'dan olamiz (haqiqiy oqimda SMS bilan keladi).
        code = cache.get(SMS_CACHE_KEY % "+998901234567")
        self.assertIsNotNone(code, "Kod cache'ga yozilishi kerak")

        response = self.client.post("/api/auth/verify-phone/", {
            "phone_number": "+998901234567", "code": "000000" if code != "000000" else "111111",
        }, format="json")
        self.assertEqual(response.status_code, 400, "Noto'g'ri kod qabul qilinmasligi kerak")

        response = self.client.post("/api/auth/verify-phone/", {
            "phone_number": "+998901234567", "code": code,
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        owner.refresh_from_db()
        self.assertTrue(owner.is_phone_verified)

        # --- 3. Login: hali biznes yo'q -------------------------------
        response = self.client.post("/api/auth/login/", {
            "username": "sardor_y", "password": "StrongPass123!",
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["user"]["role"], "user")
        self.assertIsNone(response.data["user"]["business"])

        # --- 4. "Restoran ochish" arizasi -----------------------------
        response = self.auth(owner).post("/api/business-applications/", {
            "business_type": "restaurant", "business_name": "Shoxona Restorani",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIn("BEPUL sinov", response.data["message"])

        owner.refresh_from_db()
        self.assertEqual(owner.role, "business", "Ariza yuborilgach rol business bo'lishi kerak")

        business = Business.objects.get(owner=owner)

        # MUHIM: ariza yuborilgani bilan biznes hali ISHLAMAYDI —
        # qidiruvda ko'rinmaydi va obunasi yo'q. Bepul sinov faqat admin
        # tasdiqlagach boshlanadi. Aks holda istalgan foydalanuvchi bir
        # daqiqada "restoran" ochib, tekshiruvsiz bir hafta bepul
        # ishlatib ketardi.
        self.assertFalse(business.is_visible, "Tasdiqlanmagan biznes yashirin turishi kerak")
        self.assertFalse(hasattr(business, "subscription"), "Sinov hali boshlanmasligi kerak")

        # --- 4b. Admin arizani tasdiqlaydi → 7 kunlik sinov ochiladi ---
        approver = User.objects.create_user(
            username="early_admin", password="StrongPass123!",
            full_name="Tasdiqlovchi", phone_number="+998900000777",
            is_staff=True, is_superuser=True,
        )
        approval = self.auth(approver).get("/api/admin/applications/")
        self.assertEqual(approval.status_code, 200, approval.data)
        first_application = approval.data["results"][0]["id"]
        self.assertEqual(
            self.auth(approver).post(f"/api/admin/applications/{first_application}/approve/").status_code,
            200,
        )

        business.refresh_from_db()
        self.assertTrue(business.is_visible, "Tasdiqdan keyin biznes qidiruvga chiqadi")
        self.assertEqual(business.subscription.status, "trial")

        # --- 5. Qayta login: endi business.type qaytadi ---------------
        response = self.client.post("/api/auth/login/", {
            "username": "sardor_y", "password": "StrongPass123!",
        }, format="json")
        self.assertEqual(response.data["user"]["business"]["type"], "restaurant",
                         "Frontend shu maydonga qarab restoran panelini ochadi")

        # --- 6. Egasi xona qo'shadi -----------------------------------
        owner_client = self.auth(owner)
        response = owner_client.post("/api/owner/rooms/", {
            "name": "VIP xona — 6 kishilik", "room_type": "vip",
            "capacity": 6, "deposit_tier": "premium",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        room = Room.objects.get(business=business)

        # To'yxona endpointi restoran egasiga yopiq bo'lishi kerak
        response = owner_client.get("/api/owner/halls/")
        self.assertEqual(response.status_code, 403, "Restoran egasiga Zallar bo'limi yopiq")

        # --- 7. Menyu qo'shish ----------------------------------------
        response = owner_client.post("/api/owner/menu/restaurant/", {
            "name": "Steyk Ribay", "price": "140000", "description": "",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)

        # --- 8. Bo'sh vaqt jadvalini generatsiya qilish ---------------
        today = datetime.date.today()
        response = owner_client.post("/api/owner/availability/generate/", {
            "room": str(room.id), "start_time": "08:00", "end_time": "23:00",
            "year": today.year, "months": [today.month],
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertGreater(response.data["created"], 0)

        # --- 9. Mijoz ro'yxatdan o'tadi va bron qiladi -----------------
        customer = User.objects.create_user(
            username="dilshod", password="StrongPass123!",
            full_name="Dilshod Aliyev", phone_number="+998901112233",
            is_phone_verified=True,
        )
        customer_client = self.auth(customer)

        book_date = today + datetime.timedelta(days=1)
        if book_date.month != today.month:
            book_date = today

        payload = {
            "room": str(room.id), "date": str(book_date),
            "start_time": "19:00", "end_time": "21:00", "guests_count": 4,
        }
        response = customer_client.post("/api/reservations/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["deposit_amount"], "99000.00")
        reservation_id = response.data["id"]

        # Xuddi shu vaqtga ikkinchi bron — kesishgani uchun rad etilishi kerak
        response = customer_client.post("/api/reservations/", payload, format="json")
        self.assertEqual(response.status_code, 409, "Kesishgan vaqt band bo'lishi kerak")

        # Kesishmaydigan boshqa oraliq — o'tishi kerak
        response = customer_client.post("/api/reservations/", {
            **payload, "start_time": "13:00", "end_time": "15:00",
        }, format="json")
        self.assertEqual(response.status_code, 201,
                         "Bir kunda kesishmaydigan ikkinchi bron mumkin bo'lishi kerak")

        # --- 10. Soat gridi uchun band oraliqlar ----------------------
        response = self.client.get(f"/api/rooms/{room.id}/busy-hours/?date={book_date}")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data["busy_ranges"]), 2)

        # --- 11. Egasi bronni tasdiqlaydi va yakunlaydi ---------------
        response = owner_client.patch(
            f"/api/owner/reservations/{reservation_id}/status/",
            {"status": "confirmed"}, format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

        response = owner_client.patch(
            f"/api/owner/reservations/{reservation_id}/status/",
            {"status": "completed"}, format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

        # --- 12. Sharh — faqat yakunlangan bron uchun -----------------
        other = Reservation.objects.exclude(pk=reservation_id).first()
        response = customer_client.post("/api/reviews/", {
            "reservation": str(other.id), "rating": 5, "comment": "Zo'r!",
        }, format="json")
        self.assertEqual(response.status_code, 400,
                         "Yakunlanmagan bron uchun sharh qoldirib bo'lmaydi")

        response = customer_client.post("/api/reviews/", {
            "reservation": reservation_id, "rating": 5, "comment": "Xizmat a'lo darajada!",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)

        business.refresh_from_db()
        self.assertEqual(business.rating_avg, 5.0, "Sharhdan keyin reyting yangilanishi kerak")

        # --- 13. Ommaviy qidiruv --------------------------------------
        response = self.client.get("/api/businesses/?type=restaurant&search=Shoxona")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["rooms_count"], 1)

        response = self.client.get(f"/api/businesses/{business.id}/")
        self.assertEqual(len(response.data["rooms"]), 1)
        self.assertEqual(len(response.data["menu"]), 1)

        # --- 14. Admin arizani tasdiqlaydi ---------------------------
        admin = User.objects.create_user(
            username="platform_admin", password="StrongPass123!",
            full_name="Uvente Admin", phone_number="+998900000000",
            is_staff=True, is_superuser=True,
        )
        admin_client = self.auth(admin)

        # Oddiy foydalanuvchiga admin bo'limi yopiq
        self.assertEqual(customer_client.get("/api/admin/overview/").status_code, 403)

        # Ariza 4b-qadamda tasdiqlangan edi — endi PULLIK obunaga o'tamiz.
        # Bu alohida oqim: egasi tarif tanlaydi → ariza → admin to'lovni
        # tasdiqlaydi. Tasdiq "bu haqiqiy joy" degani, to'lov emas.
        from subscriptions.models import SubscriptionPlan

        plan = SubscriptionPlan.objects.get(business_type="restaurant", duration_months=1)
        response = owner_client.post("/api/owner/subscription/requests/", {
            "plan": str(plan.id), "note": "To'lov chekini yubordim",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        request_id = response.data["id"]

        # Tugmani ikki marta bosish yangi ariza YARATMASLIGI kerak.
        again = owner_client.post("/api/owner/subscription/requests/", {
            "plan": str(plan.id),
        }, format="json")
        self.assertEqual(again.status_code, 200, "Ochiq ariza bo'lsa mavjudi qaytariladi")
        self.assertEqual(again.data["id"], request_id)

        response = admin_client.post(f"/api/admin/subscription-requests/{request_id}/approve/")
        self.assertEqual(response.status_code, 200, response.data)

        business.refresh_from_db()
        business.subscription.refresh_from_db()
        self.assertEqual(business.subscription.status, "active")
        self.assertIsNotNone(business.subscription.subscription_ends_at)
        self.assertEqual(business.subscription.payments.count(), 1)

        # --- 15. Biznesni bloklash ------------------------------------
        response = admin_client.patch(f"/api/admin/businesses/{business.id}/toggle-block/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["is_visible"])

        response = self.client.get("/api/businesses/?type=restaurant")
        self.assertEqual(response.data["count"], 0, "Bloklangan biznes qidiruvda ko'rinmasligi kerak")


class VenueFlowTest(TestCase):
    """To'yxona oqimi — bir kunda faqat bitta to'y."""

    def test_venue_booking(self):
        owner = User.objects.create_user(
            username="gulnora", password="StrongPass123!",
            full_name="Gulnora Rashidova", phone_number="+998909876543",
            is_phone_verified=True,
        )
        client = APIClient()
        client.force_authenticate(user=owner)

        response = client.post("/api/business-applications/", {
            "business_type": "venue", "business_name": "Grand Palace To'yxonasi",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)

        owner.refresh_from_db()
        business = Business.objects.get(owner=owner)
        self.assertEqual(business.business_type, "venue")

        # Tasdiqlanmaguncha ma'lumot kiritib bo'lmaydi.
        blocked = client.post("/api/owner/halls/", {
            "name": "Erta zal", "people": 100, "all_price": "1000000",
        }, format="json")
        self.assertEqual(blocked.status_code, 403,
                         "Tasdiqlanmagan biznes zal qo'sha olmasligi kerak")

        # Admin tasdiqlaydi → 7 kunlik bepul sinov boshlanadi.
        approve_application(
            application=business.application,
            approved_by=User.objects.create_user(
                username="venue_admin", password="StrongPass123!",
                full_name="Admin", phone_number="+998900000888", is_staff=True,
            ),
        )
        business.refresh_from_db()
        self.assertEqual(business.subscription.status, "trial")

        # Xonalar bo'limi to'yxona egasiga yopiq
        self.assertEqual(client.get("/api/owner/rooms/").status_code, 403)

        response = client.post("/api/owner/halls/", {
            "name": "Katta zal", "people": 500, "all_price": "9000000",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        hall_id = response.data["id"]

        today = datetime.date.today()
        response = client.post("/api/owner/availability/generate/", {
            "start_time": "08:00", "end_time": "00:00",
            "year": today.year, "months": [today.month],
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)

        customer = User.objects.create_user(
            username="nodira", password="StrongPass123!",
            full_name="Nodira Karimova", phone_number="+998907778899",
            is_phone_verified=True,
        )
        customer_client = APIClient()
        customer_client.force_authenticate(user=customer)

        payload = {"hall": hall_id, "date": str(today), "guests_count": 250, "dish_count": 2}
        response = customer_client.post("/api/reservations/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["deposit_amount"], "599000.00")

        # Availability signal orqali band bo'lishi kerak
        availability = Availability.objects.get(business=business, date=today)
        self.assertTrue(availability.is_booked)

        # Shu kunga ikkinchi bron mumkin emas
        response = customer_client.post("/api/reservations/", payload, format="json")
        self.assertEqual(response.status_code, 409, "To'yxonada bir kunda bitta to'y")

        response = APIClient().get(f"/api/halls/{hall_id}/busy-dates/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn(str(today), response.data["busy_dates"])
