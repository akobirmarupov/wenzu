"""
Banner va yangiliklar uchun boshlang'ich kontent.

Reklama hali yo'q, shuning uchun bannerda LOYIHA HAQIDAGI ma'lumot
turadi — TZ'dagi talab shunday. Reklama kelganda admin panelda shu
yozuvni tahrirlaydi yoki yangisini qo'shadi.
"""

import io

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from content.models import Banner, News

# ===================================================================
# Kirish sahifasining CHAP tomonidagi surat.
#
# Fayl ATAYLAB nomi bilan qattiq yozilgan, qidiruv orqali emas: qidiruv
# natijasi bugun bir xil, ertaga boshqacha kelishi mumkin va tanlanmagan
# kadrda restoran nomi yoki brend yozuvi chiqib qolishi mumkin. Bu kadr
# esa ko'rib tanlangan — yozuvsiz, tik (chap ustunga mos), yorug' va
# tiniq, yog'och-bej ohangi loyihaning oltin aksentiga yopishadi.
#
# Litsenziya: CC BY 2.0, muallif Shixart1985 (Wikimedia Commons).
# ===================================================================
AUTH_PHOTO = (
    "File:Table set for dining in a modern restaurant interior "
    "with wooden walls and elegant decor.jpg"
)

BANNERS = [
    {
        "title_uz": "WENZU — joyni oldindan band qiling",
        "title_ru": "WENZU — бронируйте заранее",
        "title_en": "WENZU — book your place ahead",
        "subtitle_uz": "Platforma haqida",
        "subtitle_ru": "О платформе",
        "subtitle_en": "About the platform",
        "body_uz": "Toshkentdagi restoran va to'yxonalarni bir joyda ko'ring, "
                   "bo'sh vaqtni real vaqtda tekshiring va bir necha bosishda bron qiling. "
                   "Depozit to'lovi Telegram orqali, tasdiqlashni esa joy egasi qiladi.",
        "body_ru": "Смотрите рестораны и свадебные залы Ташкента в одном месте, "
                   "проверяйте свободное время в реальном времени и бронируйте в пару кликов. "
                   "Депозит оплачивается через Telegram, подтверждает владелец заведения.",
        "body_en": "Browse Tashkent restaurants and wedding venues in one place, check live "
                   "availability and book in a few taps. The deposit is paid via Telegram and "
                   "the venue owner confirms your booking.",
        "cta_label_uz": "Joy qidirish",
        "cta_label_ru": "Найти место",
        "cta_label_en": "Find a place",
        "cta_url": "/restoranlar/",
        "order": 0,
    },
    {
        "title_uz": "Biznesingizni WENZU'ga qo'shing",
        "title_ru": "Добавьте свой бизнес в WENZU",
        "title_en": "Add your business to WENZU",
        "subtitle_uz": "Biznes egalariga",
        "subtitle_ru": "Владельцам бизнеса",
        "subtitle_en": "For business owners",
        "body_uz": "Restoran yoki to'yxonangiz platformada ko'rinadi, mijozlar to'g'ridan-to'g'ri "
                   "sizni bron qiladi. Boshlanishiga 7 kun mutlaqo bepul — to'lovsiz sinab ko'rasiz.",
        "body_ru": "Ваш ресторан или зал появится на платформе, клиенты будут бронировать напрямую. "
                   "Первые 7 дней бесплатно — попробуйте без оплаты.",
        "body_en": "Your restaurant or venue goes live on the platform and customers book you directly. "
                   "The first 7 days are completely free — try it with no payment.",
        "cta_label_uz": "Ariza yuborish",
        "cta_label_ru": "Оставить заявку",
        "cta_label_en": "Apply now",
        "cta_url": "/biznes-ochish/",
        "order": 1,
    },
]

