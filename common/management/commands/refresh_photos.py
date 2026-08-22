"""
Demo suratlarining bir qismini qayta yuklaydi.

Nega alohida buyruq: `seed_demo` butun ma'lumotni qayta yaratadi
(`--clear`), ya'ni bronlar va sharhlar ham yo'qoladi. Aslida esa ko'pincha
faqat bir nechta surat noto'g'ri chiqadi — masalan Commons'da "lemonade"
so'roviga XIX asr rasmi, "plov"ga esa oshxona jarayoni chiqib qoladi.

Bu buyruq faqat KO'RSATILGAN mavzularni qaytadan yuklaydi va o'sha
mavzuga tegishli taomlarning rasmini almashtiradi. Qolgan hamma narsa
joyida qoladi.

Ishlatish:
    python manage.py refresh_photos --list
    python manage.py refresh_photos plov ayran lemonade
    python manage.py refresh_photos --all-food
"""


from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from catalog.models import RestaurantMenuItem, VenueMenuItem
from common.management.commands._commons import CACHE_DIR, collect
from common.management.commands.seed_demo import PHOTO_TERMS, RESTAURANTS, VENUES


class Command(BaseCommand):
    help = "Demo suratlarining ayrim mavzularini qayta yuklaydi (bronlarga tegmaydi)."

    def add_arguments(self, parser):
        parser.add_argument("keys", nargs="*", help="Mavzu kalitlari, masalan: plov ayran")
        parser.add_argument("--list", action="store_true", help="Mavjud kalitlarni ko'rsatadi")
        parser.add_argument("--all-food", action="store_true", help="Barcha taom mavzulari")
        parser.add_argument("--count", type=int, default=3, help="Har mavzuga nechta surat")

    def handle(self, *args, **options):
        if options["list"]:
            for key, term in sorted(PHOTO_TERMS.items()):
                self.stdout.write(f"  {key:20} → {term}")
            return

        keys = set(options["keys"])
        if options["all_food"]:
            keys |= self._food_keys()

        unknown = keys - set(PHOTO_TERMS)
        if unknown:
            self.stdout.write(self.style.ERROR(
                f"Noma'lum kalit: {', '.join(sorted(unknown))}\n"
                f"Ro'yxatni ko'rish: python manage.py refresh_photos --list"
            ))
            return
        if not keys:
            self.stdout.write(self.style.WARNING(
                "Kalit ko'rsatilmadi. Misol: python manage.py refresh_photos plov ayran"
            ))
            return

        # Qaysi taom qaysi mavzuga tegishli — nomlar bo'yicha xarita.
        by_key = self._menu_index()
        total = 0

        for key in sorted(keys):
            self._drop_cache(key)
            files = collect(PHOTO_TERMS[key], options["count"], cache_key=key)
            if not files:
                self.stdout.write(self.style.WARNING(f"  {key}: surat topilmadi"))
                continue

            names = by_key.get(key, set())
            changed = self._reassign(names, files)
            total += changed
            self.stdout.write(
                f"  {key:20} {len(files)} ta surat → {changed} ta taom yangilandi"
            )

        self.stdout.write(self.style.SUCCESS(f"\nTayyor: {total} ta taom rasmi almashtirildi."))

    # ---------------- yordamchilar ----------------
    def _food_keys(self):
        keys = {item[3] for data in RESTAURANTS for item in data["menu"]}
        keys |= {item[2] for data in VENUES for item in data["menu"]}
        return keys

    def _menu_index(self):
        """{mavzu kaliti: {taom nomlari}} — rasmni kimga qo'yishni bilish uchun."""
        index = {}
        for data in RESTAURANTS:
            for name, _category, _price, key in data["menu"]:
                index.setdefault(key, set()).add(name)
        for data in VENUES:
            for name, _category, key in data["menu"]:
                index.setdefault(key, set()).add(name)
        return index

    def _drop_cache(self, key):
        """Eski keshni tozalaymiz — aks holda `collect` o'shani qaytaradi."""
        for path in CACHE_DIR.glob(f"{key}-*.jpg"):
            path.unlink(missing_ok=True)

    def _reassign(self, names, files):
        if not names:
            return 0

        changed = 0
        for model in (RestaurantMenuItem, VenueMenuItem):
            for index, item in enumerate(model.objects.filter(name__in=names)):
                source = files[index % len(files)]
                item.photo.save(
                    f"{item.id}.jpg", ContentFile(source.read_bytes()), save=True
                )
                changed += 1
        return changed
