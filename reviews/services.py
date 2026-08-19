"""Sharhlarga bog'liq yordamchi mantiq."""

import logging

from django.db.models import Avg, Count

logger = logging.getLogger("reviews")


def recalculate_business_rating(business):
    """
    Biznesning `rating_avg` va `reviews_count` maydonlarini qayta hisoblaydi.

    Nega denormalizatsiya: bosh sahifadagi ro'yxat so'rovi har bir biznes
    uchun AVG va COUNT hisoblaganida, 10 000 biznesda bu har safar butun
    sharhlar jadvalini kezib chiqishni anglatardi. Yozish kamdan-kam,
    o'qish esa doimiy — shuning uchun hisobni yozish paytiga surdik.
    """
    result = business.reviews.aggregate(avg=Avg("rating"), total=Count("id"))
    business.rating_avg = round(result["avg"] or 0, 2)
    business.reviews_count = result["total"] or 0
    business.save(update_fields=["rating_avg", "reviews_count"])

    logger.info(
        f"Business rating recalculated: business_id={business.id}, "
        f"avg={business.rating_avg}, count={business.reviews_count}"
    )
    return business.rating_avg
