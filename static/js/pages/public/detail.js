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
import { icon } from "../../ui/icons.js";
import { money, stars, imageUrl, timeLabel, dateLabel, initials, businessTypeLabel } from "../../ui/format.js";
import { openRoomBooking, openHallBooking, setBookingMenu } from "../../components/booking-modal.js";
import { mapLinksHtml, ROUTE_ICON } from "../../components/map-links.js";

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
          <button class="g-nav prev" type="button" data-gallery="-1" aria-label="Oldingi">${icon("chevronLeft", { size: 22 })}</button>
          <button class="g-nav next" type="button" data-gallery="1" aria-label="Keyingi">${icon("chevronRight", { size: 22 })}</button>
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

/**
 * Bo'limlar.
 *
 * To'yxonada "Narxlar" va "Taomlar" bo'limlari SHARTLI: qishloq
 * to'yxonasida kishi boshiga narx ham, to'yxonaning o'z menyusi ham
 * bo'lmasligi mumkin (oshpazni to'y egasi olib keladi). Bo'sh bo'limni
 * ko'rsatib, ichiga "ma'lumot yo'q" deb yozgandan ko'ra, uni umuman
 * chizmagan tozaroq.
 */
function tabsHtml() {
  const isVenue = business.business_type === "venue";
  const tabs = isVenue
    ? [
        ["halls", t("detail.halls")],
        business.menu?.length ? ["menu", t("detail.dishes")] : null,
        hasPerPersonPricing() ? ["pricing", t("detail.pricing")] : null,
        ["reviews", `${t("detail.reviews")} (${reviews.length})`],
      ].filter(Boolean)
    : [["menu", t("detail.menu")], ["rooms", t("detail.rooms")], ["reviews", `${t("detail.reviews")} (${reviews.length})`]];

  return `<div class="tabs" role="tablist">
    ${tabs.map(([key, label]) =>
      `<button class="tab ${activeTab === key ? "active" : ""}" data-tab="${key}" role="tab">${esc(label)}</button>`
    ).join("")}
  </div>`;
}

/**
 * Egasi taom paketlarini kiritganmi.
 *
 * `dish_pricing` ro'yxatining o'zi yetarli dalil: `pricing_mode` endi
 * `combined` ham bo'lishi mumkin (ijara + paketlar), shuning uchun
 * faqat `per_person` ga qarash "Narxlar" bo'limini yashirib qo'yardi.
 */
function hasPerPersonPricing() {
  return Boolean(business.dish_pricing?.length);
}

function roomsHtml() {
  if (!business.rooms?.length) return emptyState(t("common.empty"), "", icon("seat"));
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
          <button class="btn btn-primary btn-sm btn-block book-btn"
                  data-book-room="${esc(room.id)}">${esc(t("detail.book"))}</button>
        </div>
      </div>`).join("")}
  </div>`;
}

/**
 * Zal kartochkasi.
 *
 * Asosiy raqam — zalning BIR KUNLIK IJARASI (masalan 15 000 000 so'm).
 * To'y egasi shu summani to'lab zalni bir kunga oladi.
 *
 * Ovqat esa ALOHIDA va ixtiyoriy: egasi taom paketlari kiritgan bo'lsa,
 * ular "Narxlar" bo'limida kishi boshiga ko'rsatiladi va bron oynasida
 * tanlanadi. Ilgari bu ikkisi bir-birini INKOR qilardi — paketlar
 * bo'lsa ijara narxi umuman ko'rinmasdi, holbuki to'y egasi ikkalasini
 * ham to'laydi.
 */
function hallsHtml() {
  if (!business.halls?.length) return emptyState(t("common.empty"), "", icon("venue"));
  return `<div class="grid grid-auto">
    ${business.halls.map((hall) => `
      <div class="card">
        <img class="card-media card-media-sm" src="${esc(imageUrl(hall.photo))}" alt="${esc(hall.name)}" loading="lazy">
        <div class="card-body">
          <b>${esc(hall.name)}</b>
          <span class="small muted">${esc(t("detail.upTo", { count: hall.people }))}</span>
          ${hall.all_price
            ? `<span class="small strong">${esc(t("detail.dayRent"))}: ${money(hall.all_price)}</span>` : ""}
          <span class="seal seal-gold" style="align-self:flex-start">${esc(t("detail.deposit"))}: ${money(hall.deposit_amount)}</span>
          <button class="btn btn-primary btn-sm btn-block book-btn"
                  data-book-hall="${esc(hall.id)}">${esc(t("detail.book"))}</button>
        </div>
      </div>`).join("")}
  </div>`;
}

