/**
 * Sharh qoldirish oynasi.
 *
 * Backend qoidasi: sharh faqat YAKUNLANGAN bron uchun qoldiriladi.
 * Shuning uchun oyna bronni tanlashdan boshlanadi — foydalanuvchi
 * "nega yozolmayapman" deb chalkashmasligi uchun.
 */
import { api } from "../core/api.js";
import { openModal, modal } from "../ui/modal.js";
import { toast } from "../ui/toast.js";
import { esc, busy } from "../ui/dom.js";
import { dateLabel } from "../ui/format.js";

export function openReviewModal(reservation, { onDone } = {}) {
  const node = openModal(
    `<h2>Sharh qoldirish</h2>
     <p class="muted small">${esc(reservation.business_name)} · ${dateLabel(reservation.date)}</p>

     <form class="stack stack-4" id="review-form" style="margin-top:var(--sp-5)" novalidate>
       <div class="form-alert" id="review-error" hidden></div>

       <div class="field">
         <label>Baho</label>
         <div class="row row-2" id="rating-row">
           ${[1, 2, 3, 4, 5].map((n) => `
             <button type="button" class="btn btn-outline btn-sm" data-rating="${n}"
                     aria-pressed="${n === 5}">${n} ★</button>`).join("")}
         </div>
       </div>

       <div class="field">
         <label for="rv-text">Fikringiz</label>
         <textarea class="textarea" id="rv-text" rows="4"
                   placeholder="Tajribangiz haqida yozing..."></textarea>
       </div>

       <button class="btn btn-primary btn-block btn-lg" type="submit" id="rv-submit">Yuborish</button>
     </form>`
  );

  let rating = 5;
  const setRating = (value) => {
    rating = value;
    node.querySelectorAll("[data-rating]").forEach((button) => {
      const isActive = Number(button.dataset.rating) === value;
      button.setAttribute("aria-pressed", String(isActive));
      button.classList.toggle("btn-primary", isActive);
      button.classList.toggle("btn-outline", !isActive);
    });
  };
  setRating(5);

  node.querySelectorAll("[data-rating]").forEach((button) => {
    button.addEventListener("click", () => setRating(Number(button.dataset.rating)));
  });

  const form = node.querySelector("#review-form");
  const errorBox = node.querySelector("#review-error");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.hidden = true;
    const done = busy(node.querySelector("#rv-submit"));

    try {
      await api.reviews.create({
        reservation: reservation.id,
        rating,
        comment: node.querySelector("#rv-text").value.trim(),
      });
      modal.close();
      toast.ok("Sharhingiz uchun rahmat!");
      if (typeof onDone === "function") onDone();
    } catch (error) {
      errorBox.textContent = error.fieldError?.("reservation") || error.message;
      errorBox.hidden = false;
    } finally {
      done();
    }
  });
}
