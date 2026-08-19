"""Platformani ishga tushirish uchun boshlang'ich ma'lumotlar."""

from django.core.management.base import BaseCommand
from django.db import transaction

from common.models import PlatformSettings
from subscriptions.models import SubscriptionPlan


class Command(BaseCommand):
    help = "Platforma sozlamalari va tarif rejalarini yaratadi (mavjudlarini buzmaydi)."

    def add_arguments(self, parser):
        parser.add_argument("--telegram", default="uvente", help="Admin Telegram username (@ siz)")
        parser.add_argument("--restaurant-price", type=int, default=255000)
        parser.add_argument("--venue-price", type=int, default=255000)

    @transaction.atomic
    def handle(self, *args, **options):
        settings_obj, created = PlatformSettings.objects.get_or_create(pk=1)
        if created:
            settings_obj.admin_telegram_username = options["telegram"]
            settings_obj.save()
            self.stdout.write(self.style.SUCCESS("✓ Platforma sozlamalari yaratildi"))
        else:
            self.stdout.write("• Platforma sozlamalari allaqachon mavjud — tegilmadi")

        for business_type, price in (
            ("restaurant", options["restaurant_price"]),
            ("venue", options["venue_price"]),
        ):
            plan, created = SubscriptionPlan.objects.get_or_create(
                business_type=business_type,
                defaults={"monthly_price": price, "trial_days": settings_obj.trial_days},
            )
            mark = "✓ yaratildi" if created else "• mavjud"
            self.stdout.write(f"{mark}: {plan.get_business_type_display()} — {plan.monthly_price} so'm/oy")

        self.stdout.write(self.style.SUCCESS("\nTayyor. Endi superuser yarating:"))
        self.stdout.write("  python manage.py createsuperuser")
