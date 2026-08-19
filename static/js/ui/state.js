/**
 * Yuklanish, bo'shlik va xato holatlari.
 *
 * Har bir ro'yxat uchun bir xil ko'rinish: skeleton → ma'lumot yoki
 * bo'sh holat. Foydalanuvchi hech qachon bo'm-bo'sh oq ekranga qaramaydi.
 */
import { esc } from "./dom.js";

export function skeletonCards(count = 6) {
  return Array.from({ length: count }, () => '<div class="skeleton skeleton-card"></div>').join("");
}

export function skeletonRows(count = 5) {
  return Array.from({ length: count }, () => '<div class="skeleton skeleton-row"></div>').join("");
}

export function emptyState(title, subtitle = "", icon = "🔎") {
  return `
    <div class="empty-state">
      <div class="icon">${icon}</div>
      <h3>${esc(title)}</h3>
      ${subtitle ? `<p class="small">${esc(subtitle)}</p>` : ""}
    </div>`;
}

export function errorState(message, { retryAction = "" } = {}) {
  return `
    <div class="empty-state">
      <div class="icon">⚠️</div>
      <h3>Ma'lumotni yuklab bo'lmadi</h3>
      <p class="small">${esc(message)}</p>
      ${retryAction ? `<button class="btn btn-outline btn-sm" data-action="${esc(retryAction)}" style="margin-top:var(--sp-3)">Qayta urinish</button>` : ""}
    </div>`;
}

/**
 * Ro'yxat yuklashning umumiy naqshi:
 * skeleton ko'rsat → so'rov yubor → chiz yoki xato ko'rsat.
 */
export async function loadInto(container, { loader, render, skeleton, empty }) {
  if (!container) return null;
  container.innerHTML = skeleton || skeletonRows(4);
  try {
    const data = await loader();
    const items = Array.isArray(data) ? data : data?.results;
    if (Array.isArray(items) && items.length === 0 && empty) {
      container.innerHTML = empty;
      return data;
    }
    container.innerHTML = render(data);
    return data;
  } catch (error) {
    container.innerHTML = errorState(error.message);
    return null;
  }
}
