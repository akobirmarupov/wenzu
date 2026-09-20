/**
 * Profil sozlamalari — muqova burchagidagi uch chiziqli tugma ochadi.
 *
 * ===================================================================
 * BITTA EKRANDA BESHTA SATR, QOLGANI ICHIDA
 * ===================================================================
 * Ilgari oynada hamma narsa BIRDANIGA ochilib yotardi: hisob
 * amallari, til chiplari, tema chiplari, platforma havolalari va
 * chiqish — o'n bitta qator. Oyna telefon ekranidan uzun bo'lib
 * ketardi va uni aylantirib chiqish kerak edi.
 *
 * Endi boshlang'ich ekranda BESHTA satr bor:
 *   Tahrirlash · Til · Tema · Platforma haqida · Chiqish
 * Har biri o'z ichki ekranini ochadi, orqaga qaytarish tugmasi bilan.
 * Shunday qilib oyna har doim kichik qoladi: odam bir vaqtda faqat
 * bitta savolga qaraydi.
 *
 * "Tahrirlash" esa oynani yopib, to'liq tahrirlash shaklini ochadi
 * (`sections/info.js`) — u yerda maydonlar ham, rasm amallari ham bor.
 */
import { api } from "../core/api.js";
import { ROUTES } from "../core/config.js";
import { LANGUAGES, getLanguage, setLanguage, t } from "../core/i18n.js";
import { theme, effective } from "../core/theme.js";
import { esc } from "../ui/dom.js";
import { icon } from "../ui/icons.js";
import { modal } from "../ui/modal.js";

/* Pochta manzili platforma sozlamalarida YO'Q (`common/models.py` da
   faqat `admin_telegram_username` va `support_phone` bor), shuning
   uchun u poyloqdagi kabi shu yerda yozilgan. Ikkala joyda bir xil
   turishi kerak — bazaga maydon qo'shilsa, ikkalasi ham o'sha yerdan
   olinadigan bo'ladi. */
const SUPPORT_EMAIL = "uventgroups@gmail.com";

/** Platforma sozlamalari bir marta olinadi va oyna yopilgach ham qoladi. */
let platform = null;

function rowHtml({ action, ic, label, text, danger = false, go = false }) {
  return `
    <button class="ss-row${danger ? " is-danger" : ""}" type="button" data-ss="${esc(action)}">
      <span class="ss-ic">${icon(ic)}</span>
      <span class="ss-text">
        <b>${esc(label)}</b>
        ${text ? `<span>${esc(text)}</span>` : ""}
      </span>
      ${go ? icon("chevronRight", { className: "ss-go" }) : ""}
    </button>`;
}

function linkRowHtml({ href, ic, label, external = false }) {
  const attrs = external ? ' target="_blank" rel="noopener"' : "";
  return `
    <a class="ss-row" href="${esc(href)}"${attrs}>
      <span class="ss-ic">${icon(ic)}</span>
      <span class="ss-text"><b>${esc(label)}</b></span>
      ${icon("chevronRight", { className: "ss-go" })}
    </a>`;
}

/** Ichki ekranning sarlavhasi — chapda orqaga qaytarish tugmasi. */
function headHtml(title, { back = false } = {}) {
  return `
    <div class="ss-head">
      ${back
        ? `<button class="ss-back" type="button" data-ss-back
                   aria-label="${esc(t("common.back"))}">${icon("chevronLeft")}</button>`
        : ""}
      <h2 class="display h3">${esc(title)}</h2>
    </div>`;
}

/* ---------- ekranlar ---------- */

function rootHtml() {
  return `
    ${headHtml(t("profile.settingsTitle"))}
    <div class="ss-rows">
      ${rowHtml({ action: "edit", ic: "edit", label: t("profile.edit"), go: true })}
      ${rowHtml({ action: "lang", ic: "globe", label: t("nav.language"), go: true })}
      ${rowHtml({ action: "theme", ic: "sun", label: t("nav.theme"), go: true })}
      ${rowHtml({ action: "about", ic: "info", label: t("profile.aboutPlatform"), go: true })}
    </div>
    <div class="ss-rows">
      ${rowHtml({ action: "logout", ic: "logout", label: t("nav.logout"), danger: true })}
    </div>`;
}

