"""Sharhlarga bog'liq yordamchi mantiq."""

import logging

from django.db.models import Avg, Count, Sum

logger = logging.getLogger("reviews")


def recalculate_business_rating(business):
    """
    Biznesning `rating_avg`, `reviews_count` va `rating_points`
    maydonlarini qayta hisoblaydi.

    Nega denormalizatsiya: bosh sahifadagi ro'yxat so'rovi har bir biznes
    uchun AVG va COUNT hisoblaganida, 10 000 biznesda bu har safar butun
    sharhlar jadvalini kezib chiqishni anglatardi. Yozish kamdan-kam,
    o'qish esa doimiy — shuning uchun hisobni yozish paytiga surdik.
    """
    result = business.reviews.aggregate(
        avg=Avg("rating"), total=Count("id"), points=Sum("rating")
    )
    business.rating_avg = round(result["avg"] or 0, 2)
    business.reviews_count = result["total"] or 0
    business.rating_points = result["points"] or 0
    business.save(update_fields=["rating_avg", "reviews_count", "rating_points"])

    logger.info(
        f"Business rating recalculated: business_id={business.id}, "
        f"avg={business.rating_avg}, count={business.reviews_count}, "
        f"points={business.rating_points}"
    )
    return business.rating_avg


def recalculate_ranks(business_type):
    """
    Bitta TUR ichidagi o'rinlarni qaytadan taqsimlaydi.

    Tartib: yulduzlar yig'indisi kamayish bo'yicha. Ballar teng bo'lsa —
    sharhlar soni, keyin o'rtacha reyting, oxirida esa yaratilgan sana
    (eskisi oldinda). Oxirgi mezon TARTIBNING BARQARORLIGI uchun: usiz
    ballari teng ikki joy har hisoblashda o'rin almashib turardi va
    mijoz ro'yxatni har ochganda boshqacha ko'rardi.

    Nega har bir sharhda butun ro'yxat qayta hisoblanadi: bitta joyning
    ko'tarilishi undan yuqoridagilarning hammasini bir pog'ona pastga
    suradi, ya'ni "faqat o'zini yangilash" degan variant yo'q.

    Faqat KO'RINADIGAN joylar sanaladi. Yashirilgan joy ro'yxatda
    chiqmaydi, lekin o'rin band qilib tursa, mijoz 1, 2, 4 — deb
    sakrab ketgan raqamlarni ko'rardi. Shuning uchun yashiringanining
    o'rni nolga tushiriladi va u qaytib ochilganda (`businesses.signals`)
    jadval yana qayta taqsimlanadi.

    Yozish ARZON: faqat o'rni HAQIQATAN o'zgarganlar yangilanadi
    (`bulk_update`), ya'ni odatda bir-ikki qator tegadi.
    """
    from businesses.models import Business

    # Yashiringanlar jadvaldan chiqariladi — nol "o'rni yo'q" degani.
    Business.objects.filter(business_type=business_type, is_visible=False).exclude(
        rank=0
    ).update(rank=0)

    rows = list(
        Business.objects.filter(business_type=business_type, is_visible=True)
        .order_by("-rating_points", "-reviews_count", "-rating_avg", "created_at")
        .only("id", "rank")
    )

    changed = []
    for position, business in enumerate(rows, start=1):
        if business.rank != position:
            business.rank = position
            changed.append(business)

    if changed:
        Business.objects.bulk_update(changed, ["rank"])
        logger.info(f"Ranks recalculated: type={business_type}, changed={len(changed)}")
    return len(changed)
