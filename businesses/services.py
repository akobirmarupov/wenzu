"""
Biznes ariza oqimining "yuragi" — TZ 4-bo'limidagi bosqichlar shu yerda.

Bu mantiq view'da emas, alohida servis funksiyasida turibdi, chunki uni
API'dan ham, Django admin panelidan ham, kelajakda Telegram botdan ham
bir xil chaqirish kerak bo'ladi.
"""

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from businesses.models import Business, BusinessApplication
from businesses.tasks import notify_new_application_task
from common.queue import enqueue

logger = logging.getLogger(__name__)


@transaction.atomic
def submit_application(*, applicant, business_type, business_name):
    """
    1-3 qadam: ariza yuborish → rol darhol 'business'ga o'tadi → 7 kunlik
    trial ochiladi. TZ bo'yicha bu marketing qarori: biznes egasi to'lovdan
    OLDIN platformani sinab ko'radi.
    """
    from subscriptions.services import start_trial

    application = BusinessApplication.objects.create(
        applicant=applicant,
        business_type=business_type,
        business_name=business_name,
        status="pending_payment",
    )

    business = Business.objects.create(
        owner=applicant,
        application=application,
        name=business_name,
        business_type=business_type,
        address="",
        latitude=0,
        longitude=0,
        telegram_username="",
        is_visible=True,
    )

    if applicant.role != "business":
        applicant.role = "business"
        applicant.save(update_fields=["role"])

    subscription = start_trial(business=business)

    logger.info(
        f"Business application submitted: application_id={application.id}, "
        f"business_id={business.id}, user_id={applicant.id}, type={business_type}"
    )

    # Super-adminni xabardor qilish — tranzaksiya MUVAFFAQIYATLI yakunlangandan
    # keyin. Aks holda tranzaksiya orqaga qaytsa, mavjud bo'lmagan ariza
    # haqida xabar ketib qolardi.
    transaction.on_commit(
        lambda: enqueue(notify_new_application_task, str(application.id))
    )
    return application, business, subscription


@transaction.atomic
def approve_application(*, application, approved_by):
    """
    5-qadam: super-admin to'lovni ko'rgach tasdiqlaydi — ariza 'approved',
    obuna 'active' va 30 kunga uzaytiriladi.
    """
    from subscriptions.services import activate_subscription

    application.status = "approved"
    application.approved_at = timezone.now()
    application.approved_by = approved_by
    application.save(update_fields=["status", "approved_at", "approved_by"])

    business = getattr(application, "business", None)
    if business is not None:
        business.is_visible = True
        business.save(update_fields=["is_visible"])
        activate_subscription(business=business, approved_by=approved_by)

    logger.info(
        f"Application approved: application_id={application.id}, by={approved_by.id}"
    )
    return application


@transaction.atomic
def reject_application(*, application, rejected_by):
    """
    Ariza rad etiladi — biznes profili ommaviy qidiruvdan yashiriladi,
    lekin o'chirilmaydi (egasi keyin to'lov qilib qayta ochishi mumkin).
    """
    application.status = "rejected"
    application.approved_by = rejected_by
    application.save(update_fields=["status", "approved_by"])

    business = getattr(application, "business", None)
    if business is not None:
        business.is_visible = False
        business.save(update_fields=["is_visible"])

    logger.info(
        f"Application rejected: application_id={application.id}, by={rejected_by.id}"
    )
    return application


def trial_end_date():
    from common.models import PlatformSettings

    return timezone.now() + timedelta(days=PlatformSettings.get_solo().trial_days)
