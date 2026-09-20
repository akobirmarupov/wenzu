/**
 * Profil sahifasi.
 *
 * Bo'limlar ROLGA qarab yig'iladi:
 *   oddiy foydalanuvchi → ma'lumot, obuna/premium
 *   biznes egasi        → + o'z paneliga qisqa yo'l
 *   super-admin         → + boshqaruv
 *
 * Har bir bo'lim alohida modulda (`sections/`), bu fayl faqat
 * ularni bog'laydi — shunda bo'lim qo'shish bitta fayl qo'shish demak.
 *
 * ===================================================================
 * NEGA IXCHAM
 * ===================================================================
 * Profil — odam kuniga bir marta ham ochmaydigan sahifa: u yerga
 * aniq bir ish bilan kiradi (rasmni almashtirish, bronga o'tish,
 * chiqish). Shuning uchun sahifa IMKON QADAR PAST bo'lishi kerak —
 * hamma narsa bir ekranga sig'sin, aylantirish shart bo'lmasin.
 *
 * Shu sababli:
 *   · muqova baland emas — ism, nishon va amallar bitta qatorda;
 *   · statistika katta raqamlar bloki emas, kichik chiplar;
 *   · bo'limlar chapdagi baland kartochka emas, gorizontal tasma;
 *   · hisob bilan bog'liq TO'RTALA amal (tahrirlash, rasmni
 *     almashtirish, rasmni o'chirish, chiqish) bitta qatorda, muqova
 *     ostida — har biri alohida joyda turgani foydalanuvchini
 *     "qaysi amal qayerda?" deb qidirishga majbur qilardi.
 */
import { api } from "../../core/api.js";
import { auth } from "../../core/auth.js";
import { requireAuth } from "../../core/guard.js";
import { ROUTES } from "../../core/config.js";
import { initI18n, t } from "../../core/i18n.js";
import { theme } from "../../core/theme.js";
import { $, render, delegate, esc } from "../../ui/dom.js";
import { initPublicNav } from "../../ui/public-nav.js";
import { initTopbar } from "../../ui/topbar.js";
import { avatarHtml } from "../../ui/avatar.js";
import { toast } from "../../ui/toast.js";
import { confirmDialog } from "../../ui/modal.js";
import { dateLabel } from "../../ui/format.js";
import { icon } from "../../ui/icons.js";

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
   "Bronlarim" alohida sahifada (`/bronlarim/`) — profil ichida unga
   faqat qisqa yo'l kartochkasi qoladi.

   "Biznes ochish" esa "Premium" bo'limining ICHIDA: tarif tanlash va
   biznes ochish foydalanuvchi uchun bitta qaror. */
function sectionsFor(current) {
  const items = [
    { key: "info", icon: "user", label: () => t("profile.info"), module: infoSection },
  ];

  // "Obuna va Premium" — TASDIQLANGAN biznes egasida YO'Q.
  //
  // Uning obunasi o'z panelida ("Obuna" bo'limi): tarif tanlash,
  // muddatni uzaytirish, to'lovlar tarixi va administrator manzili —
  // hammasi bir joyda. Profilda ikkinchi nusxa saqlash "qaysinisi
  // haqiqiy?" degan savol tug'dirardi va ikkalasi bir kun bir-biriga
  // zid bo'lib qolardi.
  //
  // Arizasi hali tasdiqlanmagan egada esa BOR: u panelga kira olmaydi
  // va holatni faqat shu yerdan ko'radi.
  if (!current.business?.is_approved) {
    items.push({
      key: "premium", icon: "gem", label: () => t("premium.title"), module: premiumSection,
    });
  }

  if (current.is_staff) {
    items.push({ key: "admin", icon: "shield", label: () => t("admin.title"), module: adminSection });
  }
  return items;
}

/* ---------- 1-qatlam: kim ekanligi ---------- */

/**
 * Rol nishoni.
 *
 * Bitta nishon yetarli: odam bir vaqtda ham platforma egasi, ham oddiy
 * foydalanuvchi bo'lib ko'rinsa, qaysi huquqda ekani bilinmaydi.
 */
function roleBadge(current) {
  if (current.is_staff) {
    return `<span class="seal seal-gold">${icon("shield")} ${esc(t("panel.roleAdmin"))}</span>`;
  }
  if (current.business) {
    return `<span class="seal seal-gold">${icon("gem")} ${esc(infoSection.roleName(current))}</span>`;
  }
  return `<span class="seal">${esc(t("profile.roleUser"))}</span>`;
}

