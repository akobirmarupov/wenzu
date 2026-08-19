/**
 * Til va tema boshqaruvi — yon menyusi yo'q sahifalar uchun
 * (kirish, ro'yxatdan o'tish, tasdiqlash).
 */
import { getLanguage, setLanguage, LANGUAGES, t } from "../core/i18n.js";
import { themeToggleHtml, bindThemeToggle } from "../core/theme.js";
import { esc } from "./dom.js";

export function renderControls(selector) {
  const container = document.querySelector(selector);
  if (!container) return;

  const current = getLanguage();
  container.innerHTML = `
    <div class="lang-switch" role="group" aria-label="${esc(t("nav.language"))}">
      ${LANGUAGES.map((lang) => `
        <button type="button" data-lang="${lang.code}"
                class="${current === lang.code ? "active" : ""}"
                title="${esc(lang.label)}">${lang.short}</button>`).join("")}
    </div>
    ${themeToggleHtml()}`;

  container.querySelectorAll("[data-lang]").forEach((button) => {
    button.addEventListener("click", () => setLanguage(button.dataset.lang));
  });
  bindThemeToggle(container);
}
