"""
Testlar uchun umumiy fikstura yordamchilari.

Nega alohida modul: biznes yaratish oqimi ikki qadamli bo'lib qoldi —
avval ariza, keyin admin tasdig'i (ana shunda 7 kunlik sinov boshlanadi
va joy qidiruvga chiqadi). Har bir test faylida shu ikki qadamni qo'lda
yozish bir joyni unutishga olib kelardi va test "nega ishlamayapti?"
degan savolga aylanardi.
"""

from django.contrib.auth import get_user_model

from businesses.services import approve_application, submit_application

User = get_user_model()

_admin_cache = {}


def approving_admin():
    """
    Arizani tasdiqlaydigan xizmatchi hisob.

    Testlar uchun bitta yetadi — har chaqiruvda yangisini yaratish
    telefon raqami unikalligiga urilardi.
    """
    key = "approver"
    if key not in _admin_cache or not User.objects.filter(pk=_admin_cache[key].pk).exists():
        _admin_cache[key] = User.objects.create_user(
            username="fixture_approver",
            password="StrongPass123!",
            phone_number="+998900009999",
            full_name="Fikstura Admini",
            is_staff=True,
        )
    return _admin_cache[key]


def make_business(*, applicant, business_type, business_name, approve=True):
    """
    To'liq ishlaydigan biznes yaratadi: ariza → tasdiq → 7 kunlik sinov.

    @param approve: False bo'lsa faqat ariza qoldiriladi — "tasdiqlanmagan
        biznes hech narsa qila olmaydi" degan holatni tekshirish uchun.
    @returns: (application, business, subscription)
    """
    application, business, _ = submit_application(
        applicant=applicant,
        business_type=business_type,
        business_name=business_name,
    )

    if not approve:
        return application, business, None

    approve_application(application=application, approved_by=approving_admin())
    business.refresh_from_db()
    applicant.refresh_from_db()

    return application, business, getattr(business, "subscription", None)


def ensure_plans():
    """
    To'rttala tarif rejasini yaratadi (restoran/to'yxona × 1/3 oy).

    Testda baza bo'sh boshlanadi va `get_or_create_plan` faqat kerak
    bo'lganini yaratadi — 3 oylik reja esa hech qachon o'z-o'zidan
    paydo bo'lmaydi. Haqiqiy tizimda ularni `seed_platform` yaratadi.
    """
    from common.management.commands.seed_platform import PLAN_PRICES
    from subscriptions.models import SubscriptionPlan

    for business_type, durations in PLAN_PRICES.items():
        for months, price in durations.items():
            SubscriptionPlan.objects.get_or_create(
                business_type=business_type,
                duration_months=months,
                defaults={"price": price, "trial_days": 7},
            )
