/**
 * Tarif kartochkalari — obuna va premium tanlash oynasi.
 *
 * BITTA komponent uch joyda ishlatiladi: profil ichidagi "Premium"
 * bo'limi, biznes egasining "Obuna" paneli va (kelajakda) reklama
 * sahifasi. Har birida qaytadan yozilsa, narx yoki matn bir joyda
 * o'zgarib, boshqasida eskiligicha qolib ketardi.
 *
 * Ko'rinish HAMMA UCHUN BIR XIL — uchta ustun:
 *   [ Bepul sinov 0 so'm ]  [ Restoran ]  [ To'yxona ]
 *
 * Muddat (1 oy / 3 oy) kartochkaning ICHIDA almashadi. Foydalanuvchi
 * ikki qaror qabul qiladi — qaysi tur va qancha muddat — shuning uchun
 * ular ikki darajaga bo'lingan.
 *
 * Biznes egasi ham AYNAN shu uchtani ko'radi: o'zining turi ochiq,
 * ikkinchisi esa ko'rinadi-yu tanlab bo'lmaydi. Ilgari unga faqat o'z
 * turi ko'rsatilardi va ekran boshqa foydalanuvchinikidan farq qilib,
 * "menda nega boshqacha?" degan savol tug'dirardi.
 */
import { api } from "../core/api.js";
import { esc, busy } from "../ui/dom.js";
import { money } from "../ui/format.js";
import { openModal, modal } from "../ui/modal.js";
import { toast } from "../ui/toast.js";

/** Har bir tarifga kiradigan imkoniyatlar — barchasida bir xil asos. */
const BASE_FEATURES = [
  "Platformada ko'rinish va qidiruvda chiqish",
  "Onlayn bron qabul qilish",
  "Menyu, xona va zallarni boshqarish",
  "Mijoz sharhlari va reyting",
];

const EXTRA_FEATURES = [
  { icon: "⚡", title: "Tezkor qo'llab-quvvatlash", text: "Telegram orqali to'g'ridan-to'g'ri aloqa" },
  { icon: "📊", title: "Statistika", text: "Bronlar, daromad va reyting bir joyda" },
  { icon: "🛡", title: "Ishonchli saqlash", text: "Ma'lumotlaringiz zaxiralanadi" },
];

const TYPE_LABEL = { restaurant: "Restoran", venue: "To'yxona" };

/* ===================================================================
   Chizish
   =================================================================== */

function featureListHtml() {
  return `
    <div class="price-features">
      <span class="price-features-head">✦ Nimalar kiradi:</span>
      <ul>
        ${BASE_FEATURES.map((item) => `
          <li><span class="tick" aria-hidden="true">✓</span><span>${esc(item)}</span></li>`).join("")}
      </ul>

      <span class="price-features-head">Qo'shimcha imkoniyatlar</span>
      <ul class="extras">
        ${EXTRA_FEATURES.map((item) => `
          <li>
            <span class="ic" aria-hidden="true">${item.icon}</span>
            <span>
              <b>${esc(item.title)}</b>
              <span class="xs muted">${esc(item.text)}</span>
            </span>
          </li>`).join("")}
      </ul>
    </div>`;
}

/**
 * Bepul sinov kartochkasi.
 *
 * Sinov SOTILMAYDI — u admin arizani tasdiqlagach avtomatik beriladi.
 * Shuning uchun bu yerda tugma o'rniga holat yozuvi turadi: "faol",
 * "ishlatilgan" yoki "tasdiq kutilmoqda".
 */
function trialCardHtml(state, { trialUsed }) {
  // Holat yozuvi — tugma o'rniga ko'rsatiladigan hollarda.
  const label = {
    awaiting: "Tasdiq kutilmoqda",
    active: "Hozir faol",
    used: "Ishlatilgan",
  }[state];

  // Sinovni TANLASH mumkinmi.
  //
  // Faqat biznesi yo'q va sinovni hali ishlatmagan odam tanlaydi.
  // Har bir foydalanuvchiga bir marta — aks holda odam biznesini
  // o'chirib, yangisini ochib, sinovni cheksiz qayta olardi.
  const selectable = state === "guest" && !trialUsed;

  return `
    <article class="price-card ${
      state === "active" ? "current" : selectable ? "" : "muted-card"}">
      <div class="price-card-body">
        <h3>Bepul <span class="tone">sinov</span></h3>
        <p class="small muted">
          ${selectable
            ? "Boshlash uchun — hech qanday to'lovsiz. Har bir foydalanuvchiga bir marta."
            : trialUsed && state === "guest"
              ? "Siz bepul sinovdan allaqachon foydalangansiz."
              : "Boshlash uchun — hech qanday to'lovsiz."}
        </p>

        <div class="price-amount">
          <b>0</b>
          <span>so'm / 7 kun</span>
        </div>

        ${selectable
          ? `<button class="btn btn-outline btn-block btn-lg" type="button" data-choose-trial>
               Bepul sinovni tanlash
             </button>`
          : `<span class="price-state">${esc(
              trialUsed && state === "guest" ? "Ishlatilgan" : label || "Ishlatilgan"
            )}</span>`}
      </div>
      ${featureListHtml()}
    </article>`;
}

