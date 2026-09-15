/**
 * Biznes kartochkasi — bosh sahifada ham, katalog sahifalarida ham
 * bir xil ko'rinishda ishlatiladi.
 */
import { ROUTES } from "../core/config.js";
import { t } from "../core/i18n.js";
import { esc } from "../ui/dom.js";
import { imageUrl, stars, money, businessTypeLabel } from "../ui/format.js";
import { mapPinHtml } from "./map-links.js";

export function businessCard(business) {
  const isVenue = business.business_type === "venue";

  // O'RIN — sharhlardagi yulduzlar yig'indisi bo'yicha (`Business.rank`).
  //
  // Ilgari bu yerda xonaning sig'imi turardi ("20 o'rin") va u hech
  // qachon o'zgarmasdi: barcha restoranlarda deyarli bir xil edi va
  // mijozga hech narsa aytmasdi. O'rin esa haqiqiy ma'lumot beradi —
  // joy boshqalar orasida qayerda turibdi.
  //
  // Hali sharh olmagan joyda `rank` bo'lishi mumkin, lekin ball nol —
  // bunday joyni "1-o'rin" deb ko'rsatish yolg'on bo'lardi, shuning
  // uchun u o'rniga "Yangi" deb belgilanadi.
  const ranked = business.rank > 0 && business.rating_points > 0;
  // Yozuv BUTUNLIGICHA tarjimadan keladi ("{n}-o'rin", "{n}-е место",
  // "#{n}"). Raqam va so'zni kodda birlashtirsak, inglizchada
  // "10-place" kabi g'aliz ibora chiqardi — tartib son har tilda
  // boshqacha yasaladi.
  const rankTag = ranked
    ? `<span class="rank-tag">${esc(t("catalog.rank", { n: business.rank }))}</span>`
    : `<span class="tag">${esc(t("catalog.newPlace"))}</span>`;

  // To'yxonada mijoz ikki narsani birinchi so'raydi: nechta odam
  // sig'adi va bir kunlik ijara qancha. Restoranda ikkalasi ham
  // ma'nosiz — u yerda stol soatlab band qilinadi.
  const facts = isVenue
    ? [
        business.max_capacity
          ? t("catalog.upToPeople", { count: business.max_capacity })
          : null,
        business.min_day_price
          ? t("catalog.fromPrice", { price: money(business.min_day_price) })
          : null,
      ].filter(Boolean)
    : [];

  return `
    <a class="card card-link biz-card" href="${ROUTES.detail(business.id)}">
      <div class="biz-card-media">
        <img class="card-media" src="${esc(imageUrl(business.cover_photo))}"
             alt="${esc(business.name)}" loading="lazy">
        ${business.rating_avg ? `<span class="rating-badge">★ ${Number(business.rating_avg).toFixed(1)}</span>` : ""}
        ${business.distance_km !== undefined && business.distance_km !== null
          ? `<span class="distance-badge">${business.distance_km} km</span>` : ""}
        ${mapPinHtml(business)}
      </div>
      <div class="card-body">
        <span class="name">${esc(business.name)}</span>
        <div class="meta">
          <span>${esc(business.district || businessTypeLabel(business.business_type))}</span>
          ${business.cuisine_display ? `<span>·</span><span>${esc(business.cuisine_display)}</span>` : ""}
        </div>
        ${business.address ? `<span class="addr">📍 ${esc(business.address)}</span>` : ""}
        <div class="foot">
          <span class="rating small">${stars(business.rating_avg)}
            <span class="muted">(${business.reviews_count || 0})</span></span>
          ${rankTag}
        </div>
        ${facts.length ? `<span class="facts">${facts.map(esc).join(" · ")}</span>` : ""}
      </div>
    </a>`;
}

export function businessCards(list) {
  return list.map(businessCard).join("");
}
