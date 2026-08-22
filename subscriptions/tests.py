"""
Obuna oqimi testlari.

Ikki narsa qat'iy tekshiriladi, chunki ikkalasi ham PUL bilan bog'liq:

  1. Bepul sinov faqat ADMIN TASDIG'IDAN keyin boshlanadi. Aks holda
     istalgan foydalanuvchi bir daqiqada "restoran" ochib, hech kim
     tekshirmagan holda platformani bir hafta bepul ishlatib ketardi.

  2. Obuna o'z-o'zidan uzaymaydi — faqat admin arizani tasdiqlagach.
"""

import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from businesses.models import Business
from businesses.services import approve_application, submit_application
from common.test_utils import ensure_plans
from notifications.models import Notification
from subscriptions.models import Subscription, SubscriptionPlan, SubscriptionRequest
from subscriptions.services import send_expiry_reminders

User = get_user_model()


def make_user(username, phone, **extra):
    return User.objects.create_user(
        username=username, password="StrongPass123!",
        phone_number=phone, full_name=username.title(),
        is_phone_verified=True, **extra,
    )


class TrialStartsOnApprovalTest(TestCase):
    """Bepul sinov — ariza yuborilganda emas, TASDIQLANGANDA."""

    def setUp(self):
        self.owner = make_user("trial_owner", "+998900001001")

    def test_application_alone_gives_nothing(self):
        _, business, subscription = submit_application(
            applicant=self.owner, business_type="restaurant", business_name="Yangi Joy",
        )

        self.assertIsNone(subscription, "Ariza yuborilishi bilan sinov boshlanmasligi kerak")
        self.assertFalse(business.is_visible, "Tasdiqlanmagan joy qidiruvda ko'rinmasligi kerak")
        self.assertFalse(Subscription.objects.filter(business=business).exists())

        # Rol o'zgaradi — egasi panelga kirib, arizasi holatini ko'rishi kerak.
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.role, "business")

    def test_unapproved_business_cannot_write(self):
        _, business, _ = submit_application(
            applicant=self.owner, business_type="restaurant", business_name="Yangi Joy",
        )
        client = APIClient()
        client.force_authenticate(self.owner)

        response = client.post("/api/owner/rooms/", {"name": "Xona", "capacity": 4}, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertIn("tasdiqlanmagan", response.data["error"]["message"].lower())
        self.assertFalse(business.rooms.exists())

    def test_approval_starts_the_free_trial(self):
        application, business, _ = submit_application(
            applicant=self.owner, business_type="restaurant", business_name="Yangi Joy",
        )
        admin = make_user("trial_admin", "+998900001002", is_staff=True)

        approve_application(application=application, approved_by=admin)

        business.refresh_from_db()
        self.assertTrue(business.is_visible)
        self.assertEqual(business.subscription.status, "trial")
        # Tasdiq — to'lov EMAS, shuning uchun pullik muddat ochilmaydi.
        self.assertIsNone(business.subscription.subscription_ends_at)
        self.assertEqual(business.subscription.payments.count(), 0)


class RenewalRequestTest(TestCase):
    """Obunani uzaytirish: ariza → admin tasdig'i → muddat uzayadi."""

    def setUp(self):
        self.owner = make_user("renew_owner", "+998900002001")
        self.admin = make_user("renew_admin", "+998900002002", is_staff=True)

        application, self.business, _ = submit_application(
            applicant=self.owner, business_type="restaurant", business_name="Uzaytiruvchi",
        )
        approve_application(application=application, approved_by=self.admin)
        self.business.refresh_from_db()

        ensure_plans()
        self.plan = SubscriptionPlan.objects.get(business_type="restaurant", duration_months=3)
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def test_owner_can_request_renewal(self):
        response = self.client.post(
            reverse("subscriptions:owner-subscription-requests"),
            {"plan": str(self.plan.id)}, format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        request = SubscriptionRequest.objects.get(pk=response.data["id"])
        self.assertEqual(request.status, SubscriptionRequest.STATUS_PENDING)
        # Narx ariza paytida muzlatiladi — admin ertaga tarifni oshirsa,
        # kecha ariza bergan odam eski narxda to'laydi.
        self.assertEqual(request.price, self.plan.price)

    def test_double_click_does_not_create_two_requests(self):
        url = reverse("subscriptions:owner-subscription-requests")
        first = self.client.post(url, {"plan": str(self.plan.id)}, format="json")
        second = self.client.post(url, {"plan": str(self.plan.id)}, format="json")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(SubscriptionRequest.objects.count(), 1)

    def test_expired_owner_can_still_request(self):
        """
        Obunasi tugagan egasi ham ariza yubora olishi SHART — aks holda
        uzaytirishning iloji bo'lmasdi.
        """
        subscription = self.business.subscription
        subscription.status = "expired"
        subscription.save(update_fields=["status"])

        response = self.client.post(
            reverse("subscriptions:owner-subscription-requests"),
            {"plan": str(self.plan.id)}, format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)

    def test_approval_extends_by_plan_duration(self):
        request = self.client.post(
            reverse("subscriptions:owner-subscription-requests"),
            {"plan": str(self.plan.id)}, format="json",
        ).data

        admin_client = APIClient()
        admin_client.force_authenticate(self.admin)
        response = admin_client.post(
            reverse("subscriptions:admin-subscription-request-approve", args=[request["id"]])
        )

        self.assertEqual(response.status_code, 200, response.data)
        subscription = Subscription.objects.get(business=self.business)
        self.assertEqual(subscription.status, "active")
        self.assertEqual(subscription.plan_id, self.plan.id)

        # 3 oylik reja = 90 kun.
        days = (subscription.subscription_ends_at - timezone.now()).days
        self.assertGreaterEqual(days, 88)
        self.assertLessEqual(days, 91)
        self.assertEqual(subscription.payments.count(), 1)

    def test_approval_notifies_the_owner(self):
        request = self.client.post(
            reverse("subscriptions:owner-subscription-requests"),
            {"plan": str(self.plan.id)}, format="json",
        ).data
        Notification.objects.filter(user=self.owner).delete()

        admin_client = APIClient()
        admin_client.force_authenticate(self.admin)
        admin_client.post(
            reverse("subscriptions:admin-subscription-request-approve", args=[request["id"]])
        )

        notification = Notification.objects.filter(user=self.owner).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.kind, Notification.KIND_SUBSCRIPTION)

    def test_cannot_approve_twice(self):
        request = self.client.post(
            reverse("subscriptions:owner-subscription-requests"),
            {"plan": str(self.plan.id)}, format="json",
        ).data
        url = reverse("subscriptions:admin-subscription-request-approve", args=[request["id"]])

        admin_client = APIClient()
        admin_client.force_authenticate(self.admin)
        self.assertEqual(admin_client.post(url).status_code, 200)
        second = admin_client.post(url)

        self.assertEqual(second.status_code, 400)
        self.assertEqual(Subscription.objects.get(business=self.business).payments.count(), 1)

    def test_owner_cannot_approve_own_request(self):
        request = self.client.post(
            reverse("subscriptions:owner-subscription-requests"),
            {"plan": str(self.plan.id)}, format="json",
        ).data

        response = self.client.post(
            reverse("subscriptions:admin-subscription-request-approve", args=[request["id"]])
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            SubscriptionRequest.objects.get(pk=request["id"]).status,
            SubscriptionRequest.STATUS_PENDING,
        )

    def test_plan_of_wrong_business_type_is_rejected(self):
        venue_plan = SubscriptionPlan.objects.get(business_type="venue", duration_months=1)

        response = self.client.post(
            reverse("subscriptions:owner-subscription-requests"),
            {"plan": str(venue_plan.id)}, format="json",
        )

        self.assertEqual(response.status_code, 400)


class ExpiryReminderTest(TestCase):
    """Tugashiga 5 / 3 / 2 kun qolganda eslatma."""

    def setUp(self):
        owner = make_user("remind_owner", "+998900003001")
        admin = make_user("remind_admin", "+998900003002", is_staff=True)
        application, self.business, _ = submit_application(
            applicant=owner, business_type="restaurant", business_name="Eslatma",
        )
        approve_application(application=application, approved_by=admin)
        self.business.refresh_from_db()
        self.owner = owner
        self.subscription = self.business.subscription

    def _set_days_left(self, days):
        # Tugash vaqti — aniq kunduzi soat 12:00.
        #
        # Nima uchun: eslatma SANA farqi bilan hisoblanadi. Agar test
        # "hozir + 5 kun" desa va u yarim tunga yaqin ishga tushsa, sana
        # farqi 6 bo'lib chiqib, test tasodifan yiqilardi.
        noon = timezone.localtime(timezone.now()).replace(
            hour=12, minute=0, second=0, microsecond=0
        )
        self.subscription.status = "active"
        self.subscription.subscription_ends_at = noon + datetime.timedelta(days=days)
        self.subscription.reminded_days = []
        self.subscription.save()
        Notification.objects.filter(user=self.owner).delete()

    def test_reminder_is_sent_on_each_threshold(self):
        for days in (5, 3, 2):
            with self.subTest(days=days):
                self._set_days_left(days)

                sent = send_expiry_reminders()

                self.assertEqual(sent, 1)
                notification = Notification.objects.filter(user=self.owner).first()
                self.assertIsNotNone(notification)
                self.assertIn(str(days), notification.title)

    def test_no_reminder_on_other_days(self):
        self._set_days_left(4)

        self.assertEqual(send_expiry_reminders(), 0)
        self.assertFalse(Notification.objects.filter(user=self.owner).exists())

    def test_same_reminder_is_not_repeated(self):
        """
        Vazifa kuniga bir necha marta ishga tushishi mumkin (qayta urinish,
        qo'lda chaqirish) — xabar takrorlanmasligi kerak.
        """
        self._set_days_left(3)

        self.assertEqual(send_expiry_reminders(), 1)
        self.assertEqual(send_expiry_reminders(), 0)
        self.assertEqual(Notification.objects.filter(user=self.owner).count(), 1)

    def test_trial_expiry_is_also_reminded(self):
        noon = timezone.localtime(timezone.now()).replace(
            hour=12, minute=0, second=0, microsecond=0
        )
        self.subscription.status = "trial"
        self.subscription.trial_ends_at = noon + datetime.timedelta(days=2)
        self.subscription.reminded_days = []
        self.subscription.save()
        Notification.objects.filter(user=self.owner).delete()

        self.assertEqual(send_expiry_reminders(), 1)
        self.assertIn("sinov", Notification.objects.filter(user=self.owner).first().title.lower())

    def test_renewal_resets_the_reminder_history(self):
        """Yangi muddat boshlandi — eski eslatmalar endi ahamiyatsiz."""
        self._set_days_left(2)
        send_expiry_reminders()

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.reminded_days, [2])

        from subscriptions.services import approve_renewal

        plan = SubscriptionPlan.objects.get(business_type="restaurant", duration_months=1)
        request = SubscriptionRequest.objects.create(
            business=self.business, plan=plan, price=plan.price,
        )
        approve_renewal(request=request, approved_by=make_user("r_admin", "+998900003003", is_staff=True))

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.reminded_days, [])


