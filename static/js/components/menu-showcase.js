/**
 * Bosh sahifadagi menyu vitrinasi.
 *
 * Ikki bo'lim, ikkalasi ham SEKIN SURILADIGAN tasma:
 *   restoran taomi → bitta qator
 *   to'yxona taomi → besh qator
 *
 * ===================================================================
 * NEGA SAKRAB ALMASHISH EMAS, SURILISH
 * ===================================================================
 * Ilgari taomlar 2×4 li to'rda turardi va har 6,5 soniyada butun to'r
 * birdan almashardi. Odam bitta taomni o'qiyotgan paytda ekran
 * o'zgarib ketardi — ya'ni o'qishning o'rtasida matn yo'qolardi.
 * Sekin surilish esa o'qishni uzmaydi: taom ko'z oldidan asta o'tadi
 * va keraklisini bosishga ulgurasiz. Sichqoncha ustiga borsa tasma
 * butunlay to'xtaydi.
 *
 * ===================================================================
 * NAVBAT: HAR JOYDAN BITTADAN
 * ===================================================================
 * Taomlar shunchaki aralashtirilmaydi, NAVBAT bilan teriladi:
 *   1-restoran 1-taomi → 2-restoran 1-taomi → 1-restoran 2-taomi → …
 * Ilgari oddiy aralashtirish ishlatilardi va tasodif bilan bitta
 * joyning o'nta taomi ketma-ket tushib qolishi mumkin edi — vitrina
 * o'sha joyning reklamasiga aylanardi. Navbat bilan har bir joy teng
 * ko'rinadi.
 */
import { api } from "../core/api.js";
import { ROUTES } from "../core/config.js";
import { t } from "../core/i18n.js";
import { esc } from "../ui/dom.js";
import { icon } from "../ui/icons.js";
import { emptyState, errorState, skeletonCards } from "../ui/state.js";
import { money, imageUrl } from "../ui/format.js";

/**
 * To'yxona devorining ustunlari soni — EKRAN KENGLIGIGA qarab.
 *
 * Nega CSS emas, JS hal qiladi: ustunlar soni `grid-template-columns`
 * bilan cheklansa, ortiqcha ustunlar yo'qolmaydi — ular to'rning
 * PASTKI qatoriga tushadi va devorning qat'iy balandligi ostida
 * kesilib qoladi. Ya'ni telefonda oltita ustundan to'rttasi shunchaki
 * ko'rinmay qolardi va ulardagi taomlar hech qachon chiqmasdi.
 *
 * Endi ustun soni chizishdan OLDIN hisoblanadi: tor ekranda ustun
 * kam, lekin har birida taom ko'p — hammasi baribir ko'rinadi.
 *
 * Yotiq kartochkaga kamida ~180 px kerak (yozuv + 52 px rasm).
 */
function wallColumns() {
  const width = window.innerWidth;
  if (width <= 700) return 2;
  if (width <= 1100) return 4;
  return 6;
}

/** Ustundagi bitta taomga ketadigan vaqt — qatordagidan sekinroq.
    Vertikal harakat ko'zga ko'proq tashlanadi, shuning uchun u
    gorizontaldan sezilarli sekin bo'lishi kerak. */
const COLUMN_SECONDS_PER_ITEM = 16;

/** Bitta taom ko'z oldidan o'tishiga ketadigan vaqt — sekinligi shu. */
const SECONDS_PER_ITEM = 10;

/** Tasma uzluksiz ko'rinishi uchun qatorda kamida shuncha element bo'lsin. */
const MIN_PER_ROW = 6;

