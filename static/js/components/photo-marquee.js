/**
 * Rasm lentasi — bosh sahifa tepasidagi uzluksiz surat oqimi.
 *
 * Yozuv YO'Q: bu bo'lim ma'lumot bermaydi, platformada qanday joylar
 * borligini ko'z bilan ilg'ab olish uchun xizmat qiladi.
 *
 * ASOSIY QOIDA: bitta joyning suratlari KETMA-KET kelmaydi.
 *
 * Oddiy aralashtirish (shuffle) buni kafolatlamaydi — tasodifan bitta
 * restoranning to'rttala surati yonma-yon tushib qolishi mumkin va lenta
 * "bitta joy" haqidagi slayd-shouga o'xshab qoladi. Shuning uchun bu yerda
 * suratlar avval EGASI bo'yicha guruhlanadi, keyin navbatma-navbat
 * teriladi: 1-joy → 2-joy → 3-joy → 1-joy → ... Joylar soni qancha ko'p
 * bo'lsa, takror shuncha uzoqlashadi.
 */
import { ROUTES } from "../core/config.js";
import { esc } from "../ui/dom.js";

/** Har bir qatorda kamida shuncha kadr bo'lsin — aks holda lenta uziladi. */
const MIN_TILES = 8;

/** Fisher–Yates — `sort(() => Math.random()-0.5)` teng taqsimlamaydi. */
function shuffle(list) {
  const copy = [...list];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

/** Suratlarni egasi (biznes) bo'yicha guruhlaydi. */
function groupByOwner(photos) {
  const groups = new Map();
  photos.forEach((photo) => {
    if (!groups.has(photo.id)) groups.set(photo.id, []);
    groups.get(photo.id).push(photo);
  });
  return [...groups.entries()].map(([id, items]) => ({ id, items: shuffle(items) }));
}

/**
 * Navbatma-navbat terish.
 *
 * Har qadamda QOLGANI ENG KO'P guruhdan olinadi (lekin oldingisi bilan
 * bir xil egadan emas). "Eng ko'pi"ni tanlash muhim: aks holda ko'p
 * suratli joy oxirida yolg'iz qolib, hammasi ketma-ket tushardi.
 *
 * Agar bitta joyda qolganlarning yarmidan ko'pi bo'lsa, takrorsiz terish
 * matematik jihatdan imkonsiz — bunday holatda qolganlari ketma-ket
 * qo'yiladi (kamdan-kam holat: platformada bitta joy qolganda).
 */
function interleaveByOwner(photos) {
  const buckets = shuffle(groupByOwner(photos));
  const out = [];
  let lastOwner = null;

  for (;;) {
    let pick = null;
    for (const bucket of buckets) {
      if (!bucket.items.length || bucket.id === lastOwner) continue;
      if (!pick || bucket.items.length > pick.items.length) pick = bucket;
    }
    // Faqat oxirgi eganing suratlari qoldi — chorasiz, ketma-ket qo'yamiz.
    if (!pick) pick = buckets.find((bucket) => bucket.items.length);
    if (!pick) break;

    out.push(pick.items.pop());
    lastOwner = pick.id;
  }
  return out;
}

/**
 * Halqa chokini tuzatadi.
 *
 * Lenta uzluksiz ko'rinishi uchun ro'yxat ikki marta chiziladi, ya'ni
 * OXIRGI kadr BIRINCHI kadrning yoniga tushadi. Agar ikkalasi bir joyniki
 * bo'lsa, aylanish nuqtasida takror ko'rinib qoladi — shuni almashtiramiz.
 */
function fixSeam(list) {
  if (list.length < 3) return list;
  if (list[0].id !== list[list.length - 1].id) return list;

  for (let i = 1; i < list.length - 1; i += 1) {
    const fits =
      list[i].id !== list[0].id &&
      list[i - 1].id !== list[list.length - 1].id &&
      list[i + 1].id !== list[list.length - 1].id;
    if (fits) {
      [list[i], list[list.length - 1]] = [list[list.length - 1], list[i]];
      break;
    }
  }
  return list;
}

function tileHtml(place) {
  return `
    <a class="marquee-item" href="${ROUTES.detail(place.id)}" title="${esc(place.name)}"
       aria-label="${esc(place.name)}">
      <img src="${esc(place.photo)}" alt="" loading="lazy" decoding="async">
    </a>`;
}

/**
 * Lentani chizadi.
 * @param {string} selector - konteyner
 * @param {Array} places - [{id, name, photo}] — `id` biznes ID'si
 * @param {object} options - {rows: 1|2}
 */
export function renderPhotoMarquee(selector, places, { rows = 2 } = {}) {
  const container = document.querySelector(selector);
  if (!container) return;

  const photos = (places || []).filter((place) => place.photo);
  if (photos.length < 2) {
    container.innerHTML = "";
    return;
  }

  // Joylarni qatorlarga taqsimlaymiz: har bir qatorda bir nechta JOY
  // bo'lishi shart, aks holda o'sha qatorda navbatlashtirib bo'lmaydi.
  const owners = shuffle(groupByOwner(photos));
  const rowCount = owners.length >= 4 ? rows : 1;
  const rowOwners = Array.from({ length: rowCount }, () => []);
  owners.forEach((owner, index) => rowOwners[index % rowCount].push(owner));

  const tracks = rowOwners
    .filter((group) => group.length)
    .map((group) => {
      let pool = group.flatMap((owner) => owner.items);
      // Kadr kam bo'lsa lenta uzilib qoladi — havzani takrorlaymiz.
      // Takrordan keyin ham navbatlashtirish qaytadan hisoblanadi,
      // shuning uchun ulash joyida takror chiqmaydi.
      const base = [...pool];
      while (pool.length < MIN_TILES) pool = pool.concat(base);
      return fixSeam(interleaveByOwner(pool));
    });

  container.innerHTML = `
    <div class="marquee">
      ${tracks.map((track, index) => `
        <div class="marquee-row">
          <div class="marquee-track ${index % 2 ? "reverse" : ""}">
            ${track.map(tileHtml).join("")}
            ${track.map(tileHtml).join("")}
          </div>
        </div>`).join("")}
    </div>`;
}

/* Tashqarida sinash uchun ochib qo'yamiz (brauzerda ishlatilmaydi). */
export const __test = { interleaveByOwner, fixSeam, groupByOwner };
