/**
 * Ommaviy sahifalarning CHAP yon menyusi.
 *
 * Menyu bandlari, til tanlagichi, tema tugmasi va foydalanuvchi bloki —
 * hammasi shu yerda quriladi. Sahifalar bu haqda bilmaydi, ular faqat
 * `initPublicNav()` ni chaqiradi.
 */
import { auth } from "../core/auth.js";
import { ROUTES } from "../core/config.js";
import { api } from "../core/api.js";
import { t } from "../core/i18n.js";
import { $, esc } from "./dom.js";
import { avatarHtml } from "./avatar.js";

const MAIN_LINKS = [
  { href: ROUTES.home, icon: "◈", key: "nav.home" },
  { href: ROUTES.restaurants, icon: "🍽", key: "nav.restaurants" },
  { href: ROUTES.venues, icon: "🎉", key: "nav.venues" },
];

function isActive(href) {
  const path = window.location.pathname;
  return href === "/" ? path === "/" : path.startsWith(href);
}

function linkHtml({ href, icon, key }) {
  return `
    <a class="nav-item ${isActive(href) ? "active" : ""}" href="${href}">
      <span class="ic" aria-hidden="true">${icon}</span>
      <span>${esc(t(key))}</span>
    </a>`;
}

function userBlockHtml() {
  const user = auth.user();

  if (!user) {
    return `
      <a class="btn btn-primary btn-block btn-sm" href="${ROUTES.login}">${esc(t("nav.login"))}</a>
      <a class="btn btn-outline btn-block btn-sm" href="${ROUTES.register}">${esc(t("nav.register"))}</a>`;
  }

  const roleLabel = user.is_staff
    ? t("nav.admin")
    : user.business
      ? t("nav.panel")
      : t("nav.profile");
  const panelHref = auth.homeFor(user);

  return `
    <a class="nav-user" href="${ROUTES.profile}">
      ${avatarHtml(user, { size: "md" })}
      <span class="meta">
        <span class="name">${esc(user.full_name || "")}</span>
        <span class="role">${esc(roleLabel)}</span>
      </span>
    </a>
    ${panelHref !== ROUTES.home
      ? `<a class="btn btn-outline btn-block btn-sm" href="${panelHref}">${esc(roleLabel)}</a>`
      : ""}
    <button class="btn btn-ghost btn-block btn-sm" type="button" data-logout>${esc(t("nav.logout"))}</button>`;
}

export function initPublicNav() {
  const nav = $("#side-nav");
  if (!nav) return;

  const user = auth.user();
  // Bronlar va biznes — alohida sahifalar, profil ichidagi tab emas.
  const secondary = user
    ? [
        { href: ROUTES.myBookings, icon: "📅", key: "nav.bookings" },
        { href: ROUTES.openBusiness, icon: "🏢", key: user.business ? "business.mine" : "nav.business" },
        { href: ROUTES.profile, icon: "👤", key: "nav.profile" },
      ]
    : [{ href: ROUTES.openBusiness, icon: "🏢", key: "nav.business" }];

  nav.innerHTML = `
    <a class="brand" href="/"><span class="dot"></span>WENZU</a>
    <p class="brand-sub">${esc(t("brand.tagline"))}</p>

    ${MAIN_LINKS.map(linkHtml).join("")}

    <div class="nav-group-label">${esc(t("nav.menu"))}</div>
    ${secondary.map(linkHtml).join("")}

    <div class="side-nav-bottom">
      ${userBlockHtml()}
    </div>`;

  nav.querySelector("[data-logout]")?.addEventListener("click", () => auth.logout());

  // Mobil: gamburger va orqa fon
  const toggle = $("[data-nav-toggle]");
  const scrim = $("#nav-scrim");
  const close = () => {
    nav.classList.remove("open");
    if (scrim) scrim.hidden = true;
  };
  toggle?.addEventListener("click", () => {
    nav.classList.toggle("open");
    if (scrim) scrim.hidden = !nav.classList.contains("open");
  });
  scrim?.addEventListener("click", close);
  nav.addEventListener("click", (event) => {
    if (event.target.closest("a")) close();
  });

  fillFooterContacts();
}

/** Poyloqdagi aloqa ma'lumotini platforma sozlamalaridan to'ldiradi. */
async function fillFooterContacts() {
  const telegram = $("[data-footer-telegram]");
  const phone = $("[data-footer-phone]");
  if (!telegram && !phone) return;
  try {
    const settings = await api.settings();
    if (telegram && settings.admin_telegram) {
      telegram.textContent = `${settings.admin_telegram} — Telegram`;
      telegram.href = `https://t.me/${settings.admin_telegram.replace("@", "")}`;
    }
    if (phone && settings.support_phone) {
      phone.textContent = settings.support_phone;
      phone.href = `tel:${settings.support_phone}`;
    }
  } catch {
    /* aloqa ma'lumoti yuklanmasa sahifa baribir ishlaydi */
  }
}
