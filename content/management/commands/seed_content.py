"""
Banner va yangiliklar uchun boshlang'ich kontent.

Reklama hali yo'q, shuning uchun bannerda LOYIHA HAQIDAGI ma'lumot
turadi — TZ'dagi talab shunday. Reklama kelganda admin panelda shu
yozuvni tahrirlaydi yoki yangisini qo'shadi.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from content.models import Banner, News

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
        "cta_url": "/profil/?tab=business",
        "order": 1,
    },
]

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

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"]:
            Banner.objects.all().delete()
            News.objects.all().delete()
            self.stdout.write(self.style.WARNING("Eski kontent o'chirildi"))

        created_banners = 0
        for data in BANNERS:
            _, created = Banner.objects.get_or_create(
                title_uz=data["title_uz"],
                defaults={**data, "placement": Banner.PLACEMENT_HERO,
                          "media_type": Banner.MEDIA_NONE, "is_active": True},
            )
            created_banners += int(created)

        created_news = 0
        for index, data in enumerate(NEWS):
            _, created = News.objects.get_or_create(
                title_uz=data["title_uz"],
                defaults={**data, "order": index, "is_active": True},
            )
            created_news += int(created)

        self.stdout.write(self.style.SUCCESS(
            f"Kontent tayyor: {created_banners} ta banner, {created_news} ta yangilik.\n"
            f"Tahrirlash: /admin/content/banner/ va /admin/content/news/"
        ))
