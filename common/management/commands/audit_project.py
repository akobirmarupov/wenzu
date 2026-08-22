"""
Loyihaning YAXLITLIK tekshiruvi.

Testlar kodning ishlashini tekshiradi; bu buyruq esa BOG'LANISHLARNI:
o'chirilgan sahifaga qolgan havola, tarjimasi yozilmagan kalit,
aniqlanmagan CSS klassi, mavjud bo'lmagan API endpointi.

Bunday uzilishlarni testlar ushlamaydi — ular odatda foydalanuvchi 404
ko'rganda yoki ekranda tarjima o'rniga kalit chiqqanda bilinadi.

Ishlatish:
    python manage.py audit_project

Deploy oldidan `python manage.py test` bilan birga ishlatish tavsiya etiladi.
"""

import json
import re
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.urls import get_resolver

# Django admin shablonlari Tailwind ishlatadi — ularning klasslari
# loyiha CSS'ida bo'lmasligi normal.
SKIP_FILES = {"templates/admin/reservations/availability/generate_form.html"}

# JS tomonidan ish paytida o'rnatiladigan yoki tashqi tizim tokenlari.
RUNTIME_TOKENS = {"auth-photo", "color-primary-600"}

# Lug'atlarni Node orqali o'qiymiz — qo'lda yozilgan parser ichma-ich
# obyektlarda adashib, yo'q muammolarni ko'rsatardi.
DUMP_I18N = """
const out = {};
for (const lang of ['uz','ru','en']) {
  const mod = await import('./static/js/i18n/' + lang + '.js');
  const keys = [];
  const walk = (obj, prefix='') => {
    for (const [k, v] of Object.entries(obj)) {
      if (v && typeof v === 'object') walk(v, prefix + k + '.');
      else keys.push(prefix + k);
    }
  };
  walk(mod.default);
  out[lang] = keys;
}
console.log(JSON.stringify(out));
"""


def strip_comments(text):
    """
    Izohlarni olib tashlaydi.

    Kerak, chunki izohlarda ham namuna sifatida `data-i18n="kalit"` kabi
    yozuvlar uchraydi va ular "tarjimasi yo'q" bo'lib ko'rinardi.
    """
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
    text = re.sub(r"\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}", "", text, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)


