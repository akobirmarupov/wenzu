"""
Loyihani bo'sh, "toza" holatga qaytaradi.

Nima uchun kerak: ishlab chiqish paytida to'plangan sinov ma'lumotlari
(bizneslar, bronlar, sharhlar, demo foydalanuvchilar) haqiqiy ishga
o'tishdan oldin butunlay olib tashlanishi kerak. Qo'lda o'chirish
xavfli — bog'liq yozuvlar qolib ketadi va panelda "yo'q joyning broni"
kabi holatlar chiqadi.

NIMA QOLADI (ataylab):
  · super-admin akkauntlari — aks holda tizimga kirib bo'lmaydi;
  · PlatformSettings — platforma sozlamalari;
  · SubscriptionPlan — tarif rejalari, ularsiz ariza yuborib bo'lmaydi.

Boshqa hamma narsa o'chadi, shu jumladan yuklangan rasm fayllari.

Ishlatish:
    python manage.py reset_data            # faqat nima o'chishini ko'rsatadi
    python manage.py reset_data --yes      # haqiqatan o'chiradi
    python manage.py reset_data --yes --keep-media   # fayllarga tegmaydi
"""

import shutil
from pathlib import Path

from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db import transaction

from businesses.models import (
    Business,
    BusinessApplication,
    BusinessPhoto,
    Hall,
    Room,
    VenuePricing,
)
from catalog.models import RestaurantMenuItem, VenueMenuItem
from common.models import Feedback
from content.models import Banner, News
from notifications.models import Notification
from reservations.models import Availability, Reservation
from reviews.models import Review, ReviewPhoto
from subscriptions.models import PaymentLog, Subscription, SubscriptionRequest

# Tartib muhim: avval bog'liq (bola) yozuvlar, keyin asosiylari. Aks holda
# ForeignKey cheklovi yiqiladi yoki CASCADE kutilmagan narsani olib ketadi.
MODELS_IN_ORDER = (
    Reservation,
    Availability,
    ReviewPhoto,
    Review,
    PaymentLog,
    SubscriptionRequest,
    Subscription,
    RestaurantMenuItem,
    VenueMenuItem,
    VenuePricing,
    Room,
    Hall,
    BusinessPhoto,
    Business,
    BusinessApplication,
    Notification,
    Banner,
    News,
    Feedback,
    LogEntry,
    Session,
)


def upload_dirs():
    """
    Fayl yuklanadigan papkalar RO'YXATI — modellarning o'zidan.

    Ilgari bu ro'yxat qo'lda yozilgan edi va tabiiy ravishda eskirdi:
    `venue_menu/` qo'shilganda ro'yxatga tushmay qoldi, natijada
    tozalashdan keyin ham 30 MB fayl qolib ketdi. Endi ro'yxat
    modellardagi `upload_to` dan yig'iladi — yangi maydon qo'shilsa
    o'zi paydo bo'ladi.
    """
    from django.apps import apps
    from django.db.models import FileField

    names = set()
    for model in apps.get_models():
        for field in model._meta.get_fields():
            if isinstance(field, FileField) and isinstance(field.upload_to, str):
                # "banners/video/" → eng yuqori papka: "banners"
                top = field.upload_to.strip("/").split("/")[0]
                if top:
                    names.add(top)

    # Demo suratlar keshi — modelga bog'lanmagan, lekin joy egallaydi.
    names.add("_demo_cache")
    return sorted(names)


class Command(BaseCommand):
    help = "Sinov ma'lumotlarini o'chiradi. Super-admin, sozlamalar va tarif rejalari qoladi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes", action="store_true",
            help="Haqiqatan o'chirish. Busiz faqat hisobot chiqadi.",
        )
        parser.add_argument(
            "--keep-media", action="store_true",
            help="media/ ichidagi yuklangan fayllarga tegmaydi.",
        )

    def handle(self, *args, **options):
        confirmed = options["yes"]
        user_model = get_user_model()
        doomed_users = user_model.objects.filter(is_superuser=False)

        self.stdout.write(self.style.MIGRATE_HEADING("O'chiriladigan yozuvlar:"))
        for model in MODELS_IN_ORDER:
            count = model.objects.count()
            if count:
                self.stdout.write(f"  {model._meta.label:<40} {count}")
        self.stdout.write(f"  {'account.User (super-admindan boshqa)':<40} {doomed_users.count()}")

        if not confirmed:
            self.stdout.write(self.style.WARNING(
                "\nHech narsa o'chirilmadi. Haqiqatan o'chirish uchun: "
                "python manage.py reset_data --yes"
            ))
            return

        # Blacklist jadvallari faqat simplejwt o'rnatilgan bo'lsa bor.
        extra_models = []
        try:
            from rest_framework_simplejwt.token_blacklist.models import (
                BlacklistedToken,
                OutstandingToken,
            )
            extra_models = [BlacklistedToken, OutstandingToken]
        except ImportError:  # pragma: no cover
            pass

        with transaction.atomic():
            for model in (*MODELS_IN_ORDER, *extra_models):
                deleted, _ = model.objects.all().delete()
                if deleted:
                    self.stdout.write(f"  ✓ {model._meta.label}: {deleted}")
            deleted, _ = doomed_users.delete()
            self.stdout.write(f"  ✓ account.User: {deleted}")

        if not options["keep_media"]:
            self._clear_media()

        self.stdout.write(self.style.SUCCESS(
            "\nBaza toza. Endi platformaga kiritilgan har qanday ma'lumot "
            "haqiqiy ma'lumot bo'ladi."
        ))

    def _clear_media(self):
        root = Path(settings.MEDIA_ROOT)
        if not root.exists():
            return
        for name in upload_dirs():
            target = root / name
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
                self.stdout.write(f"  ✓ media/{name}/ o'chirildi")