function langViewHtml() {
  const current = getLanguage();
  return `
    ${headHtml(t("nav.language"), { back: true })}
    <div class="ss-rows">
      ${LANGUAGES.map((lang) => `
        <button class="ss-row" type="button" data-ss-lang="${esc(lang.code)}">
          <span class="ss-ic">${esc(lang.short)}</span>
          <span class="ss-text"><b>${esc(lang.label)}</b></span>
          ${lang.code === current ? icon("check", { className: "ss-tick" }) : ""}
        </button>`).join("")}
    </div>`;
}

function themeViewHtml() {
  const now = effective();
  const options = [
    { value: "light", ic: "sun", label: t("nav.themeLight") },
    { value: "dark", ic: "moon", label: t("nav.themeDark") },
  ];
  return `
    ${headHtml(t("nav.theme"), { back: true })}
    <div class="ss-rows">
      ${options.map((option) => `
        <button class="ss-row" type="button" data-ss-theme="${option.value}">
          <span class="ss-ic">${icon(option.ic)}</span>
          <span class="ss-text"><b>${esc(option.label)}</b></span>
          ${option.value === now ? icon("check", { className: "ss-tick" }) : ""}
        </button>`).join("")}
    </div>`;
}

function aboutViewHtml() {
  const telegram = platform?.admin_telegram || "";
  const phone = platform?.support_phone || "";

  return `
    ${headHtml(t("profile.aboutPlatform"), { back: true })}
    <div class="ss-rows">
      ${rowHtml({ action: "admin", ic: "send", label: t("profile.adminWrite"),
                  text: t("profile.adminWriteText"), go: Boolean(telegram) })}
      ${phone ? linkRowHtml({ href: `tel:${phone}`, ic: "phone", label: phone }) : ""}
      ${linkRowHtml({ href: `mailto:${SUPPORT_EMAIL}`, ic: "mail", label: SUPPORT_EMAIL })}
      ${linkRowHtml({ href: ROUTES.restaurants, ic: "restaurant", label: t("nav.restaurants") })}
      ${linkRowHtml({ href: ROUTES.venues, ic: "venue", label: t("nav.venues") })}
    </div>
    <p class="ss-note">${esc(t("footer.about"))}</p>`;
}

const VIEWS = {
  root: rootHtml,
  lang: langViewHtml,
  theme: themeViewHtml,
  about: aboutViewHtml,
};

/**
 * Sozlamalar oynasini ochadi.
 *
 * @param {object} user - joriy foydalanuvchi
 * @param {object} actions - {onEdit, onLogout}
 */
export function openSettingsSheet(user, { onEdit, onLogout } = {}) {
  const node = modal.open('<div class="settings-sheet" id="ss-view"></div>');
  // Oyna oddiy oynadan ENSIZ: ichida faqat qisqa satrlar bor va
  // 460 px da ular cho'zilib, o'rtasida katta bo'shliq qolardi.
  node.classList.add("modal-sheet");

  const view = node.querySelector("#ss-view");
  let current = "root";

  const paint = () => {
    view.innerHTML = VIEWS[current]();
  };
  paint();

  /* Aloqa ma'lumoti bir marta olinadi. Yuklanmasa "Platforma haqida"
     ekrani telefon raqamisiz chiqadi — qolgani baribir ishlaydi. */
  if (!platform) {
    api.settings()
      .then((settings) => {
        platform = settings;
        if (current === "about") paint();
      })
      .catch(() => { /* aloqa ma'lumotisiz davom etamiz */ });
  }

  node.addEventListener("click", (event) => {
    if (event.target.closest("[data-ss-back]")) {
      current = "root";
      paint();
      return;
    }

    const langButton = event.target.closest("[data-ss-lang]");
    if (langButton) {
      setLanguage(langButton.dataset.ssLang);
      return;
    }

    const themeButton = event.target.closest("[data-ss-theme]");
    if (themeButton) {
      theme.set(themeButton.dataset.ssTheme);
      // Belgi darhol ko'chadi: oyna ochiq turadi va odam natijani shu
      // yerda ko'rishi kerak.
      paint();
      return;
    }

    const row = event.target.closest("[data-ss]");
    if (!row) return;

    switch (row.dataset.ss) {
      case "lang":
      case "theme":
      case "about":
        current = row.dataset.ss;
        paint();
        break;
      case "edit":
        modal.close();
        onEdit?.();
        break;
      case "admin":
        if (platform?.admin_telegram) {
          window.open(`https://t.me/${platform.admin_telegram.replace("@", "")}`,
                      "_blank", "noopener");
        }
        break;
      case "logout":
        modal.close();
        onLogout?.();
        break;
      default:
        break;
    }
  });

  return node;
}
