/** Yangiliklar: to'liq kartochkalar va yon ustundagi qisqa lenta. */
import { api } from "../core/api.js";
import { getLanguage, t } from "../core/i18n.js";
import { esc } from "../ui/dom.js";
import { modal } from "../ui/modal.js";
import { dateLabel } from "../ui/format.js";

// Ochilgan oynaga ma'lumotni id bo'yicha topamiz: HTML atributiga
// butun matnni yozib qo'yish sahifani og'irlashtirardi va uzun
// yangilikda qochirish (escaping) muammosi tug'ilardi.
let loaded = [];

function categoryClass(category) {
  return `news-cat news-cat-${category || "news"}`;
}

function cardHtml(item) {
  const inner = `
    ${item.cover ? `<img src="${esc(item.cover)}" alt="" loading="lazy">` : ""}
    <div class="body">
      <span class="${categoryClass(item.category)}">${esc(item.category_display || "")}</span>
      <h3 class="display">${esc(item.title)}</h3>
      ${item.excerpt ? `<p>${esc(item.excerpt)}</p>` : ""}
      <div class="foot">
        <span class="xs faint">${dateLabel(item.created_at)}</span>
      </div>
    </div>`;

  // Kartochka HAVOLA emas, TUGMA.
  //
  // Ilgari u to'g'ridan-to'g'ri `link_url` ga olib ketardi: odam
  // yangilikni o'qimasdan turib boshqa saytga tushib qolardi, matn
  // esa (`body`) hech qayerda ko'rinmasdi — bekorga yozilardi.
  // Endi avval oyna ochiladi, havolaga o'tish esa pastdagi tugma
  // orqali — ya'ni ongli tanlov.
  return `
    <button class="news-card ${item.is_pinned ? "news-pinned" : ""}" type="button"
            data-news="${esc(item.id)}">${inner}</button>`;
}

function stripHtml(item) {
  const inner = `
    <span class="dot" aria-hidden="true"></span>
    <div class="stack stack-1" style="min-width:0">
      <b class="small">${esc(item.title)}</b>
      ${item.excerpt ? `<span class="xs muted">${esc(item.excerpt)}</span>` : ""}
      <span class="xs faint">${dateLabel(item.created_at)}</span>
    </div>`;
  return `<button class="news-strip-item" type="button" data-news="${esc(item.id)}">${inner}</button>`;
}

/** To'liq yangilik oynasi. */
function openNews(item) {
  // Matn `body` da abzatslar bilan yoziladi. `esc` dan keyin qatorlarni
  // <p> ga aylantiramiz — HTML kiritishga yo'l qo'ymay, lekin abzats
  // ko'rinishini saqlab. Bo'sh bo'lsa qisqacha matn ishlatiladi.
  // Ichki havola SHU OYNADA ochiladi, tashqisi — yangi ilovada.
  // Aks holda o'z saytimizning sahifasi ham yangi ilovada ochilib,
  // odamda o'nlab ilova to'planib qolardi.
  const external = /^https?:\/\//i.test(item.link_url || "");

  const text = (item.body || item.excerpt || "").trim();
  const paragraphs = text
    ? text.split(/\n{2,}|\r\n{2,}/).map((part) => `<p>${esc(part.trim()).replace(/\n/g, "<br>")}</p>`).join("")
    : "";

  modal.open(`
    ${item.cover ? `<img class="news-modal-cover" src="${esc(item.cover)}" alt="">` : ""}
    <span class="${categoryClass(item.category)}">${esc(item.category_display || "")}</span>
    <h2 class="display h2" style="margin-top:var(--sp-3)">${esc(item.title)}</h2>
    <span class="xs faint">${dateLabel(item.created_at)}</span>

    <div class="news-modal-body">${paragraphs || `<p class="muted">—</p>`}</div>

    <div class="row row-2" style="margin-top:var(--sp-6)">
      <button class="btn btn-outline" style="flex:1" type="button" data-modal-close>
        ${esc(t("common.close"))}
      </button>
      ${item.link_url ? `
        <a class="btn btn-primary" style="flex:1" href="${esc(item.link_url)}"
           ${external ? 'target="_blank" rel="noopener noreferrer"' : ""}>
          ${esc(t("news.open"))}${external ? " ↗" : ""}
        </a>` : ""}
    </div>`, { wide: true });
}

/** Kartochka va lenta bosilganda oynani ochadi (bir marta ulanadi). */
function bindOnce() {
  if (bindOnce.done) return;
  bindOnce.done = true;
  document.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-news]");
    if (!trigger) return;
    const item = loaded.find((news) => String(news.id) === trigger.dataset.news);
    if (item) openNews(item);
  });
}

/**
 * Yangiliklarni ikki joyga chizadi: yon lentaga va kartochkalar bo'limiga.
 * Yangilik bo'lmasa bo'limlar yashirin qoladi.
 */
export async function renderNews({ stripSelector, gridSelector, sectionSelector, limit = 8 }) {
  let items = [];
  try {
    const data = await api.news.list({ page_size: limit, lang: getLanguage() });
    items = data.results || [];
  } catch {
    return;
  }

  loaded = items;
  bindOnce();

  const strip = stripSelector ? document.querySelector(stripSelector) : null;
  if (strip) {
    strip.innerHTML = items.length
      ? items.slice(0, 5).map(stripHtml).join("")
      : `<p class="small muted" style="padding:var(--sp-4) 0">—</p>`;
  }

  const grid = gridSelector ? document.querySelector(gridSelector) : null;
  const section = sectionSelector ? document.querySelector(sectionSelector) : null;

  if (grid && items.length) {
    // Yon lentada ko'rsatilganlaridan keyingilari kartochka bo'lib chiqadi.
    const rest = items.slice(strip ? 5 : 0);
    if (rest.length) {
      grid.innerHTML = rest.map(cardHtml).join("");
      if (section) section.hidden = false;
    }
  }
}