class PlanPricingTest(TestCase):
    """Tarif narxlari va muddatlari."""

    def test_four_plans_exist_with_expected_prices(self):
        from common.management.commands.seed_platform import PLAN_PRICES

        for business_type, durations in PLAN_PRICES.items():
            for months, price in durations.items():
                plan, _ = SubscriptionPlan.objects.get_or_create(
                    business_type=business_type, duration_months=months,
                    defaults={"price": price},
                )
                self.assertEqual(plan.days, months * 30)

    def test_longer_plan_is_cheaper_per_month(self):
        ensure_plans()
        monthly = SubscriptionPlan.objects.get(business_type="restaurant", duration_months=1)
        quarterly = SubscriptionPlan.objects.get(business_type="restaurant", duration_months=3)

        self.assertLess(quarterly.price_per_month, monthly.price_per_month)

    def test_duration_is_unique_per_business_type(self):
        from django.db import IntegrityError, transaction

        ensure_plans()

        with self.assertRaises(IntegrityError), transaction.atomic():
            SubscriptionPlan.objects.create(
                business_type="restaurant", duration_months=1, price=1,
            )


class VisibilityLifecycleTest(TestCase):
    """
    Joyning ommaviy ko'rinishi obunaga BOG'LIQ.

    Uch nuqta:
      · tasdiqlanmagan  → ko'rinmaydi
      · obuna tugadi    → avtomatik yashiriladi
      · to'lov tasdiqlandi → avtomatik qaytadi

    Oxirgisi muhim: tiklashni adminning qo'liga qoldirib bo'lmaydi. U
    to'lovni tasdiqlab, ko'rinish tugmasini bosishni unutsa, egasi pul
    to'lab turib qidiruvda ko'rinmay qolardi va buni faqat mijozlar
    yo'qolganda bilardi.
    """

    def setUp(self):
        ensure_plans()
        self.owner = make_user("vis_owner", "+998900004001")
        self.admin = make_user("vis_admin", "+998900004002", is_staff=True)

        self.application, self.business, _ = submit_application(
            applicant=self.owner, business_type="restaurant", business_name="Ko'rinish",
        )

    def test_hidden_before_approval(self):
        self.assertFalse(self.business.is_visible)

    def test_visible_after_approval(self):
        approve_application(application=self.application, approved_by=self.admin)

        self.business.refresh_from_db()
        self.assertTrue(self.business.is_visible)

    def test_expiry_hides_the_business(self):
        from subscriptions.services import expire_subscription

        approve_application(application=self.application, approved_by=self.admin)
        self.business.refresh_from_db()

        expire_subscription(subscription=self.business.subscription)

        self.business.refresh_from_db()
        self.assertFalse(self.business.is_visible)
        self.assertEqual(self.business.subscription.status, "expired")

    def test_payment_brings_it_back(self):
        from subscriptions.services import approve_renewal, expire_subscription

        approve_application(application=self.application, approved_by=self.admin)
        self.business.refresh_from_db()
        expire_subscription(subscription=self.business.subscription)
        self.business.refresh_from_db()
        self.assertFalse(self.business.is_visible)

        plan = SubscriptionPlan.objects.get(business_type="restaurant", duration_months=1)
        request = SubscriptionRequest.objects.create(
            business=self.business, plan=plan, price=plan.price,
        )
        approve_renewal(request=request, approved_by=self.admin)

        self.business.refresh_from_db()
        self.assertTrue(self.business.is_visible, "To'lovdan keyin joy qidiruvga qaytishi kerak")
        self.assertEqual(self.business.subscription.status, "active")

    def test_hidden_business_is_absent_from_public_search(self):
        client = APIClient()

        before = client.get("/api/businesses/?type=restaurant")
        self.assertEqual(before.data["count"], 0, "Tasdiqlanmagan joy qidiruvda bo'lmasligi kerak")

        approve_application(application=self.application, approved_by=self.admin)
        after = client.get("/api/businesses/?type=restaurant")
        self.assertEqual(after.data["count"], 1)


