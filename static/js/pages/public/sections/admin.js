/**
 * Profil — super-admin uchun "Boshqaruv" bo'limi.
 *
 * Bu yerda platformaning umumiy holati va tez-tez kerak bo'ladigan
 * amallarga qisqa yo'l turadi — admin har safar panelni kezib
 * yurmasligi uchun.
 */
import { api } from "../../../core/api.js";
import { t } from "../../../core/i18n.js";
import { $, esc } from "../../../ui/dom.js";
import { skeletonRows, errorState } from "../../../ui/state.js";
import { icon } from "../../../ui/icons.js";

/* `icon` — ikonka to'plamidagi nom, chizish paytida SVG ga aylanadi. */
const SHORTCUTS = [
  { href: "/boshqaruv/", icon: "grid", key: "panel.overview" },
  { href: "/boshqaruv/arizalar/", icon: "document", key: "panel.applications" },
  { href: "/boshqaruv/foydalanuvchilar/", icon: "users", key: "panel.users" },
  { href: "/boshqaruv/bizneslar/", icon: "building", key: "panel.businesses" },
  { href: "/boshqaruv/obunalar/", icon: "gem", key: "panel.subscriptions" },
  { href: "/boshqaruv/kontent/", icon: "megaphone", key: "panel.content" },
];

export function render() {
  return `<div id="admin-root">${skeletonRows(2)}</div>`;
}

export async function load() {
  const root = $("#admin-root");
  if (!root) return;

  let stats = null;
  try {
    const data = await api.admin.overview();
    stats = data.stats;
  } catch (error) {
    root.innerHTML = errorState(error.message);
    return;
  }

  root.innerHTML = `
    <div class="panel stack stack-5">
      <div class="panel-head" style="margin-bottom:0">
        <div class="stack stack-1">
          <span class="eyebrow">${esc(t("panel.roleAdmin"))}</span>
          <h2 class="display h2">${esc(t("admin.title"))}</h2>
        </div>
      </div>

      <div class="grid grid-4">
        <div class="stat-card">
          <span class="label">${esc(t("panel.users"))}</span>
          <span class="value">${stats.users_count}</span>
        </div>
        <div class="stat-card">
          <span class="label">${esc(t("panel.businesses"))}</span>
          <span class="value">${stats.businesses_count}</span>
        </div>
        <div class="stat-card">
          <span class="label">${esc(t("panel.applications"))}</span>
          <span class="value accent">${stats.pending_applications}</span>
        </div>
        <div class="stat-card">
          <span class="label">${esc(t("panel.bookings"))}</span>
          <span class="value">${stats.reservations_count}</span>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-head"><h2 class="display h3">${esc(t("admin.shortcuts"))}</h2></div>
      <div class="grid grid-auto-sm">
        ${SHORTCUTS.map((item) => `
          <a class="card card-link" href="${item.href}" style="padding:var(--sp-5)">
            <div>${icon(item.icon, { size: 26 })}</div>
            <b style="display:block;margin-top:var(--sp-2)">${esc(t(item.key))}</b>
          </a>`).join("")}
      </div>
    </div>`;
}
