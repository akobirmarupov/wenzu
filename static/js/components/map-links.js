/**
 * Joylashuv bloki — "Xaritada ochish" va "Yo'nalish".
 *
 * Havolalar SERVERDAN tayyor holda keladi (`business.map_links`):
 * koordinata bo'lsa aniq nuqtaga, bo'lmasa nom + manzil bo'yicha
 * qidiruvga. Manzilni bu yerda qaytadan yig'ish — Yandex koordinatani
 * teskari tartibda kutishini ikkinchi marta eslab qolish demak edi,
 * va bir kun kelib ikkalasi bir-biridan farq qila boshlardi.
 *
 * Havola bo'lmasa (egasi na koordinata, na manzil kiritgan) blok
 * UMUMAN chizilmaydi — "xaritada ochish" deb turgan, lekin hech qayerga
 * olib bormaydigan tugma yomonroq.
 */
import { esc } from "../ui/dom.js";
import { t } from "../core/i18n.js";

/**
 * Xarita nishoni — EMOJI EMAS, SVG.
 *
 * Emoji shriftga bog'liq: u yo'q tizimda 🗺 bo'sh to'rtburchakka
 * aylanadi va kartochkada "nimadir buzilgan" degan taassurot beradigan
 * quruq oq doira qolib ketadi. SVG esa hamma joyda bir xil chiziladi va
 * `currentColor` orqali mavzuga (kunduzgi/tungi) moslashadi.
 */
function icon(paths, size = 15) {
  return `
    <svg viewBox="0 0 24 24" width="${size}" height="${size}" aria-hidden="true"
         focusable="false" fill="none" stroke="currentColor" stroke-width="2"
         stroke-linecap="round" stroke-linejoin="round">${paths}</svg>`;
}

const PIN_ICON = icon(
  `<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"></path>
   <circle cx="12" cy="10" r="3"></circle>`
);

/** Yo'nalish — burilish belgisi. Detal sahifasi ham ishlatadi. */
export const ROUTE_ICON = icon(
  `<polygon points="3 11 22 2 13 21 11 13 3 11"></polygon>`
);

/**
 * To'liq joylashuv bloki — manzil, tuman va tugmalar.
 *
 * @param {object} business  `map_links`, `district`, `address` bo'lgan obyekt
 * @param {object} options   `compact` — faqat tugmalar, sarlavhasiz
 */
export function mapLinksHtml(business, { compact = false } = {}) {
  const links = business?.map_links || {};
  if (!links.google && !links.yandex && !links.custom) return "";

  // Egasining o'z havolasi bo'lsa u asosiy tugma bo'ladi: aynan o'sha
  // manzilni u mijozlariga beradi va unda ba'zan bizda yo'q tafsilot
  // bo'ladi (kirish yo'li, ichki nuqta).
  //
  // Yozuvlar TARJIMADAN keladi ("Xaritada ochish", "Yo'nalish"), brend
  // nomlari esa o'zgarmaydi: Google Maps hamma tilda Google Maps.
  const primary = links.custom
    ? { href: links.custom, label: t("detail.openInMap"), icon: PIN_ICON }
    : { href: links.google, label: "Google Maps", icon: PIN_ICON };

  const buttons = [
    primary,
    links.custom && links.google
      ? { href: links.google, label: "Google Maps", icon: PIN_ICON } : null,
    links.yandex ? { href: links.yandex, label: "Yandex Maps", icon: PIN_ICON } : null,
    links.google_directions
      ? { href: links.google_directions, label: t("detail.directions"),
          icon: ROUTE_ICON, strong: true }
      : null,
  ].filter(Boolean);

  const list = buttons.map((button) => `
    <a class="map-btn ${button.strong ? "primary" : ""}" href="${esc(button.href)}"
       target="_blank" rel="noopener noreferrer">${button.icon}${esc(button.label)}</a>`).join("");

  if (compact) return `<div class="map-links compact">${list}</div>`;

  const where = [business.district, business.address].filter(Boolean).join(", ");
  return `
    <div class="map-block">
      ${where ? `<p class="map-where">${PIN_ICON} ${esc(where)}</p>` : ""}
      <div class="map-links">${list}</div>
    </div>`;
}

/**
 * Kartochka uchun bitta kichik xarita nuqtasi.
 *
 * Ro'yxatda to'rtta tugma juda ko'p — u yerda odam joyni TANLAYAPTI,
 * hali yo'lga chiqmagan. Shuning uchun faqat bittasi: bosgan zahoti
 * xaritada ochiladi.
 *
 * ===================================================================
 * NEGA BU `<a>` EMAS, `<button>`
 * ===================================================================
 * Kartochkaning O'ZI havola (`<a class="card-link">`). HTML'da esa
 * havola ichiga havola qo'yish TAQIQLANGAN va bu shunchaki "nostandart"
 * degani emas — brauzer parseri ichki `<a>` ni ko'rgan zahoti tashqi
 * `<a>` ni majburan YOPADI.
 *
 * Oqibati ko'zga tashlanadi: `card-body` kartochkadan tashqarida qolib,
 * to'rda alohida katak sifatida chiziladi — rasm bir joyda, matn boshqa
 * joyda. Aynan shu xato katalog sahifasini buzgan edi.
 *
 * `<button>` bunday qilmaydi: parser uni ichkarida qoldiradi va
 * kartochka butun bo'lib turadi. Bosilganda esa `preventDefault` +
 * `stopPropagation` tashqi havolaning yurishiga yo'l qo'ymaydi.
 */
export function mapPinHtml(business) {
  const links = business?.map_links || {};
  const href = links.custom || links.google;
  if (!href) return "";
  const label = esc(t("detail.openInMap"));
  return `
    <button type="button" class="map-pin" data-map-url="${esc(href)}"
            title="${label}" aria-label="${label}">${PIN_ICON}</button>`;
}

/**
 * Xarita nuqtalarining bosilishini bir joyda ushlaymiz.
 *
 * Listener HUJJATGA bir marta ulanadi, har bir kartochkaga emas: ro'yxat
 * qayta chizilganda (filtr, sahifa almashishi) nuqtalar yangidan
 * yaratiladi va har safar qayta ulanish kerak bo'lardi — biri unutilsa
 * tugma jim qolardi.
 */
if (typeof document !== "undefined") {
  document.addEventListener("click", (event) => {
    const pin = event.target.closest?.("[data-map-url]");
    if (!pin) return;
    // Kartochkaning o'zi ham havola — uni to'xtatmasak, brauzer bir
    // vaqtning o'zida detal sahifasiga ham o'tib ketardi.
    event.preventDefault();
    event.stopPropagation();
    window.open(pin.dataset.mapUrl, "_blank", "noopener,noreferrer");
  });
}
