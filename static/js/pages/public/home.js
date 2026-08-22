/**
 * Bosh sahifa.
 *
 * Bo'limlar ataylab har xil turdagi ma'lumot beradi va HECH BIRI
 * takrorlanmaydi:
 *   qidiruv → rasm lentasi (yozuvsiz) → banner → restoran taomlari
 *   → to'yxona menyusi + yangiliklar → qanday ishlaydi → biznes ochish
 *
 * Joy kartochkalari ("mashhur restoranlar", "to'yxonalar") ataylab
 * OLIB TASHLANGAN: ular chap menyudagi katalog sahifalari bilan
 * bir xil narsani ko'rsatardi.
 */
import { api } from "../../core/api.js";
import { ROUTES } from "../../core/config.js";
import { initI18n, t } from "../../core/i18n.js";
import { theme } from "../../core/theme.js";
import { $, render } from "../../ui/dom.js";
import { initPublicNav } from "../../ui/public-nav.js";
import { initTopbar } from "../../ui/topbar.js";
import { renderBanner } from "../../components/banner.js";
import { renderPhotoMarquee } from "../../components/photo-marquee.js";
import { renderDishWall, renderFeastList } from "../../components/menu-showcase.js";
import { renderNews } from "../../components/news.js";
import { toast } from "../../ui/toast.js";

theme.init();
await initI18n();
initPublicNav();
initTopbar();

let activeType = "restaurant";

/* ---------- qidiruv paneli ---------- */
document.querySelectorAll(".home-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".home-tab").forEach((other) => {
      other.classList.remove("active");
      other.setAttribute("aria-selected", "false");
    });
    tab.classList.add("active");
    tab.setAttribute("aria-selected", "true");
    activeType = tab.dataset.type;
  });
});

$("#home-search").addEventListener("submit", (event) => {
  event.preventDefault();
  const query = $("#home-q").value.trim();
  const base = activeType === "venue" ? ROUTES.venues : ROUTES.restaurants;
  window.location.href = query ? `${base}?search=${encodeURIComponent(query)}` : base;
});

$("#near-me").addEventListener("click", () => {
  if (!navigator.geolocation) {
    toast.error(t("common.error"));
    return;
  }
  toast.show(t("common.loading"));
  navigator.geolocation.getCurrentPosition(
    ({ coords }) => {
      const base = activeType === "venue" ? ROUTES.venues : ROUTES.restaurants;
      window.location.href =
        `${base}?lat=${coords.latitude.toFixed(6)}&lng=${coords.longitude.toFixed(6)}&radius_km=5`;
    },
    () => toast.error(t("common.error"))
  );
});

function renderStats({ restaurants, venues, reviews }) {
  const items = [
    { value: restaurants, key: "home.statRestaurants" },
    { value: venues, key: "home.statVenues" },
    { value: reviews, key: "home.statReviews" },
  ];
  render(
    "#home-stats",
    items
      .map((item) => `
        <div class="home-stat">
          <span class="value">${item.value}</span>
          <span class="label">${t(item.key)}</span>
        </div>`)
      .join("")
  );
}

/**
 * Lenta uchun suratlar.
 *
 * Alohida yengil endpoint (`/showcase/photos/`) ishlatiladi: u muqova
 * rasmini ham, galereyani ham beradi — shunda bitta joyning tashqarisi,
 * yo'lagi, zallari ham lentada aylanib o'tadi, faqat kirish eshigi emas.
 */
async function loadMarquee() {
  try {
    const photos = await api.showcase.photos({ limit: 60 });
    renderPhotoMarquee(
      "#photo-marquee",
      photos.map((row) => ({ id: row.business, name: row.business_name, photo: row.image })),
      { rows: 2 }
    );
  } catch {
    $("#photo-marquee").innerHTML = "";
  }
}

(async function init() {
  // Banner, taomlar va yangiliklar bir-birini kutmaydi — har biri
  // tayyor bo'lishi bilan ekranga chiqadi.
  renderBanner("#banner-slot", "hero");
  renderNews({
    stripSelector: "#news-strip",
    gridSelector: "#news-grid",
    sectionSelector: "#news-section",
  });
  renderDishWall("#dish-wall", "#dish-dots");
  renderFeastList("#feast-list", { limit: 8 });
  loadMarquee();

  try {
    const [restaurants, venues] = await Promise.all([
      api.businesses.list({ type: "restaurant", page_size: 24 }),
      api.businesses.list({ type: "venue", page_size: 24 }),
    ]);

    const reviewsTotal = [...restaurants.results, ...venues.results]
      .reduce((sum, business) => sum + (business.reviews_count || 0), 0);

    renderStats({
      restaurants: restaurants.count,
      venues: venues.count,
      reviews: reviewsTotal,
    });
  } catch {
    // Raqamlar yuklanmasa sahifaning qolgan qismi baribir ishlaydi.
    render("#home-stats", "");
  }
})();