function verifyBadge(current) {
  return current.is_phone_verified
    ? `<span class="seal seal-ok">${icon("check")} ${esc(t("profile.verified"))}</span>`
    : `<span class="seal seal-warn">${icon("alert")} ${esc(t("profile.notVerified"))}</span>`;
}

/**
 * Statistika chiplari.
 *
 * Platforma egasida KO'RSATILMAYDI: u bron qilmaydi va uning profilida
 * to'rtta nol turishi ma'lumot emas, shovqin edi.
 */
function statsHtml(current) {
  if (current.is_staff) return "";

  const stats = current.stats || {};
  const items = [
    { value: stats.total ?? 0, key: "profile.statBookings" },
    { value: stats.completed ?? 0, key: "profile.statCompleted" },
    { value: stats.upcoming ?? 0, key: "profile.statUpcoming" },
    { value: stats.reviews ?? 0, key: "profile.statReviews" },
  ];

  return `
    <div class="pid-stats">
      ${items.map((item) => `
        <span class="pid-stat">
          <b>${esc(String(item.value))}</b>
          <span>${esc(t(item.key))}</span>
        </span>`).join("")}
    </div>`;
}

function identityHtml(current) {
  // Rasm almashtirish `label` ko'rinishida chiziladi: ichida fayl
  // tanlagich turadi, chunki brauzerning o'z "Choose file" tugmasini
  // dizaynga moslab bo'lmaydi. Tugma avatar USTIDA emas, amallar
  // qatorida — doira ustiga qo'yilgan kichik tugma bosh harflarni
  // yopib qo'yardi va telefonda barmoq uchun ham kichik edi.
  return `
    <div class="pid-main">
      <div class="pid-avatar">
        ${avatarHtml(current, { size: "lg", ring: true })}
      </div>

      <div class="pid-text">
        <h1 class="display h2">${esc(current.full_name || current.username)}</h1>
        <p class="pid-meta">
          <span class="mono">@${esc(current.username)}</span>
          <span class="dot">·</span>
          <span class="mono">${esc(current.phone_number)}</span>
          <span class="dot">·</span>
          <span>${esc(t("profile.memberSince"))}: ${dateLabel(current.date_joined)}</span>
        </p>
        <div class="pid-badges">${roleBadge(current)}${verifyBadge(current)}</div>
      </div>

    </div>

    ${statsHtml(current)}

    <div class="pid-actions">
      <button class="btn btn-outline btn-sm" type="button" data-edit-profile>
        ${icon("edit")} ${esc(t("profile.edit"))}
      </button>

      <label class="btn btn-ghost btn-sm" for="avatar-input">
        ${icon("camera")} ${esc(t("profile.changePhoto"))}
        <input type="file" id="avatar-input" accept="image/*" hidden>
      </label>

      ${current.avatar
        ? `<button class="btn btn-ghost btn-sm" type="button" data-remove-avatar>
             ${icon("trash")} ${esc(t("profile.removePhoto"))}
           </button>`
        : ""}

      <button class="btn btn-ghost btn-sm pid-logout" type="button" data-logout>
        ${icon("logout")} ${esc(t("nav.logout"))}
      </button>
    </div>`;
}

/* ---------- 2-qatlam: bo'limlar tasmasi ---------- */
function tabsHtml(current, key) {
  const items = sectionsFor(current);
  // Bitta bo'lim qolsa tasma ma'nosiz — tanlashga narsa yo'q.
  if (items.length < 2) return "";

  return items.map((item) => `
    <button type="button" class="profile-tab${key === item.key ? " is-active" : ""}"
            data-section="${item.key}" ${key === item.key ? 'aria-current="page"' : ""}>
      ${icon(item.icon)}<span>${esc(item.label())}</span>
    </button>`).join("");
}

/* ---------- 3-qatlam: qisqa yo'llar va chiqish ---------- */

/**
 * Qisqa yo'llar — alohida sahifalarga olib boradi.
 *
 * ===================================================================
 * EGASINING PANELI TELEFONDA AYNAN SHU YERDA
 * ===================================================================
 * Kompyuterda "Restoran panelim" / "To'yxona panelim" chap menyuda
 * turadi. Telefonda esa chap menyu yo'q: u pastki menyuga ko'chgan,
 * u yerda esa beshta katakdan ortiq joy yo'q va panelni u yerga tiqish
 * "Bronlarim" yoki "Profil" ni qurbon qilishni talab qilardi.
 *
 * Shuning uchun telefonda panelga yo'l shu kartochka orqali o'tadi va
 * u BIRINCHI turadi — joy egasi profilga kirganda birinchi ko'radigan
 * narsasi o'z joyi bo'lishi kerak, bronlari emas.
 */
