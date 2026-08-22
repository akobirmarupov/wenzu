"""Obuna hayotiy sikli — trial ochish, faollashtirish, muddati tugaganini belgilash."""

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from subscriptions.models import PaymentLog, Subscription, SubscriptionPlan

logger = logging.getLogger(__name__)


# Standart narxlar (so'm). Admin ularni panelda o'zgartiradi — bu yerda
# faqat reja umuman bo'lmasa ishlatiladi.
DEFAULT_PRICES = {
    # biznes turi: {muddat (oy): narx}
    "restaurant": {1: 250000, 3: 600000},
    "venue": {1: 300000, 3: 800000},
}


def get_or_create_plan(business_type, duration_months=1):
    """
    Tarif rejasini beradi, yo'q bo'lsa yaratadi.

    Standart — bir oylik reja: yangi biznes obunani shundan boshlaydi.
    Uzunroq muddatni foydalanuvchi keyin o'zi tanlaydi.
    """
    from common.models import PlatformSettings

    platform = PlatformSettings.get_solo()
    fallback = DEFAULT_PRICES.get(business_type, {}).get(duration_months, 250000 * duration_months)

    plan, created = SubscriptionPlan.objects.get_or_create(
        business_type=business_type,
        duration_months=duration_months,
        defaults={"price": fallback, "trial_days": platform.trial_days},
    )
    if created:
        logger.info(
            f"SubscriptionPlan auto-created: type={business_type}, "
            f"duration={duration_months} oy"
        )
    return plan


@transaction.atomic
class TrialAlreadyUsed(Exception):
    """Bepul sinov allaqachon ishlatilgan — ikkinchi marta berilmaydi."""


def start_trial(*, business):
    """
    7 kunlik bepul sinovni ochadi (admin arizani tasdiqlagach).

    Sinov FOYDALANUVCHIGA bir marta beriladi — biznesga emas. Aks holda
    odam biznesini o'chirib, yangisini ochib, sinovni cheksiz qayta
    olardi.
    """
    owner = business.owner
    if owner.has_used_trial:
        raise TrialAlreadyUsed(
            "Bu foydalanuvchi bepul sinovni allaqachon ishlatgan."
        )

    plan = get_or_create_plan(business.business_type)
    subscription, created = Subscription.objects.get_or_create(
        business=business,
        defaults={
            "plan": plan,
            "status": "trial",
            "trial_ends_at": timezone.now() + timedelta(days=plan.trial_days),
        },
    )

    if created:
        owner.has_used_trial = True
        owner.save(update_fields=["has_used_trial"])

    logger.info(
        f"Trial started: business_id={business.id}, subscription_id={subscription.id}, "
        f"trial_ends_at={subscription.trial_ends_at}"
    )
    return subscription


def start_paid(*, business, plan, approved_by, amount=None, note=""):
    """
    Obunani SINOVSIZ, darhol pullik holatda ochadi.

    Foydalanuvchi tarifni ariza bosqichidayoq tanlab, to'lovni qilgan —
    unga yana bepul kun qo'shishning ma'nosi yo'q. `trial_ends_at`
    hozirgi vaqtga qo'yiladi, ya'ni "sinov muddati allaqachon o'tgan".
    """
    now = timezone.now()
    Subscription.objects.get_or_create(
        business=business,
        defaults={"plan": plan, "status": "trial", "trial_ends_at": now},
    )
    return activate_subscription(
        business=business, approved_by=approved_by,
        amount=amount, note=note or f"Ariza bilan birga to'landi — {plan.duration_label}",
        plan=plan,
    )