/**
 * Bitta biznes turi uchun BITTA kartochka.
 *
 * Muddatlar (1 oy, 3 oy) kartochka ICHIDA almashtirgich bo'lib turadi.
 * Ilgari har bir muddat alohida kartochka edi va ekranda to'rtta
 * ustun paydo bo'lardi: "Restoran 1 oy", "Restoran 3 oy", "To'yxona
 * 1 oy", "To'yxona 3 oy". Foydalanuvchi esa aslida IKKI qaror qabul
 * qiladi — qaysi tur va qancha muddat — shuning uchun ular ikki
 * darajaga bo'lingani tabiiyroq.
 *
 * Barcha variantlar birdaniga chiziladi, almashtirish esa faqat
 * ko'rinishni o'zgartiradi — shunda bosilganda hech narsa qayta
 * yuklanmaydi va sakrash bo'lmaydi.
 */
function planCardHtml(businessType, plans, { disabled, foreign, reason }) {
  const sorted = [...plans].sort((a, b) => a.duration_months - b.duration_months);
  const hasLong = sorted.some((plan) => plan.duration_months > 1);
  const off = disabled || foreign;

  return `
    <article class="price-card ${foreign ? "muted-card" : ""}" data-plan-card="${esc(businessType)}">
      <span class="price-ribbon"${hasLong ? "" : ' hidden'}>Tavsiya etiladi</span>

      <div class="price-card-body">
        <h3>${esc(TYPE_LABEL[businessType] || "")} <span class="tone">obunasi</span></h3>

        ${sorted.length > 1 ? `
          <div class="plan-toggle" role="group" aria-label="Muddat">
            ${sorted.map((plan, index) => `
              <button type="button" data-duration="${plan.duration_months}"
                      class="${index === 0 ? "active" : ""}">
                ${esc(plan.duration_label)}
                ${plan.savings ? `<span class="cut">−${money(plan.savings, { withSuffix: false })}</span>` : ""}
              </button>`).join("")}
          </div>` : ""}

        ${sorted.map((plan, index) => `
          <div class="plan-variant ${index === 0 ? "active" : ""}" data-variant="${plan.duration_months}">
            <p class="small muted">
              ${plan.duration_months > 1
                ? `Uzoq muddat — oyiga ${money(plan.price_per_month, { withSuffix: false })} so'm.`
                : "Oyma-oy to'lov, istalgan vaqtda to'xtatasiz."}
            </p>

            <div class="price-amount">
              <b>${money(plan.price, { withSuffix: false })}</b>
              <span>so'm / ${esc(plan.duration_label)}</span>
            </div>

            ${plan.savings
              ? `<span class="price-save">${money(plan.savings, { withSuffix: false })} so'm tejaysiz</span>`
              : ""}

            <button class="btn ${plan.duration_months > 1 ? "btn-gold" : "btn-primary"} btn-block btn-lg"
                    type="button" data-choose-plan="${esc(plan.id)}" ${off ? "disabled" : ""}>
              ${esc(plan.duration_label)}ni tanlash
            </button>
            ${foreign && reason ? `<span class="xs muted center">${esc(reason)}</span>` : ""}
          </div>`).join("")}
      </div>

      ${featureListHtml()}
    </article>`;
}

/**
 * Tarif oynasini chizadi.
 *
 * @param {object} options
 *   businessType — qaysi turdagi rejalar ko'rsatilsin
 *   plans        — `/api/owner/subscription/` yoki `/api/settings/` dan kelgan ro'yxat
 *   status       — obuna holati: trial | active | expired | awaiting_approval
 *   pending      — ochiq ariza (bo'lsa tugmalar bloklanadi)
 */
