"""Celery vazifalari — obuna muddatlarini kuzatish."""

import logging

from celery import shared_task

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
    Har kuni 09:00 da: biznes EGASIGA — saytdagi qo'ng'iroqcha ostiga,
    tugashiga 5 / 3 / 2 kun qolganda eslatma (`send_expiry_reminders`).
    Egasi shu xabarni bosib, obunani uzaytirish arizasini yuboradi.

    Obuna to'satdan o'chib qolmasligi — biznes egasi uchun eng og'riqli holat.
    """
    from subscriptions.services import send_expiry_reminders

    reminded = send_expiry_reminders()
    logger.info(f"notify_expiring_subscriptions_task: {reminded} ta egaga eslatma")
    return reminded

