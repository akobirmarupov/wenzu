"""Celery vazifalari — bronlar bilan bog'liq muntazam ishlar."""

import datetime
import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger("reservations")


@shared_task(name="reservations.tasks.complete_past_reservations_task")
def complete_past_reservations_task():
    """
    Har kuni 04:00 da: sanasi o'tib ketgan tasdiqlangan bronlarni
    'completed' qiladi.

    Bu nafaqat tozalik uchun — sharh qoldirish faqat YAKUNLANGAN bron
    uchun ruxsat etilgani sababli, bu bo'lmasa mijoz hech qachon
    sharh yoza olmaydi.
    """
    from reservations.models import Reservation

    yesterday = timezone.localdate() - datetime.timedelta(days=1)

    queryset = Reservation.objects.filter(
        status="confirmed", availability__date__lte=yesterday
    )

    completed = 0
    with transaction.atomic():
        for reservation in queryset.select_for_update(skip_locked=True).iterator(chunk_size=500):
            reservation.status = "completed"
            reservation.save(update_fields=["status"])
            completed += 1

    logger.info(f"complete_past_reservations_task: {completed} ta bron yakunlandi")
    return completed


@shared_task(name="reservations.tasks.send_reservation_notification_task")
def send_reservation_notification_task(reservation_id):
    """
    Bron haqida Telegram xabarnomasi — FON rejimida.

    Nega fon: Telegram API sekin javob bersa yoki umuman javob bermasa,
    mijoz bron qilish tugmasini bosib 5 sekund kutib qolmasligi kerak.
    """
    from common.telegram import notify_new_reservation
    from reservations.models import Reservation

    reservation = (
        Reservation.objects.select_related("business", "user", "room", "hall", "availability")
        .filter(pk=reservation_id)
        .first()
    )
    if reservation is None:
        logger.warning(f"send_reservation_notification_task: bron topilmadi id={reservation_id}")
        return False
    return notify_new_reservation(reservation)
