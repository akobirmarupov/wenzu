/**
 * "Restoran / To'yxona ochish" arizasi oynasi.
 *
 * Uch bosqichli:
 *   1. Telefon tasdig'i  — tasdiqlanmagan bo'lsa forma umuman ochilmaydi
 *   2. Ariza formasi     — faqat nom so'raladi
 *   3. Tasdiq ekrani     — ariza ketdi, admin bilan hozir yoki keyin
 *
 * Ariza yuborilgach rol serverda o'zgaradi, lekin qo'ldagi JWT ichida
 * eski rol qolib ketadi — shuning uchun profilni qayta o'qib olamiz.
 */
import { api } from "../core/api.js";
import { auth } from "../core/auth.js";
import { ROUTES } from "../core/config.js";
import { openModal, modal } from "../ui/modal.js";
import { esc, busy } from "../ui/dom.js";
import { money } from "../ui/format.js";
import { toast } from "../ui/toast.js";

/**
 * Telefon tasdiqlanmaganini ALOHIDA ekranda aytamiz.
 *
 * Ilgari foydalanuvchi butun formani to'ldirib, "Yuborish" bosgandan
 * keyingina qizil yozuv ko'rardi — va o'sha yozuvdan chiqib ketadigan
 * yo'l yo'q edi. Ya'ni ariza umuman ketmasdi, sabab esa tushunarsiz
 * qolardi. Endi to'siq BOSHIDA aytiladi va darhol yechim tugmasi bor.
 */
function openVerifyGate(label) {
  openModal(
    `<h2>Telefonni tasdiqlash kerak</h2>
     <div class="notice">
       <p>Assalomu alaykum! 👋</p>
       <p>${esc(label)} ochish uchun avval telefon raqamingizni SMS-kod
          orqali tasdiqlashingiz kerak — bu bir daqiqalik ish.</p>
       <p class="xs muted">Bu talab tekshirilmagan raqamlar bilan soxta
          joy ochilishining oldini oladi.</p>
     </div>
     <a class="btn btn-primary btn-block btn-lg" style="margin-top:var(--sp-5)"
        href="${ROUTES.verify}">Raqamni tasdiqlash</a>
     <button class="btn btn-ghost btn-block" style="margin-top:var(--sp-2)"
             type="button" data-modal-close>Keyinroq</button>`,
    { wide: true }
  );
}

/**
 * Ariza yuborilgandan keyingi ekran.
 *
 * Ikki tugma, chunki ikki xil odam bor: biri hoziroq admin bilan
 * gaplashmoqchi, ikkinchisi keyin. Ilgari faqat Telegram havolasi
 * turardi va "keyinroq" degan odam uni boshqa topa olmasdi — endi
 * admin manzili "Obuna va Premium" bo'limining tepasida doim turadi.
 */
function openSentScreen({ message, telegram, onDone }) {
  const handle = telegram.replace("@", "");

  const node = openModal(
    `<h2>Arizangiz yuborildi ✅</h2>
     <div class="notice">
       <p>${esc(message)}</p>
     </div>

     <p class="small" style="margin-top:var(--sp-5)">
       Administrator bilan hoziroq bog'lanasizmi? Bu tasdiqni tezlashtiradi.
     </p>

     <a class="tg-line" style="margin-top:var(--sp-3)"
        href="https://t.me/${esc(handle)}" target="_blank" rel="noopener"
        data-modal-close>
       <span class="ic" aria-hidden="true">✈️</span>
       <span>Ha, admin bilan bog'lanaman (${esc(telegram)})</span>
     </a>

     <button class="btn btn-outline btn-block" style="margin-top:var(--sp-3)"
             type="button" id="apply-later">
       Keyinroq bog'lanaman
     </button>

     <p class="xs muted center" style="margin-top:var(--sp-3)">
       Admin manzili profilingizdagi "Obuna va Premium" bo'limining
       tepasida turadi — istalgan paytda topasiz.
     </p>`,
    { wide: true }
  );

  node.querySelector("#apply-later").addEventListener("click", () => {
    modal.close();
    toast.ok("Arizangiz yuborildi. Admin manzili shu bo'limda turadi.");
    onDone?.();
  });

  // Telegramga o'tgan odam ham ekranni yangilashi kerak — qaytganda
  // "ariza ko'rib chiqilmoqda" holati ko'rinsin.
  node.querySelector(".tg-line")?.addEventListener("click", () => onDone?.());
}

/**
 * @param {string} type - "restaurant" | "venue"
 * @param {object} options
 *   plan   — tanlangan tarif (profil ichidagi kartochkadan kelganda).
 *            Bo'lsa narx shu rejadan olinadi va qayta so'ralmaydi.
 *   onSent — ariza ketgach chaqiriladi (ekranni yangilash uchun).
 */
