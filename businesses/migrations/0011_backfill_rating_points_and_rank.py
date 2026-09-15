"""
Mavjud bizneslarga ball va o'rin beradi.

`rating_points` va `rank` yangi maydonlar — ular sharh yozilganda
to'ldiriladi (`reviews.signals`). Lekin bazada ALLAQACHON sharhlar bor
va ularsiz barcha joylar 0 ball bilan qolib, o'rinlar jadvali bo'sh
ko'rinardi. Bu migratsiya bir marta o'sha bo'shliqni to'ldiradi.
"""

from django.db import migrations
from django.db.models import Sum


def fill(apps, schema_editor):
    Business = apps.get_model("businesses", "Business")

    # Ballar: har bir joyning sharhlaridagi yulduzlar yig'indisi.
    #
    # Bitta so'rov bilan olamiz — biznes bo'yicha aylanib, har biriga
    # alohida `aggregate` qilish 10 000 joyda 10 000 so'rov bo'lardi.
    points = dict(
        Business.objects.annotate(total=Sum("reviews__rating"))
        .values_list("id", "total")
    )

    updates = []
    for business in Business.objects.all().only("id", "rating_points"):
        value = points.get(business.id) or 0
        if business.rating_points != value:
            business.rating_points = value
            updates.append(business)
    if updates:
        Business.objects.bulk_update(updates, ["rating_points"])

    # O'rinlar — har bir tur ichida alohida.
    for business_type in ("restaurant", "venue"):
        rows = list(
            Business.objects.filter(business_type=business_type)
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


def unfill(apps, schema_editor):
    """Orqaga qaytish — maydonlar baribir o'chiriladi, nolga qaytaramiz."""
    Business = apps.get_model("businesses", "Business")
    Business.objects.update(rating_points=0, rank=0)


class Migration(migrations.Migration):

    dependencies = [
        ("businesses", "0010_business_rank_business_rating_points_and_more"),
        ("reviews", "0001_initial"),
    ]

    operations = [migrations.RunPython(fill, unfill)]
