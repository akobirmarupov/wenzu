/**
 * Ikonka to'plami.
 *
 * Nega o'z to'plamimiz: ilgari interfeysda emoji ishlatilardi (📅 🏢 ★).
 * Emoji uchta jiddiy muammo beradi:
 *   1. Har tizimda boshqacha chiziladi — Windowsda bitta, iPhone'da
 *      butunlay boshqa rasm. Interfeys tanish ko'rinishini yo'qotadi.
 *   2. Rangi qulflangan. Brend zumradiga ham, xato qizillikka ham
 *      bo'yab bo'lmaydi.
 *   3. Matn qatorida o'lchami va bazasi suzib yuradi — yozuvga tekis
 *      tushmaydi.
 *
 * Shu sababli barcha ikonka — qo'lda chizilgan SVG. Umumiy qoidalar:
 *   · 24×24 to'r, chiziq 1.75px, uchlari va burchaklari yumaloq;
 *   · rang `currentColor` — ota elementning rangini oladi, ya'ni
 *     tugma ichida tugma rangida, xato matnida qizil bo'ladi;
 *   · o'lcham `em` da — shrift kattalashsa ikonka ham o'sadi.
 *
 * Ishlatish:
 *   import { icon } from "../ui/icons.js";
 *   el.innerHTML = `${icon("calendar")} 12-dekabr`;
 *   icon("star", { size: 18, fill: true, className: "star-on" })
 */

/* Har bir ikonka — faqat ichki shakllar. O'ram (svg tegi) pastda
   bir marta yasaladi, shunda o'lcham va uslub bir joyda boshqariladi. */