@transaction.atomic
def activate_subscription(*, business, approved_by, amount=None, note="", plan=None):
    """
    Admin to'lovni tasdiqlagach chaqiriladi: obuna 'active' bo'ladi va
    REJA MUDDATIGA uzayadi (1 oylik → 30 kun, 3 oylik → 90 kun).

    `plan` berilsa obuna o'sha rejaga o'tadi — mijoz oylikdan choraklikka
    ko'chganda shu ishlatiladi.

    To'lov Telegram orqali qo'lda bo'lgani uchun PaymentLog'ga qo'lda
    yozuv qo'shiladi.
    """
    subscription = getattr(business, "subscription", None)
    if subscription is None:
        # Obuna yo'q — SINOVSIZ yaratamiz. Ilgari bu yerda `start_trial`
        # chaqirilardi va pul to'lagan odamga ustiga yana 7 bepul kun
        # qo'shilib ketardi.
        subscription = Subscription.objects.create(
            business=business,
            plan=plan or get_or_create_plan(business.business_type),
            status="trial",
            trial_ends_at=timezone.now(),
        )

    fields = ["status", "subscription_ends_at", "approved_by"]
    if plan is not None and plan.pk != subscription.plan_id:
        subscription.plan = plan
        fields.append("plan")

    now = timezone.now()
    base = subscription.subscription_ends_at
    if base is None or base < now:
        base = now

    subscription.status = "active"
    subscription.subscription_ends_at = base + timedelta(days=subscription.plan.days)
    subscription.approved_by = approved_by
    subscription.save(update_fields=fields)

    PaymentLog.objects.create(
        subscription=subscription,
        amount=amount if amount is not None else subscription.plan.price,
        confirmed_by=approved_by,
        note=note or "Telegram orqali qo'lda tasdiqlangan to'lov",
    )

    # To'lov tasdiqlandi — joy yana ommaviy qidiruvga QAYTADI.
    #
    # Obuna tugaganda `expire_subscription` uni yashirgan edi. Tiklashni
    # adminning qo'liga qoldirib bo'lmaydi: u to'lovni tasdiqlab, ko'rinish
    # tugmasini bosishni unutsa, egasi pul to'lab turib qidiruvda
    # ko'rinmay qolardi va buni faqat mijozlar yo'qolganda bilardi.
    #
    # Admin baribir istalgan paytda qo'lda bloklay oladi
    # (`/api/admin/businesses/{id}/toggle-block/`) — bu yerdagi tiklash
    # unga xalaqit bermaydi, chunki bloklash keyin bo'ladi.
    if not business.is_visible:
        business.is_visible = True
        business.save(update_fields=["is_visible"])

        # Kesh eskirmasin — aks holda joy qayta yoqilgani bilan ro'yxatda
        # 60 soniya davomida ko'rinmasdi.
        from common.cache import invalidate_business_cache

        invalidate_business_cache()
        logger.info(f"Business restored to public search: business_id={business.id}")

    logger.info(
        f"Subscription activated: subscription_id={subscription.id}, "
        f"business_id={business.id}, ends_at={subscription.subscription_ends_at}, "
        f"by={approved_by.id}"
    )
    return subscription


@transaction.atomic
def expire_subscription(*, subscription):
    """
    Muddat tugadi: obuna 'expired', biznes ommaviy qidiruvdan yashiriladi.
    Rol 'business' bo'lib qoladi — egasi to'lov qilib qayta faollashtira oladi.
    """
    subscription.status = "expired"
    subscription.save(update_fields=["status"])

    business = subscription.business
    if business.is_visible:
        business.is_visible = False
        business.save(update_fields=["is_visible"])

        from common.cache import invalidate_business_cache

        invalidate_business_cache()

    logger.info(f"Subscription expired: subscription_id={subscription.id}, business_id={business.id}")
    return subscription


def check_expired_subscriptions():
    """
    Har kuni ishga tushadigan job (Celery Beat). Trial yoki active muddati
    o'tib ketgan barcha obunalarni 'expired' qiladi.

    Bittalab emas, OMMAVIY (bulk) yangilanadi: 10 000+ biznesda har biriga
    alohida UPDATE yuborish jobni daqiqalab cho'zib yuborardi.
    """
    from django.db.models import Q

    from businesses.models import Business

    now = timezone.now()

    expired_qs = Subscription.objects.filter(
        Q(status="trial", trial_ends_at__lt=now)
        | Q(status="active", subscription_ends_at__lt=now)
    )

    business_ids = list(expired_qs.values_list("business_id", flat=True))
    if not business_ids:
        logger.info("check_expired_subscriptions: muddati o'tgan obuna yo'q")
        return 0

    with transaction.atomic():
        expired_count = expired_qs.update(status="expired")
        Business.objects.filter(id__in=business_ids, is_visible=True).update(is_visible=False)

    # Kesh eskirmasin — bloklangan bizneslar ro'yxatda qolib ketmasligi kerak.
    from common.cache import invalidate_business_cache
    invalidate_business_cache()

    logger.info(f"check_expired_subscriptions finished: expired={expired_count}")
    return expired_count


