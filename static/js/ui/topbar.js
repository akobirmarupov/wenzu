/**
 * Yuqori panel — o'ng burchakda bildirishnoma qo'ng'irog'i, til
 * tanlagichi, tema tugmasi va foydalanuvchi bloki.
 *
 * MUHIM qoida: profilga o'tishning YAGONA yo'li shu yerdagi
 * foydalanuvchi tugmasi. Ilgari uchta yo'l bor edi — yon menyudagi
 * "Profil" bandi, yon menyu pastidagi karta va shu tugma — bu esa
 * "qaysi biri to'g'ri?" degan chalkashlik tug'dirardi. Chiqish (logout)
 * ham endi profil sahifasining ichida.
 *
 * Kirmagan foydalanuvchiga esa shu burchakda "Kirish" va "Ro'yxatdan
 * o'tish" tugmalari turadi.
 */
import { auth } from "../core/auth.js";
import { ROUTES } from "../core/config.js";
import { getLanguage, setLanguage, LANGUAGES, t } from "../core/i18n.js";
import { themeToggleHtml, bindThemeToggle } from "../core/theme.js";
import { $, esc } from "./dom.js";
import { avatarHtml } from "./avatar.js";
import { bellHtml, bindBell } from "./notifications.js";

function langSelectHtml() {
  const current = getLanguage();
  const active = LANGUAGES.find((lang) => lang.code === current) || LANGUAGES[0];

  return `
    <div class="lang-menu" data-lang-menu>
      <button class="lang-trigger" type="button" aria-haspopup="true" aria-expanded="false"
              title="${esc(t("nav.language"))}">
        <span class="globe" aria-hidden="true">🌐</span>
        <span class="code">${active.short}</span>
        <span class="caret" aria-hidden="true">▾</span>
      </button>
      <div class="lang-dropdown" role="menu" hidden>
        ${LANGUAGES.map((lang) => `
          <button type="button" role="menuitem" data-lang="${lang.code}"
                  class="${current === lang.code ? "active" : ""}">
            <span class="short">${lang.short}</span>
            <span>${esc(lang.label)}</span>
            ${current === lang.code ? '<span class="tick" aria-hidden="true">✓</span>' : ""}
          </button>`).join("")}
      </div>
    </div>`;
}

function userHtml() {
  const user = auth.user();
  if (!user) {
    return `
      <a class="btn btn-ghost btn-sm" href="${ROUTES.login}">${esc(t("nav.login"))}</a>
      <a class="btn btn-primary btn-sm" href="${ROUTES.login}">${esc(t("nav.register"))}</a>`;
  }
  return `
    <a class="topbar-user" href="${ROUTES.profile}" title="${esc(t("nav.profile"))}">
      ${avatarHtml(user, { size: "sm" })}
      <span class="name">${esc((user.full_name || "").split(" ")[0])}</span>
    </a>`;
}

/**
 * Yuqori panelni to'ldiradi.
 * @param {object} options - {showUser: boolean}
 */
export function initTopbar({ showUser = true } = {}) {
  const container = $("#topbar-right");
  if (!container) return;

  const signedIn = auth.isAuthenticated();

  container.innerHTML = `
    ${signedIn ? bellHtml() : ""}
    ${langSelectHtml()}
    ${themeToggleHtml()}
    ${showUser ? userHtml() : ""}`;

  bindThemeToggle(container);
  if (signedIn) bindBell(container);

  // --- til menyusi ---
  const menu = container.querySelector("[data-lang-menu]");
  const trigger = menu?.querySelector(".lang-trigger");
  const dropdown = menu?.querySelector(".lang-dropdown");

  const close = () => {
    if (!dropdown) return;
    dropdown.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
  };

  trigger?.addEventListener("click", (event) => {
    event.stopPropagation();
    const isOpen = !dropdown.hidden;
    dropdown.hidden = isOpen;
    trigger.setAttribute("aria-expanded", String(!isOpen));
  });

  dropdown?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-lang]");
    if (button) setLanguage(button.dataset.lang);
  });

  document.addEventListener("click", close);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") close();
  });
}
