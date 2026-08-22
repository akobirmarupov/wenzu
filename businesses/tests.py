"""
Ariza tasdiqlash oqimining ADMIN PANELI tomoni.

Bu yerda tekshiriladigan narsa bitta, lekin muhim: admin arizani QAYSI
yo'l bilan tasdiqlashidan qat'i nazar natija bir xil bo'lishi kerak —
obuna ochiladi va joy ommaga chiqadi. Ilgari faqat ro'yxatdagi "amal"
(action) servisga borardi; shaklni ochib `status` ni qo'lda o'zgartirish
esa faqat maydonni yozardi va egasi tasdiqlangan ko'rinib turib
boshqaruv paneliga kira olmasdi.
"""

import io
import shutil
import tempfile

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from businesses.admin import BusinessApplicationAdmin
from businesses.models import BusinessApplication
from businesses.services import submit_application
from common.test_utils import make_business

User = get_user_model()


def a_png(name="cover.png"):
    """Kichik, haqiqiy PNG — `validate_image_file` uni qabul qiladi."""
    buffer = io.BytesIO()
    Image.new("RGB", (12, 12), (200, 120, 60)).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class AdminFormApprovalTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="form_owner", password="StrongPass123!",
            phone_number="+998900009001", full_name="Form Owner",
            is_phone_verified=True,
        )
        self.admin = User.objects.create_user(
            username="form_admin", password="StrongPass123!",
            phone_number="+998900009002", full_name="Form Admin", is_staff=True,
        )
        self.application, self.business, _ = submit_application(
            applicant=self.owner, business_type="venue", business_name="Shakl to'yxonasi",
        )
        self.model_admin = BusinessApplicationAdmin(BusinessApplication, AdminSite())

    def _save_through_form(self, status):
        request = RequestFactory().post("/admin/")
        request.user = self.admin
        # `message_user` sessiya/messages talab qiladi — testda kerak emas.
        request._messages = type("Stub", (), {"add": lambda *a, **kw: None})()
        self.application.status = status
        self.model_admin.save_model(request, self.application, form=None, change=True)

    def test_form_approval_opens_the_subscription(self):
        self._save_through_form("approved")

        self.business.refresh_from_db()
        self.assertTrue(self.business.is_visible)
        self.assertIsNotNone(
            getattr(self.business, "subscription", None),
            "Shakl orqali tasdiqlash ham obunani ochishi kerak",
        )

    def test_form_rejection_hides_the_business(self):
        self._save_through_form("rejected")

        self.business.refresh_from_db()
        self.assertFalse(self.business.is_visible)

    def test_saving_without_status_change_does_nothing_extra(self):
        """
        Admin boshqa maydonni tahrirlab saqlasa, tasdiq qayta
        ishlamasligi kerak — aks holda har saqlashda obuna uzayardi.
        """
        self._save_through_form("approved")
        subscription_id = self.business.subscription.id

        self.application.business_name = "Nomi o'zgardi"
        self._save_through_form("approved")

        self.business.refresh_from_db()
        self.assertEqual(self.business.subscription.id, subscription_id)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="wenzu-test-media-"))
class CoverPhotoUploadTest(TestCase):
    """
    "Sozlamalar" ekranidagi asosiy rasm — multipart PATCH bilan keladi.

    Frontend matn maydonlarini JSON bilan, faylni esa alohida multipart
    so'rovda yuboradi. Server ikkalasini ham bir xil endpointda qabul
    qilishi kerak, aks holda rasm hech qachon saqlanmaydi.
    """

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._overridden_settings["MEDIA_ROOT"], ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username="cover_owner", password="StrongPass123!",
            phone_number="+998900009101", full_name="Cover Owner",
            is_phone_verified=True,
        )
        _, self.business, _ = make_business(
            applicant=self.owner, business_type="restaurant", business_name="Cover Restoran",
        )
        self.client.force_authenticate(self.owner)

    def test_owner_can_upload_the_cover(self):
        response = self.client.patch(
            "/api/owner/business/", {"cover_photo": a_png()}, format="multipart",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.business.refresh_from_db()
        self.assertTrue(self.business.cover_photo, "Rasm saqlanmadi")
        self.assertIn("cover_photo", response.data)

    def test_json_patch_does_not_wipe_the_cover(self):
        """
        Matn maydonlari alohida so'rovda keladi — ular rasmni
        o'chirib yubormasligi kerak.
        """
        self.client.patch(
            "/api/owner/business/", {"cover_photo": a_png()}, format="multipart",
        )

        self.client.patch("/api/owner/business/", {"district": "Yunusobod"}, format="json")

        self.business.refresh_from_db()
        self.assertEqual(self.business.district, "Yunusobod")
        self.assertTrue(self.business.cover_photo)

    def test_non_image_is_rejected(self):
        bad = SimpleUploadedFile("script.svg", b"<svg onload=alert(1)>", content_type="image/svg+xml")

        response = self.client.patch(
            "/api/owner/business/", {"cover_photo": bad}, format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.business.refresh_from_db()
        self.assertFalse(self.business.cover_photo)
