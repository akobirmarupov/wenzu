/**
 * Profil — "Obuna va Premium" bo'limi.
 *
 * Biznes egasi uchun: joriy tarif, qolgan kun, imkoniyatlar va to'lov
 * yo'riqnomasi. Oddiy foydalanuvchi uchun: Premium nima berishini
 * tushuntirib, biznes ochishga yo'naltiradi.
 */
import { api } from "../../../core/api.js";
import { t } from "../../../core/i18n.js";
import { $, esc } from "../../../ui/dom.js";
import { skeletonRows, errorState } from "../../../ui/state.js";
import { pricingHtml, bindPricing, pendingApprovalText } from "../../../components/pricing.js";
import { icon } from "../../../ui/icons.js";

export function render() {
  return `<div id="premium-root">${skeletonRows(3)}</div>`;
}

function paymentStepsHtml() {
  return `
    <div class="panel">
      <div class="panel-head"><h2 class="display h3">${esc(t("premium.howTitle"))}</h2></div>
      <div class="pay-steps">
        ${[1, 2, 3].map((n) => `
          <div class="pay-step">
            <p>${esc(t(`premium.how${n}`))}</p>
          </div>`).join("")}
      </div>
    </div>`;
}

/** Biznes egasi ko'radigan ko'rinish. */
/**
 * Tasdiqlangan egaga — panelga qisqa yo'l.
 *
 * Bu ekran odatda ko'rinmaydi (bo'lim menyudan olib tashlangan), lekin
 * eski havola yoki xatcho'p bilan kirilsa bo'sh sahifa chiqmasligi
 * kerak.
 */
function panelRedirectHtml(subscription) {
  const isVenue = subscription.business_type === "venue";
  return `
    <div class="panel">
      <div class="panel-head">
        <div class="stack stack-1">
          <h2 class="display h3">${esc(t("premium.panelRedirectTitle"))}</h2>
          <span class="small muted">${esc(t("premium.panelRedirectText"))}</span>
        </div>
      </div>
      <a class="card card-link shortcut-card" href="/panel/obuna/" style="max-width:340px">
        <span class="ic">${icon(isVenue ? "venue" : "seat")}</span>
        <b>${esc(t(isVenue ? "nav.panelVenue" : "nav.panelRestaurant"))}</b>
        <span class="small muted">${esc(t("premium.goToSubscription"))}</span>
        <span class="go">${icon("chevronRight")}</span>
      </a>
    </div>`;
}

/**
 * Arizasi RAD ETILGAN egaga — qayta yuborish ekrani.
 *
 * Rad etish joyni o'chirmaydi, faqat yashiradi. Ilgari bu holat kutish
 * holati bilan bir xil ko'rinardi ("arizangiz tekshiruvida") va tarif
 * tugmalari ham bloklangan bo'lardi — ya'ni odam hech qachon kelmaydigan
 * javobni kutib, ekranda hech narsa qila olmasdi. Endi u tarifni tanlab,
 * arizani QAYTA yuboradi: eski joyi o'sha yangi arizaga ulanadi.
 */
function rejectedHtml(subscription) {
  const telegram = subscription.admin_telegram || "@akobir_marupov";
  return `
    ${adminContactHtml(telegram)}

    <div class="price-pending" style="border-color:var(--danger);background:var(--danger-dim)">
      <span class="ic">${icon("ban", { className: "ico-danger" })}</span>
      <span>
        <b>${esc(t("premium.rejectedTitle"))}</b>
        <span class="small">
          ${t("premium.rejectedText", { telegram: esc(telegram) })}
        </span>
      </span>
    </div>

    <div class="panel" style="margin-top:var(--sp-5)">
      <div class="panel-head">
        <div class="stack stack-1">
          <h2 class="display h3">${esc(t("premium.reapplyTitle"))}</h2>
          <span class="small muted">${esc(t("premium.reapplyLead"))}</span>
        </div>
      </div>
      <div id="premium-pricing">
        ${pricingHtml({
          plans: subscription.plans,
          status: "rejected",
          trialUsed: Boolean(subscription.trial_used),
        })}
      </div>
    </div>`;
}

