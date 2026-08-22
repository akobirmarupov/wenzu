/**
 * Biznes detal sahifasi.
 *
 * Butun sahifa BITTA so'rov bilan to'ladi (`/api/businesses/{id}/`) —
 * backend galereya, xona/zal, menyu va narxlarni birga qaytaradi.
 */
import { api } from "../../core/api.js";
import { t } from "../../core/i18n.js";
import { ROUTES } from "../../core/config.js";
import { $, render, delegate, esc } from "../../ui/dom.js";
import { initI18n } from "../../core/i18n.js";
import { theme } from "../../core/theme.js";
import { initPublicNav } from "../../ui/public-nav.js";
import { initTopbar } from "../../ui/topbar.js";
import { emptyState, errorState } from "../../ui/state.js";
import { money, stars, imageUrl, timeLabel, dateLabel, initials, businessTypeLabel } from "../../ui/format.js";
import { openRoomBooking, openHallBooking, setBookingMenu } from "../../components/booking-modal.js";

theme.init();
await initI18n();
initPublicNav();
initTopbar();

const businessId = window.location.pathname.split("/").filter(Boolean)[1];
let business = null;
let reviews = [];
let activeTab = null;

async function load() {
  try {
    business = await api.businesses.detail(businessId);
    setBookingMenu(business.menu);
    activeTab = business.business_type === "venue" ? "halls" : "menu";
    const data = await api.businesses.reviews(businessId, { page_size: 10 });
    reviews = data.results || [];
    renderPage();
  } catch (error) {
    render("#detail-root", errorState(error.message));
  }
}

/**
 * Galereya — joyning BARCHA suratlari aylanib turadi.
 *
 * Restoran faqat kirish eshigini emas, ichkarisini, yo'lagini,
 * stollarini ham suratga oladi. Ilgari bu yerda bittasi katta, ikkitasi
 * kichik qilib qotirilgan edi va qolganlari umuman ko'rinmasdi — endi
 * hammasi navbat bilan chiqadi, pastda esa kichik nishonlar orqali
 * istalganiga o'tish mumkin.
 */
function galleryHtml() {
  const photos = galleryPhotos();

  return `
    <div class="detail-gallery" id="detail-gallery">
      <div class="stage">
        ${photos.map((src, index) => `
          <img class="${index === 0 ? "active" : ""}" data-slide="${index}"
               src="${esc(src)}" alt="${esc(business.name)}"
               loading="${index === 0 ? "eager" : "lazy"}" decoding="async">`).join("")}
        ${photos.length > 1 ? `
          <button class="g-nav prev" type="button" data-gallery="-1" aria-label="Oldingi">‹</button>
          <button class="g-nav next" type="button" data-gallery="1" aria-label="Keyingi">›</button>
          <span class="g-count"><b id="g-current">1</b> / ${photos.length}</span>` : ""}
      </div>
      ${photos.length > 1 ? `
        <div class="thumbs">
          ${photos.map((src, index) => `
            <button type="button" class="thumb ${index === 0 ? "active" : ""}" data-thumb="${index}">
              <img src="${esc(src)}" alt="" loading="lazy" decoding="async">
            </button>`).join("")}
        </div>` : ""}
    </div>`;
}

/** Muqova + galereya, takrorlanmagan holda. */
function galleryPhotos() {
  const list = [];
  if (business.cover_photo) list.push(business.cover_photo);
  (business.gallery || []).forEach((photo) => {
    if (photo.image && !list.includes(photo.image)) list.push(photo.image);
  });
  return list.length ? list : [imageUrl(null)];
}

/** Galereyani aylantirish — sahifa qayta chizilganda qaytadan ulanadi. */
function bindGallery() {
  const root = document.getElementById("detail-gallery");
  if (!root) return;

  const slides = root.querySelectorAll(".stage img");
  const thumbs = root.querySelectorAll("[data-thumb]");
  const counter = root.querySelector("#g-current");
  if (slides.length < 2) return;

  let index = 0;
  let timer = null;

  const show = (next) => {
    index = (next + slides.length) % slides.length;
    slides.forEach((img, i) => img.classList.toggle("active", i === index));
    thumbs.forEach((btn, i) => btn.classList.toggle("active", i === index));
    if (counter) counter.textContent = String(index + 1);
  };

  const start = () => { timer = setInterval(() => show(index + 1), 4500); };
  const stop = () => clearInterval(timer);

  root.querySelectorAll("[data-gallery]").forEach((button) => {
    button.addEventListener("click", () => {
      stop();
      show(index + Number(button.dataset.gallery));
      start();
    });
  });
  thumbs.forEach((button) => {
    button.addEventListener("click", () => {
      stop();
      show(Number(button.dataset.thumb));
      start();
    });
  });

  root.addEventListener("mouseenter", stop);
  root.addEventListener("mouseleave", start);
  document.addEventListener("visibilitychange", () => (document.hidden ? stop() : start()));
  start();
}