class ApprovalFlagInLoginTest(TestCase):
    """
    Login javobidagi `business.is_approved` — frontend shu bayroqqa qarab
    panelga kiritadi yoki "ariza ko'rib chiqilmoqda" sahifasiga qaytaradi.
    """

    def setUp(self):
        self.client = APIClient()
        self.owner = make_user("flag_owner", "+998900005001")
        self.admin = make_user("flag_admin", "+998900005002", is_staff=True)
        self.application, self.business, _ = submit_application(
            applicant=self.owner, business_type="venue", business_name="Bayroq",
        )

    def _login(self):
        response = self.client.post("/api/auth/login/", {
            "username": "flag_owner", "password": "StrongPass123!",
        }, format="json")
        return response.data["user"]["business"]

    def test_flag_is_false_before_approval(self):
        business = self._login()

        self.assertFalse(business["is_approved"])
        self.assertIsNone(business["subscription_status"])

    def test_flag_is_true_after_approval(self):
        approve_application(application=self.application, approved_by=self.admin)

        business = self._login()

        self.assertTrue(business["is_approved"])
        self.assertEqual(business["subscription_status"], "trial")

    def test_me_endpoint_reports_the_same(self):
        approve_application(application=self.application, approved_by=self.admin)
        self.client.force_authenticate(self.owner)

        response = self.client.get("/api/auth/me/")

        self.assertTrue(response.data["business"]["is_approved"])


