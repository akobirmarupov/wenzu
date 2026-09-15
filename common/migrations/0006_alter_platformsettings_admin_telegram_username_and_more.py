"""Platformaning aloqa ma'lumoti — poyloqda va ariza oqimida shu ko'rinadi."""

from django.db import migrations, models


def fill_contacts(apps, schema_editor):
    """
    Mavjud yozuvni ham yangilaydi.

    `AlterField` dagi yangi standart qiymat faqat YANGI yozuvga
    tegadi, bazada esa allaqachon eski "uvente" turibdi — poyloqdagi
    Telegram JS orqali aynan o'sha yozuvdan to'ldiriladi.

    Admin panelda o'z qiymatini kiritgan bo'lsa TEGILMAYDI: faqat eski
    standart qiymat va bo'sh telefon almashtiriladi.
    """
    PlatformSettings = apps.get_model("common", "PlatformSettings")
    PlatformSettings.objects.filter(admin_telegram_username="uvente").update(
        admin_telegram_username="akobir_marupov"
    )
    PlatformSettings.objects.filter(support_phone="").update(support_phone="+998771210418")


def unfill_contacts(apps, schema_editor):
    PlatformSettings = apps.get_model("common", "PlatformSettings")
    PlatformSettings.objects.filter(admin_telegram_username="akobir_marupov").update(
        admin_telegram_username="uvente"
    )
    PlatformSettings.objects.filter(support_phone="+998771210418").update(support_phone="")


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0005_feedback'),
    ]

    operations = [
        migrations.AlterField(
            model_name='platformsettings',
            name='admin_telegram_username',
            field=models.CharField(default='akobir_marupov', help_text="@ belgisiz kiriting. Business ariza/to'lov oqimida foydalanuvchiga shu ko'rsatiladi.", max_length=32),
        ),
        migrations.AlterField(
            model_name='platformsettings',
            name='support_phone',
            field=models.CharField(blank=True, default='+998771210418', max_length=20),
        ),
        migrations.RunPython(fill_contacts, unfill_contacts),
    ]
