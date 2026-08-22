/**
 * Bosh sahifadagi menyu vitrinasi.
 *
 * Ikki bo'lim, ikki xil ko'rinish — chunki ikkalasi ikki xil qaror:
 *   restoran taomi → rasm bilan tanlanadi (kichik kartochkalar to'ri)
 *   to'yxona taomi → narx va joy bilan tanlanadi (matn qatorlari)
 */
import { api } from "../core/api.js";
import { ROUTES } from "../core/config.js";
import { t } from "../core/i18n.js";
import { esc } from "../ui/dom.js";
import { emptyState, errorState, skeletonCards } from "../ui/state.js";
import { money, imageUrl } from "../ui/format.js";

/** Ikki qator × to'rtta ustun = bir "sahifa". */
const PAGE_SIZE = 8;
const ROTATE_MS = 6500;

function shuffle(list) {
  const copy = [...list];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
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
 * Restoran taomlari — ikki qator, qatorda to'rtta, sekin almashadi.
 * @param {string} selector - `.dish-wall` joylashadigan konteyner
 * @param {string} dotsSelector - sahifa chiziqchalari konteyneri
 */
export async function renderDishWall(selector, dotsSelector) {
  const container = document.querySelector(selector);
  if (!container) return;

  // Bo'shlik va xatoni JIM yutmaymiz.
  //
  // Ilgari ikkala holatda ham blok bo'sh qolardi va sahifada tushunarsiz
  // katta oq joy paydo bo'lardi — "ishlamayaptimi yoki taom yo'qmi?"
  // degan savolga javob yo'q edi. Endi sabab yozib ko'rsatiladi.
  container.innerHTML = `<div class="dish-wall">${skeletonCards(PAGE_SIZE)}</div>`;

  let items = [];
  try {
    const data = await api.showcase.restaurantMenu({ page_size: 40 });
    items = shuffle(data.results || []);
  } catch (error) {
    container.innerHTML = errorState(error.message);
    return;
  }
  if (!items.length) {
    container.innerHTML = emptyState(
      "Hozircha taom qo'shilmagan",
      "Restoranlar menyusini kiritgach, taomlar shu yerda ko'rinadi.",
      "🍽️"
    );
    return;
  }

  const pages = [];
  for (let i = 0; i < items.length; i += PAGE_SIZE) {
    const page = items.slice(i, i + PAGE_SIZE);
    // To'liq bo'lmagan oxirgi sahifa to'rni buzadi — boshidan to'ldiramiz.
    while (page.length < PAGE_SIZE && items.length >= PAGE_SIZE) {
      page.push(items[page.length % items.length]);
    }
    pages.push(page);
  }

  const dots = document.querySelector(dotsSelector);
  let index = 0;

  const paint = () => {
    container.innerHTML = `<div class="dish-wall">${pages[index].map(dishTileHtml).join("")}</div>`;
    if (dots) {
      dots.innerHTML = pages
        .map((_, i) => `<span class="${i === index ? "active" : ""}"></span>`)
        .join("");
    }
  };

  paint();
  if (pages.length === 1) return;

  let timer = null;
  const start = () => {
    timer = setInterval(() => {
      const wall = container.querySelector(".dish-wall");
      if (wall) wall.classList.add("fading");
      setTimeout(() => {
        index = (index + 1) % pages.length;
        paint();
      }, 420);
    }, ROTATE_MS);
  };
  start();

  container.addEventListener("mouseenter", () => clearInterval(timer));
  container.addEventListener("mouseleave", start);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) clearInterval(timer);
    else start();
  });
}

function feastRowHtml(item) {
  const price = item.price_from ? money(item.price_from) : "—";
  return `
    <a class="feast-row" href="${ROUTES.detail(item.business)}">
      <span class="info">
        <b>${esc(item.name)}</b>
        <span class="place">${esc(item.business_name || "")}${item.business_district ? ` · ${esc(item.business_district)}` : ""}</span>
      </span>
      <span class="amount">
        <b>${esc(price)}</b>
        <span>${esc(t("home.perPerson"))}</span>
      </span>
      <img src="${esc(imageUrl(item.photo))}" alt="" loading="lazy" decoding="async">
    </a>`;
}

/** To'yxona taomlari — matn qatorlari ro'yxati. */
export async function renderFeastList(selector, { limit = 8 } = {}) {
  const container = document.querySelector(selector);
  if (!container) return;

  container.innerHTML = `<div class="feast-list">${skeletonCards(4)}</div>`;

  try {
    const data = await api.showcase.venueMenu({ page_size: 30 });
    const items = shuffle(data.results || []).slice(0, limit);
    container.innerHTML = items.length
      ? `<div class="feast-list">${items.map(feastRowHtml).join("")}</div>`
      : emptyState(
          "To'yxona menyusi hali bo'sh",
          "To'yxonalar taom ro'yxatini kiritgach, shu yerda chiqadi.",
          "🎉"
        );
  } catch (error) {
    container.innerHTML = errorState(error.message);
  }
}