# Kirish/ro'yxatdan o'tish sahifasining CHAP tomoni.
#
# Bu ham banner: admin "Kontent → Bannerlar"da rasm yuklasa, kirish
# sahifasining chap yarmi o'sha suratga aylanadi. Rasm yuklanmasa —
# standart zumrad gradient qoladi va faqat matn almashadi.
AUTH_BANNER = {
    "title_uz": "Joyni *oldindan* band qiling",
    "title_ru": "Бронируйте место *заранее*",
    "title_en": "Book your place *ahead*",
    "subtitle_uz": "Toshkent · Restoran va to'yxonalar",
    "subtitle_ru": "Ташкент · Рестораны и залы",
    "subtitle_en": "Tashkent · Restaurants and venues",
    "body_uz": "Bo'sh vaqtni real vaqtda ko'ring, bir necha bosishda bron qiling "
               "va navbatda turmang.",
    "body_ru": "Смотрите свободное время в реальном времени, бронируйте в пару "
               "кликов и не стойте в очереди.",
    "body_en": "See live availability, book in a few taps and skip the queue.",
    "order": 0,
}

NEWS = [
    {
        "category": News.CATEGORY_UPDATE,
        "is_pinned": True,
        "title_uz": "Platforma uch tilda ishlaydi",
        "title_ru": "Платформа работает на трёх языках",
        "title_en": "The platform now speaks three languages",
        "excerpt_uz": "O'zbek, rus va ingliz tillari qo'shildi — tilni yon menyudan almashtiring.",
        "excerpt_ru": "Добавлены узбекский, русский и английский — язык меняется в боковом меню.",
        "excerpt_en": "Uzbek, Russian and English are live — switch the language in the side menu.",
    },
    {
        "category": News.CATEGORY_TIP,
        "title_uz": "To'y sanasini oldindan tanlang",
        "title_ru": "Выбирайте дату свадьбы заранее",
        "title_en": "Pick your wedding date early",
        "excerpt_uz": "To'yxonada bir kunda faqat bitta to'y bo'ladi — mavsumda sanalar tez band bo'ladi.",
        "excerpt_ru": "В зале проходит только одна свадьба в день — в сезон даты разбирают быстро.",
        "excerpt_en": "A venue hosts just one wedding per day — in season the dates go fast.",
    },
    {
        "category": News.CATEGORY_TIP,
        "title_uz": "Depozit qanday ishlaydi?",
        "title_ru": "Как работает депозит?",
        "title_en": "How the deposit works",
        "excerpt_uz": "Restoranda depozit ovqatlanganingizga qo'shiladi — ya'ni pul yo'qolmaydi.",
        "excerpt_ru": "В ресторане депозит засчитывается в счёт заказа — деньги не пропадают.",
        "excerpt_en": "At a restaurant the deposit is applied to your bill — the money is not lost.",
    },
    {
        "category": News.CATEGORY_NEWS,
        "title_uz": "Yangi joylar har hafta qo'shilmoqda",
        "title_ru": "Новые заведения добавляются каждую неделю",
        "title_en": "New places join every week",
        "excerpt_uz": "Bosh sahifadagi karuselda eng so'nggi qo'shilgan joylar ko'rinadi.",
        "excerpt_ru": "В карусели на главной показаны недавно добавленные места.",
        "excerpt_en": "The carousel on the home page highlights the newest additions.",
    },
    {
        "category": News.CATEGORY_EVENT,
        "title_uz": "Kuz mavsumi: to'y bronlari ochildi",
        "title_ru": "Осенний сезон: бронь свадеб открыта",
        "title_en": "Autumn season: wedding bookings are open",
        "excerpt_uz": "Sentyabr–noyabr oylari uchun zallar jadvali to'ldirildi.",
        "excerpt_ru": "Расписание залов на сентябрь–ноябрь уже заполнено.",
        "excerpt_en": "Hall schedules for September–November are now filled in.",
    },
    {
        "category": News.CATEGORY_TIP,
        "title_uz": "Sharh faqat tashrifdan keyin",
        "title_ru": "Отзыв — только после визита",
        "title_en": "Reviews come after the visit",
        "excerpt_uz": "Sharhni faqat yakunlangan bron egasi qoldiradi — reyting shuning uchun ishonchli.",
        "excerpt_ru": "Отзыв оставляет только тот, чья бронь завершена — поэтому рейтингу можно верить.",
        "excerpt_en": "Only guests with a completed booking can review — that keeps ratings honest.",
    },
]


