"""Obuna hayotiy sikli — trial ochish, faollashtirish, muddati tugaganini belgilash."""

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from subscriptions.models import PaymentLog, Subscription, SubscriptionPlan

logger = logging.getLogger(__name__)


def get_or_create_plan(business_type):
    """
    Har bir biznes turi uchun bitta tarif rejasi bo'lishi kerak. Admin uni
    keyin panelda tahrirlaydi — bu yerda faqat yo'q bo'lsa yaratiladi.
    """
    from common.models import PlatformSettings

    platform = PlatformSettings.get_solo()
    plan, created = SubscriptionPlan.objects.get_or_create(
        business_type=business_type,
        defaults={"monthly_price": 255000, "trial_days": platform.trial_days},
    )
    if created:
        logger.info(f"SubscriptionPlan auto-created for business_type={business_type}")
    return plan


@transaction.atomic
def start_trial(*, business):
    """Ariza yuborilgan zahoti 7 kunlik bepul sinov obunasini ochadi."""
    plan = get_or_create_plan(business.business_type)
    subscription, _ = Subscription.objects.get_or_create(
        business=business,
        defaults={
            "plan": plan,
            "status": "trial",
            "trial_ends_at": timezone.now() + timedelta(days=plan.trial_days),
        },
    )
    logger.info(
        f"Trial started: business_id={business.id}, subscription_id={subscription.id}, "
        f"trial_ends_at={subscription.trial_ends_at}"
    )
    return subscription


@transaction.atomic
def activate_subscription(*, business, approved_by, amount=None, note=""):
    """
    Admin to'lovni tasdiqlagach chaqiriladi: obuna 'active' bo'ladi va
    30 kunga uzayadi. To'lov Telegram orqali qo'lda bo'lgani uchun
    PaymentLog'ga qo'lda yozuv qo'shiladi.
    """
    subscription = getattr(business, "subscription", None)
    if subscription is None:
        subscription = start_trial(business=business)

    now = timezone.now()
    base = subscription.subscription_ends_at
    if base is None or base < now:
        base = now

    from common.models import PlatformSettings

    subscription.status = "active"
    subscription.subscription_ends_at = base + timedelta(
        days=PlatformSettings.get_solo().subscription_days
    )
    subscription.approved_by = approved_by
    subscription.save(update_fields=["status", "subscription_ends_at", "approved_by"])

    PaymentLog.objects.create(
        subscription=subscription,
        amount=amount if amount is not None else subscription.plan.monthly_price,
        confirmed_by=approved_by,
        note=note or "Telegram orqali qo'lda tasdiqlangan to'lov",
    )

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
