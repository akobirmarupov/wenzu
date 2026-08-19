/**
 * Biznes kartochkasi — bosh sahifada ham, katalog sahifalarida ham
 * bir xil ko'rinishda ishlatiladi.
 */
import { ROUTES } from "../core/config.js";
import { esc } from "../ui/dom.js";
import { imageUrl, stars, businessTypeLabel } from "../ui/format.js";

export function businessCard(business) {
  const isVenue = business.business_type === "venue";
  const capacity = business.max_capacity;

  return `
    <a class="card card-link biz-card" href="${ROUTES.detail(business.id)}">
      <div class="biz-card-media">
        <img class="card-media" src="${esc(imageUrl(business.cover_photo))}"
             alt="${esc(business.name)}" loading="lazy">
        ${business.rating_avg ? `<span class="rating-badge">★ ${Number(business.rating_avg).toFixed(1)}</span>` : ""}
        ${business.distance_km !== undefined && business.distance_km !== null
          ? `<span class="distance-badge">${business.distance_km} km</span>` : ""}
      </div>
      <div class="card-body">
        <span class="name">${esc(business.name)}</span>
        <div class="meta">
          <span>${esc(business.district || businessTypeLabel(business.business_type))}</span>
          ${business.cuisine_display ? `<span>·</span><span>${esc(business.cuisine_display)}</span>` : ""}
        </div>
        <div class="foot">
          <span class="rating small">${stars(business.rating_avg)}
            <span class="muted">(${business.reviews_count || 0})</span></span>
          ${capacity ? `<span class="tag">${isVenue ? `${capacity} kishigacha` : `${capacity} o'rin`}</span>` : ""}
        </div>
      </div>
    </a>`;
}

export function businessCards(list) {
  return list.map(businessCard).join("");
}