# ===================================================================
# Obunani uzaytirish arizasi
#
# Oqim biznes ochish bilan bir xil — egasi shunga o'rgangan:
#   ariza yuboradi → Telegram orqali to'laydi → admin tasdiqlaydi.
# ===================================================================
@transaction.atomic
def request_renewal(*, business, plan, note=""):
    """
    Egasi obunani uzaytirish arizasini yuboradi.

    Ochiq ariza allaqachon bo'lsa YANGISI YARATILMAYDI — mavjudi
    qaytariladi. Aks holda tugmani ikki marta bosgan odam adminga ikkita
    bir xil ariza yuborardi.
    """
    from subscriptions.models import SubscriptionRequest

    if plan.business_type != business.business_type:
        raise ValueError("Tarif rejasi biznes turiga mos emas.")

    existing = SubscriptionRequest.objects.filter(
        business=business, status=SubscriptionRequest.STATUS_PENDING
    ).first()
    if existing is not None:
        return existing, False

    request = SubscriptionRequest.objects.create(
        business=business,
        plan=plan,
        price=plan.price,          # narx ariza paytida muzlatiladi
        note=note[:255],
    )

    logger.info(
        f"Subscription renewal requested: request_id={request.id}, "
        f"business_id={business.id}, plan={plan.duration_months} oy"
    )
    _notify_staff_about_request(request)
    return request, True


def _notify_staff_about_request(request):
    """Adminlarga xabar — panelda kutib turgan ish borligini bilsin."""
    try:
        from django.contrib.auth import get_user_model

        from notifications.models import Notification
        from notifications.services import notify_many

        staff = get_user_model().objects.filter(is_staff=True, is_active=True)
        notify_many(
            list(staff),
            kind=Notification.KIND_SUBSCRIPTION,
            title="Obunani uzaytirish arizasi",
            body=f"{request.business.name} — {request.plan.duration_label}, {request.price:,.0f} so'm".replace(",", " "),
            link_url="/boshqaruv/obunalar/",
        )
    except Exception as error:  # noqa: BLE001
        # Bildirishnoma IKKINCHI DARAJALI: u yiqilsa ham ariza saqlanishi kerak.
        logger.warning(f"Obuna arizasi haqida xabar yuborilmadi: {error}")


@transaction.atomic
def approve_renewal(*, request, approved_by, amount=None, note=""):
    """
    Admin to'lovni ko'rgach tasdiqlaydi — obuna reja muddatiga uzayadi.

    Muddat MAVJUD tugash sanasidan boshlab qo'shiladi (agar u hali
    o'tmagan bo'lsa), ya'ni erta to'lagan odam kunini yo'qotmaydi.
    """
    from subscriptions.models import SubscriptionRequest

    if request.status != SubscriptionRequest.STATUS_PENDING:
        raise ValueError(f'Bu ariza allaqachon "{request.get_status_display()}" holatida.')

    subscription = activate_subscription(
        business=request.business,
        approved_by=approved_by,
        amount=amount if amount is not None else request.price,
        note=note or f"Obuna uzaytirildi — {request.plan.duration_label}",
        plan=request.plan,
    )

    # Yangi muddat boshlandi — eski eslatmalar endi ahamiyatsiz.
    subscription.reminded_days = []
    subscription.save(update_fields=["reminded_days"])

    request.status = SubscriptionRequest.STATUS_APPROVED
    request.reviewed_at = timezone.now()
    request.reviewed_by = approved_by
    request.admin_note = note[:255]
    request.save(update_fields=["status", "reviewed_at", "reviewed_by", "admin_note"])

    _notify_owner(
        request.business,
        title="Obunangiz faollashtirildi ✅",
        body=f"{request.plan.duration_label} muddatga uzaytirildi. "
             f"Tugash sanasi: {subscription.subscription_ends_at:%d.%m.%Y}",
        level="success",
    )
    logger.info(f"Renewal approved: request_id={request.id}, by={approved_by.id}")
    return request


