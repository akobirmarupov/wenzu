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
 * NEGA TINCH
 * ===================================================================
 * Profil — odam kuniga bir marta ham ochmaydigan sahifa: u yerga
 * aniq bir ish bilan kiradi (rasmni almashtirish, bronga o'tish,
 * chiqish). Shuning uchun ekranda KO'RINADIGAN element imkon qadar
 * kam bo'lishi kerak — har bir ramka, nishon va chip ko'zni bo'ladi.
 *
 * Shu sababli:
 *   · muqova kartochka emas — fonsiz, ramkasiz, soyasiz;
 *   · rol va tasdiq holati nishon emas, oddiy yozuv qatori;
 *   · statistika to'rtta chip emas, chiziq bilan ajratilgan bitta
 *     tasma;
 *   · sahifada YAGONA kartochka bor — "Tez o'tish", chunki u yagona
 *     bosiladigan taklif;
 *   · aksent (zumrad) faqat UCH joyda: tasdiq belgisi, "Tahrirlash"
 *     tugmasi va tez o'tish ikonkasi;
 *   · hisob bilan bog'liq TO'RTALA amal (tahrirlash, rasmni
 *     almashtirish, rasmni o'chirish, chiqish) bitta qatorda, ism
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

import { icon } from "../../ui/icons.js";

import { openSettingsSheet } from "../../components/settings-sheet.js";

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
 * Tasdiq holati — nishon EMAS, yozuv qatori.
 *
 * Ilgari rol ham, tasdiq holati ham oltin/yashil fonli nishon edi va
 * ikkalasi ism ostida yonma-yon turardi: ikkita rangli tabletka ismdan
 * ko'ra ko'proq ko'zga tashlanardi. Endi rol — sust yozuv (username
 * yonida), tasdiq esa yagona rangli belgi, chunki u YAGONA javob
 * beradigan savol: "bu hisob haqiqiymi?".
 */
function verifyLine(current) {
  return current.is_phone_verified
    ? `<span class="pid-verify">${icon("check")} ${esc(t("profile.verified"))}</span>`
    : `<span class="pid-verify is-off">${icon("alert")} ${esc(t("profile.notVerified"))}</span>`;
}

/* Statistika (jami bron, yakunlangan, kutilayotgan, sharh) profilda
   KO'RSATILMAYDI — u "Bronlarim" sahifasida, aynan o'sha bronlar
   ro'yxatining tepasida turadi. Ikki joyda ko'rsatish profil
   muqovasini uzaytirardi va raqamlar bosilmaydigan bezakka
   aylanardi: odam ularni ko'rib baribir "Bronlarim" ga o'tardi. */

function identityHtml(current) {
  // ===================================================================
  // IJTIMOIY TARMOQ TARTIBI
  // ===================================================================
  // Chapda doira rasm, o'ngda username va ostida kim ekanligi.
  // Uch chiziqli menyu esa O'NG YUQORI BURCHAKDA — Instagram'dagidek.
  //
  // Nega burchakda: u muqovaning bir qismi emas, butun SAHIFAning
  // boshqaruvi. Username yonida turganda u ismning davomiday ko'rinib,
  // ko'z avval unga tushardi.
  //
  // "Tahrirlash" tugmasi bu yerdan OLIB TASHLANDI: u sozlamalar
  // oynasining birinchi satri. Muqovada ikkita boshqaruv turgani
  // ortiqcha edi — odam profilga kuniga bir marta ham kirmaydi,
  // tahrirlash esa undan ham kam bo'ladigan ish.
  return `
    <button class="pid-menu" type="button" data-settings
            aria-label="${esc(t("profile.settingsTitle"))}">
      ${icon("menu")}
    </button>

    <div class="pid-main">
      <div class="pid-avatar">
        ${avatarHtml(current, { size: "lg" })}
      </div>

      <div class="pid-body">
        <h1 class="pid-name">@${esc(current.username)}</h1>
        <p class="pid-bio">
          <b>${esc(current.full_name || current.username)}</b>
          <span>${esc(infoSection.roleName(current))}</span>
          ${verifyLine(current)}
        </p>
      </div>
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

  // Sahifadagi YAGONA kartochka. Fon, chegara va burchak aynan shu
  // yerga sarflanadi: bu bosiladigan taklif va taklifdek ko'rinishi
  // kerak. Qolgan bo'limlar chiziq bilan ajratiladi.
  return `
    <section class="profile-quick">
      <h2 class="block-title">${esc(t("profile.quickLinks"))}</h2>
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

  // BITTA USTUN. Ilgari bu yerda ikki ustunli to'r bor edi: o'ngda
  // "ishonchlilik" kartochkasi turardi va uning ostida yarim ekran
  // bo'sh maydon qolardi. Ishonchlilik endi ma'lumot qatorlarining
  // biri (`info.js`) — u ham oddiy ko'rsatkich, alohida ramka talab
  // qilmaydi.
  //
  // Qisqa yo'llar faqat asosiy bo'limda va ma'lumotlardan OLDIN:
  // odam profilga ko'pincha bronlariga yoki paneliga o'tish uchun
  // kiradi, o'z tug'ilgan sanasini o'qish uchun emas.
  const lead = activeKey === "info" ? shortcutsHtml(user) : "";

  render("#profile-content", `
    <div class="profile-stack">
      ${lead}
      ${section.module.render(user)}
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

  // Uch chiziqli menyu — tahrirlash, til, tema, platforma, chiqish.
  //
  // Tinglovchi bir marta, muqova konteyneriga qo'yiladi: bo'lim qayta
  // chizilganda u yo'qolmaydi va ko'paymaydi ham.
  delegate("#profile-id", "[data-settings]", () => {
    openSettingsSheet(user, {
      onEdit: openEditor,
      onLogout: () => auth.logout(),
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

}

/* ---------- muqovadan ham, sozlamalardan ham chaqiriladigan amallar ---------- */

function openEditor() {
  infoSection.openEditor(user, {
    onUpdated: (fresh) => {
      user = fresh;
      paint();
    },
    onRemoveAvatar: removeAvatar,
  });
}

async function removeAvatar() {
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
}
