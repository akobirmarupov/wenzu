/** Yangiliklar: to'liq kartochkalar va yon ustundagi qisqa lenta. */
import { api } from "../core/api.js";
import { getLanguage } from "../core/i18n.js";
import { esc } from "../ui/dom.js";
import { dateLabel } from "../ui/format.js";

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

  const classes = `news-card ${item.is_pinned ? "news-pinned" : ""}`;
  return item.link_url
    ? `<a class="${classes}" href="${esc(item.link_url)}">${inner}</a>`
    : `<article class="${classes}">${inner}</article>`;
}

function stripHtml(item) {
  const inner = `
    <span class="dot" aria-hidden="true"></span>
    <div class="stack stack-1" style="min-width:0">
      <b class="small">${esc(item.title)}</b>
      ${item.excerpt ? `<span class="xs muted">${esc(item.excerpt)}</span>` : ""}
      <span class="xs faint">${dateLabel(item.created_at)}</span>
    </div>`;
  return item.link_url
    ? `<a class="news-strip-item" href="${esc(item.link_url)}">${inner}</a>`
    : `<div class="news-strip-item">${inner}</div>`;
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
