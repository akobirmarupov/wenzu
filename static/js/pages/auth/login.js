/**
 * Kirish sahifasi.
 *
 * Asosiy yo'l — Google tugmasi (`ui/google-signin.js`). Pastdagi
 * parol formasi eski hisoblar va administrator uchun qoldirilgan;
 * yangi ro'yxat u yerdan o'tmaydi.
 */
import { auth } from "../../core/auth.js";
import { redirectIfAuthenticated } from "../../core/guard.js";
import { $, formValues, busy } from "../../ui/dom.js";
import { toast } from "../../ui/toast.js";
import { initI18n } from "../../core/i18n.js";
import { theme } from "../../core/theme.js";
import { renderControls } from "../../ui/controls.js";
import { initAuthVisual } from "../../ui/auth-visual.js";
import { consumeGoogleRedirect, renderGoogleButton } from "../../ui/google-signin.js";

// GOOGLE'DAN QAYTISH — ENG BIRINCHI TEKSHIRILADI.
//
// `redirectIfAuthenticated()` dan ham oldin. Sabab: u
// `location.replace` bilan ishlaydi va manzilni almashtirganda
// fragmentdagi (`#access=...`) tokenlar yo'qolardi. Ya'ni eski
// sessiyasi bor odam Google bilan qaytganda kirishi bekorga
// ketardi.
const arrivedFromGoogle = consumeGoogleRedirect();

if (!arrivedFromGoogle) {
  redirectIfAuthenticated();
}

theme.init();
await initI18n();
renderControls("#auth-controls");
initAuthVisual();

if (!arrivedFromGoogle) {
  renderGoogleButton("#google-button");
}

const form = $("#login-form");
const errorBox = $("#form-error");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.hidden = true;

  const { username, password } = formValues(form);
  const done = busy($("#submit"));

  try {
    const user = await auth.login(username.trim(), password);
    toast.ok(`Xush kelibsiz, ${user.full_name.split(" ")[0]}!`);

    // `?next=` bo'lsa foydalanuvchini o'zi ketayotgan sahifaga qaytaramiz.
    const next = new URLSearchParams(window.location.search).get("next");
    window.location.href = next || auth.homeFor(user);
  } catch (error) {
    errorBox.textContent =
      error.status === 401
        ? "Username yoki parol noto'g'ri."
        : error.message;
    errorBox.hidden = false;
  } finally {
    done();
  }
});