export function pricingHtml({ plans, status, pending, ownedType = null, trialUsed = false }) {
  if (!plans?.length) return "";

  // Tur bo'yicha guruhlaymiz: har bir turga BITTA kartochka, muddatlar
  // esa uning ichida almashadi. FILTR YO'Q — ikkala tur ham har doim
  // ko'rinadi, ya'ni ekran hamma uchun bir xil.
  const groups = new Map();
  plans.forEach((plan) => {
    if (!groups.has(plan.business_type)) groups.set(plan.business_type, []);
    groups.get(plan.business_type).push(plan);
  });

  const trialState =
    status === "guest" ? "guest"
      : status === "awaiting_approval" ? "awaiting"
        : status === "trial" ? "active" : "used";
  const locked = Boolean(pending) || status === "awaiting_approval";

  return `
    <div class="price-wrap">
      ${pending ? pendingNoticeHtml(pending) : ""}
      <div class="price-grid">
        ${trialCardHtml(trialState, { trialUsed })}
        ${[...groups.entries()]
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([type, list]) => planCardHtml(type, list, {
            disabled: locked,
            // Biznes egasiga BEGONA tur ko'rinadi, lekin tanlab
            // bo'lmaydi: server baribir "reja biznes turiga mos emas"
            // deb rad etardi, ya'ni tugma bosiladigan bo'lsa faqat
            // xato chiqarardi.
            foreign: Boolean(ownedType) && type !== ownedType,
            reason: `Sizning biznesingiz — ${TYPE_LABEL[ownedType] || ""}`,
          }))
          .join("")}
      </div>
    </div>`;
}

function pendingNoticeHtml(pending) {
  return `
    <div class="price-pending">
      <span class="ic" aria-hidden="true">⏳</span>
      <span>
        <b>Arizangiz ko'rib chiqilmoqda</b>
        <span class="small">
          ${esc(pending.plan_label)} — ${money(pending.price)}.
          To'lovni amalga oshiring va administrator tasdiqlashini kuting.
        </span>
      </span>
    </div>`;
}

/* ===================================================================
   Ariza yuborish
   =================================================================== */

/**
 * Tanlangan tarif uchun ariza yuborish oynasi.
 *
 * Oqim biznes ochish bilan bir xil: ariza → Telegram orqali to'lov →
 * admin tasdig'i. To'lov platformada emas, shuning uchun bu oynaning
 * asosiy vazifasi — nima qilish kerakligini aniq aytish.
 */
/**
 * @param {object} options
 *   mode — "renew": obunani uzaytirish arizasi (biznesi bor egasi)
 *          "open" : biznes ochish arizasi (biznesi yo'q foydalanuvchi)
 *
 * Nega bitta komponent ikki rejimda: tarif tanlash va biznes ochish —
 * foydalanuvchi uchun BITTA qaror ("shu narxga ishlayman"). Ularni ikki
 * ekranga bo'lish "endi qayerga bosay?" degan savol tug'dirardi.
 */
export function bindPricing(root, { plans, telegram = "@uvente", onSent, mode = "renew" } = {}) {
  const container = typeof root === "string" ? document.querySelector(root) : root;
  if (!container) return;

  // Muddat almashtirgichi — faqat ko'rinish o'zgaradi, hech narsa
  // qayta yuklanmaydi.
  container.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-duration]");
    if (!chip) return;

    const card = chip.closest("[data-plan-card]");
    const months = chip.dataset.duration;

    card.querySelectorAll("[data-duration]").forEach((other) =>
      other.classList.toggle("active", other === chip)
    );
    card.querySelectorAll("[data-variant]").forEach((variant) =>
      variant.classList.toggle("active", variant.dataset.variant === months)
    );
    // "Tavsiya etiladi" lentasi faqat uzoq muddat tanlanganda.
    card.classList.toggle("best", Number(months) > 1);
  });

  // Bepul sinov — tarifsiz ariza (`plan: null`).
  container.addEventListener("click", async (event) => {
    if (!event.target.closest("[data-choose-trial]")) return;

    const { openTypePicker } = await import("./apply-modal.js");
    openTypePicker({ plan: null, onSent });
  });

  container.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-choose-plan]");
    if (!button) return;

    const plan = (plans || []).find((row) => row.id === button.dataset.choosePlan);
    if (!plan) return;

    if (mode === "open") {
      // Biznesi yo'q — tarif tanlash "biznes ochish" arizasini boshlaydi.
      // Tur rejadan ma'lum, ya'ni foydalanuvchidan qayta so'ralmaydi.
      const { openApplyModal } = await import("./apply-modal.js");
      openApplyModal(plan.business_type, { plan, onSent });
      return;
    }

    openRequestModal(plan, telegram, onSent);
  });
}

