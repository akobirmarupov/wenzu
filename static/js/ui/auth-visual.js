/**
 * Kirish/ro'yxat sahifasining CHAP tomoni.
 *
 * Rasm va matn admin panelda boshqariladi: "Kontent → Bannerlar" da
 * joylashuvi `auth` bo'lgan banner yaratilsa, shu yerda o'sha chiqadi.
 * Banner bo'lmasa — standart zumrad gradient va standart matn qoladi,
 * ya'ni sahifa hech qachon bo'sh ko'rinmaydi.
 */
import { api } from "../core/api.js";
import { getLanguage } from "../core/i18n.js";
import { esc } from "./dom.js";

export async function initAuthVisual(selector = ".auth-visual") {
  const visual = document.querySelector(selector);
  if (!visual) return;

  let banner = null;
  try {
    const banners = await api.banners({ placement: "auth", lang: getLanguage() });
    banner = banners[0] || null;
  } catch {
    return; // standart ko'rinish qoladi
  }
  if (!banner) return;

  if (banner.media_type === "image" && banner.media_src) {
    visual.classList.add("has-photo");
    visual.style.setProperty("--auth-photo", `url("${banner.media_src}")`);
  }

  const title = visual.querySelector(".auth-text h2") || visual.querySelector("h2");
  const lead = visual.querySelector(".auth-text p") || visual.querySelector("p");

  if (title && banner.title) title.innerHTML = accentuate(banner.title);
  if (lead && banner.body) lead.textContent = banner.body;

  if (banner.subtitle) {
    const eyebrow = document.createElement("span");
    eyebrow.className = "auth-eyebrow";
    eyebrow.textContent = banner.subtitle;
    title?.before(eyebrow);
  }
}

/**
 * Sarlavhadagi urg'uli so'zni oltin rangga bo'yaydi.
 *
 * Admin matnni `*yulduzcha*` ichiga oladi — masalan
 * "Joyni *oldindan* band qiling" — va o'sha so'z `<em>` bo'lib chiqadi.
 *
 * Nega kerak: ilgari bu yerda `textContent` ishlatilardi va admin banner
 * qo'ygan zahoti shablondagi `<em>` yo'qolib, sarlavha butunlay oq bo'lib
 * qolardi — dizayndagi oltin urg'u faqat standart matndagina ko'rinardi.
 *
 * Belgisiz matn ham bemalol ishlaydi: shunchaki urg'usiz chiqadi.
 */
function accentuate(text) {
  return esc(text).replace(/\*([^*]+)\*/g, "<em>$1</em>");
}
