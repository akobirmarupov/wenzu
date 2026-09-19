/**
 * "Google bilan davom etish".
 *
 * NEGA POPUP EMAS. Avval Google Identity Services (GSI) ishlatilgan
 * edi: Google o'z tugmasini chizadi, bosilganda popup ochiladi va
 * token `postMessage` orqali qaytadi. Amalda u ishlamadi — Google
 * doimiy ravishda
 *
 *     [GSI_LOGGER]: The given origin is not allowed for the given client ID
 *
 * deb turdi. Manzil Google Console'dagi "Authorized JavaScript
 * origins" ro'yxatiga qo'shilgan va saqlangan bo'lsa ham. O'zgarish
 * Google serverlariga soatlab tarqaladi va biz buni tezlashtira
 * olmaymiz — ya'ni tuzatish bizning qo'limizda emas edi.
 *
 * Endi oddiy qayta yo'naltirish: tugma foydalanuvchini serverimizga
 * yuboradi, u esa Google'ga. Bu yo'l butunlay boshqa ro'yxatga
 * ("Authorized redirect URIs") tayanadi va popup umuman yo'q —
 * demak popup bloklagichlari, uchinchi tomon cookie cheklovlari va
 * `postMessage` uzilishlari ham yo'q. Telefonda ham ishonchliroq:
 * popup o'rniga oddiy sahifa o'tishi.
 *
 * Tugmani endi O'ZIMIZ chizamiz — Google brend qoidasiga mos: oq
 * fon, rasmiy "G" belgisi, aniq matn.
 */
import { auth } from "../core/auth.js";
import { ROUTES } from "../core/config.js";
import { storage } from "../core/storage.js";
import { toast } from "./toast.js";

const START_URL = "/api/auth/google/start/";

/** Rasmiy Google "G" belgisi (SVG, to'rt rangli). */
const GOOGLE_MARK = `
  <svg class="google-mark" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
    <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
    <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
    <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
    <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
  </svg>`;

/**
 * Kirishdan keyin Google bizni `#access=...&refresh=...` bilan
 * qaytaradi. Fragment ATAYLAB: u serverga yuborilmaydi, ya'ni
 * tokenlar kirish jurnallarida yoki `Referer` sarlavhasida qolib
 * ketmaydi.
 *
 * Bu funksiya sahifa ochilishida BIRINCHI bo'lib chaqiriladi.
 * @returns {boolean} kirish amalga oshdimi (shunda sahifa chizilmaydi)
 */
export function consumeGoogleRedirect() {
  const params = new URLSearchParams(window.location.hash.slice(1));
  const access = params.get("access");
  const refresh = params.get("refresh");

  if (!access || !refresh) {
    showRedirectError();
    return false;
  }

  // Fragmentni DARHOL tozalaymiz: odam manzilni nusxalab yuborsa,
  // uning bilan birga amaldagi tokenlari ham ketardi.
  history.replaceState({}, "", window.location.pathname + window.location.search);

  storage.setSession({ access, refresh, user: null });

  // Foydalanuvchi ma'lumotini serverdan olamiz — kimligini va qaysi
  // panelga tegishli ekanini shu javob hal qiladi.
  const created = params.get("created") === "1";
  // `next` fragmentda keladi (serverdan), manzil qatorida emas.
  const next = params.get("next");

  auth
    .refreshUser()
    .then((user) => {
      const name = (user.full_name || "").split(" ")[0];
      toast.ok(
        created
          ? `Xush kelibsiz${name ? ", " + name : ""}! Hisobingiz ochildi.`
          : `Xush kelibsiz${name ? ", " + name : ""}!`
      );

      // YANGI hisob — PROFILGA.
      //
      // Odam endigina ro'yxatdan o'tdi va birinchi ko'radigan narsasi
      // o'z profili bo'lishi kerak: ismi, rasmi va pochtasi Google'dan
      // olinganini shu yerda ko'radi. Aks holda u qayerdan boshlagan
      // bo'lsa o'sha yerga qaytardi va "ro'yxatdan o'tdimmi?" degan
      // savol qolardi.
      //
      // QAYTGAN odam esa ketayotgan joyiga qaytadi — u nima
      // qilayotganini biladi.
      if (created) {
        window.location.href = ROUTES.profile;
        return;
      }
      window.location.href = next || auth.homeFor(user) || ROUTES.home;
    })
    .catch(() => {
      storage.clear();
      toast.error("Kirish yakunlanmadi. Qaytadan urinib ko'ring.");
    });

  return true;
}

/** Google xato bilan qaytargan bo'lsa sababini aytamiz. */
function showRedirectError() {
  const code = new URLSearchParams(window.location.search).get("google_error");
  if (!code) return;

  const messages = {
    cancelled: "Kirish bekor qilindi.",
    blocked: "Hisobingiz bloklangan. Administrator bilan bog'laning.",
    state: "Xavfsizlik tekshiruvi o'tmadi. Sahifani yangilab, qaytadan urining.",
    nocode: "Google javobi to'liq kelmadi. Qaytadan urinib ko'ring.",
    google: "Google bilan bog'lanib bo'lmadi. Qaytadan urinib ko'ring.",
  };
  toast.error(messages[code] || "Kirishda xatolik yuz berdi.");

  // Xato belgisini manzildan olib tashlaymiz — sahifa yangilanganda
  // xabar qaytadan chiqmasin.
  const url = new URL(window.location.href);
  url.searchParams.delete("google_error");
  history.replaceState({}, "", url);
}

/**
 * Tugmani chizadi.
 *
 * @param {string} selector - tugma joylashadigan element
 * @param {object} options  - {label}
 */
export function renderGoogleButton(selector, { label = "Google bilan davom etish" } = {}) {
  const host = document.querySelector(selector);
  if (!host) return;

  const next = new URLSearchParams(window.location.search).get("next");
  const href = next ? `${START_URL}?next=${encodeURIComponent(next)}` : START_URL;

  host.innerHTML = `
    <a class="btn-google" href="${href}">
      ${GOOGLE_MARK}
      <span>${label}</span>
    </a>`;
}
