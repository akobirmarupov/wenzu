"""
Wikimedia Commons'dan demo uchun HAQIQIY surat oladi.

Nega Commons: bu yerdagi fayllar erkin litsenziyali (CC / public domain),
ya'ni demo loyihada ishlatish qonuniy. Tasodifiy "placeholder" xizmatlardan
farqi — surat MAVZUGA mos keladi: osh so'ralsa oshning o'zi, to'yxona
so'ralsa to'yxona zali chiqadi.

Ikki muhim tafsilot:

  · KESH. Har bir surat `media/_demo_cache/` ga saqlanadi. Seeder qayta
    ishga tushirilganda fayllar qaytadan yuklanmaydi — Commons serveriga
    ortiqcha yuk bermaymiz va internetsiz ham ishlayveradi.

  · MUALLIFLIK. Har bir faylning manbasi va litsenziyasi
    `media/_demo_cache/manifest.json` ga yoziladi. Demo suratlarni
    haqiqiysiga almashtirganda bu fayl ham keraksiz bo'ladi.

Internet bo'lmasa modul jimgina bo'sh ro'yxat qaytaradi — seeder
suratsiz davom etadi, yiqilmaydi.
"""

import json
import logging
import urllib.parse
import urllib.request
from pathlib import Path

from django.conf import settings

logger = logging.getLogger("common")

API = "https://commons.wikimedia.org/w/api.php"

# Commons qoidasi: har bir mijoz o'zini tanishtirishi kerak.
USER_AGENT = "WENZU-demo-seeder/1.0 (https://wenzu.uz; student project) python-urllib"

TIMEOUT = 25
CACHE_DIR = Path(settings.MEDIA_ROOT) / "_demo_cache"
MANIFEST = CACHE_DIR / "manifest.json"


def _load_manifest():
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save_manifest(data):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def _fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read()


def search(term, limit=6, width=1400):
    """
    Commons'da rasm qidiradi.

    Qaytaradi: [{title, url, license, author}]. Xato bo'lsa — bo'sh ro'yxat.
    `filetype:bitmap` — SVG va PDF'larni chetlab o'tadi (ular kadr sifatida
    yaramaydi).
    """
    query = urllib.parse.urlencode({
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"filetype:bitmap {term}",
        "gsrlimit": limit,
        "gsrnamespace": 6,           # faqat File: makon nomi
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": width,         # katta originalni emas, kichraytirilganini olamiz
    })

    try:
        payload = json.loads(_fetch(f"{API}?{query}"))
    except Exception as error:  # noqa: BLE001 — internet yo'qligi ham shu yerga tushadi
        logger.warning(f"Commons qidiruvi ishlamadi ({term}): {error}")
        return []

    pages = payload.get("query", {}).get("pages", {})
    found = []
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        meta = info.get("extmetadata", {})
        found.append({
            "title": page.get("title", ""),
            "url": url,
            "license": meta.get("LicenseShortName", {}).get("value", "?"),
            "author": _strip_html(meta.get("Artist", {}).get("value", "")),
            "page": f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(page.get('title', ''))}",
        })
    return found


def _strip_html(value):
    """Commons muallif maydonida HTML bo'ladi — sodda matnga aylantiramiz."""
    out, inside = [], False
    for char in value:
        if char == "<":
            inside = True
        elif char == ">":
            inside = False
        elif not inside:
            out.append(char)
    return " ".join("".join(out).split())[:150]


def collect(term, count, *, cache_key):
    """
    Bir mavzu bo'yicha `count` ta suratni yuklab oladi (yoki keshdan beradi).

    @param cache_key: fayl nomi uchun qisqa belgi, masalan "osh".
    @returns: [Path] — diskdagi fayllar ro'yxati.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest()

    # Avval keshda bormi?
    cached = sorted(CACHE_DIR.glob(f"{cache_key}-*.jpg"))
    if len(cached) >= count:
        return cached[:count]

    results = search(term, limit=count + 4)
    files = list(cached)

    for index, item in enumerate(results):
        if len(files) >= count:
            break
        path = CACHE_DIR / f"{cache_key}-{index}.jpg"
        if path.exists():
            if path not in files:
                files.append(path)
            continue
        try:
            path.write_bytes(_fetch(item["url"]))
        except Exception as error:  # noqa: BLE001
            logger.warning(f"Surat yuklanmadi ({item['title']}): {error}")
            continue

        manifest[path.name] = {
            "term": term,
            "title": item["title"],
            "license": item["license"],
            "author": item["author"],
            "source": item["page"],
        }
        files.append(path)

    _save_manifest(manifest)
    return files[:count]


def fetch_file(title, width=1920):
    """
    ANIQ bitta faylni nomi bo'yicha oladi.

    `search()` dan farqi: natija tasodifiy emas. Kirish sahifasidagi
    surat kabi "bu aynan shu kadr bo'lsin" degan joylarda kerak —
    qidiruv natijasi bugun bir xil, ertaga boshqacha kelishi mumkin,
    va tanlanmagan kadrda yozuv yoki brend chiqib qolishi mumkin.

    @param title: "File:...jpg" ko'rinishidagi to'liq nom.
    @returns: (baytlar, ma'lumot) yoki (None, None).
    """
    query = urllib.parse.urlencode({
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
        "iiurlwidth": width,
    })

    try:
        payload = json.loads(_fetch(f"{API}?{query}"))
        page = next(iter(payload["query"]["pages"].values()))
        info = page["imageinfo"][0]
        meta = info.get("extmetadata", {})
        data = _fetch(info.get("thumburl") or info["url"])
    except Exception as error:  # noqa: BLE001
        logger.warning(f"Commons fayli olinmadi ({title}): {error}")
        return None, None

    return data, {
        "title": title,
        "license": meta.get("LicenseShortName", {}).get("value", "?"),
        "author": _strip_html(meta.get("Artist", {}).get("value", "")),
        "source": f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(title)}",
    }