function shuffle(list) {
  const copy = [...list];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

/**
 * Taomlarni joylar bo'yicha NAVBATGA teradi.
 *
 * Har bir joyning taomlari o'z ichida aralashtiriladi, joylarning
 * tartibi ham aralashtiriladi — shunda sahifa har safar yangilanganda
 * boshqa taom birinchi bo'lib chiqadi. Keyin har aylanishda har bir
 * joydan BITTADAN olinadi: taomi tugagan joy navbatdan chiqib ketadi,
 * qolganlari davom etadi.
 */
function interleaveByBusiness(items) {
  const groups = new Map();
  items.forEach((item) => {
    const key = item.business ?? item.business_name ?? "?";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  });

  const lists = shuffle([...groups.values()].map(shuffle));
  const out = [];
  for (let depth = 0; ; depth += 1) {
    let taken = false;
    lists.forEach((list) => {
      if (depth < list.length) {
        out.push(list[depth]);
        taken = true;
      }
    });
    if (!taken) break;
  }
  return out;
}

/**
 * Sekin suriladigan bitta tasma.
 *
 * Ichidagi ro'yxat IKKI MARTA yoziladi va tasma yarmigacha suriladi:
 * shunda oxiriga yetganda u aynan boshlang'ich holatga tushadi va
 * "sakrash" ko'rinmaydi. Bitta nusxa bilan tasma oxirida bo'sh joy
 * qolardi.
 */
function marqueeHtml(items, renderItem, { reverse = false, factor = 1 } = {}) {
  // Qator qisqa bo'lsa ekranni to'ldirmaydi — ro'yxat takrorlanadi.
  let row = items;
  while (row.length && row.length < MIN_PER_ROW) row = [...row, ...items];

  const body = row.map(renderItem).join("");
  const duration = Math.max(24, Math.round(row.length * SECONDS_PER_ITEM * factor));

  return `
    <div class="mm-row${reverse ? " is-reverse" : ""}" style="--mm-dur:${duration}s">
      <div class="mm-track">${body}${body}</div>
    </div>`;
}

function dishTileHtml(item) {
  return `
    <a class="dish-tile" href="${ROUTES.detail(item.business)}">
      <img src="${esc(imageUrl(item.photo))}" alt="${esc(item.name)}" loading="lazy" decoding="async">
      <div class="body">
        <span class="name">${esc(item.name)}</span>
        <span class="place">${esc(item.business_name || "")}</span>
        <span class="price">${item.price ? money(item.price) : ""}</span>
      </div>
    </a>`;
}

/**
 * Ustundagi kartochka — ESKI ko'rinish: chapda nomi, joyi va narxi,
 * o'ngda kichik rasm.
 *
 * Restoran taomining kartochkasidan ATAYLAB farq qiladi (u yerda rasm
 * tepada, katta). Sabab: restoran taomini odam RASMga qarab tanlaydi
 * ("nima yeyishim kerak?"), to'y dasturxonini esa NARX va joyga qarab
 * ("qanchaga tushadi, qayerda?"). Shuning uchun bu yerda birinchi
 * o'rinda yozuv turadi, rasm esa yordamchi.
 */
function feastRowHtml(item) {
  const price = item.price_from ? money(item.price_from) : "";
  return `
    <a class="feast-row" href="${ROUTES.detail(item.business)}">
      <span class="info">
        <b>${esc(item.name)}</b>
        <span class="place">${esc(item.business_name || "")}</span>
        ${price ? `<span class="amount">${esc(price)}</span>` : ""}
      </span>
      <img src="${esc(imageUrl(item.photo))}" alt="" loading="lazy" decoding="async">
    </a>`;
}

/**
 * Sekin suriladigan bitta USTUN.
 *
 * Tasma bilan bir xil hiyla: ro'yxat ikki marta yoziladi va ustun
 * yarmigacha (-50%) suriladi, shunda qaytish ko'rinmaydi. Farqi
 * shundaki, bu yerda harakat vertikal.
 */
function columnHtml(items, index) {
  let col = items;
  while (col.length && col.length < MIN_PER_ROW) col = [...col, ...items];

  const body = col.map(feastRowHtml).join("");
  const duration = Math.max(60, Math.round(col.length * COLUMN_SECONDS_PER_ITEM * (1 + index * 0.08)));

  return `
    <div class="mw-col${index % 2 === 1 ? " is-reverse" : ""}" style="--mm-dur:${duration}s">
      <div class="mw-track">${body}${body}</div>
    </div>`;
}

/**
 * Restoran taomlari — BITTA qator, sekin suriladi.
 *
 * @param {string} selector - tasma joylashadigan konteyner
 * @param {string} dotsSelector - eski sahifa chiziqchalari (endi ishlatilmaydi)
 */
export async function renderDishWall(selector, dotsSelector) {
  const container = document.querySelector(selector);
  if (!container) return;

  // Sahifa chiziqchalari surilishda ma'nosiz: "sahifa" tushunchasining
  // o'zi yo'q, tasma uzluksiz oqadi.
  const dots = document.querySelector(dotsSelector);
  if (dots) dots.innerHTML = "";

  // Bo'shlik va xatoni JIM yutmaymiz: ilgari ikkala holatda ham blok
  // bo'sh qolardi va sahifada tushunarsiz katta oq joy paydo bo'lardi.
  container.innerHTML = `<div class="dish-wall-skeleton">${skeletonCards(4)}</div>`;

  let items = [];
  try {
    const data = await api.showcase.restaurantMenu({ page_size: 40 });
    items = interleaveByBusiness(data.results || []);
  } catch (error) {
    container.innerHTML = errorState(error.message);
    return;
  }
  if (!items.length) {
    container.innerHTML = emptyState(
      t("home.noDishes"),
      t("home.noDishesText"),
      icon("restaurant", { size: 40 })
    );
    return;
  }

  container.innerHTML = `<div class="menu-marquee">${marqueeHtml(items, dishTileHtml)}</div>`;
}

/**
 * To'yxona taomlari — OLTI USTUNLI devor, har biri sekin pastga
 * (yoki tepaga) suriladi.
 *
 * Ustunlar navbat bilan to'ldiriladi (1-taom 1-ustunga, 2-taom
 * 2-ustunga…), shunda joylar navbati ustunlar ichida ham saqlanadi:
 * bitta ustunda bitta to'yxonaning taomlari to'planib qolmaydi.
 *
 * Qo'shni ustunlar QARAMA-QARSHI yo'nalishda harakatlanadi va
 * tezligi ham bir xil emas — aks holda oltita ustun bitta katta
 * devor bo'lib pastga sirg'anayotganday ko'rinardi.
 */
export async function renderFeastList(selector, { limit = 40 } = {}) {
  const container = document.querySelector(selector);
  if (!container) return;

  container.innerHTML = `<div class="dish-wall-skeleton">${skeletonCards(4)}</div>`;

  let items = [];
  try {
    const data = await api.showcase.venueMenu({ page_size: limit });
    items = interleaveByBusiness(data.results || []);
  } catch (error) {
    container.innerHTML = errorState(error.message);
    return;
  }
  if (!items.length) {
    container.innerHTML = emptyState(
      t("home.noFeast"),
      t("home.noFeastText"),
      icon("party", { size: 40 })
    );
    return;
  }

  // Taom kam bo'lsa hamma ustun ochilmaydi: har birida bitta-ikkitadan
  // taom qolib, devor siyrak ko'rinardi.
  const paint = () => {
    const colCount = Math.min(wallColumns(), Math.max(1, Math.ceil(items.length / 2)));
    const columns = Array.from({ length: colCount }, () => []);
    items.forEach((item, index) => columns[index % colCount].push(item));

    container.innerHTML = `
      <div class="menu-wall" style="--wall-cols:${colCount}">
        ${columns.map((column, index) => columnHtml(column, index)).join("")}
      </div>`;
    return colCount;
  };

  let drawn = paint();

  // Ekran o'lchami o'zgarganda faqat USTUN SONI o'zgarsa qayta
  // chizamiz. Har bir piksel o'zgarishida qayta chizish animatsiyani
  // boshidan boshlab yuborardi — tasma sakraganday ko'rinardi.
  window.addEventListener("resize", () => {
    if (wallColumns() === drawn) return;
    drawn = paint();
  });
}
