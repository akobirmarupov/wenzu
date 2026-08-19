/**
 * Profil sahifasi.
 *
 * Bo'limlar ROLGA qarab yig'iladi:
 *   oddiy foydalanuvchi → ma'lumot, bronlar, premium, biznes ochish
 *   biznes egasi        → + biznesim (panelga qisqa yo'l)
 *   super-admin         → + boshqaruv
 *
 * Har bir bo'lim alohida modulda (`sections/`), bu fayl faqat
 * ularni bog'laydi — shunda bo'lim qo'shish bitta fayl qo'shish demak.
 */
import { api } from "../../core/api.js";
import { auth } from "../../core/auth.js";
import { requireAuth } from "../../core/guard.js";
import { ROUTES } from "../../core/config.js";
import { initI18n, t } from "../../core/i18n.js";
import { theme } from "../../core/theme.js";
import { $, render, delegate, esc, busy } from "../../ui/dom.js";
import { initPublicNav } from "../../ui/public-nav.js";
import { initTopbar } from "../../ui/topbar.js";
import { avatarHtml } from "../../ui/avatar.js";
import { toast } from "../../ui/toast.js";
import { confirmDialog } from "../../ui/modal.js";
import { dateLabel } from "../../ui/format.js";

import * as infoSection from "./sections/info.js";
import * as premiumSection from "./sections/premium.js";
import * as adminSection from "./sections/admin.js";

theme.init();
await initI18n();
initPublicNav();
initTopbar();

let user = requireAuth();
if (user) start();

/* ---------- bo'limlar ro'yxati ----------
   "Bronlarim" va "Biznes ochish" bu yerda YO'Q — ular alohida
   sahifalarga chiqarildi (`/bronlarim/`, `/biznes-ochish/`).
   Profil ichida ularga faqat qisqa yo'l kartochkalari qoladi. */
function sectionsFor(current) {
  const items = [
    { key: "info", icon: "👤", label: () => t("profile.info"), module: infoSection, group: "account" },
    { key: "premium", icon: "💎", label: () => t("premium.title"), module: premiumSection, group: "account" },
  ];

  if (current.is_staff) {
    items.push({ key: "admin", icon: "🛡", label: () => t("admin.title"), module: adminSection, group: "manage" });
  }
  return items;
}

/** Profil ichidagi qisqa yo'llar — alohida sahifalarga olib boradi. */
function shortcutsHtml(current) {
  const cards = [
    {
      href: ROUTES.myBookings,
      icon: "📅",
      title: t("profile.bookings"),
      text: t("bookingsPage.lead"),
    },
    {
      href: ROUTES.openBusiness,
      icon: current.business ? "🏢" : "✦",
      title: current.business ? t("business.mine") : t("nav.business"),
      text: current.business ? t("business.ownerHint") : t("business.trialNote"),
    },
  ];

  if (current.business) {
    cards.push({
      href: ROUTES.ownerHome,
      icon: "◈",
      title: t("business.goToPanel"),
      text: t("panel.overview"),
    });
  }

  return `
    <div class="panel">
      <div class="panel-head"><h2 class="display h3">${esc(t("profile.quickLinks"))}</h2></div>
      <div class="grid grid-auto-sm">
        ${cards.map((card) => `
          <a class="card card-link shortcut-card" href="${card.href}">
            <span class="ic" aria-hidden="true">${card.icon}</span>
            <b>${esc(card.title)}</b>
            <span class="small muted">${esc(card.text)}</span>
            <span class="go" aria-hidden="true">→</span>
          </a>`).join("")}
      </div>
    </div>`;
}

