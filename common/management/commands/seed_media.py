"""
Demo uchun rasm generatsiyasi.

Nega kerak: bosh sahifadagi rasm lentasi, menyu vitrinasi va detal
sahifasidagi galereya — hammasi SURATGA tayanadi. Bazada esa bitta
surat bor edi, shuning uchun bu bo'limlar bo'sh chiqardi va loyihani
ko'rsatib bo'lmasdi.

Bu buyruq HAQIQIY fotosurat qo'ymaydi (ularni joy egasi o'zi yuklaydi) —
har bir joy va taom uchun uning nomi yozilgan chiroyli gradient kadr
chizadi. Shunda tuzilma va animatsiyalar ko'rinadi, keyin esa har bir
rasmni panelidan haqiqiysiga almashtirish kifoya.

Ishlatish:
    python manage.py seed_media              # faqat rasmi yo'qlarga
    python manage.py seed_media --force      # borini ham qayta chizadi
"""

import io
import random

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from businesses.models import Business, BusinessPhoto, Hall, Room
from catalog.models import RestaurantMenuItem, VenueMenuItem

# Brend palitrasi: zumrad, oltin va to'q ko'k. Har bir kadr shu
# ranglardan ikkitasi orasidagi gradient bo'ladi — sayt bilan bitta
# ohangda turadi.
PALETTES = [
    ((8, 50, 42), (18, 119, 95)),      # zumrad
    ((10, 17, 28), (27, 127, 168)),    # tungi ko'k
    ((60, 38, 10), (201, 162, 39)),    # oltin
    ((26, 20, 5), (176, 96, 58)),      # terrakota
    ((36, 25, 48), (107, 68, 137)),    # siyoh binafsha
    ((6, 31, 26), (34, 165, 131)),     # yashil choy
]

# Har bir surat turi uchun o'z o'lchami — kartochkalar bir xil
# nisbatda kesilishi uchun.
SIZES = {
    "cover": (1400, 875),    # 16:10 — kartochka va lenta
    "gallery": (1200, 900),  # 4:3
    "dish": (900, 675),      # 4:3 — menyu kadri
}

# Galereyada qanday ko'rinishlar bo'lishi kerak: foydalanuvchi
# "faqat kirish eshigi emas, ichkarisi ham" degan edi.
GALLERY_SCENES = [
    "Kirish",
    "Asosiy zal",
    "Yo'lak",
    "Stollar",
    "Terrasa",
    "Kechki ko'rinish",
]


