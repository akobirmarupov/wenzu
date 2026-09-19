/**
 * Yuklanish, bo'shlik va xato holatlari.
 *
 * Har bir ro'yxat uchun bir xil ko'rinish: skeleton → ma'lumot yoki
 * bo'sh holat. Foydalanuvchi hech qachon bo'm-bo'sh oq ekranga qaramaydi.
 */
import { t } from "../core/i18n.js";
import { esc } from "./dom.js";
import { icon } from "./icons.js";

export function skeletonCards(count = 6) {
  return Array.from({ length: count }, () => '<div class="skeleton skeleton-card"></div>').join("");
}

export function skeletonRows(count = 5) {
  return Array.from({ length: count }, () => '<div class="skeleton skeleton-row"></div>').join("");
}

// Uchinchi argument — tayyor HTML (odatda `icon(...)` natijasi), shuning
// uchun sahifalar o'z ikonkasini shu ko'rinishda uzatadi.
export function emptyState(title, subtitle = "", glyph = icon("search")) {
  return `
    <div class="empty-state">
      <div class="icon">${glyph}</div>
      <h3>${esc(title)}</h3>
      ${subtitle ? `<p class="small">${esc(subtitle)}</p>` : ""}
    </div>`;
}

export function errorState(message, { retryAction = "" } = {}) {
  return `
    <div class="empty-state">
      <div class="icon">${icon("alert")}</div>
      <h3>${esc(t("common.loadFailed"))}</h3>
      <p class="small">${esc(message)}</p>
      ${retryAction ? `<button class="btn btn-outline btn-sm" data-action="${esc(retryAction)}" style="margin-top:var(--sp-3)">${esc(t("common.retry"))}</button>` : ""}
    </div>`;
}
