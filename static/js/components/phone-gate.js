/**
 * Aloqa raqamini bir marta so'raydigan oyna.
 *
 * NEGA KERAK. Ro'yxatdan o'tish Google orqali bo'lgani uchun hisobda
 * telefon raqami YO'Q — Google uni bermaydi. Bron qilinganda esa joy
 * egasi mehmonga qo'ng'iroq qiladi: tasdiqlaydi, kechikish haqida
 * so'raydi, mehmonlar sonini aniqlaydi. Raqamsiz bron — egasi uchun
 * boshi berk ko'cha.
 *
 * NEGA AYNAN SHU YERDA. Raqamni kirish paytida so'rash "bir bosishda
 * kirish"ni buzardi — odam Google tugmasini bosib, darhol yana bir
 * forma ko'rardi. Bron paytida esa u allaqachon aniq maqsad bilan
 * kelgan va raqam so'ralishi tabiiy ko'rinadi.
 *
 * SMS YO'Q. Kod yuborilmaydi, tasdiqlanmaydi — foydalanuvchi shunchaki
 * o'z raqamini yozadi. Yolg'on raqam yozishdan yutadigan narsasi yo'q:
 * qo'ng'iroq unga kelmaydi va broni tasdiqlanmay qoladi.
 */
import { api } from "../core/api.js";
import { auth } from "../core/auth.js";
import { modal } from "../ui/modal.js";
import { busy } from "../ui/dom.js";
import { toast } from "../ui/toast.js";

const PHONE_PATTERN = /^\+998\d{9}$/;

// Raqam NEGA kerakligi har joyda boshqacha. Umumiy "raqamingizni
// kiriting" degan matn odamni shubhaga soladi: "nega endi, men
// shunchaki tarif tanlayapman-ku?". Aniq sabab esa savolni yopadi.
const REASONS = {
  booking: "Joy egasi bronni tasdiqlash uchun shu raqamga qo'ng'iroq qiladi.",
  application: "Administrator arizangizni ko'rib chiqib, shu raqamga bog'lanadi.",
  subscription: "Administrator to'lovni shu raqam orqali siz bilan kelishadi.",
};

/**
 * Raqam bo'lsa darhol `true` qaytaradi, bo'lmasa oyna ochib so'raydi.
 *
 * @param {string} reason - nima uchun so'ralayotgani: "booking" |
 *        "application" | "subscription"
 * @returns {Promise<boolean>} davom etish mumkinmi
 */
export function ensurePhone(reason = "booking") {
  const user = auth.user();
  if (user?.phone_number) return Promise.resolve(true);

  return new Promise((resolve) => {
    let saved = false;

    const node = modal.open(`
      <h2 class="display h3">Aloqa raqamingiz</h2>
      <p class="muted small">
        ${REASONS[reason] || REASONS.booking}
        Bir marta yoziladi — boshqa so'ralmaydi.
      </p>

      <form class="stack stack-4" id="phone-form" style="margin-top:var(--sp-5)" novalidate>
        <div class="form-alert" id="phone-error" hidden></div>

        <div class="field">
          <label for="gate-phone">Telefon raqami</label>
          <input class="input" id="gate-phone" name="phone_number" type="tel"
                 inputmode="tel" autocomplete="tel" placeholder="+998901234567"
                 value="+998" required>
          <span class="field-hint">SMS yuborilmaydi — raqam faqat kerakli odamga ko'rinadi.</span>
        </div>

        <button class="btn btn-primary btn-block" type="submit" id="phone-save">
          Saqlash va davom etish
        </button>
      </form>`, {
      onClose: () => {
        // Oyna yopilsa bron oqimi TO'XTAYDI: raqamsiz server baribir
        // rad etadi (`HasContactPhone`), formani ochib qo'yish esa
        // odamni bekorga to'ldirishga majburlardi.
        if (!saved) resolve(false);
      },
    });

    const input = node.querySelector("#gate-phone");
    const errorBox = node.querySelector("#phone-error");

    // Kursor "+998" dan KEYIN tursin — odam boshiga yozib, raqamni
    // buzib qo'ymasin.
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);

    node.querySelector("#phone-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      errorBox.hidden = true;

      const phone = input.value.replace(/[\s()-]/g, "");
      if (!PHONE_PATTERN.test(phone)) {
        errorBox.textContent = "Raqam +998 bilan boshlanib, 9 ta raqamdan iborat bo'lsin.";
        errorBox.hidden = false;
        input.focus();
        return;
      }

      const done = busy(node.querySelector("#phone-save"));
      try {
        await api.auth.updateMe({ phone_number: phone });
        // Saqlangan nusxani yangilaymiz — aks holda keyingi bronda
        // oyna qaytadan ochilardi.
        await auth.refreshUser();
        saved = true;
        modal.close();
        toast.ok("Raqam saqlandi.");
        resolve(true);
      } catch (error) {
        // Raqam boshqa hisobda ham bo'lishi mumkin — bu xato emas.
        // Bu yerga faqat format xatosi yoki tarmoq uzilishi tushadi.
        errorBox.textContent =
          error.fieldError?.("phone_number") ||
          "Raqamni saqlab bo'lmadi. Qaytadan urinib ko'ring.";
        errorBox.hidden = false;
      } finally {
        done();
      }
    });
  });
}
