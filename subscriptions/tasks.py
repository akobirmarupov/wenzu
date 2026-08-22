"""Celery vazifalari — obuna muddatlarini kuzatish."""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("subscriptions")


@shared_task(name="subscriptions.tasks.check_expired_subscriptions_task")
def check_expired_subscriptions_task():
    """
    Har kuni 03:00 da: trial yoki obuna muddati o'tgan bizneslarni
    'expired' qiladi va ommaviy qidiruvdan yashiradi (TZ 4.1, 6-qadam).
    """
    from subscriptions.services import check_expired_subscriptions

    count = check_expired_subscriptions()
    logger.info(f"check_expired_subscriptions_task: {count} ta obuna muddati tugadi")
    return count


@shared_task(name="subscriptions.tasks.notify_expiring_subscriptions_task")
def notify_expiring_subscriptions_task():
    """
    Har kuni 09:00 da ishlaydi va IKKI xil eslatma yuboradi:

      1. Biznes EGASIGA — saytdagi qo'ng'iroqcha ostiga, tugashiga
         5 / 3 / 2 kun qolganda (`send_expiry_reminders`). Egasi shu
         xabarni bosib, obunani uzaytirish arizasini yuboradi.

      2. ADMINGA — Telegramga, 3 kun ichida tugaydiganlar ro'yxati.
         Bu operatorga "kim bilan bog'lanish kerak"ligini ko'rsatadi.

    Obuna to'satdan o'chib qolmasligi — biznes egasi uchun eng og'riqli holat.
    """
    from common.telegram import send_telegram_message
    from subscriptions.models import Subscription
    from subscriptions.services import send_expiry_reminders

    # 1) Egalariga — saytdagi bildirishnoma.
    reminded = send_expiry_reminders()
    logger.info(f"notify_expiring_subscriptions_task: {reminded} ta egaga eslatma")

    now = timezone.now()
    deadline = now + timedelta(days=3)

    expiring = Subscription.objects.filter(
        status__in=["trial", "active"]
    ).select_related("business", "business__owner")

    notified = 0
    for subscription in expiring:
        ends_at = (
            subscription.subscription_ends_at
            if subscription.status == "active"
            else subscription.trial_ends_at
        )
        if ends_at is None or not (now < ends_at <= deadline):
            continue

        days_left = (ends_at - now).days
        send_telegram_message(
            f"⏳ <b>Obuna tugayapti</b>\n\n"
            f"🏢 {subscription.business.name}\n"
            f"👤 {subscription.business.owner.full_name} "
            f"({subscription.business.owner.phone_number})\n"
            f"📅 Qolgan: {days_left} kun"
        )
        notified += 1

    logger.info(f"notify_expiring_subscriptions_task: adminga {notified} ta xabar")
    return {"owners": reminded, "admin": notified}
