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


class TrialNotAvailable(Exception):
    """Bepul sinov allaqachon ishlatilgan — ariza qabul qilinmaydi."""


class BusinessLimitReached(Exception):
    """Bitta hisobda bitta biznes — ikkinchisiga ariza qabul qilinmaydi."""


@transaction.atomic
def submit_application(*, applicant, business_type, business_name, plan=None):
    """
    Ariza yuborish.

    MUHIM: bu bosqichda biznes HALI ISHLAMAYDI —
      · `is_visible=False` — qidiruvda chiqmaydi, bron qabul qilmaydi
      · obuna umuman ochilmaydi — bepul sinov ham yo'q

    Nega shunday: ilgari ariza yuborilishi bilan 7 kunlik bepul sinov
    boshlanib, biznes darhol ommaga chiqardi. Ya'ni istalgan foydalanuvchi
    bir daqiqada "restoran" ochib, hech kim tekshirmagan holda platformani
    bir hafta bepul ishlatib tashlashi mumkin edi.

    Endi tartib: ariza → admin Telegram orqali tekshiradi → tasdiqlaydi →
    ANA SHUNDA obuna ochiladi (`approve_application`).

    `plan` — foydalanuvchi ariza bosqichidayoq tanlagan tarif:
      · `None`  → bepul sinov. Har bir foydalanuvchiga BIR MARTA.
      · reja    → pullik. Tasdiqlangach darhol o'sha muddat boshlanadi,
                  sinov berilmaydi.

    Rol darhol 'business'ga o'tadi — egasi o'z paneliga kirib, arizasi
    qanday holatda ekanini ko'rishi kerak.
    """
    # BITTA FOYDALANUVCHI — BITTA BIZNES.
    #
    # Restoran ochgan odam to'yxona ham ocha olmaydi va aksincha.
    # Tizimning butun mantig'i shu farazga tayanadi:
    #   · `user.businesses.first()` — panel qaysi biznesniki ekanini
    #     shundan biladi
    #   · obuna biznesga OneToOne bog'langan
    #   · login javobidagi `business` maydoni bitta obyekt
    # Ikkinchi biznes paydo bo'lsa, egasi ikkinchisini panelda umuman
    # ko'rmasdi — u "yo'qolgan" bo'lib qolardi.
    #
    # Admin panelidagi qo'lda ochish oqimida ham xuddi shu qoida bor
    # (`BusinessAdminCreateSerializer.validate_owner`).
    existing = applicant.businesses.first()
    if existing is not None:
        raise BusinessLimitReached(
            f"Sizda allaqachon biznes bor — «{existing.name}». "
            "Bitta hisobda faqat bitta joy ochish mumkin. Ikkinchi joy uchun "
            "alohida hisob oching."
        )

    # Bepul sinov ikkinchi marta so'ralsa — ARIZA BOSQICHIDAYOQ to'xtatamiz.
    # Aks holda odam ariza yuborib, admin tasdiqlaganda kutilmaganda
    # xato chiqardi va ikkalasi ham sababini tushunmasdi.
    if plan is None and applicant.has_used_trial:
        raise TrialNotAvailable(
            "Bepul sinovdan allaqachon foydalangansiz. Davom ettirish uchun "
            "pullik tariflardan birini tanlang."
        )
    if plan is not None and plan.business_type != business_type:
        raise ValueError("Tanlangan tarif biznes turiga mos emas.")
    application = BusinessApplication.objects.create(
        applicant=applicant,
        business_type=business_type,
        business_name=business_name,
        plan=plan,
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
        # Tasdiqlanmaguncha yashirin — tekshirilmagan joy qidiruvga
        # chiqmasligi kerak.
        is_visible=False,
    )

    if applicant.role != "business":
        applicant.role = "business"
        applicant.save(update_fields=["role"])

    # Obuna ATAYLAB ochilmaydi. U `approve_application` da boshlanadi.
    subscription = None

    logger.info(
        f"Business application submitted: application_id={application.id}, "
        f"business_id={business.id}, user_id={applicant.id}, type={business_type} "
        f"(sinov hali boshlanmadi — admin tasdig'i kutilmoqda)"
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
    Admin arizani tasdiqlaydi — ANA SHU YERDA 7 kunlik BEPUL SINOV
    boshlanadi va biznes ommaviy qidiruvga chiqadi.

    Ilgari bu funksiya `activate_subscription` ni chaqirib, darhol 30
    kunlik PULLIK muddat berardi. Bu ikki jihatdan noto'g'ri edi:
      · tasdiq — to'lov emas, faqat "bu haqiqiy joy" degan tekshiruv
      · sinov muddati ariza berilishi bilanoq boshlanib ketardi

    Pullik muddat endi alohida oqimda: egasi obuna arizasini yuboradi
    (`SubscriptionRequest`), to'laydi, admin o'sha arizani tasdiqlaydi.
    """
    from subscriptions.services import TrialAlreadyUsed, start_paid, start_trial

    application.status = "approved"
    application.approved_at = timezone.now()
    application.approved_by = approved_by
    application.save(update_fields=["status", "approved_at", "approved_by"])

    business = getattr(application, "business", None)
    if business is not None:
        business.is_visible = True
        business.save(update_fields=["is_visible"])

        if application.plan is not None:
            # Pullik tarif tanlangan — sinovsiz, darhol to'liq muddat.
            start_paid(
                business=business, plan=application.plan, approved_by=approved_by,
            )
        else:
            try:
                start_trial(business=business)
            except TrialAlreadyUsed:
                # Ariza berilgandan keyin sinov boshqa joyda ishlatilgan
                # bo'lishi mumkin. Tasdiqni yiqitmaymiz — joy ochiladi,
                # lekin obunasi darhol "tugagan" holatda bo'ladi va egasi
                # tarif tanlashi kerak.
                logger.warning(
                    f"Trial unavailable at approval: application_id={application.id}"
                )

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
