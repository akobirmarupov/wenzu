/** Panel — mijozlar sharhlari. */
import { api } from "../../core/api.js";
import { initOwnerPage } from "./shell.js";
import { $, render, delegate, esc } from "../../ui/dom.js";
import { skeletonRows, emptyState, errorState } from "../../ui/state.js";
import { paginationHtml } from "../../ui/pagination.js";
import { initials, stars, dateLabel } from "../../ui/format.js";

const filters = { page: 1 };
const session = await initOwnerPage();
if (session) init();

function init() {
  delegate("#pager", "[data-action='page']", (button) => {
    filters.page = Number(button.dataset.page);
    load();
  });
  loadStats();
  load();
}

async function loadStats() {
  try {
    const overview = await api.owner.overview();
    render("#review-stats", `
      <div class="stat-card"><span class="label">O'rtacha reyting</span>
        <span class="value accent">${Number(overview.stats.rating_avg || 0).toFixed(1)} ★</span></div>
      <div class="stat-card"><span class="label">Jami sharhlar</span>
        <span class="value">${overview.stats.reviews_count}</span></div>
      <div class="stat-card"><span class="label">Yakunlangan bronlar</span>
        <span class="value">${overview.stats.completed_reservations}</span></div>`);
  } catch {
    render("#review-stats", "");
  }
}

async function load() {
  $("#list").innerHTML = skeletonRows(4);
  try {
    const data = await api.owner.reviews({ ...filters, page_size: 10 });
    $("#list").innerHTML = data.results.length
      ? data.results.map((review) => `
        <div class="review">
          <div class="review-head">
            <span class="review-user">
              <span class="avatar">${esc(initials(review.user_name))}</span>
              ${esc(review.user_name)}
            </span>
            <span class="rating">${stars(review.rating)}</span>
          </div>
          ${review.comment ? `<p class="small" style="margin-top:var(--sp-2)">${esc(review.comment)}</p>` : ""}
          <span class="xs faint">${dateLabel(review.created_at)}</span>
        </div>`).join("")
      : emptyState("Hozircha sharhlar yo'q",
          "Sharh faqat yakunlangan bronlar uchun qoldiriladi.", "⭐");
    $("#pager").innerHTML = paginationHtml(data);
  } catch (error) {
    $("#list").innerHTML = errorState(error.message);
  }
}