class Command(BaseCommand):
    help = "Havola, tarjima, CSS va API bog'lanishlarining yaxlitligini tekshiradi."

    def handle(self, *args, **options):
        self.base = Path(settings.BASE_DIR)
        self.failures = []
        self.checks = 0

        self.routes = set()
        self._collect_routes(get_resolver().url_patterns)

        self._check_links()
        self._check_api()
        self._check_assets()
        self._check_i18n()
        self._check_css()
        self._check_postman()

        self.stdout.write("\n" + "=" * 60)
        if self.failures:
            raise CommandError(
                f"{len(self.failures)} bo'limda muammo topildi "
                f"({self.checks} tekshiruvdan)."
            )
        self.stdout.write(
            self.style.SUCCESS(f"{self.checks} tekshiruvning hammasi toza")
        )

    # ---------------- yordamchilar ----------------
    def _report(self, name, items):
        self.checks += 1
        if not items:
            self.stdout.write(f"  ✓ {name}")
            return

        self.failures.append(name)
        self.stdout.write(self.style.ERROR(f"  ✗ {name}: {len(items)} ta"))
        for item in sorted(items)[:12]:
            self.stdout.write(f"      {item}")
        if len(items) > 12:
            self.stdout.write(f"      … yana {len(items) - 12} ta")

    def _collect_routes(self, patterns, prefix=""):
        for pattern in patterns:
            if hasattr(pattern, "url_patterns"):
                self._collect_routes(pattern.url_patterns, prefix + str(pattern.pattern))
            else:
                self.routes.add("/" + prefix + str(pattern.pattern))

    @staticmethod
    def _to_regex(route):
        # `^media/(?P<path>.*)$` kabilar allaqachon naqsh — tegmaymiz.
        if "(?P<" in route:
            return route.lstrip("/")
        return "^" + re.sub(r"<[^>]+>", "[^/]+", route.rstrip("$")) + "$"

    def _route_exists(self, path, only_api=False):
        path = path.split("?")[0].split("#")[0]
        routes = {r for r in self.routes if r.startswith("/api/")} if only_api else self.routes
        for route in routes:
            try:
                regex = self._to_regex(route)
                if re.match(regex, path) or re.match(regex, path.lstrip("/")):
                    return True
            except re.error:
                continue
        return False

    def _source_files(self, *patterns):
        for pattern in patterns:
            yield from self.base.glob(pattern)

    # ---------------- tekshiruvlar ----------------
    def _check_links(self):
        self.stdout.write("\n1. SAHIFA HAVOLALARI")

        broken = set()
        for path in self._source_files("templates/**/*.html", "static/js/**/*.js"):
            for href in re.findall(r'href="(/[^"{}\s]*)"', path.read_text()):
                if not self._route_exists(href):
                    broken.add(f"{path.relative_to(self.base)} → {href}")
        self._report("Shablon/JS ichidagi ichki havolalar", broken)

        config = (self.base / "static/js/core/config.js").read_text()
        bad = {
            f"ROUTES.{name} → {value}"
            for name, value in re.findall(r'^\s*(\w+):\s*"(/[^"]*)"', config, re.MULTILINE)
            if not self._route_exists(value)
        }
        self._report("ROUTES dagi manzillar", bad)

    def _check_api(self):
        self.stdout.write("\n2. API ENDPOINTLARI")

        text = (self.base / "static/js/core/api.js").read_text()
        broken = set()
        for call in re.findall(r'http\.\w+\(\s*[`"]([^`"]+)[`"]', text):
            normalized = "/api" + re.sub(r"\$\{[^}]+\}", "x", call).split("?")[0]
            if not self._route_exists(normalized, only_api=True):
                broken.add(call)
        self._report("api.js dagi endpointlar", broken)

    def _check_assets(self):
        self.stdout.write("\n3. FAYLLAR")

        broken = set()
        for path in self.base.glob("static/js/**/*.js"):
            text = path.read_text()
            specs = re.findall(r'from\s+"([^"]+)"', text)
            specs += re.findall(r'import\("([^"]+)"\)', text)
            for spec in specs:
                if spec.startswith(".") and not (path.parent / spec).resolve().exists():
                    broken.add(f"{path.relative_to(self.base)} → {spec}")
        self._report("Modul importlari", broken)

        missing = set()
        for path in self.base.glob("templates/**/*.html"):
            for name in re.findall(r"\{% static '([^']+)' %\}", path.read_text()):
                if not (self.base / "static" / name).exists():
                    missing.add(f"{path.relative_to(self.base)} → {name}")
        self._report("Shablondagi {% static %} fayllari", missing)

        from web.context_processors import STYLESHEETS

        listed = set(STYLESHEETS)
        self._report(
            "STYLESHEETS ro'yxatidagi fayllar",
            {s for s in listed if not (self.base / "static" / s).exists()},
        )
        # Ro'yxatga tushmagan CSS umuman yuklanmaydi — jimgina yo'qoladi.
        self._report(
            "Ro'yxatga kirmagan CSS fayllari",
            {
                str(p.relative_to(self.base / "static"))
                for p in (self.base / "static/css").rglob("*.css")
                if str(p.relative_to(self.base / "static")) not in listed
            },
        )

    def _check_i18n(self):
        self.stdout.write("\n4. TARJIMALAR")

        dump = subprocess.run(
            ["node", "--input-type=module", "-e", DUMP_I18N],
            capture_output=True, text=True, cwd=self.base, check=True,
        )
        dictionaries = {lang: set(keys) for lang, keys in json.loads(dump.stdout).items()}

        used = set()
        for path in self._source_files("static/js/**/*.js", "templates/**/*.html"):
            text = strip_comments(path.read_text())
            # `(?<![\w$.])` — `parseInt(`, `split(`, `.at(` chalkashmasin.
            used |= set(re.findall(r'(?<![\w$.])t\(\s*"([\w.]+)"', text))
            used |= set(re.findall(r'data-i18n(?:-\w+)?="([\w.]+)"', text))

        self._report("Ishlatilgan, lekin o'zbekchada yo'q kalitlar", used - dictionaries["uz"])
        for lang in ("ru", "en"):
            self._report(f"O'zbekchada bor, {lang} da yo'q", dictionaries["uz"] - dictionaries[lang])
            self._report(f"{lang} da bor, o'zbekchada yo'q", dictionaries[lang] - dictionaries["uz"])

        # Ishlatilmaydiganlari — faqat eslatma, xato emas: bir qism
        # kalitlar kod ichida hisoblab yasaladi (`t(\`premium.how${n}\`)`)
        # va bu qidiruvga tushmaydi.
        unused = dictionaries["uz"] - used
        if unused:
            self.stdout.write(f"  · eslatma: {len(unused)} ta kalit qidiruvda uchramadi")

    def _check_css(self):
        self.stdout.write("\n5. CSS")

        defined = set()
        for path in (self.base / "static/css").rglob("*.css"):
            defined |= set(re.findall(r"\.([a-zA-Z][\w-]*)", path.read_text()))

        used = {}
        for path in self._source_files("templates/**/*", "static/js/**/*"):
            if path.suffix not in (".html", ".js"):
                continue
            if str(path.relative_to(self.base)) in SKIP_FILES:
                continue
            for group in re.findall(r'class="([^"$`{}]*)"', path.read_text()):
                for token in group.split():
                    used.setdefault(token, set()).add(str(path.relative_to(self.base)))

        self._report(
            "CSS'da aniqlanmagan klasslar",
            {
                f"{name}  ({', '.join(sorted(where)[:2])})"
                for name, where in used.items()
                if name not in defined
            },
        )

        tokens_defined = set(
            re.findall(r"--([\w-]+):", (self.base / "static/css/base/_tokens.css").read_text())
        )
        tokens_used = set()
        for path in self._source_files("static/css/**/*", "static/js/**/*", "templates/**/*"):
            if path.is_file() and path.suffix in (".css", ".js", ".html"):
                tokens_used |= set(re.findall(r"var\(--([\w-]+)", path.read_text()))
        self._report(
            "Aniqlanmagan CSS tokenlari", (tokens_used - tokens_defined) - RUNTIME_TOKENS
        )

    def _check_postman(self):
        self.stdout.write("\n6. POSTMAN")

        collection = json.loads(
            (self.base / "postman/WENZU.postman_collection.json").read_text()
        )
        covered = set()

        def walk(items):
            for item in items:
                if "item" in item:
                    walk(item["item"])
                    continue
                url = item["request"]["url"]
                raw = url["raw"] if isinstance(url, dict) else url
                raw = raw.replace("{{base_url}}", "").split("?")[0]
                covered.add("/" + re.sub(r"\{\{[^}]+\}\}", "{}", raw).strip("/") + "/")

        walk(collection["item"])
        api = {
            "/" + re.sub(r"<[^>]+>", "{}", r).strip("/") + "/"
            for r in self.routes
            if r.startswith("/api/")
        }
        self._report("Postmanda qoplanmagan endpointlar", api - covered)
