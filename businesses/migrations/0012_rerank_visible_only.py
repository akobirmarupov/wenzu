"""
O'rinlarni qaytadan taqsimlaydi — endi faqat KO'RINADIGAN joylar uchun.

0011 barcha joylarga o'rin bergan edi, yashiringanlariga ham. Ro'yxatda
esa faqat ko'rinadiganlari chiqadi — natijada raqamlar sakrab ketishi
mumkin edi. Bir vaqtning o'zida 0011 dan keyin qo'shilgan, hali sharhi
yo'q joylar ham o'rinsiz (0) qolgan; ular ham shu yerda o'rin oladi.
"""

from django.db import migrations


def rerank(apps, schema_editor):
    Business = apps.get_model("businesses", "Business")

    for business_type in ("restaurant", "venue"):
        rows = Business.objects.filter(business_type=business_type)

        # Yashiringanlarning o'rni yo'q.
        rows.filter(is_visible=False).exclude(rank=0).update(rank=0)

        visible = list(
            rows.filter(is_visible=True)
            .order_by("-rating_points", "-reviews_count", "-rating_avg", "created_at")
            .only("id", "rank")
        )
        changed = []
        for position, business in enumerate(visible, start=1):
            if business.rank != position:
                business.rank = position
                changed.append(business)
        if changed:
            Business.objects.bulk_update(changed, ["rank"])


def noop(apps, schema_editor):
    """Orqaga qaytishda o'rinlar o'zgarishsiz qoladi — ular baribir qayta hisoblanadi."""


class Migration(migrations.Migration):

    dependencies = [
        ("businesses", "0011_backfill_rating_points_and_rank"),
    ]

    operations = [migrations.RunPython(rerank, noop)]