function menuHtml() {
  if (!business.menu?.length) return emptyState(t("common.empty"), "", icon("restaurant"));

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
    return emptyState(t("common.empty"), t("detail.priceNote"), icon("wallet"));
  }
  // Ijara ham bo'lsa, uni ALOHIDA aytamiz: aks holda "kishi boshiga
  // 120 000" degan raqamni ko'rgan odam butun summani shundan hisoblab,
  // bron oynasida kutilmagan qo'shimchani ko'rardi.
  const rents = (business.halls || []).filter((hall) => hall.all_price != null);
  const rentNote = rents.length
    ? `<p class="small strong" style="margin-bottom:var(--sp-2)">
         ${esc(t("detail.dayRent"))} alohida to'lanadi —
         ${money(Math.min(...rents.map((hall) => Number(hall.all_price))))} dan boshlab.
         Taom tanlash ixtiyoriy.
       </p>` : "";

  return `
    ${rentNote}
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
  if (!reviews.length) return emptyState(t("detail.noReviews"), t("detail.beFirst"), icon("star", { fill: true }));
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
    business.district ? ["mapPin", t("detail.district"), business.district] : null,
    business.address ? ["home", t("detail.address"), business.address] : null,
    !isVenue && business.open_time
      ? ["clock", t("detail.hours"), `${timeLabel(business.open_time)}–${timeLabel(business.close_time)}`]
      : null,
  ].filter(Boolean);

  const contacts = business.contacts_locked
    ? `<a class="biz-locked" href="${ROUTES.login}?next=${encodeURIComponent(window.location.pathname)}">
         <span class="ic">${icon("lock")}</span>
         <span>
           <b>${esc(t("detail.contactsLocked"))}</b>
           <span class="small">${esc(t("detail.contactsLockedText"))}</span>
         </span>
         <span class="go">${icon("chevronRight")}</span>
       </a>`
    : `<div class="biz-contacts">
         ${phone ? `
           <a class="biz-contact" href="tel:${esc(phone)}">
             <span class="ic">${icon("phone")}</span>
             <span><b>${esc(phone)}</b><span class="small">${esc(t("detail.callUs"))}</span></span>
           </a>` : ""}
         ${telegram ? `
           <a class="biz-contact tg" href="https://t.me/${esc(telegram.replace("@", ""))}"
              target="_blank" rel="noopener">
             <span class="ic">${icon("send")}</span>
             <span><b>${esc(telegram)}</b><span class="small">${esc(t("detail.writeUs"))}</span></span>
           </a>` : ""}
         ${!phone && !telegram
           ? `<p class="small muted">${esc(t("detail.noContacts"))}</p>` : ""}
       </div>`;

  // Joylashuv bloki aloqadan OLDIN: odam avval "qayerda?" deb so'raydi,
  // "qanday bog'lanaman?" degan savol undan keyin keladi.
  //
  // Kirmagan foydalanuvchiga aniq manzil ham, xarita ham KO'RINMAYDI —
  // server ularni umuman qaytarmaydi (`location_locked`). Uning
  // o'rniga aloqa blokidagi kabi "kirish kerak" kartochkasi chiziladi.
  const location = business.location_locked
    ? `<a class="biz-locked" href="${ROUTES.login}?next=${encodeURIComponent(window.location.pathname)}">
         <span class="ic">${icon("lock")}</span>
         <span>
           <b>${esc(t("detail.locationLocked"))}</b>
           <span class="small">${esc(t("detail.locationLockedText"))}</span>
         </span>
         <span class="go">${icon("chevronRight")}</span>
       </a>`
    : mapLinksHtml(business);

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
          ${rows.map(([iconName, label, value]) => `
            <div>
              <dt>${icon(iconName)} ${esc(label)}</dt>
              <dd>${esc(value)}</dd>
            </div>`).join("")}
        </dl>` : ""}

      ${location ? `
        <span class="biz-profile-label">${esc(t("detail.howToGet"))}</span>
        ${location}` : ""}

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
          ${business.district ? `<span>${icon("mapPin")} ${esc(business.district)}</span>` : ""}
          ${!isVenue && business.open_time
            ? `<span>${icon("clock")} ${timeLabel(business.open_time)}–${timeLabel(business.close_time)}</span>` : ""}
          ${business.map_links?.google_directions
            ? `<a class="meta-link" href="${esc(business.map_links.google_directions)}"
                  target="_blank" rel="noopener noreferrer">${ROUTE_ICON}${esc(t("detail.directions"))}</a>` : ""}
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