function awaitingHtml(subscription) {
  const telegram = subscription.admin_telegram || "@akobir_marupov";
  return `
    ${adminContactHtml(telegram)}

    <div class="price-pending">
      <span class="ic">${icon("clock")}</span>
      <span>
        <b>${esc(t("premium.awaitingTitle"))}</b>
        <span class="small">
          ${pendingApprovalText(subscription)}
          ${esc(t("premium.speedUp", { telegram }))}
        </span>
      </span>
    </div>

    ${/* Ikkinchi Telegram havolasi ATAYLAB yo'q: tepada allaqachon
         "Admin bilan bog'lanish" tugmasi turibdi va u aynan shu joyga
         olib boradi. Ikkita bir xil tugma bir ekranda — "qaysi biri
         to'g'ri?" degan ortiqcha savol. */""}
    <div class="panel" style="margin-top:var(--sp-5)">
      <div class="panel-head">
        <div class="stack stack-1">
          <h2 class="display h3">${esc(t("premium.plansTitle"))}</h2>
          <span class="small muted">${esc(t("premium.plansLead"))}</span>
        </div>
      </div>
      <div id="premium-pricing">
        ${pricingHtml({
          plans: subscription.plans,
          status: "awaiting_approval",
          pending: subscription.pending_request,
          ownedType: subscription.business_type,
        })}
      </div>
    </div>`;
}

/**
 * Platforma egasi ko'radigan ko'rinish.
 *
 * U obuna sotib olmaydi — obunalarni yaratadi, tasdiqlaydi va
 * o'chiradi. Shuning uchun bu yerda narx emas, boshqaruv bo'limlariga
 * qisqa yo'llar turadi.
 */
function adminHtml() {
  const links = [
    { href: "/boshqaruv/obunalar/", icon: "gem", title: t("panel.subscriptions"),
      text: t("premium.linkSubscriptionsText") },
    { href: "/boshqaruv/arizalar/", icon: "document", title: t("panel.applications"),
      text: t("premium.linkApplicationsText") },
    { href: "/boshqaruv/bizneslar/", icon: "building", title: t("panel.businesses"),
      text: t("premium.linkBusinessesText") },
    { href: "/boshqaruv/tolovlar/", icon: "card", title: t("panel.payments"),
      text: t("premium.linkPaymentsText") },
  ];

  return `
    <div class="panel">
      <div class="panel-head">
        <div class="stack stack-1">
          <h2 class="display h3">${esc(t("premium.manageTitle"))}</h2>
          <span class="small muted">${esc(t("premium.manageLead"))}</span>
        </div>
      </div>
      <div class="grid grid-auto-sm">
        ${links.map((link) => `
          <a class="card card-link shortcut-card" href="${link.href}">
            <span class="ic">${icon(link.icon)}</span>
            <b>${esc(link.title)}</b>
            <span class="small muted">${esc(link.text)}</span>
            <span class="go">${icon("chevronRight")}</span>
          </a>`).join("")}
      </div>
    </div>`;
}

/**
 * Biznesi YO'Q foydalanuvchi ko'radigan ko'rinish.
 *
 * Bu yerda ham xuddi shu tarif kartochkalari turadi, faqat tugmalar
 * boshqa ish qiladi: "1 oyni tanlash" bosilsa BIZNES OCHISH arizasi
 * boshlanadi (rejaning turi restoranmi yoki to'yxonami — o'zi bilinadi).
 *
 * Nega shunday: "biznes ochish" va "tarif tanlash" foydalanuvchi uchun
 * bitta qaror — "shu narxga ishlayman". Ilgari ular ikki alohida
 * bo'limda edi va odam qayerdan boshlashni bilmasdi. Endi menyudagi
 * "Biznes ochish" bandi ham olib tashlandi.
 */
function guestHtml(settings, user) {
  const plans = settings?.plans || [];
  const telegram = settings?.admin_telegram || "@akobir_marupov";

  // Katta "hero" bloki ATAYLAB olib tashlandi.
  //
  // Unda tarif imkoniyatlari sanab o'tilardi, lekin AYNAN o'sha ro'yxat
  // har bir kartochkaning ichida "Nimalar kiradi" bo'limida yana bir bor
  // takrorlanardi. Bir xil to'rt qatorni ikki marta o'qitishning ma'nosi
  // yo'q — ekran cho'zilib, asosiy narsa (narxlar) pastga tushib ketardi.
  //
  // Endi tartib sodda: admin bilan aloqa → tariflar → to'lov qanday ishlaydi.
  return `
    ${adminContactHtml(telegram)}

    <div class="panel">
      <div class="panel-head">
        <div class="stack stack-1">
          <h2 class="display h3">${esc(t("premium.plansTitle"))}</h2>
          <span class="small muted">
            ${esc(t("premium.guestText"))}
            ${esc(t("premium.guestPickPlan"))}
          </span>
        </div>
        <span class="premium-plan premium-plan-trial">
          ${icon("sparkle", { fill: true })} ${settings?.trial_days ?? 7} ${esc(t("premium.days"))} ${esc(t("premium.trial")).toLowerCase()}
        </span>
      </div>
      <div id="premium-pricing">
        ${pricingHtml({ plans, status: "guest", trialUsed: user.has_used_trial })}
      </div>
    </div>

    ${paymentStepsHtml()}`;
}

