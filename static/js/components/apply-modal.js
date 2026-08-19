/**
 * "Restoran / To'yxona ochish" arizasi oynasi.
 *
 * Ariza yuborilgach rol serverda o'zgaradi, lekin qo'ldagi JWT ichida
 * eski rol qolib ketadi — shuning uchun profilni qayta o'qib olamiz.
 */
import { api } from "../core/api.js";
import { auth } from "../core/auth.js";
import { ROUTES } from "../core/config.js";
import { openModal, modal } from "../ui/modal.js";
import { toast } from "../ui/toast.js";
import { esc, busy } from "../ui/dom.js";
import { money } from "../ui/format.js";

export async function openApplyModal(type) {
  const isRestaurant = type === "restaurant";
  const label = isRestaurant ? "Restoran" : "To'yxona";

  let settings = null;
  try {
    settings = await api.settings();
  } catch {
    /* narxsiz ham davom etamiz */
  }

  const plan = settings?.plans?.find((p) => p.business_type === type);
  const price = plan ? money(plan.monthly_price) : "—";
  const trialDays = settings?.trial_days ?? 7;
  const telegram = settings?.admin_telegram || "@uvente";

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
         <p>${label}ingizni WENZU platformasiga qo'shish uchun oylik obuna narxi —
            <b>${esc(price)}</b>. Boshlanishiga esa <b>${trialDays} kun mutlaqo bepul</b>:
            tizimni sinab ko'rasiz, keyin xohlasangiz davom ettirasiz.</p>
         <p>Arizani tasdiqlatish uchun <b>${esc(telegram)}</b> administratorga
            Telegram orqali murojaat qiling.</p>
       </div>

       <a class="tg-line" href="https://t.me/${esc(telegram.replace("@", ""))}" target="_blank" rel="noopener">
         ✈️ Telegram: ${esc(telegram)}
       </a>

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
    const done = busy(node.querySelector("#apply-submit"));

    try {
      const result = await api.applications.create({
        business_type: type,
        business_name: businessName,
      });

      await auth.refreshUser();
      modal.close();

      openModal(
        `<h2>Arizangiz qabul qilindi ✅</h2>
         <div class="notice">
           <p>${esc(result.message)}</p>
         </div>
         <a class="tg-line" href="https://t.me/${esc((result.admin_telegram || telegram).replace("@", ""))}"
            target="_blank" rel="noopener">✈️ ${esc(result.admin_telegram || telegram)}</a>
         <a class="btn btn-primary btn-block btn-lg" style="margin-top:var(--sp-5)"
            href="${ROUTES.ownerHome}">Panelimga o'tish</a>`,
        { wide: true }
      );
    } catch (error) {
      errorBox.textContent = error.fieldError?.("business_name") || error.message;
      errorBox.hidden = false;
    } finally {
      done();
    }
  });
}
