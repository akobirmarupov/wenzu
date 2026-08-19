/**
 * Panel yon menyusi (biznes egasi va super-admin).
 *
 * Menyu bandlari ROLGA qarab quriladi — restoran egasida "Xonalar",
 * to'yxona egasida "Zallar", adminda butunlay boshqa ro'yxat. Bu farq
 * shu faylda bir marta belgilangan, sahifalar bu haqda bilmaydi.
 */
import { auth } from "../core/auth.js";
import { t } from "../core/i18n.js";
import { $, esc } from "./dom.js";

const OWNER_COMMON = [
  { href: "/panel/", icon: "◈", label: () => t("panel.overview") },
  { href: "/panel/bronlar/", icon: "📅", label: () => t("panel.bookings"), badge: "pending" },
];
const OWNER_RESTAURANT = [{ href: "/panel/xonalar/", icon: "🪑", label: () => t("panel.rooms") }];
const OWNER_VENUE = [{ href: "/panel/zallar/", icon: "🏛", label: () => t("panel.halls") }];
const OWNER_TAIL = [
  { href: "/panel/menyu/", icon: "🍽", label: () => t("panel.menu") },
  { href: "/panel/jadval/", icon: "🗓", label: () => t("panel.schedule") },
  { href: "/panel/sharhlar/", icon: "★", label: () => t("panel.reviews") },
];
const OWNER_ACCOUNT = [
  { href: "/panel/obuna/", icon: "💎", label: () => t("panel.subscription") },
  { href: "/panel/sozlamalar/", icon: "⚙", label: () => t("panel.settings") },
];

const ADMIN_MAIN = [
  { href: "/boshqaruv/", icon: "◈", label: () => t("panel.overview") },
  { href: "/boshqaruv/arizalar/", icon: "📝", label: () => t("panel.applications"), badge: "applications" },
];
const ADMIN_MANAGE = [
  { href: "/boshqaruv/foydalanuvchilar/", icon: "👥", label: () => t("panel.users") },
  { href: "/boshqaruv/bizneslar/", icon: "🏢", label: () => t("panel.businesses") },
  { href: "/boshqaruv/obunalar/", icon: "💎", label: () => t("panel.subscriptions") },
];
const ADMIN_CONTENT = [
  { href: "/boshqaruv/kontent/", icon: "📢", label: () => t("panel.content") },
  { href: "/boshqaruv/sozlamalar/", icon: "⚙", label: () => t("panel.settings") },
];

export function isAdminUser(user) {
  return Boolean(user?.is_staff && !user?.business);
}

function panelFor(user) {
  if (isAdminUser(user)) return "admin";
  return user?.business?.type === "venue" ? "venue" : "restaurant";
}

function roleLabel(user) {
  if (isAdminUser(user)) return t("panel.roleAdmin");
  return user?.business?.type === "venue" ? t("panel.roleVenue") : t("panel.roleRestaurant");
}

function itemHtml(item, path) {
  const active = item.href === path;
  return `
    <a class="nav-item ${active ? "active" : ""}" href="${item.href}">
      <span class="ic" aria-hidden="true">${item.icon}</span>
      <span>${esc(item.label())}</span>
      ${item.badge ? `<span class="count-pill" data-badge="${item.badge}" hidden>0</span>` : ""}
    </a>`;
}

function groupHtml(label, items, path) {
  return `
    <div class="nav-group-label">${esc(label)}</div>
    ${items.map((item) => itemHtml(item, path)).join("")}`;
}

/** Yon menyuni chizadi va panel aksentini o'rnatadi. */
export function initSidebar(user) {
  const sidebar = $("#sidebar");
  if (!sidebar || !user) return user;

  sidebar.classList.add("panel");
  document.documentElement.setAttribute("data-panel", panelFor(user));

  const path = window.location.pathname;
  const admin = isAdminUser(user);

  const body = admin
    ? `${ADMIN_MAIN.map((item) => itemHtml(item, path)).join("")}
       ${groupHtml(t("panel.groupManage"), ADMIN_MANAGE, path)}
       ${groupHtml(t("panel.groupContent"), ADMIN_CONTENT, path)}`
    : `${OWNER_COMMON.map((item) => itemHtml(item, path)).join("")}
       ${groupHtml(t("panel.groupPlace"),
         [...(user.business?.type === "venue" ? OWNER_VENUE : OWNER_RESTAURANT), ...OWNER_TAIL], path)}
       ${groupHtml(t("panel.groupAccount"), OWNER_ACCOUNT, path)}`;

  sidebar.innerHTML = `
    <a class="brand" href="/"><span class="dot"></span>WENZU</a>
    <span class="role-pill">${esc(roleLabel(user))}</span>
    ${body}
    <div class="side-nav-bottom">
      ${admin ? "" : `<a class="nav-item" href="/"><span class="ic">🌐</span><span>${esc(t("nav.home"))}</span></a>`}
      <a class="nav-item" href="/profil/"><span class="ic">👤</span><span>${esc(t("nav.profile"))}</span></a>
      <button class="nav-item" type="button" data-logout>
        <span class="ic">↩</span><span>${esc(t("nav.logout"))}</span>
      </button>
    </div>`;

  sidebar.querySelector("[data-logout]")?.addEventListener("click", () => auth.logout());

  // Mobil: gamburger va orqa fon
  const scrim = $("#nav-scrim");
  const close = () => {
    sidebar.classList.remove("open");
    if (scrim) scrim.hidden = true;
  };
  $("[data-nav-toggle]")?.addEventListener("click", () => {
    sidebar.classList.toggle("open");
    if (scrim) scrim.hidden = !sidebar.classList.contains("open");
  });
  scrim?.addEventListener("click", close);
  sidebar.addEventListener("click", (event) => {
    if (event.target.closest("a")) close();
  });

  return user;
}

/** Menyudagi raqamli nishonni yangilaydi (masalan kutilayotgan bronlar). */
export function setSidebarBadge(name, count) {
  const badge = document.querySelector(`[data-badge="${name}"]`);
  if (!badge) return;
  badge.textContent = count;
  badge.hidden = !count;
}