export async function openApplyModal(type, { plan = null, onSent } = {}) {
  const isRestaurant = type === "restaurant";
  const label = isRestaurant ? "Restoran" : "To'yxona";

  // `plan` bo'sh — BEPUL SINOV arizasi. Reja berilgan bo'lsa — pullik.
  const isTrial = !plan;

  // Telefon tasdiqlanmagan bo'lsa formani ochishning ma'nosi yo'q —
  // server baribir rad etadi.
  const user = auth.user();
  if (user && !user.is_phone_verified) {
    openVerifyGate(label);
    return;
  }

  let settings = null;
  try {
    settings = await api.settings();
  } catch {
    /* narxsiz ham davom etamiz */
  }

  const trialDays = settings?.trial_days ?? 7;
  const telegram = settings?.admin_telegram || "@uvente";

  // Izoh matni tarifga qarab boshqacha.
  //
  // Pullik tarifda "7 kun bepul" haqida HECH NARSA yozilmaydi: odam pul
  // to'laydi va muddat tasdiq kunidan boshlanadi. Ilgari ikkalasida ham
  // bir xil matn turardi va pul to'laydigan odam ustiga yana bepul kun
  // kutardi.
  const notice = isTrial
    ? `<p><b>${trialDays} kun mutlaqo bepul</b> — hech qanday to'lovsiz.
          Administrator arizangizni tasdiqlagach sinov boshlanadi.</p>
       <p class="xs muted">Bepul sinov har bir foydalanuvchiga bir marta beriladi.</p>`
    : `<p>Tanlangan tarif — <b>${esc(plan.duration_label)}</b>,
          <b>${money(plan.price)}</b>.</p>
       <p>To'lovni Telegram orqali amalga oshirasiz. Administrator tasdiqlagach
          obunangiz <b>o'sha kundan boshlab</b> ${esc(plan.duration_label)}ga
          faollashadi.</p>`;

  const node = openModal(
    `<h2>${label} ochish</h2>

     <form class="stack stack-4" id="apply-form" novalidate>
       <div class="form-alert" id="apply-error" hidden></div>

       <div class="field">
         <label for="business_name">${label} nomi</label>
         <input class="input" id="business_name" name="business_name" required
                placeholder="${isRestaurant ? "Masalan: Bahor Taomxonasi" : "Masalan: Navro'z Saroyi"}">
       </div>

       <div class="notice">
         <p>Assalomu alaykum! 👋</p>
         ${notice}
       </div>

       ${/* Telegram havolasi bu bosqichda ATAYLAB yo'q: odam avval arizani
            yuborishi kerak. Ilgari u shu yerda turardi va ko'pchilik
            arizani yubormasdan to'g'ri Telegramga o'tib ketardi —
            adminda esa hech qanday ariza ko'rinmasdi. */""}
       <button class="btn btn-primary btn-block btn-lg" type="submit" id="apply-submit">
         Arizani yuborish
       </button>
     </form>`,
    { wide: true }
  );

  const form = node.querySelector("#apply-form");
  const errorBox = node.querySelector("#apply-error");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.hidden = true;

    const businessName = form.business_name.value.trim();
    if (!businessName) {
      errorBox.textContent = `${label} nomini kiriting.`;
      errorBox.hidden = false;
      return;
    }

    const done = busy(node.querySelector("#apply-submit"));

    try {
      const result = await api.applications.create({
        business_type: type,
        business_name: businessName,
        plan: plan?.id ?? null,
      });

      await auth.refreshUser();
      modal.close();
      openSentScreen({
        message: result.message,
        telegram: result.admin_telegram || telegram,
        onDone: onSent,
      });
    } catch (error) {
      // Telefon tasdig'i oradan chiqib qolgan bo'lsa (masalan boshqa
      // qurilmada bekor qilingan) — qizil yozuv o'rniga yechim ekrani.
      if (error.status === 403 && /telefon/i.test(error.message)) {
        modal.close();
        openVerifyGate(label);
        return;
      }
      errorBox.textContent = error.fieldError?.("business_name") || error.message;
      errorBox.hidden = false;
    } finally {
      done();
    }
  });
}

/**
 * Bepul sinov uchun: avval TURNI so'raymiz.
 *
 * Pullik tarifda tur rejadan bilinadi ("Restoran 3 oy"), sinovda esa
 * reja yo'q — shuning uchun restoranmi yoki to'yxonami degan savol
 * alohida beriladi.
 */
export function openTypePicker({ plan = null, onSent } = {}) {
  const node = openModal(
    `<h2>Bepul sinov</h2>
     <div class="notice">
       <p>Assalomu alaykum! 👋</p>
       <p><b>7 kun mutlaqo bepul</b> — hech qanday to'lovsiz. Administrator
          arizangizni tasdiqlagach sinov boshlanadi.</p>
       <p class="xs muted">Bepul sinov har bir foydalanuvchiga bir marta
          beriladi. Muddat tugagach pullik tariflardan birini tanlaysiz.</p>
     </div>

     <p class="small strong" style="margin-top:var(--sp-5)">Nima ochmoqchisiz?</p>
     <div class="biz-choice" style="margin-top:var(--sp-3)">
       <button class="opt" type="button" data-pick-type="restaurant">
         <div class="ic">🍽️</div>
         <h3 class="display h4" style="margin-top:var(--sp-2)">Restoran</h3>
       </button>
       <button class="opt" type="button" data-pick-type="venue">
         <div class="ic">🎉</div>
         <h3 class="display h4" style="margin-top:var(--sp-2)">To'yxona</h3>
       </button>
     </div>`,
    { wide: true }
  );

  node.querySelectorAll("[data-pick-type]").forEach((button) => {
    button.addEventListener("click", () => {
      modal.close();
      openApplyModal(button.dataset.pickType, { plan, onSent });
    });
  });
}
