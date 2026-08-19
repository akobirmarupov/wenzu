/**
 * Sahifalash boshqaruvi.
 * Backend `{count, total_pages, current_page, next, previous, results}`
 * qaytaradi — shu shaklga moslangan.
 */
import { esc } from "./dom.js";

export function paginationHtml(meta, { action = "page" } = {}) {
  if (!meta || (meta.total_pages || 1) <= 1) return "";
  const current = meta.current_page || 1;
  const total = meta.total_pages || 1;

  return `
    <nav class="pagination" aria-label="Sahifalash">
      <button class="btn btn-outline btn-sm" data-action="${esc(action)}" data-page="${current - 1}"
        ${current <= 1 ? "disabled" : ""}>← Oldingi</button>
      <span class="page-info">${current} / ${total}</span>
      <button class="btn btn-outline btn-sm" data-action="${esc(action)}" data-page="${current + 1}"
        ${current >= total ? "disabled" : ""}>Keyingi →</button>
    </nav>`;
}
