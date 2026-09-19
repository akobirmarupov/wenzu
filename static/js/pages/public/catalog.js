/**
 * Restoranlar / to'yxonalar ro'yxati.
 *
 * Bitta modul ikkala sahifaga xizmat qiladi — turi `data-type` orqali
 * uzatiladi. Filtrlar URL'ga yoziladi, shunda havolani ulashish yoki
 * sahifani yangilash natijani yo'qotmaydi.
 */
import { api } from "../../core/api.js";
import { CUISINES } from "../../core/config.js";
import { t } from "../../core/i18n.js";
import { $, render, delegate, esc } from "../../ui/dom.js";
import { initI18n } from "../../core/i18n.js";
import { theme } from "../../core/theme.js";
import { initPublicNav } from "../../ui/public-nav.js";
import { initTopbar } from "../../ui/topbar.js";
import { skeletonCards, emptyState, errorState } from "../../ui/state.js";
import { paginationHtml } from "../../ui/pagination.js";
import { businessCards } from "../../components/business-card.js";
import { toast } from "../../ui/toast.js";

theme.init();
await initI18n();
initPublicNav();
initTopbar();

const TYPE = document.currentScript?.dataset.type
  || document.querySelector("script[data-type]")?.dataset.type
  || "restaurant";

const params = new URLSearchParams(window.location.search);

const filters = {
  type: TYPE,
  search: params.get("search") || "",
  cuisine: params.get("cuisine") || "",
  guests: params.get("guests") || "",
  lat: params.get("lat") || "",
  lng: params.get("lng") || "",
  radius_km: params.get("radius_km") || "",
  page: Number(params.get("page")) || 1,
};

/* ---------- filtr boshqaruvi ---------- */
if ($("#q")) $("#q").value = filters.search;
if ($("#guests")) $("#guests").value = filters.guests;

if ($("#cuisine-chips")) {
  render(
    "#cuisine-chips",
    [{ value: "", label: t("catalog.all") }, ...CUISINES]
      .map((item) => `<button class="chip ${filters.cuisine === item.value ? "active" : ""}"
                        data-cuisine="${esc(item.value)}" type="button">${esc(item.label)}</button>`)
      .join("")
  );
  delegate("#cuisine-chips", "[data-cuisine]", (button) => {
    filters.cuisine = button.dataset.cuisine;
    filters.page = 1;
    load();
  });
}

let debounce;
$("#q")?.addEventListener("input", (event) => {
  clearTimeout(debounce);
  debounce = setTimeout(() => {
    filters.search = event.target.value.trim();
    filters.page = 1;
    load();
  }, 350);
});

$("#guests")?.addEventListener("input", (event) => {
  clearTimeout(debounce);
  debounce = setTimeout(() => {
    filters.guests = event.target.value;
    filters.page = 1;
    load();
  }, 350);
});

$("#near-me")?.addEventListener("click", () => {
  if (filters.lat) {
    // Ikkinchi bosishda masofa filtri o'chadi.
    filters.lat = filters.lng = filters.radius_km = "";
    $("#near-me").classList.remove("active");
    load();
    return;
  }
  if (!navigator.geolocation) {
    toast.error("Brauzeringiz joylashuvni qo'llab-quvvatlamaydi.");
    return;
  }
  navigator.geolocation.getCurrentPosition(
    ({ coords }) => {
      filters.lat = coords.latitude.toFixed(6);
      filters.lng = coords.longitude.toFixed(6);
      filters.radius_km = "5";
      filters.page = 1;
      $("#near-me").classList.add("active");
      load();
    },
    () => toast.error("Joylashuvga ruxsat berilmadi.")
  );
});

delegate("#pager", "[data-action='page']", (button) => {
  filters.page = Number(button.dataset.page);
  load();
  window.scrollTo({ top: 0, behavior: "smooth" });
});

/* ---------- yuklash ---------- */
function syncUrl() {
  const next = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (key === "type" || !value || (key === "page" && value === 1)) return;
    next.set(key, value);
  });
  const query = next.toString();
  window.history.replaceState({}, "", query ? `?${query}` : window.location.pathname);
}

async function load() {
  const list = $("#list");
  list.innerHTML = skeletonCards(6);
  $("#pager").innerHTML = "";
  syncUrl();

  try {
    const data = await api.businesses.list(filters);
    $("#result-count").textContent = t("catalog.found", { count: data.count });
    list.innerHTML = data.results.length
      ? businessCards(data.results)
      : emptyState(t("catalog.nothingFound"), t("catalog.tryOther"));
    $("#pager").innerHTML = paginationHtml(data);
  } catch (error) {
    $("#result-count").textContent = t("common.error");
    list.innerHTML = errorState(error.message);
  }
}

if (filters.lat) $("#near-me")?.classList.add("active");
load();