function shortcutsHtml(current) {
  const cards = [];

  if (current.is_staff) {
    cards.push({
      href: ROUTES.adminHome, icon: "shield",
      title: t("nav.admin"), text: t("panel.overview"),
    });
  }

  // Egasining paneli faqat ariza TASDIQLANGANDAN keyin — aks holda
  // odam bo'sh, ishlamaydigan panelga tushardi.
  if (current.business?.is_approved) {
    const isVenue = current.business.type === "venue";
    cards.push({
      href: ROUTES.ownerHome,
      icon: isVenue ? "venue" : "seat",
      title: t(isVenue ? "nav.panelVenue" : "nav.panelRestaurant"),
      text: current.business.name,
    });
  }

  // Platforma egasi bron qilmaydi — u bronlarni boshqaradi.
  if (!current.is_staff) {
    cards.push({
      href: ROUTES.myBookings, icon: "calendar",
      title: t("profile.bookings"), text: t("bookingsPage.lead"),
    });
  }

  if (!cards.length) return "";

  return `
    <section class="panel profile-links">
      <h2 class="display h3">${esc(t("profile.quickLinks"))}</h2>
      <div class="link-tiles">
        ${cards.map((card) => `
          <a class="link-tile" href="${card.href}">
            <span class="lt-ic">${icon(card.icon)}</span>
            <span class="lt-text">
              <b>${esc(card.title)}</b>
              <span>${esc(card.text)}</span>
            </span>
            ${icon("chevronRight", { className: "lt-go" })}
          </a>`).join("")}
      </div>
    </section>`;
}

/* ---------- boshqaruv ---------- */
let activeKey = new URLSearchParams(window.location.search).get("tab") || "info";

async function paint() {
  render("#profile-id", identityHtml(user));
  render("#profile-tabs", tabsHtml(user, activeKey));

  const sections = sectionsFor(user);
  const section = sections.find((item) => item.key === activeKey) || sections[0];
  activeKey = section.key;

  // Tartib SHU YERDA yig'iladi, bo'lim ichida emas: asosiy ustun —
  // bo'limning o'zi, yon ustun — uning qo'shimchasi (`aside`) va qisqa
  // yo'llar. Shunday qilinmasa yon ustun ostida katta bo'sh maydon
  // qolardi, chunki qisqa yo'llar butun enni egallab pastda turardi.
  //
  // Qisqa yo'llar faqat asosiy bo'limda: Premium yoki Boshqaruv
  // ochilganda ular e'tiborni tortib turmasligi kerak.
  const side = (section.module.aside?.(user) || "")
    + (activeKey === "info" ? shortcutsHtml(user) : "");

  render("#profile-content", `
    <div class="profile-grid${side ? "" : " is-single"}">
      <div class="pg-main">${section.module.render(user)}</div>
      ${side ? `<aside class="pg-side">${side}</aside>` : ""}
    </div>`);

  section.module.bind?.({
    user,
    onUpdated: (fresh) => {
      user = fresh;
      paint();
    },
    onGoToBusiness: () => {
      window.location.href = ROUTES.premium;
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

  delegate("#profile-tabs", "[data-section]", (button) => switchTo(button.dataset.section));
  delegate("#profile-id", "[data-logout]", () => auth.logout());

  // Tahrirlash oynasi YAGONA joydan ochiladi — muqovadagi tugma.
  // Tinglovchi bir marta, muqova konteyneriga qo'yiladi: bo'lim qayta
  // chizilganda u yo'qolmaydi va ko'paymaydi ham.
  delegate("#profile-id", "[data-edit-profile]", () => {
    infoSection.openEditor(user, (fresh) => {
      user = fresh;
      paint();
    });
  });

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
      render("#profile-id", identityHtml(user));
      toast.ok(t("profile.photoUpdated"));
    } catch (error) {
      toast.fromError(error);
    } finally {
      event.target.value = "";
    }
  });

  delegate("#profile-id", "[data-remove-avatar]", async () => {
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
      render("#profile-id", identityHtml(user));
      toast.ok(t("profile.photoRemoved"));
    } catch (error) {
      toast.fromError(error);
    }
  });
}