def _font(size):
    """Tizimdagi mavjud shriftni topadi; topilmasa standartga qaytadi."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _gradient(size, start, end):
    """Diagonal gradient — tekis rangdan ko'ra "suratga" o'xshaydi."""
    width, height = size
    # Kichik kadr chizib, keyin kattalashtiramiz: piksel-piksel chizish
    # 1400×875 uchun sekin, natija esa aynan bir xil.
    small = Image.new("RGB", (64, 64))
    pixels = small.load()
    for y in range(64):
        for x in range(64):
            ratio = (x + y) / 126
            pixels[x, y] = tuple(
                int(start[i] + (end[i] - start[i]) * ratio) for i in range(3)
            )
    return small.resize((width, height), Image.LANCZOS)


def _texture(image, seed):
    """Yumshoq yorug'lik dog'lari — kadr yassi ko'rinmasligi uchun."""
    rng = random.Random(seed)
    width, height = image.size
    glow = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(glow)
    for _ in range(5):
        radius = rng.randint(width // 6, width // 3)
        cx = rng.randint(0, width)
        cy = rng.randint(0, height)
        tone = rng.randint(30, 70)
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=(tone, tone - 8, tone - 22),
        )
    glow = glow.filter(ImageFilter.GaussianBlur(width // 12))
    return Image.blend(image, Image.blend(image, glow, 0.5), 0.45)


def make_image(title, subtitle="", kind="cover", seed=0):
    """Nomi yozilgan bitta kadr qaytaradi (JPEG baytlari)."""
    size = SIZES[kind]
    start, end = PALETTES[seed % len(PALETTES)]

    image = _texture(_gradient(size, start, end), seed)
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = size

    # Pastdan yuqoriga qorong'i parda — matn har qanday fonda o'qiladi.
    for offset in range(height // 2):
        alpha = int(150 * (offset / (height / 2)))
        draw.line(
            [(0, height - offset), (width, height - offset)],
            fill=(0, 0, 0, alpha),
        )

    # Oltin chiziq — brend belgisi
    draw.rectangle([0, 0, width, max(4, height // 160)], fill=(201, 162, 39, 235))

    title_font = _font(max(28, width // 16))
    small_font = _font(max(16, width // 38))

    margin = width // 14
    if subtitle:
        draw.text((margin, height - margin - width // 11), subtitle.upper(),
                  font=small_font, fill=(240, 215, 133, 235))
    draw.text((margin, height - margin - width // 18), title,
              font=title_font, fill=(255, 255, 255, 245))

    # Burchakdagi kichik nuqta — logotipga ishora
    dot = width // 60
    draw.ellipse(
        [width - margin - dot, margin, width - margin, margin + dot],
        fill=(233, 206, 114, 240),
    )

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=88, optimize=True)
    return buffer.getvalue()


class Command(BaseCommand):
    help = "Demo uchun biznes muqovalari, galereya va taom rasmlarini generatsiya qiladi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force", action="store_true",
            help="Rasmi bor yozuvlarni ham qayta chizadi.",
        )
        parser.add_argument(
            "--gallery", type=int, default=5,
            help="Har bir joy uchun nechta galereya surati (standart 5).",
        )

    def handle(self, *args, **options):
        force = options["force"]
        gallery_count = max(0, min(options["gallery"], len(GALLERY_SCENES)))

        covers = self._seed_covers(force)
        gallery = self._seed_gallery(force, gallery_count)
        dishes = self._seed_dishes(force)
        rooms = self._seed_rooms_and_halls(force)

        self.stdout.write(self.style.SUCCESS(
            f"\nTayyor: {covers} muqova, {gallery} galereya surati, "
            f"{dishes} taom rasmi, {rooms} xona/zal rasmi."
        ))
        self.stdout.write(
            "Eslatma: bular DEMO kadrlar. Haqiqiy fotosuratlarni "
            "panel → Sozlamalar → Rasm galereyasi orqali yuklang."
        )

    # ---------------- muqovalar ----------------
    def _seed_covers(self, force):
        queryset = Business.objects.all()
        if not force:
            queryset = queryset.filter(cover_photo="")

        made = 0
        for index, business in enumerate(queryset):
            kind_label = "To'yxona" if business.business_type == "venue" else "Restoran"
            data = make_image(
                business.name,
                subtitle=f"{kind_label}{' · ' + business.district if business.district else ''}",
                kind="cover",
                seed=hash(str(business.id)) % 1000 + index,
            )
            business.cover_photo.save(
                f"{business.id}.jpg", ContentFile(data), save=True
            )
            made += 1
            self.stdout.write(f"  muqova: {business.name}")
        return made

    # ---------------- galereya ----------------
    def _seed_gallery(self, force, count):
        if not count:
            return 0

        made = 0
        for business in Business.objects.all():
            existing = business.photos.count()
            if existing >= count and not force:
                continue

            kind_label = "To'yxona" if business.business_type == "venue" else "Restoran"
            for order in range(existing if not force else 0, count):
                scene = GALLERY_SCENES[order % len(GALLERY_SCENES)]
                data = make_image(
                    scene,
                    subtitle=f"{business.name} · {kind_label}",
                    kind="gallery",
                    seed=hash(f"{business.id}{order}") % 1000,
                )
                photo = BusinessPhoto(business=business, order=order)
                photo.image.save(f"{business.id}-{order}.jpg", ContentFile(data), save=True)
                made += 1
            self.stdout.write(f"  galereya: {business.name} (+{count - existing})")
        return made

    # ---------------- taomlar ----------------
    def _seed_dishes(self, force):
        made = 0
        for model in (RestaurantMenuItem, VenueMenuItem):
            queryset = model.objects.select_related("business")
            if not force:
                queryset = queryset.filter(photo="")

            for index, item in enumerate(queryset):
                data = make_image(
                    item.name,
                    subtitle=item.business.name,
                    kind="dish",
                    seed=hash(str(item.id)) % 1000 + index,
                )
                item.photo.save(f"{item.id}.jpg", ContentFile(data), save=True)
                made += 1
        self.stdout.write(f"  taom rasmlari: {made}")
        return made

    # ---------------- xona va zallar ----------------
    def _seed_rooms_and_halls(self, force):
        made = 0
        for model, label in ((Room, "Xona"), (Hall, "Zal")):
            queryset = model.objects.select_related("business")
            if not force:
                queryset = queryset.filter(photo="")

            for index, item in enumerate(queryset):
                data = make_image(
                    item.name,
                    subtitle=f"{item.business.name} · {label}",
                    kind="gallery",
                    seed=hash(str(item.id)) % 1000 + index,
                )
                item.photo.save(f"{item.id}.jpg", ContentFile(data), save=True)
                made += 1
        self.stdout.write(f"  xona/zal rasmlari: {made}")
        return made
