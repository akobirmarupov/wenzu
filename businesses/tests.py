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
from businesses.services import approve_application, reject_application, submit_application
from common.test_utils import make_business

User = get_user_model()


def a_png(name="cover.png"):
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


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="feasto-test-media-"))
class CoverPhotoUploadTest(TestCase):
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


class ReapplyAfterRejectionTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username="reapply_owner", password="StrongPass123!",
            phone_number="+998900009201", full_name="Reapply Owner",
            is_phone_verified=True,
        )
        self.admin = User.objects.create_user(
            username="reapply_admin", password="StrongPass123!",
            phone_number="+998900009202", full_name="Reapply Admin", is_staff=True,
        )
        self.application, self.business, _ = submit_application(
            applicant=self.owner, business_type="restaurant",
            business_name="Birinchi Restoran",
        )
        self.client.force_authenticate(self.owner)

    def _reject(self):
        reject_application(application=self.application, rejected_by=self.admin)
        self.application.refresh_from_db()

    def test_rejected_applicant_can_send_a_new_application(self):
        self._reject()

        response = self.client.post(
            "/api/business-applications/",
            {"business_type": "restaurant", "business_name": "Ikkinchi Restoran"},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(BusinessApplication.objects.filter(applicant=self.owner).count(), 2)

    def test_the_place_is_reused_not_duplicated(self):
        """Joy o'chirilmaydi — u YANGI arizaga ulanadi va yashirin qoladi."""
        self._reject()

        self.client.post(
            "/api/business-applications/",
            {"business_type": "restaurant", "business_name": "Ikkinchi Restoran"},
            format="json",
        )

        self.assertEqual(self.owner.businesses.count(), 1, "Ikkinchi joy yaratilmasligi kerak")
        self.business.refresh_from_db()
        fresh = BusinessApplication.objects.filter(applicant=self.owner).order_by("-created_at").first()
        self.assertEqual(self.business.application_id, fresh.id)
        self.assertEqual(self.business.name, "Ikkinchi Restoran")
        self.assertFalse(self.business.is_visible, "Tasdiqlanmagan joy ko'rinmasligi kerak")

    def test_business_type_can_change_on_reapply(self):
        """Ariza noto'g'ri tur bilan yuborilgani uchun rad etilgan bo'lishi mumkin."""
        self._reject()

        response = self.client.post(
            "/api/business-applications/",
            {"business_type": "venue", "business_name": "To'yxona"},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.business.refresh_from_db()
        self.assertEqual(self.business.business_type, "venue")

    def test_pending_application_still_blocks_a_second_one(self):
        """Rad etilmagan ariza — eski qoida o'z kuchida."""
        response = self.client.post(
            "/api/business-applications/",
            {"business_type": "restaurant", "business_name": "Ikkinchi Restoran"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.owner.businesses.count(), 1)

    def test_approved_application_still_blocks_a_second_one(self):
        approve_application(application=self.application, approved_by=self.admin)

        response = self.client.post(
            "/api/business-applications/",
            {"business_type": "venue", "business_name": "To'yxona"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get("code"), "business_limit")

    def test_subscription_screen_reports_the_rejection(self):
        """Egasi kutish emas, RAD ETILGAN holatni ko'rishi kerak."""
        self._reject()

        response = self.client.get("/api/owner/subscription/")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["has_subscription"])
        self.assertEqual(response.data["status"], "rejected")
        self.assertTrue(response.data["can_reapply"])