function openRequestModal(plan, telegram, onSent) {
  const handle = telegram.replace("@", "");
  const telegramUrl = `https://t.me/${handle}`;

  const node = openModal(
    `<h2>Obunani faollashtirish</h2>
     <p class="muted small" style="margin-bottom:var(--sp-5)">
       ${esc(TYPE_LABEL[plan.business_type] || "")} · ${esc(plan.duration_label)}
     </p>

     <div class="notice">
       <p><b>Assalomu alaykum! 👋</b></p>
       <p>Obunani faollashtirish uchun adminlarimiz bilan bog'laning.
          Quyidagi tugmani bossangiz arizangiz <b>shu zahoti yuboriladi</b>
          va Telegram ochiladi — u yerda to'lov bo'yicha kelishasiz.</p>
       <p>Administrator to'lovni tasdiqlagach, obunangiz
          <b>${esc(plan.duration_label)}</b>ga uzayadi va joyingiz
          qidiruvda qayta ko'rinadi.</p>
     </div>

     <div class="total-box" style="margin-top:var(--sp-4)">
       <div class="row"><span>Muddat</span><b>${esc(plan.duration_label)}</b></div>
       ${plan.duration_months > 1
         ? `<div class="row"><span>Oyiga</span><b>${money(plan.price_per_month)}</b></div>` : ""}
       <div class="row grand"><span>To'lov summasi</span><b>${money(plan.price)}</b></div>
     </div>

     <div class="field" style="margin-top:var(--sp-4)">
       <label for="renew-note">Izoh (ixtiyoriy)</label>
       <input class="input" id="renew-note" placeholder="Masalan: to'lov chekini yuboraman">
     </div>

     ${/* BITTA tugma — ikki ish: ariza yuboriladi va Telegram ochiladi.
          Ilgari ikkita alohida element edi (havola + tugma) va odam
          faqat bittasini bosib, ikkinchisini o'tkazib yuborardi:
          yo ariza yubormay Telegramga yozardi, yo ariza yuborib
          admin bilan bog'lanmasdi. */""}
     <button class="btn btn-primary btn-block btn-lg" style="margin-top:var(--sp-4)"
             type="button" id="renew-submit">
       ✈️ Ariza yuborish va admin bilan bog'lanish
     </button>
     <p class="xs muted center" style="margin-top:var(--sp-2)">
       Bir bosishda ikkalasi ham bajariladi
     </p>`,
    { wide: true }
  );

  node.querySelector("#renew-submit").addEventListener("click", async (event) => {
    // Telegram oynasi BOSISH PAYTIDA ochiladi, so'rovdan keyin emas.
    //
    // Brauzerlar `window.open` ni faqat foydalanuvchi harakatiga javoban
    // ruxsat beradi. `await` dan keyin ochilsa, u "foydalanuvchi
    // so'ramagan qalqib chiquvchi oyna" hisoblanib bloklanadi. Shuning
    // uchun avval bo'sh oyna ochamiz, manzilni keyin qo'yamiz.
    const tab = window.open("", "_blank");

    const done = busy(event.currentTarget);
    try {
      await api.owner.requestRenewal({
        plan: plan.id,
        note: node.querySelector("#renew-note").value.trim(),
      });

      if (tab && !tab.closed) {
        tab.location.href = telegramUrl;
      } else {
        // Qalqib chiquvchi oyna bloklangan — hech bo'lmasa shu oynada.
        window.location.href = telegramUrl;
        return;
      }

      modal.close();
      toast.ok("Ariza yuborildi. Telegram orqali to'lovni kelishing.");
      onSent?.();
    } catch (error) {
      // Ariza ketmadi — bo'sh oynani yopamiz, aks holda odam bo'm-bo'sh
      // sahifa bilan qolib, arizasi yuborilgan deb o'ylardi.
      if (tab && !tab.closed) tab.close();
      toast.fromError(error);
    } finally {
      done();
    }
  });
}
