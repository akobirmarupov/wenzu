"""Celery vazifalari — bronlar bilan bog'liq muntazam ishlar."""

import logging

from celery import shared_task
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger("reservations")

# Vazifa bir yurishda nechta bronni yakunlaydi.
#
# Chegara bor, chunki vazifa har 15 daqiqada ishlaydi: kechqurun
# bir vaqtning o'zida yuzlab bron tugashi mumkin va ularning hammasini
# bitta tranzaksiyada qulflash bazani uzoq ushlab turardi. Qolgani
# keyingi yurishda olinadi — kechikish eng ko'pi bilan 15 daqiqa.
BATCH_SIZE = 500


@shared_task(name="reservations.tasks.complete_past_reservations_task")
def complete_past_reservations_task():
    """
    Vaqti TUGAGAN tasdiqlangan bronlarni 'completed' qiladi va mijozdan
    sharh so'raydi.

    ===================================================================
    NEGA HAR 15 DAQIQADA, KUNIGA BIR MARTA EMAS
    ===================================================================
    Ilgari bu vazifa har kuni 04:00 da ishlardi va "kechagi" bronlarni
    yakunlardi. Ya'ni soat 20:00 da kechki ovqatdan chiqqan odam sharh
    yozmoqchi bo'lsa, tizim "bron hali yakunlanmagan" deb rad etardi —
    u faqat ertasi kuni ertalab yoza olardi. Amalda esa odam ertasiga
    qaytib kelmaydi va joy sharhsiz qoladi.

    Endi bron o'z vaqti tugashi bilan (masalan 18:00–20:00 bronida
    soat 20:00 da) yakunlanadi va mijozga darrov "qanday o'tdi?" degan
    bildirishnoma boradi. Taassurot yangi bo'lganda yozilgan sharh
    ham rostroq bo'ladi.

    Bildirishnoma yiqilsa bron baribir yakunlanadi: sharh so'rash
    ikkinchi darajali, holatning to'g'ri bo'lishi esa birinchi.
    """
    from notifications.models import Notification
    from notifications.services import notify
    from reservations.models import Reservation

    now = timezone.localtime()
    today = now.date()

    # Qaysi bron tugagan:
    #   · kechagi va undan oldingi kunlar — shubhasiz tugagan;
    #   · bugungilar — tugash soati hozirgi soatdan o'tgan bo'lsa.
    #
    # Tugash soati bronning o'zida bo'lmasligi mumkin (to'yxona) — u
    # holda jadvaldagi soat olinadi.
    ended = (
        Q(availability__date__lt=today)
        | Q(availability__date=today, end_time__lte=now.time())
        | Q(
            availability__date=today,
            end_time__isnull=True,
            availability__end_time__lte=now.time(),
        )
    )

    queryset = (
        Reservation.objects.filter(status="confirmed")
        .filter(ended)
        .select_related("business", "user", "availability")
        .order_by("availability__date")[:BATCH_SIZE]
    )

    finished = []
    with transaction.atomic():
        # `select_for_update` — o'sha lahzada joy egasi holatni
        # o'zgartirayotgan bo'lishi mumkin. `skip_locked` bilan band
        # yozuvni chetlab o'tamiz: u keyingi yurishda olinadi.
        for reservation in queryset.select_for_update(skip_locked=True):
            # Tungi oraliqni (22:00–02:00) filtr "tugagan" deb hisoblab
            # yuborishi mumkin, shuning uchun aniq vaqtni modeldan
            # qayta tekshiramiz — u kun oshishini ham hisobga oladi.
            ends_at = reservation.event_ends_at()
            if ends_at is not None and ends_at > timezone.now():
                continue

            reservation.status = "completed"
            reservation.save(update_fields=["status"])
            finished.append(reservation)

    for reservation in finished:
        _ask_for_review(reservation, notify, Notification)

    logger.info(f"complete_past_reservations_task: {len(finished)} ta bron yakunlandi")
    return len(finished)


def _ask_for_review(reservation, notify, Notification):
    """
    Mijozga "sharh qoldiring" bildirishnomasi.

    Alohida funksiyada va tranzaksiyadan TASHQARIDA: bildirishnoma
    yozishdagi xato bronning yakunlanishini orqaga qaytarmasligi kerak.
    """
    try:
        notify(
            reservation.user,
            kind=Notification.KIND_REVIEW,
            title="Tashrifingiz qanday o'tdi?",
            body=f"{reservation.business.name} — bahoingizni qoldiring, "
                 f"bu boshqa mijozlarga tanlashda yordam beradi.",
            link_url="/bronlarim/",
        )
    except Exception as error:  # noqa: BLE001
        logger.warning(f"Sharh so'rovi yuborilmadi (bron {reservation.pk}): {error}")

