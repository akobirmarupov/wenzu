/**
 * Reklama / e'lon banneri.
 *
 * Mazmuni admin paneldan keladi: matn, rasm yoki video.
 *
 * ALMASHISH QOIDASI turga qarab boshqacha:
 *   video       — kadr TUGAGUNCHA turadi, keyin keyingisiga o'tadi
 *   rasm/matn   — 12 soniya turadi
 *
 * Nega shunday: videoni yarmida uzib qo'yish reklama uchun eng yomon
 * narsa — mijoz gapning oxirini eshitmaydi. Rasm va matnni esa aksincha
 * uzoq ushlab turishning ma'nosi yo'q, 12 soniyada o'qib bo'linadi.
 *
 * Banner umuman bo'lmasa, blok jimgina bo'sh qoladi (sahifa buzilmaydi).
 */
import { api } from "../core/api.js";
import { getLanguage } from "../core/i18n.js";
import { esc } from "../ui/dom.js";

/** Rasm va matnli banner shuncha turadi. */
const STATIC_MS = 12000;

/**
 * Video uchun zaxira chegara.
 *
 * `ended` hodisasi har doim ham kelmaydi: fayl buzilgan bo'lishi, tarmoq
 * uzilishi yoki brauzer avtoijroni to'sib qo'yishi mumkin. Bunday holatda
 * banner MANGU o'sha kadrda qotib qolardi — shuning uchun oxirgi chora
 * sifatida taymer ham qo'yiladi.
 */
const VIDEO_FALLBACK_MS = 30000;

function slideHtml(banner, { loopVideo }) {
  // Video bannerda tuzilish boshqacha: matn chapda, video o'ngda TO'LIQ
  // ko'rinadi. Video fon qilinsa, ustidagi qorong'i parda uni bosib
  // ketardi va kadr amalda bilinmasdi.
  const isVideo = banner.media_type === "video" && banner.media_src;

  const media =
    banner.media_type === "image" && banner.media_src
      ? `<div class="banner-media"><img src="${esc(banner.media_src)}" alt="" loading="lazy"></div>`
      : isVideo
        ? `<div class="banner-media">
             <video src="${esc(banner.media_src)}" autoplay muted playsinline
                    ${loopVideo ? "loop" : ""}
                    preload="metadata" controls controlslist="nodownload"></video>
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
    <article class="banner ${isVideo ? "banner-video" : ""}"${accent}>
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
 * @param {string} placement - hero | inline | sidebar | auth
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

  // Bitta banner — almashadigan narsa yo'q, video esa aylanaversin.
  if (banners.length === 1) {
    container.innerHTML = slideHtml(banners[0], { loopVideo: true });
    return;
  }

  const dots = document.createElement("div");
  dots.className = "banner-dots";
  dots.innerHTML = banners
    .map((_, index) => `<button type="button" class="${index === 0 ? "active" : ""}"
      aria-label="Banner ${index + 1}"></button>`)
    .join("");

  let index = -1;
  let timer = null;
  let paused = false;

  // Har bir kadrga o'z raqami beriladi.
  //
  // Kerak bo'lish sababi: bitta kadrni ikki narsa oldinga surishi mumkin —
  // videoning `ended` hodisasi va zaxira taymer. Ikkalasi ham ishlab
  // ketsa, banner bitta o'rniga ikkita kadr sakrab ketardi. Raqam mos
  // kelmasa, kechikkan chaqiruv e'tiborsiz qoldiriladi.
  let generation = 0;

  const clearTimer = () => {
    clearTimeout(timer);
    timer = null;
  };

  /** @param {number} at - qaysi kadrdan chaqirilgani */
  const advance = (at) => {
    if (at !== generation) return;
    show(index + 1);
  };

  /** Joriy kadr qancha turishini va qachon o'tishini hal qiladi. */
  function schedule() {
    clearTimer();
    if (paused) return;

    const at = generation;
    const video = container.querySelector(".banner-media video");

    // Rasm yoki matn — belgilangan vaqt.
    if (!video) {
      timer = setTimeout(() => advance(at), STATIC_MS);
      return;
    }

    // Video TUGAGUNCHA kutamiz. `once: true` — kadr almashgach eshituvchi
    // o'zi o'chadi; element ham innerHTML bilan almashadi.
    video.addEventListener("ended", () => advance(at), { once: true });
    video.addEventListener("error", () => advance(at), { once: true });

    // Zaxira: `ended` kelmasa ham banner qotib qolmasin.
    const known = Number.isFinite(video.duration) && video.duration > 0;
    timer = setTimeout(
      () => advance(at),
      known ? video.duration * 1000 + 1500 : VIDEO_FALLBACK_MS
    );

    // Uzunligi odatda keyinroq ma'lum bo'ladi — o'shanda chegarani
    // aniqlashtiramiz, aks holda qisqa video 30 soniya turib qolardi.
    video.addEventListener(
      "loadedmetadata",
      () => {
        if (paused || at !== generation) return;
        if (!Number.isFinite(video.duration) || video.duration <= 0) return;
        clearTimer();
        timer = setTimeout(() => advance(at), video.duration * 1000 + 1500);
      },
      { once: true }
    );
  }

  function show(nextIndex) {
    clearTimer();
    generation += 1;
    index = (nextIndex + banners.length) % banners.length;

    // Bir nechta banner bo'lganda video TAKRORLANMAYDI — aks holda
    // `ended` hech qachon kelmasdi va lenta o'sha kadrda qolib ketardi.
    container.innerHTML = slideHtml(banners[index], { loopVideo: false });
    container.querySelector(".banner").append(dots);
    dots.querySelectorAll("button").forEach((dot, i) => dot.classList.toggle("active", i === index));

    schedule();
  }

  dots.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    show(Array.from(dots.children).indexOf(button));
  });

  // Sahifa ko'rinmayotganda taymer ishlamasin — batareyani tejaydi va
  // foydalanuvchi qaytganda reklama boshidan ko'rinadi.
  document.addEventListener("visibilitychange", () => {
    paused = document.hidden;
    if (paused) clearTimer();
    else schedule();
  });

  show(0);
}