/**
 * Administrator bilan bog'lanish — bo'limning TEPASIDA, doimiy.
 *
 * "Keyinroq bog'lanaman" degan odam admin manzilini qayta izlab
 * yurmasligi kerak.
 */
function adminContactHtml(telegram) {
  const handle = telegram.replace("@", "");
  return `
    <a class="admin-contact" href="https://t.me/${esc(handle)}" target="_blank" rel="noopener">
      <span class="ic">${icon("send")}</span>
      <span class="text">
        <b>${esc(t("business.contactAdmin"))}</b>
        <span class="small">${esc(t("business.contactAdminText"))} · ${esc(telegram)}</span>
      </span>
      <span class="go">${icon("chevronRight")}</span>
    </a>`;
}

export async function load(user) {
  const root = $("#premium-root");
  if (!root) return;

  try {
    // PLATFORMA EGASI uchun alohida ko'rinish.
    //
    // Unga tarif kartochkalari ko'rsatishning ma'nosi yo'q: u biznes
    // ochmaydi va obuna sotib olmaydi — obunalarni BOSHQARADI. Ilgari
    // unga "biznes ochish" kartochkalari chiqardi va bosganda server
    // rad etardi.
    if (user.is_staff) {
      root.innerHTML = adminHtml();
      return;
    }

    // Shart ROLGA emas, JOYGA qaraydi. Rol endi faqat tasdiqlangan
    // egada bo'ladi, arizasi kutayotgan yoki rad etilgan odamda esa
    // 'user' — lekin uning arizasi bor va u shu yerda o'z holatini
    // ko'rishi kerak.
    if (user.business) {
      const subscription = await api.owner.subscription();

      // TASDIQLANGAN egaga bu bo'lim KO'RSATILMAYDI.
      //
      // Obunani uzaytirish, to'lovlar tarixi va admin Telegrami —
      // hammasi uning o'z panelida ("Obuna" bo'limi). Ikki joyda ikki
      // xil ko'rinish saqlash "qaysinisi haqiqiy?" degan savol
      // tug'dirardi. `profile.js` bu bo'limni menyuga umuman
      // qo'shmaydi; bu yer faqat to'g'ridan-to'g'ri havola bilan
      // kirilganda ishlaydi.
      if (subscription.has_subscription !== false) {
        root.innerHTML = panelRedirectHtml(subscription);
        return;
      }

      // `has_subscription === false` — bu XATO EMAS: ariza hali
      // tasdiqlanmagan, ya'ni panelga kira olmaydi va obuna holatini
      // faqat SHU YERDA ko'radi.
      //
      // Ariza RAD ETILGAN bo'lsa ekran boshqacha: kutish o'rniga qayta
      // yuborish. Tanlangan tarif obuna arizasini emas, YANGI BIZNES
      // arizasini boshlaydi — shuning uchun `mode: "open"`.
      const reapply = Boolean(subscription.can_reapply);
      root.innerHTML = reapply ? rejectedHtml(subscription) : awaitingHtml(subscription);
      bindPricing("#premium-pricing", {
        plans: subscription.plans || [],
        telegram: subscription.admin_telegram || "@akobir_marupov",
        mode: reapply ? "open" : "renew",
        onSent: () => load(user),
      });
    } else {
      const settings = await api.settings();
      root.innerHTML = guestHtml(settings, user);

      // Biznesi yo'q — tarif tanlash BIZNES OCHISH arizasini boshlaydi.
      bindPricing("#premium-pricing", {
        plans: settings?.plans || [],
        telegram: settings?.admin_telegram || "@akobir_marupov",
        mode: "open",
        onSent: () => load(user),
      });
    }
  } catch (error) {
    root.innerHTML = errorState(error.message);
  }
}

export function bind({ onGoToBusiness }) {
  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-goto-business]")) onGoToBusiness?.();
  });
}
