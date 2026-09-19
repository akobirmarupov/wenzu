"""
Tarif rejalariga MUDDAT qo'shiladi.

Ilgari har bir biznes turi uchun bitta reja bo'lardi va uning narxi
`monthly_price` deb atalardi. Endi bir nechta muddat bor (1 oylik,
3 oylik), shuning uchun:

  · `monthly_price` → `price`  — bu endi SHU MUDDAT uchun to'liq summa,
    oylik emas. 3 oylik reja uchun 600 000 "oylik narx" emasdi.
  · `duration_months` qo'shiladi — mavjud rejalarning hammasi oylik edi,
    shuning uchun standart qiymat 1.
  · (`business_type`, `duration_months`) juftligi yagona bo'ladi.

Maydon O'CHIRILIB QAYTA yaratilmaydi, `RenameField` ishlatiladi —
aks holda mavjud narxlar yo'qolib ketardi.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0002_paymentlog_idx_payment_sub_created_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="subscriptionplan",
            old_name="monthly_price",
            new_name="price",
        ),
        migrations.AlterField(
            model_name="subscriptionplan",
            name="price",
            field=models.DecimalField(
                decimal_places=2, max_digits=12,
                help_text="Shu muddat uchun TO'LIQ summa.", verbose_name="Narx",
            ),
        ),
        migrations.AddField(
            model_name="subscriptionplan",
            name="duration_months",
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text="Reja necha oyga amal qiladi. 1 = oylik, 3 = choraklik.",
                verbose_name="Muddat (oy)",
            ),
        ),
        migrations.AlterModelOptions(
            name="subscriptionplan",
            options={
                "ordering": ["business_type", "duration_months"],
                "verbose_name": "Tarif rejasi",
                "verbose_name_plural": "Tarif rejalari",
            },
        ),
        migrations.AddConstraint(
            model_name="subscriptionplan",
            constraint=models.UniqueConstraint(
                fields=("business_type", "duration_months"),
                name="uniq_plan_type_duration",
            ),
        ),
    ]