@transaction.atomic
def reject_renewal(*, request, rejected_by, note=""):
    """Admin arizani rad etadi — obuna holati o'zgarmaydi."""
    from subscriptions.models import SubscriptionRequest

    if request.status != SubscriptionRequest.STATUS_PENDING:
        raise ValueError(f'Bu ariza allaqachon "{request.get_status_display()}" holatida.')

    request.status = SubscriptionRequest.STATUS_REJECTED
    request.reviewed_at = timezone.now()
    request.reviewed_by = rejected_by
    request.admin_note = note[:255]
    request.save(update_fields=["status", "reviewed_at", "reviewed_by", "admin_note"])

    _notify_owner(
        request.business,
        title="Obuna arizasi rad etildi",
        body=note or "Batafsil ma'lumot uchun administrator bilan bog'laning.",
        level="warning",
    )
    logger.info(f"Renewal rejected: request_id={request.id}, by={rejected_by.id}")
    return request


def _notify_owner(business, *, title, body, level="info"):
    try:
        from notifications.models import Notification
        from notifications.services import notify

        notify(
            business.owner,
            kind=Notification.KIND_SUBSCRIPTION,
            title=title,
            body=body,
            link_url="/panel/obuna/",
            level=level,
        )
    except Exception as error:  # noqa: BLE001
        logger.warning(f"Egaga xabar yuborilmadi: {error}")


# ===================================================================
# Tugash oldidan eslatma
# ===================================================================
# Necha kun qolganda eslatiladi. Uchta bosqich ataylab:
#   5 kun — "rejalashtiring"
#   3 kun — "endi haqiqatan vaqt keldi"
#   2 kun — oxirgi ogohlantirish
REMINDER_DAYS = (5, 3, 2)


def send_expiry_reminders():
    """
    Obuna tugashiga 5 / 3 / 2 kun qolganda egasiga eslatma yuboradi.

    Har kuni ishga tushadi (Celery Beat). Bir xil eslatma ikki marta
    ketmasligi uchun yuborilganlari `Subscription.reminded_days` ga
    yoziladi — vazifa kunda bir necha marta ishga tushsa ham xabar
    takrorlanmaydi.

    Sinov (`trial`) va pullik (`active`) obunalarning ikkalasi ham
    qamrab olinadi: sinov tugashi ham egasi uchun muhim sana.
    """
    from subscriptions.models import Subscription

    now = timezone.now()
    sent = 0

    queryset = Subscription.objects.filter(
        status__in=("trial", "active")
    ).select_related("business", "business__owner", "plan")

    for subscription in queryset:
        ends_at = (
            subscription.subscription_ends_at
            if subscription.status == "active"
            else subscription.trial_ends_at
        )
        if ends_at is None or ends_at < now:
            continue

        # SANA farqi, soat farqi emas.
        #
        # "Obunangizga 3 kun qoldi" — bu odam uchun kalendar hisobi:
        # bugundan tugash kunigacha nechta kun bor. Soat bilan hisoblansa
        # 4 kun 23 soat "4 kun" bo'lib chiqardi va foydalanuvchi bir
        # kunni yo'qotgandek his qilardi.
        days_left = (timezone.localtime(ends_at).date() - timezone.localtime(now).date()).days

        if days_left not in REMINDER_DAYS:
            continue

        already = subscription.reminded_days or []
        if days_left in already:
            continue

        is_trial = subscription.status == "trial"
        _notify_owner(
            subscription.business,
            title=(
                f"Bepul sinovga {days_left} kun qoldi"
                if is_trial else f"Obunangizga {days_left} kun qoldi"
            ),
            body=(
                f"{subscription.business.name} — "
                f"{'sinov muddati' if is_trial else 'obuna'} "
                f"{ends_at:%d.%m.%Y} da tugaydi. Uzluksiz ishlashi uchun "
                f"obunani oldindan uzaytiring."
            ),
            level="warning" if days_left <= 3 else "info",
        )

        subscription.reminded_days = [*already, days_left]
        subscription.save(update_fields=["reminded_days"])
        sent += 1

    logger.info(f"Expiry reminders sent: {sent}")
    return sent
