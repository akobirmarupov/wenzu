/**
 * Bosh sahifa.
 *
 * Bo'limlar ataylab har xil turdagi ma'lumot beradi:
 *   qidiruv → spotlight (yangi joylar) → banner → yangiliklar →
 *   mashhur restoranlar → to'yxonalar → qanday ishlaydi → biznes ochish
 * Shunda sahifa bir xil kartochkalar ro'yxatiga aylanib qolmaydi.
 */
import { api } from "../../core/api.js";
import { ROUTES } from "../../core/config.js";
import { initI18n, t } from "../../core/i18n.js";
import { theme } from "../../core/theme.js";
import { $, render } from "../../ui/dom.js";
import { initPublicNav } from "../../ui/public-nav.js";
import { initTopbar } from "../../ui/topbar.js";
import { skeletonCards, emptyState, errorState } from "../../ui/state.js";
import { businessCards } from "../../components/business-card.js";
import { renderBanner } from "../../components/banner.js";
import { renderSpotlight } from "../../components/spotlight.js";
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

/* ---------- ma'lumot yuklash ---------- */
async function loadSection(selector, params) {
  const container = $(selector);
  container.innerHTML = skeletonCards(4);
  try {
    const data = await api.businesses.list(params);
    container.innerHTML = data.results.length
      ? businessCards(data.results)
      : emptyState(t("catalog.nothingFound"), t("catalog.tryOther"));
    return data;
  } catch (error) {
    container.innerHTML = errorState(error.message);
    return { count: 0, results: [] };
  }
}

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

(async function init() {
  // Banner va yangiliklar mustaqil — ular biznes ro'yxatini kutmaydi.
  renderBanner("#banner-slot", "hero");
  renderNews({
    stripSelector: "#news-strip",
    gridSelector: "#news-grid",
    sectionSelector: "#news-section",
  });

  const [restaurants, venues] = await Promise.all([
    loadSection("#top-restaurants", { type: "restaurant", page_size: 4 }),
    loadSection("#top-venues", { type: "venue", page_size: 3 }),
  ]);

  const reviewsTotal = [...restaurants.results, ...venues.results]
    .reduce((sum, business) => sum + (business.reviews_count || 0), 0);

  renderStats({
    restaurants: restaurants.count,
    venues: venues.count,
    reviews: reviewsTotal,
  });

  // Spotlight — eng yangi qo'shilgan joylar, tasodifiy tartibda.
  try {
    const fresh = await api.businesses.list({ page_size: 10 });
    const withPhoto = fresh.results.filter((business) => business.cover_photo);
    renderSpotlight("#spotlight", withPhoto.length ? withPhoto : fresh.results);
  } catch {
    $("#spotlight").innerHTML = "";
  }
})();
