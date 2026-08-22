"""
Ma'lumotdagi nomuvofiqliklarni topadi va tuzatadi.

Bunday holatlar odatda Django adminkasidan qo'lda o'chirish natijasida
paydo bo'ladi: yozuv ketadi, unga bog'liq holat esa qoladi. Kod bunga
tayyor bo'lsa ham, foydalanuvchi ekranda "hech narsa yo'q"ni ko'radi va
sababini bilmaydi.

Ishlatish:
    python manage.py repair_data            # faqat ko'rsatadi
    python manage.py repair_data --fix      # tuzatadi
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from businesses.models import Business, BusinessApplication

User = get_user_model()


class Command(BaseCommand):
    help = "Ma'lumotdagi nomuvofiqliklarni topadi (--fix bilan tuzatadi)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix", action="store_true",
            help="Topilganlarini tuzatadi. Bo'lmasa faqat ro'yxat chiqadi.",
        )

    def handle(self, *args, **options):
        self.fix = options["fix"]
        self.found = 0

        self._approved_without_business()
        self._business_role_without_business()
        self._staff_with_business()

        self.stdout.write("")
        if not self.found:
            self.stdout.write(self.style.SUCCESS("Nomuvofiqlik topilmadi."))
        elif self.fix:
            self.stdout.write(self.style.SUCCESS(f"{self.found} ta holat tuzatildi."))
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"{self.found} ta holat topildi. Tuzatish uchun: "
                    "python manage.py repair_data --fix"
                )
            )

    # ---------------- 1 ----------------
    def _approved_without_business(self):
        """
        Ariza tasdiqlangan, lekin biznes yozuvi yo'q.

        Egasi uchun eng chalkash holat: "arizam tasdiqlangan" deb
        biladi, lekin paneli ochilmaydi va sababi hech qayerda
        yozilmagan. Biznesni arizadan qayta tiklaymiz — ma'lumot
        o'ylab topilmaydi, ariza ichida allaqachon bor.
        """
        self.stdout.write("\n1. Tasdiqlangan ariza, biznes yo'q")

        broken = [
            application
            for application in BusinessApplication.objects.filter(
                status=BusinessApplication.STATUS_APPROVED
            ).select_related("applicant")
            if not hasattr(application, "business")
        ]

        if not broken:
            self.stdout.write("   ✓ toza")
            return

        for application in broken:
            self.found += 1
            self.stdout.write(
                f"   · {application.business_name!r} "
                f"({application.get_business_type_display()}) — "
                f"egasi: {application.applicant.username}"
            )
            if not self.fix:
                continue

            with transaction.atomic():
                business = Business.objects.create(
                    owner=application.applicant,
                    application=application,
                    name=application.business_name,
                    business_type=application.business_type,
                    is_visible=True,
                )
                # Tasdiqlangan ariza = sinov ochilgan bo'lishi kerak.
                # Egasi sinovni allaqachon ishlatgan bo'lsa, obuna
                # muddati tugagan holatda ochiladi va u tarif tanlaydi.
                self._restore_subscription(business, application)

            self.stdout.write(self.style.SUCCESS(f"     → tiklandi: {business.id}"))

    def _restore_subscription(self, business, application):
        from subscriptions.services import TrialAlreadyUsed, start_paid, start_trial

        approver = application.approved_by or User.objects.filter(is_staff=True).first()

        if application.plan is not None:
            start_paid(business=business, plan=application.plan, approved_by=approver)
            return
        try:
            start_trial(business=business)
        except TrialAlreadyUsed:
            self.stdout.write(
                "     · sinov allaqachon ishlatilgan — egasi tarif tanlashi kerak"
            )

    # ---------------- 2 ----------------
    def _business_role_without_business(self):
        """
        `role='business'`, lekin biznesi yo'q va tasdiqlangan arizasi ham yo'q.

        Bunday odam "yarim holatda": profilida panel yo'q, obuna bo'limi
        nima ko'rsatishni bilmaydi. Rolini oddiy foydalanuvchiga
        qaytaramiz — u istalgan paytda qaytadan ariza bera oladi.
        """
        self.stdout.write("\n2. Biznes roli, lekin biznesi yo'q")

        stranded = [
            user
            for user in User.objects.filter(role="business")
            if not user.businesses.exists()
        ]

        if not stranded:
            self.stdout.write("   ✓ toza")
            return

        for user in stranded:
            self.found += 1
            self.stdout.write(f"   · {user.username}")
            if self.fix:
                user.role = "user"
                user.save(update_fields=["role"])
                self.stdout.write(self.style.SUCCESS("     → rol 'user'ga qaytarildi"))

    # ---------------- 3 ----------------
    def _staff_with_business(self):
        """
        Bitta hisob ham platforma egasi, ham biznes egasi.

        Bu OGOHLANTIRISH, avtomatik tuzatilmaydi: qaysi rol keraklini
        faqat egasi biladi. Platforma egasi biznes panelidan foydalana
        olmaydi (`IsBusinessRole` uni kiritmaydi), ya'ni bunday hisobdagi
        biznes boshqarilmay qoladi.
        """
        self.stdout.write("\n3. Ham platforma egasi, ham biznes egasi")

        both = [user for user in User.objects.filter(is_staff=True) if user.businesses.exists()]

        if not both:
            self.stdout.write("   ✓ toza")
            return

        for user in both:
            names = ", ".join(user.businesses.values_list("name", flat=True))
            self.stdout.write(self.style.WARNING(f"   ! {user.username} — {names}"))
        self.stdout.write(
            "     Yechim: hisobdan `is_staff` ni olib tashlang YOKI biznesni "
            "alohida hisobga o'tkazing.\n"
            "     Avtomatik tuzatilmaydi — qaysi rol kerakligini siz hal qilasiz."
        )