function tabsHtml() {
  const isVenue = business.business_type === "venue";
  const tabs = isVenue
    ? [["halls", t("detail.halls")], ["menu", t("detail.dishes")], ["pricing", t("detail.pricing")], ["reviews", `${t("detail.reviews")} (${reviews.length})`]]
    : [["menu", t("detail.menu")], ["rooms", t("detail.rooms")], ["reviews", `${t("detail.reviews")} (${reviews.length})`]];

  return `<div class="tabs" role="tablist">
    ${tabs.map(([key, label]) =>
      `<button class="tab ${activeTab === key ? "active" : ""}" data-tab="${key}" role="tab">${esc(label)}</button>`
    ).join("")}
  </div>`;
}

function roomsHtml() {
  if (!business.rooms?.length) return emptyState(t("common.empty"), "", "🪑");
  return `<div class="grid grid-auto">
    ${business.rooms.map((room) => `
      <div class="card">
        <img class="card-media card-media-sm" src="${esc(imageUrl(room.photo))}" alt="${esc(room.name)}" loading="lazy">
        <div class="card-body">
          <b>${esc(room.name)}</b>
          <span class="small muted">${esc(room.room_type_display)} · ${esc(t("detail.upTo", { count: room.capacity }))}</span>
          <span class="seal ${room.deposit_tier === "premium" ? "seal-gold" : "seal-ok"}" style="align-self:flex-start">
            ${esc(t("detail.deposit"))}: ${money(room.deposit_amount)}
          </span>
          <button class="btn btn-primary btn-sm btn-block" data-book-room="${esc(room.id)}"
                  style="margin-top:var(--sp-2)">${esc(t("detail.book"))}</button>
        </div>
      </div>`).join("")}
  </div>`;
}

function hallsHtml() {
  if (!business.halls?.length) return emptyState(t("common.empty"), "", "🏛️");
  return `<div class="grid grid-auto">
    ${business.halls.map((hall) => `
      <div class="card">
        <img class="card-media card-media-sm" src="${esc(imageUrl(hall.photo))}" alt="${esc(hall.name)}" loading="lazy">
        <div class="card-body">
          <b>${esc(hall.name)}</b>
          <span class="small muted">${esc(t("detail.upTo", { count: hall.people }))}</span>
          <span class="seal seal-gold" style="align-self:flex-start">${esc(t("detail.deposit"))}: ${money(hall.deposit_amount)}</span>
          <button class="btn btn-primary btn-sm btn-block" data-book-hall="${esc(hall.id)}"
                  style="margin-top:var(--sp-2)">${esc(t("detail.book"))}</button>
        </div>
      </div>`).join("")}
  </div>`;
}

function menuHtml() {
  if (!business.menu?.length) return emptyState(t("common.empty"), "", "🍽️");

  // Turkumlar bo'yicha guruhlaymiz — uzun ro'yxat shunday o'qiladi.
  const groups = new Map();
  business.menu.forEach((item) => {
    const key = item.category_display || "Boshqa";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  });

  return Array.from(groups.entries()).map(([category, items]) => `
    <h3 class="h4 display" style="margin:var(--sp-6) 0 var(--sp-3)">${esc(category)}</h3>
    <div class="menu-grid">
      ${items.map((item) => `
        <div class="menu-item">
          <img src="${esc(imageUrl(item.photo))}" alt="${esc(item.name)}" loading="lazy">
          <div class="body">
            <b class="small">${esc(item.name)}</b>
            ${item.price ? `<span class="xs strong">${money(item.price)}</span>` : ""}
            ${item.description ? `<span class="xs muted">${esc(item.description)}</span>` : ""}
          </div>
        </div>`).join("")}
    </div>`).join("");
}

function pricingHtml() {
  if (!business.dish_pricing?.length) {
    return emptyState(t("common.empty"), t("detail.priceNote"), "💰");
  }
  return `
    <p class="muted small" style="margin-bottom:var(--sp-4)">
      ${esc(t("detail.priceNote"))}
    </p>
    <div class="grid grid-3">
      ${business.dish_pricing.map((row) => `
        <div class="stat-card">
          <span class="label">${row.dish_count} ${esc(t("detail.dishCount"))}</span>
          <span class="value accent">${money(row.price_per_person, { withSuffix: false })}</span>
          <span class="small muted">${esc(t("detail.perPerson"))}</span>
        </div>`).join("")}
    </div>`;
}

function reviewsHtml() {
  if (!reviews.length) return emptyState(t("detail.noReviews"), t("detail.beFirst"), "⭐");
  return reviews.map((review) => `
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
    </div>`).join("");
}

function tabBody() {
  switch (activeTab) {
    case "rooms": return roomsHtml();
    case "halls": return hallsHtml();
    case "pricing": return pricingHtml();
    case "reviews": return reviewsHtml();
    default: return menuHtml();
  }
}