const PATHS = {
  /* --- navigatsiya --- */
  home: '<path d="M3.5 10.5 12 4l8.5 6.5V19a1.5 1.5 0 0 1-1.5 1.5h-3.5v-6h-7v6H5A1.5 1.5 0 0 1 3.5 19z"/>',
  grid: '<rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  close: '<path d="m6 6 12 12M18 6 6 18"/>',
  chevronDown: '<path d="m6 9 6 6 6-6"/>',
  chevronRight: '<path d="m9 6 6 6-6 6"/>',
  chevronLeft: '<path d="m15 6-6 6 6 6"/>',
  arrowRight: '<path d="M4 12h15m0 0-6-6m6 6-6 6"/>',
  externalLink: '<path d="M14 4h6v6"/><path d="M20 4 11 13"/><path d="M18 14v4.5A1.5 1.5 0 0 1 16.5 20h-11A1.5 1.5 0 0 1 4 18.5v-11A1.5 1.5 0 0 1 5.5 6H10"/>',

  /* --- joy va biznes --- */
  building: '<path d="M4 20.5V5.5A1.5 1.5 0 0 1 5.5 4h9A1.5 1.5 0 0 1 16 5.5v15"/><path d="M16 10h2.5A1.5 1.5 0 0 1 20 11.5v9"/><path d="M3 20.5h18"/><path d="M7.5 8h5M7.5 12h5M7.5 16h5"/>',
  venue: '<path d="M3 20.5h18"/><path d="M4.5 20.5V10L12 4.5 19.5 10v10.5"/><path d="M9 20.5v-5a3 3 0 0 1 6 0v5"/><path d="M4.5 10h15"/>',
  restaurant: '<path d="M6 3v7a2.5 2.5 0 0 0 5 0V3"/><path d="M8.5 10v11"/><path d="M17.5 3c-1.7 1-2.5 2.8-2.5 5s.8 3.6 2.5 4v9"/>',
  seat: '<path d="M7 11V6.5A2.5 2.5 0 0 1 9.5 4h5A2.5 2.5 0 0 1 17 6.5V11"/><path d="M5 11h14a1.5 1.5 0 0 1 1.5 1.5v3A1.5 1.5 0 0 1 19 17H5a1.5 1.5 0 0 1-1.5-1.5v-3A1.5 1.5 0 0 1 5 11Z"/><path d="M6 17v3.5M18 17v3.5"/>',
  mapPin: '<path d="M12 21s7-5.6 7-11a7 7 0 1 0-14 0c0 5.4 7 11 7 11Z"/><circle cx="12" cy="10" r="2.6"/>',
  map: '<path d="m9 4.5-5 2v13l5-2 6 2 5-2v-13l-5 2z"/><path d="M9 4.5v13M15 6.5v13"/>',
  globe: '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17"/><path d="M12 3.5c2.2 2.4 3.3 5.3 3.3 8.5S14.2 18.1 12 20.5c-2.2-2.4-3.3-5.3-3.3-8.5S9.8 5.9 12 3.5Z"/>',

  /* --- vaqt va jadval --- */
  calendar: '<rect x="3.5" y="5.5" width="17" height="15" rx="2"/><path d="M3.5 10h17"/><path d="M8 3.5v4M16 3.5v4"/>',
  calendarDays: '<rect x="3.5" y="5.5" width="17" height="15" rx="2"/><path d="M3.5 10h17"/><path d="M8 3.5v4M16 3.5v4"/><path d="M7.5 13.5h2M11 13.5h2M14.5 13.5h2M7.5 17h2M11 17h2"/>',
  clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
  history: '<path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1"/><path d="M3.5 4v4h4"/><path d="M12 7.5V12l3 2"/>',

  /* --- odamlar --- */
  user: '<circle cx="12" cy="8" r="3.75"/><path d="M4.5 20.5a7.5 7.5 0 0 1 15 0"/>',
  users: '<circle cx="9.5" cy="8" r="3.4"/><path d="M3 20.5a6.5 6.5 0 0 1 13 0"/><path d="M16.5 4.9a3.4 3.4 0 0 1 0 6.2"/><path d="M18 14.6a6.5 6.5 0 0 1 3 5.9"/>',
  userCheck: '<circle cx="10" cy="8" r="3.75"/><path d="M3 20.5a7.5 7.5 0 0 1 12.2-5.9"/><path d="m16 17.5 2 2 4-4"/>',
  wave: '<path d="M8 12.5V6a1.6 1.6 0 0 1 3.2 0v5"/><path d="M11.2 11V4.6a1.6 1.6 0 0 1 3.2 0V11"/><path d="M14.4 11.4V7.2a1.6 1.6 0 0 1 3.2 0v7.1a6.3 6.3 0 0 1-6.3 6.3h-.6a5 5 0 0 1-3.6-1.5l-3.4-3.5a1.7 1.7 0 0 1 2.4-2.4L8 15.1"/>',

  /* --- harakatlar --- */
  search: '<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/>',
  filter: '<path d="M4 6h16l-6.2 7.3v5.2l-3.6 2v-7.2z"/>',
  edit: '<path d="M4 20h4l10-10a2.1 2.1 0 0 0-3-3L5 17z"/><path d="m14.5 6.5 3 3"/>',
  trash: '<path d="M4.5 7h15"/><path d="M9.5 7V5.5A1.5 1.5 0 0 1 11 4h2a1.5 1.5 0 0 1 1.5 1.5V7"/><path d="M6.5 7.5 7.4 19A1.6 1.6 0 0 0 9 20.5h6a1.6 1.6 0 0 0 1.6-1.5l.9-11.5"/><path d="M10.5 11v6M13.5 11v6"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  minus: '<path d="M5 12h14"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  checkCircle: '<circle cx="12" cy="12" r="8.5"/><path d="m8.2 12.2 2.6 2.6 5-5.2"/>',
  ban: '<circle cx="12" cy="12" r="8.5"/><path d="m6 18 12-12"/>',
  send: '<path d="M20.5 3.5 10.5 13.5"/><path d="M20.5 3.5 14 20.5l-3.5-7-7-3.5z"/>',
  refresh: '<path d="M20 11a8 8 0 0 0-13.7-4.7L3.5 9"/><path d="M4 13a8 8 0 0 0 13.7 4.7L20.5 15"/><path d="M3.5 4.5V9H8M20.5 19.5V15H16"/>',
  download: '<path d="M12 4v11"/><path d="m7.5 11 4.5 4.5 4.5-4.5"/><path d="M4.5 20.5h15"/>',
  upload: '<path d="M12 20V9"/><path d="m7.5 12.5 4.5-4.5 4.5 4.5"/><path d="M4.5 3.5h15"/>',

  /* --- holat va xabar --- */
  bell: '<path d="M6.5 10a5.5 5.5 0 0 1 11 0c0 4 1.5 5.5 1.5 5.5H5S6.5 14 6.5 10Z"/><path d="M10 19a2.2 2.2 0 0 0 4 0"/>',
  info: '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5"/><path d="M12 7.8h.01"/>',
  alert: '<path d="M10.6 4.3 3.3 17a1.6 1.6 0 0 0 1.4 2.4h14.6a1.6 1.6 0 0 0 1.4-2.4L13.4 4.3a1.6 1.6 0 0 0-2.8 0Z"/><path d="M12 9.5v4"/><path d="M12 16.8h.01"/>',
  shield: '<path d="M12 3.5 5 6.2v5.4c0 4.2 2.9 7.6 7 8.9 4.1-1.3 7-4.7 7-8.9V6.2Z"/><path d="m9 12 2.2 2.2L15.5 10"/>',
  lock: '<rect x="4.5" y="10.5" width="15" height="10" rx="2"/><path d="M8 10.5V7.8a4 4 0 0 1 8 0v2.7"/>',
  megaphone: '<path d="M4 10v4a2 2 0 0 0 2 2h1.5L17 20.5V3.5L7.5 8H6a2 2 0 0 0-2 2Z"/><path d="M20 9.5a3.5 3.5 0 0 1 0 5"/><path d="M7.5 16v4.5"/>',
  chat: '<path d="M20.5 11.8c0 4.1-3.8 7.4-8.5 7.4a10 10 0 0 1-2.6-.3L4.5 20.5l1.3-3.6A7 7 0 0 1 3.5 11.8c0-4.1 3.8-7.4 8.5-7.4s8.5 3.3 8.5 7.4Z"/>',
  mail: '<rect x="3.5" y="5" width="17" height="14" rx="2"/><path d="m4 7 8 6 8-6"/>',
  phone: '<path d="M8.4 4.5H5.6A1.9 1.9 0 0 0 3.7 6.7C4.3 13.4 10.6 19.7 17.3 20.3a1.9 1.9 0 0 0 2.2-1.9v-2.8l-4-1.4-1.9 1.9a13.4 13.4 0 0 1-4.7-4.7l1.9-1.9Z"/>',

  /* --- pul va obuna --- */
  gem: '<path d="m3.5 9.5 3-5h11l3 5L12 20.5Z"/><path d="M3.5 9.5h17"/><path d="m8.5 9.5 3.5 11 3.5-11-2-5h-3z"/>',
  card: '<rect x="3" y="5.5" width="18" height="13" rx="2.2"/><path d="M3 10h18"/><path d="M7 14.5h3"/>',
  wallet: '<path d="M3.5 7.5A2 2 0 0 1 5.5 5.5h11a2 2 0 0 1 2 2"/><rect x="3.5" y="7.5" width="17" height="11" rx="2"/><path d="M16 13h2"/>',
  receipt: '<path d="M6 3.5h12v17l-2.5-1.5L13 20.5 10.5 19 8 20.5 6 19Z"/><path d="M9.5 8h5M9.5 12h5"/>',
  chart: '<path d="M4 20.5V4"/><path d="M4 20.5h16.5"/><path d="M8 17V11M12.5 17V7M17 17v-4"/>',
  trendUp: '<path d="m4 16 5-5 3.5 3.5L20 7"/><path d="M15 7h5v5"/>',

  /* --- kontent --- */
  image: '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><circle cx="8.8" cy="9.6" r="1.7"/><path d="m4 17 4.8-4.4a1.7 1.7 0 0 1 2.3 0l5.2 4.8"/><path d="m14 14 1.6-1.5a1.7 1.7 0 0 1 2.3 0L20.5 15"/>',
  camera: '<path d="M4.5 7.5h3L9 5h6l1.5 2.5h3a1.7 1.7 0 0 1 1.7 1.7v8.1a1.7 1.7 0 0 1-1.7 1.7h-15a1.7 1.7 0 0 1-1.7-1.7V9.2a1.7 1.7 0 0 1 1.7-1.7Z"/><circle cx="12" cy="13" r="3.4"/>',
  news: '<path d="M4 6a1.5 1.5 0 0 1 1.5-1.5h11A1.5 1.5 0 0 1 18 6v12.5a2 2 0 0 0 2 2H6a2 2 0 0 1-2-2Z"/><path d="M18 9h1.5A1.5 1.5 0 0 1 21 10.5v8"/><path d="M7.5 8h7M7.5 11.5h7M7.5 15h4"/>',
  document: '<path d="M6 3.5h7l5 5v12a1.5 1.5 0 0 1-1.5 1.5h-10A1.5 1.5 0 0 1 5 20.5v-15A1.5 1.5 0 0 1 6.5 3.5Z"/><path d="M13 3.5V9h5"/><path d="M8.5 13h7M8.5 16.5h5"/>',
  list: '<path d="M8.5 6.5h12M8.5 12h12M8.5 17.5h12"/><path d="M4 6.5h.01M4 12h.01M4 17.5h.01"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 14.5a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1v.3a2 2 0 1 1-4 0v-.2a1.6 1.6 0 0 0-2.8-1.1l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0-1.1-2.7h-.3a2 2 0 1 1 0-4h.2a1.6 1.6 0 0 0 1.1-2.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 2.7-1.1v-.3a2 2 0 1 1 4 0v.2a1.6 1.6 0 0 0 2.8 1.1l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0 1.1 2.7h.3a2 2 0 1 1 0 4h-.2a1.6 1.6 0 0 0-1.4 1Z"/>',
  logout: '<path d="M14.5 7.5V5.5A1.5 1.5 0 0 0 13 4H6a1.5 1.5 0 0 0-1.5 1.5v13A1.5 1.5 0 0 0 6 20h7a1.5 1.5 0 0 0 1.5-1.5v-2"/><path d="M9.5 12h11"/><path d="m17.5 8.5 3.5 3.5-3.5 3.5"/>',

  /* --- boshqa --- */
  star: '<path d="m12 3.8 2.7 5.5 6 .9-4.35 4.25 1.03 6-5.38-2.83L6.62 20.5l1.03-6L3.3 10.2l6-.9z"/>',
  sparkle: '<path d="m12 3.5 1.9 5.1 5.1 1.9-5.1 1.9L12 17.5l-1.9-5.1L5 10.5l5.1-1.9z"/><path d="M18.5 16.5l.7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7z"/>',
  bolt: '<path d="M13.5 3.5 5 13.5h5.5l-1 7 8.5-10h-5.5z"/>',
  bulb: '<path d="M9 17.5a6 6 0 1 1 6 0v1.2a1.3 1.3 0 0 1-1.3 1.3h-3.4A1.3 1.3 0 0 1 9 18.7Z"/><path d="M10 20.5h4"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M2.5 12h2M19.5 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/>',
  moon: '<path d="M20 14.2A8.4 8.4 0 0 1 9.8 4 8.5 8.5 0 1 0 20 14.2Z"/>',
  key: '<circle cx="8" cy="12" r="4"/><path d="M12 12h9"/><path d="M17 12v3.5M20 12v2.5"/>',
  party: '<path d="M3.5 20.5 8 8.5l7.5 7.5z"/><path d="M14 4.5v2M19.5 10h2M17.6 6.4l1.4-1.4"/><path d="M13 9.5a3.5 3.5 0 0 1 3.5-3.5"/><path d="M15 13a3.5 3.5 0 0 1 3.5-3.5"/>',
  signal: '<path d="M5 12a7 7 0 0 1 2-4.9M19 12a7 7 0 0 0-2-4.9"/><path d="M2.5 15a10.5 10.5 0 0 1 2.4-11M21.5 15a10.5 10.5 0 0 0-2.4-11"/><circle cx="12" cy="13.5" r="2.2"/><path d="M12 15.7V21"/>',
};

