/**
 * "Bronlarim" — alohida sahifa.
 *
 * Ilgari profil ichidagi ichki bo'lim edi. Endi o'z manzili bor
 * (`/bronlarim/`), shuning uchun havolani ulashish, sahifani
 * yangilash va "orqaga" tugmasi to'g'ri ishlaydi.
 */
import { api } from "../../core/api.js";
import { requireAuth } from "../../core/guard.js";
import { initI18n, t } from "../../core/i18n.js";
import { theme } from "../../core/theme.js";
import { $, render, esc } from "../../ui/dom.js";
import { initPublicNav } from "../../ui/public-nav.js";
import { initTopbar } from "../../ui/topbar.js";
import * as bookingsSection from "./sections/bookings.js";

theme.init();
await initI18n();
initPublicNav();
initTopbar();

const user = requireAuth();
if (user) start();

async function loadStats() {
  try {
    const me = await api.auth.me();
    const stats = me.stats || {};
    render("#booking-stats", [
      { value: stats.total ?? 0, key: "profile.statBookings" },
      { value: stats.upcoming ?? 0, key: "profile.statUpcoming", accent: true },
      { value: stats.completed ?? 0, key: "profile.statCompleted" },
      { value: stats.reviews ?? 0, key: "profile.statReviews" },
    ].map((item) => `
      <div class="stat-card">
        <span class="label">${esc(t(item.key))}</span>
        <span class="value ${item.accent ? "accent" : ""}">${item.value}</span>
      </div>`).join(""));
  } catch {
    render("#booking-stats", "");
  }
}

function start() {
  render("#bookings-root", bookingsSection.render());
  bookingsSection.bind();
  loadStats();
}