/**
 * Joyning kichik profil kartochkasi.
 *
 * Foydalanuvchi "bu qanaqa joy va u bilan qanday bog'lanaman?" degan
 * savolga bir joydan javob olsin: muqova, nom, reyting, manzil, ish
 * vaqti va aloqa.
 *
 * ALOQA QISMI kirmagan foydalanuvchiga YOPIQ. Yashirish serverda —
 * ochiq turgan raqam bir kunda spam-botlar ro'yxatiga tushadi. Bu yerda
 * faqat "nima uchun yopiq"ligi tushuntiriladi va kirishga yo'l ko'rsatiladi.
 */
function miniProfileHtml() {
  const isVenue = business.business_type === "venue";
  const telegram = business.telegram_username ? `@${business.telegram_username}` : null;
  const phone = business.phone_number;

  const rows = [
    business.district ? ["📍", t("detail.district"), business.district] : null,
    business.address ? ["🏠", t("detail.address"), business.address] : null,
    !isVenue && business.open_time
      ? ["🕗", t("detail.hours"), `${timeLabel(business.open_time)}–${timeLabel(business.close_time)}`]
      : null,
  ].filter(Boolean);

  const contacts = business.contacts_locked
    ? `<a class="biz-locked" href="${ROUTES.login}?next=${encodeURIComponent(window.location.pathname)}">
         <span class="ic" aria-hidden="true">🔒</span>
         <span>
           <b>${esc(t("detail.contactsLocked"))}</b>
           <span class="small">${esc(t("detail.contactsLockedText"))}</span>
         </span>
         <span class="go" aria-hidden="true">→</span>
       </a>`
    : `<div class="biz-contacts">
         ${phone ? `
           <a class="biz-contact" href="tel:${esc(phone)}">
             <span class="ic" aria-hidden="true">📞</span>
             <span><b>${esc(phone)}</b><span class="small">${esc(t("detail.callUs"))}</span></span>
           </a>` : ""}
         ${telegram ? `
           <a class="biz-contact tg" href="https://t.me/${esc(telegram.replace("@", ""))}"
              target="_blank" rel="noopener">
             <span class="ic" aria-hidden="true">✈️</span>
             <span><b>${esc(telegram)}</b><span class="small">${esc(t("detail.writeUs"))}</span></span>
           </a>` : ""}
         ${!phone && !telegram
           ? `<p class="small muted">${esc(t("detail.noContacts"))}</p>` : ""}
       </div>`;

  return `
    <aside class="biz-profile">
      <div class="biz-profile-head">
        <img src="${esc(imageUrl(business.cover_photo))}" alt="" loading="lazy">
        <div class="stack stack-1" style="min-width:0">
          <span class="eyebrow">${esc(businessTypeLabel(business.business_type))}</span>
          <b>${esc(business.name)}</b>
          <span class="rating">${stars(business.rating_avg)}
            <b>${Number(business.rating_avg || 0).toFixed(1)}</b>
            <span class="muted">(${business.reviews_count || 0})</span></span>
        </div>
      </div>

      ${rows.length ? `
        <dl class="biz-facts">
          ${rows.map(([icon, label, value]) => `
            <div>
              <dt><span aria-hidden="true">${icon}</span> ${esc(label)}</dt>
              <dd>${esc(value)}</dd>
            </div>`).join("")}
        </dl>` : ""}

      <span class="biz-profile-label">${esc(t("detail.contacts"))}</span>
      ${contacts}
    </aside>`;
}

function renderPage() {
  const isVenue = business.business_type === "venue";

  render("#detail-root", `
    ${galleryHtml()}

    <div class="detail-title">
      <div class="stack stack-2">
        <span class="eyebrow">${esc(businessTypeLabel(business.business_type))}${business.cuisine_display ? " · " + esc(business.cuisine_display) : ""}</span>
        <h1 class="display h1">${esc(business.name)}</h1>
        <div class="detail-meta">
          <span class="rating">${stars(business.rating_avg)}
            <b>${Number(business.rating_avg || 0).toFixed(1)}</b>
            <span class="muted">(${business.reviews_count || 0})</span></span>
          ${business.district ? `<span>📍 ${esc(business.district)}</span>` : ""}
          ${!isVenue && business.open_time
            ? `<span>🕗 ${timeLabel(business.open_time)}–${timeLabel(business.close_time)}</span>` : ""}
        </div>
      </div>
    </div>

    ${business.description ? `<p class="lede">${esc(business.description)}</p>` : ""}

    <div class="detail-split">
      <div style="min-width:0">
        ${tabsHtml()}
        <div id="tab-body">${tabBody()}</div>
      </div>
      ${miniProfileHtml()}
    </div>
  `);

  bindGallery();
}

/* ---------- hodisalar ---------- */
delegate("#detail-root", "[data-tab]", (button) => {
  activeTab = button.dataset.tab;
  renderPage();
});

delegate("#detail-root", "[data-book-room]", (button) => {
  const room = business.rooms.find((r) => r.id === button.dataset.bookRoom);
  if (room) openRoomBooking(business, room);
});

delegate("#detail-root", "[data-book-hall]", (button) => {
  const hall = business.halls.find((h) => h.id === button.dataset.bookHall);
  if (hall) openHallBooking(business, hall, business.dish_pricing);
});

load();
