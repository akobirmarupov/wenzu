/**
 * Ommaviy sahifalarning CHAP yon menyusi va TELEFONDAGI PASTKI MENYUSI.
 *
 * Ikkalasi bitta faylda, chunki ular BIR XIL ma'lumotdan quriladi:
 * kim kirgan, arizasi tasdiqlanganmi, qaysi sahifada turibmiz. Ikki
 * joyga bo'linsa, bir menyuga band qo'shib, ikkinchisini unutish oson
 * bo'lardi.
 *
 * Bu yerda FAQAT yo'nalish bandlari bo'ladi: bosh sahifa, katalog,
 * bronlarim, biznes va (egalari uchun) panel.
 *
 * Til tanlagichi, tema tugmasi, bildirishnoma qo'ng'irog'i va
 * foydalanuvchi tugmasi — yuqori panelda (`topbar.js`), chiqish esa
 * profil sahifasining ichida. Ilgari ular menyu pastida ham takrorlanardi
 * va bir amalga bir necha tugma to'g'ri kelib qolgan edi.
 */
import { auth } from "../core/auth.js";
import { ROUTES } from "../core/config.js";
import { api } from "../core/api.js";
import { t } from "../core/i18n.js";
import { $, esc } from "./dom.js";

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

/**
 * Telefondagi pastki menyu bandlari.
 *
 * Nega yon menyudan alohida ro'yxat: bu yerda joy CHEKLANGAN — beshta
 * katakdan ortig'i 360 px li ekranda o'qib bo'lmaydigan darajada
 * siqiladi. Shuning uchun bu yerga faqat eng ko'p bosiladigan bo'limlar
 * tushadi, qolgani (panel, biznes) yon menyuda qolaveradi.
 *
 * Mehmonda "Bronlarim" yo'q — u hali hech narsa bron qilmagan; o'rniga
 * to'g'ridan-to'g'ri "Kirish" turadi, chunki keyingi qadam aynan shu.
 */
function tabbarItems(user) {
  const base = [
    { href: ROUTES.home, icon: "◈", key: "nav.shortHome" },
    { href: ROUTES.restaurants, icon: "🍽", key: "nav.shortRestaurants" },
    { href: ROUTES.venues, icon: "🎉", key: "nav.shortVenues" },
  ];

  if (!user) {
    return [...base, { href: ROUTES.login, icon: "→", key: "nav.shortLogin" }];
  }

  // Platforma egasi bron QILMAYDI — u bronlarni boshqaradi. Unga
  // "Bronlarim" o'rniga boshqaruv paneli foydaliroq.
  if (user.is_staff) {
    return [
      ...base,
      { href: ROUTES.adminHome, icon: "🛡", key: "nav.shortAdmin" },
      { href: ROUTES.profile, icon: "👤", key: "nav.shortProfile" },
    ];
  }

  return [
    ...base,
    { href: ROUTES.myBookings, icon: "📅", key: "nav.shortBookings" },
    { href: ROUTES.profile, icon: "👤", key: "nav.shortProfile" },
  ];
}

function renderTabbar(user) {
  const bar = $("#tabbar");
  if (!bar) return;

  bar.innerHTML = tabbarItems(user).map(({ href, icon, key }) => `
    <a class="tabbar-item ${isActive(href) ? "active" : ""}" href="${href}"
       ${isActive(href) ? 'aria-current="page"' : ""}>
      <span class="ic" aria-hidden="true">${icon}</span>
      <span class="lb">${esc(t(key))}</span>
    </a>`).join("");
}

export function initPublicNav() {
  const user = auth.user();

  // Pastki menyu yon menyudan MUSTAQIL chiziladi: sahifada faqat
  // bittasi bo'lsa ham ishlayversin.
  renderTabbar(user);

  const nav = $("#side-nav");
  if (!nav) return;

  // Menyuda faqat DOIM kerak bo'ladigan bandlar.
  //
  // "Biznes ochish" va "Biznesim" ATAYLAB YO'Q: biznes ochish endi
  // profil ichidagi "Obuna va Premium" bo'limidan boshlanadi — tarifni
  // tanlash va biznes ochish bitta qaror, ularni ikki joyga bo'lish
  // foydalanuvchini chalkashtirardi.
  // Platforma egasida "Bronlarim" YO'Q: u bron qilmaydi, bronlarni
  // boshqaradi. Server ham unga bron yaratishga ruxsat bermaydi
  // (`IsCustomer`), ya'ni bo'lim bo'lsa faqat bo'sh turardi.
  const secondary = !user
    ? []
    : user.is_staff
      ? [{ href: ROUTES.profile, icon: "👤", key: "nav.profile" }]
      : [
          { href: ROUTES.myBookings, icon: "📅", key: "nav.bookings" },
          { href: ROUTES.profile, icon: "👤", key: "nav.profile" },
        ];

  // "Panelim" faqat ARIZA TASDIQLANGANDAN keyin ko'rinadi.
  //
  // Ilgari ariza yuborilishi bilan paydo bo'lardi va bosgan odam bo'sh,
  // ishlamaydigan panelga tushardi (server yozishni baribir rad etardi).
  // Endi band ko'rinsa — panel haqiqatan ochiq degani.
  if (user?.is_staff) {
    secondary.push({ href: ROUTES.adminHome, icon: "🛡", key: "nav.admin" });
  } else if (user?.business?.is_approved) {
    // Nomi TURGA qarab: restoran egasi "Restoran panelim"ni ko'radi,
    // to'yxona egasi "To'yxona panelim"ni. Umumiy "Panelim" so'zi
    // egasiga o'z joyini emas, mavhum bir bo'limni ko'rsatardi.
    const isVenue = user.business.type === "venue";
    secondary.push({
      href: ROUTES.ownerHome,
      icon: isVenue ? "🏛" : "🪑",
      key: isVenue ? "nav.panelVenue" : "nav.panelRestaurant",
    });
  }

  nav.innerHTML = `
    <a class="brand" href="/"><span class="dot"></span>WENZU</a>
    <p class="brand-sub">${esc(t("brand.tagline"))}</p>

    ${MAIN_LINKS.map(linkHtml).join("")}

    <div class="nav-group-label">${esc(t("nav.menu"))}</div>
    ${secondary.map(linkHtml).join("")}`;

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
