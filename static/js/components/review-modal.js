/**
 * Sharh qoldirish oynasi.
 *
 * Backend qoidasi: sharh faqat YAKUNLANGAN bron uchun qoldiriladi,
 * ya'ni tashrif vaqti tugagandan keyin. Oyna ikki joydan ochiladi:
 *   · "Bronlarim" dagi "Sharh qoldirish" tugmasi;
 *   · vaqti tugagan bron uchun O'ZI ochiladigan so'rov
 *     (`review-prompt.js`).
 *
 * ===================================================================
 * NEGA YULDUZCHA, RAQAM EMAS
 * ===================================================================
 * Ilgari baho beshta tugma edi: "1★", "2★" ... "5★". Odam raqamni
 * o'qib, keyin tanlashi kerak edi — bu bir qadam ortiqcha. Endi
 * beshta yulduzning o'zi turadi: uchinchisini bossang, uchtasi
 * yonadi. Bu butun dunyoda tanish harakat, tushuntirish talab
 * qilmaydi. Sichqoncha ustidan o'tganda ham oldindan ko'rinadi.
 */
import { api } from "../core/api.js";
import { t } from "../core/i18n.js";
import { openModal, modal } from "../ui/modal.js";
import { toast } from "../ui/toast.js";
import { esc, busy } from "../ui/dom.js";
import { icon } from "../ui/icons.js";
import { dateLabel } from "../ui/format.js";

const STARS = [1, 2, 3, 4, 5];

/**
 * @param {object} reservation - {id, business_name, date}
 * @param {object} options
 * @param {function} [options.onDone]  - sharh yuborilgach
 * @param {function} [options.onClose] - oyna yopilganda (bekor qilinsa ham)
 * @param {string}  [options.intro]    - sarlavha ostidagi qo'shimcha izoh
 */
export function openReviewModal(reservation, { onDone, onClose, intro = "" } = {}) {
  const node = openModal(
    `<h2 class="display h3">${esc(t("review.title"))}</h2>
     <p class="muted small">${esc(reservation.business_name)} · ${dateLabel(reservation.date)}</p>
     ${intro ? `<p class="small" style="margin-top:var(--sp-2)">${esc(intro)}</p>` : ""}

     <form class="stack stack-4" id="review-form" style="margin-top:var(--sp-5)" novalidate>
       <div class="form-alert" id="review-error" hidden></div>

       <div class="field">
         <label id="rating-label">${esc(t("review.rating"))}</label>
         <div class="rating-picker" id="rating-row" role="radiogroup" aria-labelledby="rating-label">
           ${STARS.map((n) => `
             <button type="button" class="rating-star" data-rating="${n}"
                     role="radio" aria-checked="false"
                     aria-label="${esc(t("review.starLabel", { n }))}">
               ${icon("star", { size: 30, fill: true })}
             </button>`).join("")}
         </div>
         <span class="rating-caption" id="rating-caption"></span>
       </div>

       <div class="field">
         <label for="rv-text">${esc(t("review.comment"))}</label>
         <textarea class="textarea" id="rv-text" rows="4"
                   placeholder="${esc(t("review.commentPlaceholder"))}"></textarea>
       </div>

       <button class="btn btn-primary btn-block btn-lg" type="submit" id="rv-submit" disabled>
         ${esc(t("review.submit"))}
       </button>
     </form>`,
    {
      onClose,
      // Oyna ochilganda fokus BIRINCHI yulduzga tushardi va uning
      // atrofidagi halqa "bir yulduz tanlangan"dek ko'rinardi —
      // aslida hali hech narsa tanlanmagan. Fokusni oynaning o'ziga
      // beramiz: klaviatura bilan yurish saqlanadi, lekin hech qaysi
      // yulduz yolg'ondan tanlangandek turmaydi.
      onMount: (dialog) => {
        dialog.setAttribute("tabindex", "-1");
        dialog.focus();
      },
    }
  );

  const caption = node.querySelector("#rating-caption");
  const submit = node.querySelector("#rv-submit");
  const buttons = [...node.querySelectorAll("[data-rating]")];

  // Baho ATAYLAB oldindan qo'yilmaydi.
  //
  // Ilgari beshta yulduz tayyor turardi va odam hech narsa tanlamasdan
  // "Yuborish" ni bossa, joy avtomatik 5 baho olardi. Ya'ni reyting
  // odamlarning fikri emas, standart qiymat bo'lib qolardi. Endi
  // tanlanmaguncha tugma ochilmaydi.
  let rating = 0;

  const paint = (value) => {
    buttons.forEach((button) => {
      const on = Number(button.dataset.rating) <= value;
      button.classList.toggle("is-on", on);
      button.setAttribute("aria-checked", String(Number(button.dataset.rating) === rating));
    });
    caption.textContent = value ? t(`review.score${value}`) : "";
  };

  buttons.forEach((button) => {
    const value = Number(button.dataset.rating);
    button.addEventListener("click", () => {
      rating = value;
      submit.disabled = false;
      paint(rating);
    });
    // Sichqoncha ustidan o'tganda oldindan ko'rsatamiz, olib ketilganda
    // tanlangan bahoga qaytadi.
    button.addEventListener("mouseenter", () => paint(value));
  });
  node.querySelector("#rating-row").addEventListener("mouseleave", () => paint(rating));

  const form = node.querySelector("#review-form");
  const errorBox = node.querySelector("#review-error");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.hidden = true;

    if (!rating) {
      errorBox.textContent = t("review.pickRating");
      errorBox.hidden = false;
      return;
    }

    const done = busy(submit);
    try {
      await api.reviews.create({
        reservation: reservation.id,
        rating,
        comment: node.querySelector("#rv-text").value.trim(),
      });
      modal.close();
      toast.ok(t("review.thanks"));
      if (typeof onDone === "function") onDone();
    } catch (error) {
      errorBox.textContent = error.fieldError?.("reservation") || error.message;
      errorBox.hidden = false;
    } finally {
      done();
    }
  });
}
