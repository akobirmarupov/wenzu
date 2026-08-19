"""Celery ilovasi — trial/obuna muddatini kuzatish va og'ir amallarni fon rejimga chiqarish."""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("wenzu")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    # TZ 9-bo'lim: har kuni ishga tushadigan job — muddati o'tgan
    # trial/obunalarni 'expired' qiladi va profilni qidiruvdan yashiradi.
    "check-expired-subscriptions": {
        "task": "subscriptions.tasks.check_expired_subscriptions_task",
        "schedule": crontab(hour=3, minute=0),
    },
    # Tugayotgan obunalar haqida egasiga eslatma.
    "notify-expiring-subscriptions": {
        "task": "subscriptions.tasks.notify_expiring_subscriptions_task",
        "schedule": crontab(hour=9, minute=0),
    },
    # O'tib ketgan sana bronlarini avtomatik yakunlash.
    "complete-past-reservations": {
        "task": "reservations.tasks.complete_past_reservations_task",
        "schedule": crontab(hour=4, minute=0),
    },
}
