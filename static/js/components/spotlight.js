/**
 * "Yangi qo'shilganlar" karuseli.
 *
 * Rasmlar TASODIFIY tartibda ko'rsatiladi va har necha soniyada
 * almashadi — shunda bosh sahifa har safar yangicha ko'rinadi va
 * ro'yxatning oxiridagi joylar ham ko'rinish oladi.
 */
import { ROUTES } from "../core/config.js";
import { esc } from "../ui/dom.js";
import { imageUrl, stars, businessTypeLabel } from "../ui/format.js";
import { t } from "../core/i18n.js";

const ROTATE_MS = 5000;

/** Fisher–Yates aralashtirish — `sort(() => Math.random()-0.5)` noto'g'ri taqsimlaydi. */
function shuffle(list) {
  const copy = [...list];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

export function renderSpotlight(selector, businesses) {
  const container = document.querySelector(selector);
  if (!container) return;

  const items = shuffle(businesses).slice(0, 6);
  if (!items.length) {
    container.innerHTML = "";
    return;
  }

  container.innerHTML = `
    <div class="spotlight">
      ${items.map((business, index) => `
        <a class="spotlight-slide ${index === 0 ? "active" : ""}"
           href="${ROUTES.detail(business.id)}" data-slide="${index}"
           ${index === 0 ? "" : 'tabindex="-1" aria-hidden="true"'}>
          <img src="${esc(imageUrl(business.cover_photo))}" alt="${esc(business.name)}"
               loading="${index === 0 ? "eager" : "lazy"}">
        </a>`).join("")}

      <div class="spotlight-progress" aria-hidden="true">
        ${items.map((_, index) => `<span class="${index === 0 ? "active" : ""}"></span>`).join("")}
      </div>

      <div class="spotlight-caption" id="spotlight-caption"></div>
    </div>`;

  const slides = container.querySelectorAll(".spotlight-slide");
  const bars = container.querySelectorAll(".spotlight-progress span");
  const caption = container.querySelector("#spotlight-caption");

  const paint = (index) => {
    const business = items[index];
    slides.forEach((slide, i) => {
      slide.classList.toggle("active", i === index);
      slide.toggleAttribute("aria-hidden", i !== index);
      slide.tabIndex = i === index ? 0 : -1;
    });
    bars.forEach((bar, i) => bar.classList.toggle("active", i === index));

    caption.innerHTML = `
      <div>
        <span class="spotlight-badge">${esc(t("home.newPlaces"))}</span>
        <div class="name" style="margin-top:var(--sp-2)">${esc(business.name)}</div>
        <div class="meta">
          <span>${esc(businessTypeLabel(business.business_type))}</span>
          ${business.district ? `<span>· ${esc(business.district)}</span>` : ""}
          ${business.rating_avg ? `<span>· ${stars(business.rating_avg)}</span>` : ""}
        </div>
      </div>
      <span class="btn btn-gold btn-sm">${esc(t("detail.book"))} →</span>`;
  };

  paint(0);
  if (items.length === 1) return;

  let index = 0;
  let timer = null;
  const start = () => {
    timer = setInterval(() => {
      index = (index + 1) % items.length;
      paint(index);
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
