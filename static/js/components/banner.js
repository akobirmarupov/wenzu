/**
 * Reklama / e'lon banneri.
 *
 * Mazmuni admin paneldan keladi: matn, rasm yoki video. Bir nechta
 * banner bo'lsa — avtomatik almashadi va nuqtali navigatsiya chiqadi.
 * Banner umuman bo'lmasa, blok jimgina bo'sh qoladi (sahifa buzilmaydi).
 */
import { api } from "../core/api.js";
import { getLanguage } from "../core/i18n.js";
import { esc } from "../ui/dom.js";

const ROTATE_MS = 9000;

function slideHtml(banner) {
  const media =
    banner.media_type === "image" && banner.media_src
      ? `<div class="banner-media"><img src="${esc(banner.media_src)}" alt="" loading="lazy"></div>`
      : banner.media_type === "video" && banner.media_src
        ? `<div class="banner-media">
             <video src="${esc(banner.media_src)}" autoplay muted loop playsinline></video>
           </div>`
        : "";

  const cta =
    banner.cta_label && banner.cta_url
      ? `<div class="banner-actions">
           <a class="btn btn-gold btn-lg" href="${esc(banner.cta_url)}">${esc(banner.cta_label)}</a>
         </div>`
      : "";

  const accent = banner.accent_color
    ? ` style="--gold-shine:linear-gradient(115deg, ${esc(banner.accent_color)}, #FFF3C4, ${esc(banner.accent_color)})"`
    : "";

  return `
    <article class="banner"${accent}>
      ${media}
      <div class="banner-body">
        ${banner.subtitle ? `<span class="banner-eyebrow"><span>${esc(banner.subtitle)}</span></span>` : ""}
        <h2 class="display">${esc(banner.title)}</h2>
        ${banner.body ? `<p>${esc(banner.body)}</p>` : ""}
        ${cta}
      </div>
    </article>`;
}

/**
 * Bannerni konteynerga chizadi.
 * @param {string} selector - konteyner CSS selektori
 * @param {string} placement - hero | inline | sidebar
 */
export async function renderBanner(selector, placement = "hero") {
  const container = document.querySelector(selector);
  if (!container) return;

  let banners = [];
  try {
    banners = await api.banners({ placement, lang: getLanguage() });
  } catch {
    return; // banner yuklanmasa sahifa baribir to'liq ishlaydi
  }
  if (!banners.length) return;

  container.innerHTML = slideHtml(banners[0]);
  if (banners.length === 1) return;

  // Bir nechta banner — almashib turadi
  const dots = document.createElement("div");
  dots.className = "banner-dots";
  dots.innerHTML = banners
    .map((_, index) => `<button type="button" class="${index === 0 ? "active" : ""}"
      aria-label="Banner ${index + 1}"></button>`)
    .join("");
  container.querySelector(".banner").append(dots);

  let index = 0;
  let timer = null;

  const show = (next) => {
    index = (next + banners.length) % banners.length;
    container.innerHTML = slideHtml(banners[index]);
    container.querySelector(".banner").append(dots);
    dots.querySelectorAll("button").forEach((dot, i) => dot.classList.toggle("active", i === index));
  };

  dots.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    clearInterval(timer);
    show(Array.from(dots.children).indexOf(button));
    start();
  });

  const start = () => {
    timer = setInterval(() => show(index + 1), ROTATE_MS);
  };
  start();

  // Sahifa ko'rinmayotganda taymer ishlamasin — batareyani tejaydi.
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) clearInterval(timer);
    else start();
  });
}