class Command(BaseCommand):
    help = "Banner va yangiliklar uchun boshlang'ich kontent yaratadi."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Avval eskisini o'chiradi")
        parser.add_argument(
            "--no-photo", action="store_true",
            help="Kirish sahifasi suratini yuklamaydi (internet talab qilmaydi).",
        )
        parser.add_argument(
            "--replace-photo", action="store_true",
            help="Surat allaqachon bo'lsa ham qaytadan yuklaydi.",
        )

    def handle(self, *args, **options):
        auth_banner, counts = self._write_content(options["clear"])

        self.stdout.write(self.style.SUCCESS(
            f"Kontent tayyor: {counts['banners']} ta banner, {counts['news']} ta yangilik."
        ))

        # Surat TRANZAKSIYADAN TASHQARIDA yuklanadi: tarmoq sekin bo'lsa
        # ochiq tranzaksiya bazani bekorga qulflab turardi.
        if not options["no_photo"]:
            self._attach_auth_photo(auth_banner, replace=options["replace_photo"])

        self.stdout.write(
            "\nTahrirlash: /admin/content/banner/ va /admin/content/news/\n"
            "Kirish sahifasi suratini almashtirish: joylashuvi \"Kirish sahifasi\" "
            "bo'lgan bannerga o'z rasmingizni yuklang."
        )

    @transaction.atomic
    def _write_content(self, clear):
        if clear:
            Banner.objects.all().delete()
            News.objects.all().delete()
            self.stdout.write(self.style.WARNING("Eski kontent o'chirildi"))

        banners = 0
        for data in BANNERS:
            _, created = Banner.objects.get_or_create(
                title_uz=data["title_uz"],
                defaults={**data, "placement": Banner.PLACEMENT_HERO,
                          "media_type": Banner.MEDIA_NONE, "is_active": True},
            )
            banners += int(created)

        # Kirish sahifasi banneri — alohida joylashuvda.
        auth_banner, created = Banner.objects.get_or_create(
            title_uz=AUTH_BANNER["title_uz"],
            placement=Banner.PLACEMENT_AUTH,
            defaults={**AUTH_BANNER, "placement": Banner.PLACEMENT_AUTH,
                      "media_type": Banner.MEDIA_NONE, "is_active": True},
        )
        banners += int(created)

        news = 0
        for index, data in enumerate(NEWS):
            _, created = News.objects.get_or_create(
                title_uz=data["title_uz"],
                defaults={**data, "order": index, "is_active": True},
            )
            news += int(created)

        return auth_banner, {"banners": banners, "news": news}

    def _attach_auth_photo(self, banner, *, replace):
        """
        Kirish sahifasining chap tomoniga restoran suratini qo'yadi.

        Surat allaqachon bo'lsa TEGILMAYDI — admin o'z rasmini yuklagan
        bo'lishi mumkin, uni har `seed_content` da bosib ketish noto'g'ri
        bo'lardi. Ataylab almashtirish uchun `--replace-photo` bor.
        """
        if banner.image and not replace:
            self.stdout.write("Kirish sahifasi surati allaqachon bor — tegilmadi.")
            return

        from common.management.commands._commons import fetch_file

        self.stdout.write("Kirish sahifasi surati yuklanmoqda...")
        data, meta = fetch_file(AUTH_PHOTO, width=1800)
        if data is None:
            self.stdout.write(self.style.WARNING(
                "  yuklab bo'lmadi — standart gradient qoladi (sahifa baribir ishlaydi)."
            ))
            return

        # Qayta siqamiz: manba 800 KB atrofida, sifatni deyarli yo'qotmasdan
        # ancha yengillashtirsa bo'ladi. Kenglik saqlanadi — surat "juda
        # tiniq" bo'lishi kerak, shuning uchun kichraytirilmaydi.
        try:
            from PIL import Image

            image = Image.open(io.BytesIO(data)).convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=88, optimize=True, progressive=True)
            data = buffer.getvalue()
            size = f"{image.width}x{image.height}"
        except Exception:  # noqa: BLE001 — siqilmasa ham asl fayl yaraydi
            size = "?"

        banner.media_type = Banner.MEDIA_IMAGE
        banner.image.save("auth-restaurant.jpg", ContentFile(data), save=True)

        self.stdout.write(self.style.SUCCESS(
            f"  qo'yildi: {size}, {len(data)//1024} KB\n"
            f"  manba: {meta['title']}\n"
            f"  litsenziya: {meta['license']} — {meta['author']}"
        ))