/* ---------- yuqoridagi cover ---------- */
function coverHtml(current) {
  const stats = current.stats || {};
  const statItems = [
    { value: stats.total ?? 0, key: "profile.statBookings" },
    { value: stats.completed ?? 0, key: "profile.statCompleted" },
    { value: stats.upcoming ?? 0, key: "profile.statUpcoming" },
    { value: stats.reviews ?? 0, key: "profile.statReviews" },
  ];

  const badges = [];
  if (current.is_staff) {
    badges.push(`<span class="profile-badge profile-badge-gold">🛡 ${esc(t("panel.roleAdmin"))}</span>`);
  } else if (current.business) {
    badges.push(`<span class="profile-badge profile-badge-gold">💎 ${esc(infoSection.roleName(current))}</span>`);
  } else {
    badges.push(`<span class="profile-badge">${esc(t("profile.roleUser"))}</span>`);
  }
  badges.push(
    current.is_phone_verified
      ? `<span class="profile-badge profile-badge-ok">✓ ${esc(t("profile.verified"))}</span>`
      : `<span class="profile-badge profile-badge-warn">! ${esc(t("profile.notVerified"))}</span>`
  );

  return `
    <div class="profile-head">
      <div class="profile-avatar avatar-slot">
        ${avatarHtml(current, { size: "xl", ring: true })}
        <label class="avatar-edit" for="avatar-input" title="${esc(t("profile.changePhoto"))}">
          <span aria-hidden="true">📷</span>
          <input type="file" id="avatar-input" accept="image/*" hidden>
        </label>
      </div>

      <div class="profile-identity">
        <h1 class="display">${esc(current.full_name || current.username)}</h1>
        <span class="handle">@${esc(current.username)} · ${esc(current.phone_number)}</span>
        ${current.bio ? `<p class="small" style="color:rgba(255,255,255,.78);max-width:52ch">${esc(current.bio)}</p>` : ""}
        <div class="profile-badges">${badges.join("")}</div>
      </div>

      <div class="stack stack-2" style="align-items:flex-end">
        <span class="small" style="color:rgba(255,255,255,.55)">
          ${esc(t("profile.memberSince"))}: ${dateLabel(current.date_joined)}
        </span>
        ${current.avatar
          ? `<button class="btn btn-outline-light btn-sm" type="button" data-remove-avatar>${esc(t("profile.removePhoto"))}</button>`
          : ""}
      </div>
    </div>

    <div class="profile-stats">
      ${statItems.map((item) => `
        <div class="profile-stat">
          <span class="value">${item.value}</span>
          <span class="label">${esc(t(item.key))}</span>
        </div>`).join("")}
    </div>`;
}

function menuHtml(current, activeKey) {
  const items = sectionsFor(current);
  const groups = [
    { key: "account", label: t("profile.groupAccount") },
    { key: "manage", label: t("profile.groupManage") },
  ];

  return groups
    .map((group) => {
      const groupItems = items.filter((item) => item.group === group.key);
      if (!groupItems.length) return "";
      return `
        <div class="nav-group-label">${esc(group.label)}</div>
        ${groupItems.map((item) => `
          <button type="button" data-section="${item.key}"
                  class="${activeKey === item.key ? "active" : ""}">
            <span class="ic" aria-hidden="true">${item.icon}</span>
            <span>${esc(item.label())}</span>
          </button>`).join("")}`;
    })
    .join("");
}

/* ---------- boshqaruv ---------- */
let activeKey = new URLSearchParams(window.location.search).get("tab") || "info";

async function paint() {
  render("#profile-cover", coverHtml(user));
  render("#profile-menu", menuHtml(user, activeKey));

  const section = sectionsFor(user).find((item) => item.key === activeKey) || sectionsFor(user)[0];
  activeKey = section.key;

  // Qisqa yo'llar faqat asosiy bo'limda ko'rinadi — Premium yoki
  // Boshqaruv ochilganda ular e'tiborni tortib turmasligi kerak.
  const shortcuts = activeKey === "info" ? shortcutsHtml(user) : "";
  render("#profile-content", section.module.render(user) + shortcuts);

  section.module.bind?.({
    onUpdated: (fresh) => {
      user = fresh;
      render("#profile-cover", coverHtml(user));
    },
    onGoToBusiness: () => {
      window.location.href = ROUTES.openBusiness;
    },
  });
  await section.module.load?.(user);
}

function switchTo(key) {
  activeKey = key;
  window.history.replaceState({}, "", `?tab=${key}`);
  paint();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function start() {
  // Profil to'liq ma'lumotini (statistika, bio, avatar) serverdan olamiz —
  // localStorage'dagi nusxa login paytidagi holatni saqlaydi va eskirgan
  // bo'lishi mumkin.
  try {
    user = await auth.refreshUser();
  } catch {
    /* eski nusxa bilan davom etamiz */
  }

  await paint();

  delegate("#profile-menu", "[data-section]", (button) => switchTo(button.dataset.section));

  // --- avatar yuklash ---
  document.addEventListener("change", async (event) => {
    if (event.target.id !== "avatar-input") return;
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("avatar", file);
    try {
      const fresh = await api.auth.uploadAvatar(formData);
      user = fresh;
      auth.setUser(fresh);
      render("#profile-cover", coverHtml(user));
      toast.ok(t("profile.photoUpdated"));
    } catch (error) {
      toast.fromError(error);
    } finally {
      event.target.value = "";
    }
  });

  document.addEventListener("click", async (event) => {
    if (!event.target.closest("[data-remove-avatar]")) return;
    const ok = await confirmDialog({
      title: t("profile.removePhoto"),
      message: t("profile.removePhotoText"),
      confirmText: t("common.delete"),
      danger: true,
    });
    if (!ok) return;
    try {
      const fresh = await api.auth.removeAvatar();
      user = fresh;
      auth.setUser(fresh);
      render("#profile-cover", coverHtml(user));
      toast.ok(t("profile.photoRemoved"));
    } catch (error) {
      toast.fromError(error);
    }
  });
}