class TrialOncePerUserTest(TestCase):
    """
    Bepul sinov har bir FOYDALANUVCHIGA bir marta.

    Nega biznesga emas, foydalanuvchiga: aks holda odam biznesini
    o'chirib, yangisini ochib, sinovni cheksiz qayta olardi.
    """

    def setUp(self):
        ensure_plans()
        self.client = APIClient()
        self.owner = make_user("once_owner", "+998900006001")
        self.admin = make_user("once_admin", "+998900006002", is_staff=True)

    def _apply(self, name="Sinov Joyi", plan=None):
        self.client.force_authenticate(self.owner)
        payload = {"business_type": "restaurant", "business_name": name}
        if plan is not None:
            payload["plan"] = str(plan.id)
        return self.client.post("/api/business-applications/", payload, format="json")

    def test_trial_is_granted_on_approval(self):
        response = self._apply()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(response.data["is_trial"])

        business = Business.objects.get(owner=self.owner)
        approve_application(application=business.application, approved_by=self.admin)

        business.refresh_from_db()
        self.owner.refresh_from_db()
        self.assertEqual(business.subscription.status, "trial")
        self.assertTrue(self.owner.has_used_trial, "Bayroq qo'yilishi kerak")

    def test_second_trial_application_is_rejected(self):
        self._apply()
        business = Business.objects.get(owner=self.owner)
        approve_application(application=business.application, approved_by=self.admin)

        # Biznesni o'chirib, qaytadan sinov olishga urinish.
        business.delete()
        self.owner.refresh_from_db()

        response = self._apply(name="Ikkinchi Urinish")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get("code"), "trial_used")
        self.assertFalse(Business.objects.filter(owner=self.owner).exists())

    def test_paid_application_is_allowed_after_trial(self):
        """Sinov ishlatilgan bo'lsa ham PULLIK tarif bilan ochish mumkin."""
        self._apply()
        business = Business.objects.get(owner=self.owner)
        approve_application(application=business.application, approved_by=self.admin)
        business.delete()
        self.owner.refresh_from_db()

        plan = SubscriptionPlan.objects.get(business_type="restaurant", duration_months=1)
        response = self._apply(name="Pullik Joy", plan=plan)

        self.assertEqual(response.status_code, 201, response.data)
        self.assertFalse(response.data["is_trial"])
        self.assertIn("250 000", response.data["message"])

    def test_paid_application_starts_without_trial(self):
        """
        Pul to'lagan odamga USTIGA yana bepul kun qo'shilmasligi kerak.

        Tasdiqlangach obuna darhol 'active' bo'ladi va muddat o'sha
        kundan boshlanadi.
        """
        plan = SubscriptionPlan.objects.get(business_type="restaurant", duration_months=3)
        self._apply(name="Choraklik Joy", plan=plan)

        business = Business.objects.get(owner=self.owner)
        approve_application(application=business.application, approved_by=self.admin)

        business.refresh_from_db()
        subscription = business.subscription
        self.assertEqual(subscription.status, "active")
        self.assertEqual(subscription.plan, plan)
        # 3 oylik reja → ~90 kun
        days = (subscription.subscription_ends_at - timezone.now()).days
        self.assertGreater(days, 85)
        self.assertLess(days, 95)

        # Sinov ISHLATILMADI — keyinchalik boshqa joyda olishi mumkin.
        self.owner.refresh_from_db()
        self.assertFalse(self.owner.has_used_trial)

    def test_plan_must_match_business_type(self):
        venue_plan = SubscriptionPlan.objects.get(business_type="venue", duration_months=1)

        response = self._apply(name="Nomos Joy", plan=venue_plan)

        self.assertEqual(response.status_code, 400)
        self.assertIn("mos emas", response.data["detail"])

    def test_trial_flag_exposed_to_frontend(self):
        self.client.force_authenticate(self.owner)
        self.assertFalse(self.client.get("/api/auth/me/").data["has_used_trial"])

        self._apply()
        business = Business.objects.get(owner=self.owner)
        approve_application(application=business.application, approved_by=self.admin)

        self.assertTrue(self.client.get("/api/auth/me/").data["has_used_trial"])
