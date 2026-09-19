"""
Biznes ariza oqimining "yuragi" — TZ 4-bo'limidagi bosqichlar shu yerda.

Bu mantiq view'da emas, alohida servis funksiyasida turibdi, chunki uni
API'dan ham, Django admin panelidan ham
bir xil chaqirish kerak bo'ladi.
"""

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from businesses.models import Business, BusinessApplication

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

    ROL BU YERDA O'ZGARMAYDI — odam oddiy foydalanuvchiligicha qoladi.

    Ilgari ariza yuborilishi bilan `role='business'` qo'yilardi. Ya'ni
    hech kim tekshirmagan, hatto keyinchalik RAD ETILADIGAN ariza ham
    odamni "restoran egasi" qilib qo'yardi: profilida shu yozuv turardi,
    rad etilgandan keyin ham o'chmasdi. Rol — tasdiqning natijasi, ariza
    yuborishning emas: u `approve_application` da beriladi va
    `reject_application` da qaytariladi.
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
    #
    # ISTISNO — ARIZASI RAD ETILGAN JOY.
    #
    # Rad etish joyni O'CHIRMAYDI, faqat yashiradi. Ilgari o'sha yashirin
    # joy egasiga MANGU to'siq bo'lardi: yangi ariza yuborsa "sizda
    # allaqachon biznes bor" deb rad etilardi, eski arizasi esa rad
    # etilgan holatda muzlab qolardi. Ya'ni bir marta rad etilgan odam
    # hech qachon qayta urina olmasdi — bu boshi berk ko'cha edi.
    #
    # Endi u qayta ariza yuboradi: joy o'chirilmaydi, YANGI arizaga
    # ulanadi (nomi va turi arizadagisiga yangilanadi). Shunda kiritilgan
    # ma'lumot — suratlar, xonalar, menyu — yo'qolmaydi.
    existing = applicant.businesses.select_related("application").first()
    reapply_to = None
    if existing is not None:
        prior = getattr(existing, "application", None)
        if prior is not None and prior.status == BusinessApplication.STATUS_REJECTED:
            reapply_to = existing
        else:
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

    if reapply_to is not None:
        # Qayta ariza — mavjud joy yangi arizaga ulanadi.
        #
        # Eski (rad etilgan) ariza tarixda qoladi, lekin endi hech qanday
        # joyga bog'lanmaydi. Turini almashtirishga ruxsat beramiz: odam
        # arizani "restoran" deb yuborib, aslida to'yxona bo'lgani uchun
        # rad etilgan bo'lishi mumkin. Eski turdagi xona/zal yozuvlari
        # O'CHIRILMAYDI — ular shunchaki ko'rinmay turadi va tur qaytsa
        # joyida bo'ladi (o'chirish bronlar tarixini ham olib ketardi).
        business = reapply_to
        business.application = application
        business.name = business_name
        business.business_type = business_type
        business.is_visible = False
        business.save(
            update_fields=["application", "name", "business_type", "is_visible"]
        )
    else:
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

    # Rol ham, obuna ham ATAYLAB tegilmaydi — ikkalasi ham
    # `approve_application` da beriladi.
    subscription = None

    logger.info(
        f"Business application submitted: application_id={application.id}, "
        f"business_id={business.id}, user_id={applicant.id}, type={business_type} "
        f"(sinov hali boshlanmadi — admin tasdig'i kutilmoqda)"
    )
    return application, business, subscription


@transaction.atomic
def approve_application(*, application, approved_by):
    """
    Admin arizani tasdiqlaydi — ANA SHU YERDA obuna ochiladi va biznes
    ommaviy qidiruvga chiqadi.

    Obuna qanday ochilishi ARIZADAGI TARIFGA bog'liq:
      · `plan is None` — bepul sinov arizasi: shu kundan boshlab
        `trial_days` kunlik sinov ochiladi (har bir foydalanuvchiga
        bir marta).
      · `plan` tanlangan — 1 yoki 3 oylik tarif: SINOV BERILMAYDI.
        Obuna tasdiq kunidan boshlab darhol 'active' bo'ladi va aynan
        o'sha muddatga ochiladi; muddat tugab, keyingi to'lov bo'lmasa
        'expired' ga o'tadi. Pul to'lagan odamga ustiga yana bepul kun
        qo'shishning ma'nosi yo'q.

    Ilgari bu funksiya `activate_subscription` ni chaqirib, tarifdan
    qat'i nazar darhol 30 kunlik muddat berardi. Bu noto'g'ri edi:
    tasdiq — to'lov emas, faqat "bu haqiqiy joy" degan tekshiruv.

    ROL HAM SHU YERDA beriladi: odam ANA ENDI "restoran/to'yxona egasi".
    Ilgari u ariza yuborgan zahoti shunday atalardi — tekshirilmagan,
    hatto keyin rad etiladigan ariza bilan.
    """
    from subscriptions.services import TrialAlreadyUsed, start_paid, start_trial

    application.status = "approved"
    application.approved_at = timezone.now()
    application.approved_by = approved_by
    application.save(update_fields=["status", "approved_at", "approved_by"])

    # PLATFORMA EGASIGA tegilmaydi: `is_staff` uchun rol boshqa vazifani
    # bildiradi va uni 'business' ga o'tkazish uni o'z panelidan
    # ayirardi (`IsBusinessRole` staff'ni kiritmaydi).
    applicant = application.applicant
    if not applicant.is_staff and applicant.role != "business":
        applicant.role = "business"
        applicant.save(update_fields=["role"])

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
    lekin O'CHIRILMAYDI.

    Rad etish — nuqta emas, ORQAGA QAYTARISH. Egasi kamchilikni to'g'rilab
    (nomi, turi, admin bilan kelishilgan to'lov) YANGI ariza yuboradi va
    o'sha joy yangi arizaga ulanadi — `submit_application` ga qarang.
    Shuning uchun bu yerda joy ham, uning suratlari ham o'chirilmaydi.

    ROL esa ODDIY FOYDALANUVCHIGA qaytadi: rad etilgan odam "restoran
    egasi" emas. Ilgari rol ariza yuborilishida qo'yilib, rad etilgandan
    keyin ham qolib ketardi — profilida "Restoran egasi" yozuvi turardi,
    lekin hech qanday joyi ishlamasdi.
    """
    application.status = "rejected"
    application.approved_by = rejected_by
    application.save(update_fields=["status", "approved_by"])

    _demote_if_no_approved_business(application.applicant)

    business = getattr(application, "business", None)
    if business is not None:
        business.is_visible = False
        business.save(update_fields=["is_visible"])

    logger.info(
        f"Application rejected: application_id={application.id}, by={rejected_by.id}"
    )
    return application


def _demote_if_no_approved_business(user):
    """
    Rolni oddiy foydalanuvchiga qaytaradi — TASDIQLANGAN joyi qolmasa.

    Tekshiruv shart: bir hisobda bir nechta ariza bo'lishi mumkin
    (qayta yuborilganlari). Ulardan bittasi tasdiqlangan bo'lsa, odam
    haqiqiy biznes egasi bo'lib qoladi va rolini olib qo'yish uni o'z
    panelidan ayirardi.

    Platforma egasiga (`is_staff`) tegilmaydi — uning roli boshqa
    vazifani bildiradi.
    """
    if user.is_staff or user.role != "business":
        return
    if BusinessApplication.objects.filter(
        applicant=user, status=BusinessApplication.STATUS_APPROVED
    ).exists():
        return

    user.role = "user"
    user.save(update_fields=["role"])
    logger.info(f"Owner role reset to 'user': user_id={user.pk} (ariza rad etildi)")