/* To'ldirilgan holati bor ikonkalar (reyting yulduzi kabi) — `fill: true`
   berilganda chiziq emas, to'liq bo'yalgan shakl chiqadi. */
const FILLABLE = new Set(["star", "sparkle", "gem", "bolt", "shield"]);

const DEFAULT_SIZE = "1.15em";

/**
 * SVG ikonka qaytaradi (HTML matn ko'rinishida).
 *
 * @param {string} name   PATHS dagi nom
 * @param {object} [opt]
 * @param {number|string} [opt.size]  24 yoki "1.2em" — standart: matnga mos
 * @param {boolean} [opt.fill]        to'ldirilgan variant
 * @param {string} [opt.className]    qo'shimcha CSS sinf
 * @param {string} [opt.title]        skrinrider uchun nom; berilmasa ikonka
 *                                    yordamchi texnologiyalardan yashiriladi
 */
export function icon(name, opt = {}) {
  const shape = PATHS[name];
  if (!shape) {
    // Nomi xato bo'lsa interfeys yiqilmasin — bo'sh joy qoldiramiz va
    // ishlab chiquvchiga konsolda aytamiz.
    if (typeof console !== "undefined") console.warn(`icon(): "${name}" topilmadi`);
    return "";
  }
  const size = opt.size == null ? DEFAULT_SIZE : (typeof opt.size === "number" ? `${opt.size}px` : opt.size);
  const filled = opt.fill && FILLABLE.has(name);
  const cls = ["ico", opt.className].filter(Boolean).join(" ");
  const a11y = opt.title
    ? `role="img" aria-label="${escapeAttr(opt.title)}"`
    : 'aria-hidden="true" focusable="false"';

  return (
    `<svg class="${escapeAttr(cls)}" width="${size}" height="${size}" viewBox="0 0 24 24" ` +
    `fill="${filled ? "currentColor" : "none"}" stroke="currentColor" stroke-width="1.75" ` +
    `stroke-linecap="round" stroke-linejoin="round" ${a11y}>${shape}</svg>`
  );
}

/** Reyting yulduzlari: to'ldirilgan/bo'sh, 5 ta. */
export function starRow(rating, opt = {}) {
  const value = Number(rating) || 0;
  const filled = Math.round(value);
  const size = opt.size || "1em";
  let html = "";
  for (let i = 0; i < 5; i += 1) {
    const on = i < filled;
    html += `<span class="star${on ? " is-on" : ""}">${icon("star", { size, fill: on })}</span>`;
  }
  return html;
}

/** Ikonka + matn — qatorda tekis tursin uchun bitta o'ram. */
export function iconLabel(name, text, opt = {}) {
  return `<span class="icon-label">${icon(name, opt)}<span>${text}</span></span>`;
}

/** Ikonka nomi mavjudligini tekshirish (testlar va dinamik nomlar uchun). */
export function hasIcon(name) {
  return Object.prototype.hasOwnProperty.call(PATHS, name);
}

export const ICON_NAMES = Object.keys(PATHS);

function escapeAttr(value) {
  return String(value).replace(/[&<>"]/g, (ch) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]
  ));
}
