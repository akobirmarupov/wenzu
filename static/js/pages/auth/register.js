/** Ro'yxatdan o'tish sahifasi. */
import { auth } from "../../core/auth.js";
import { api } from "../../core/api.js";
import { ROUTES } from "../../core/config.js";
import { redirectIfAuthenticated } from "../../core/guard.js";
import { $, $$, formValues, busy } from "../../ui/dom.js";
import { toast } from "../../ui/toast.js";
import { initI18n } from "../../core/i18n.js";
import { theme } from "../../core/theme.js";
import { renderControls } from "../../ui/controls.js";

redirectIfAuthenticated();
theme.init();
await initI18n();
renderControls("#auth-controls");

const form = $("#register-form");
const errorBox = $("#form-error");

function clearFieldErrors() {
  $$("[data-error]").forEach((node) => {
    node.hidden = true;
    node.textContent = "";
  });
  $$(".input").forEach((input) => input.removeAttribute("aria-invalid"));
}

function showFieldErrors(error) {
  let shown = false;
  $$("[data-error]").forEach((node) => {
    const field = node.dataset.error;
    const message = error.fieldError?.(field);
    if (!message) return;
    node.textContent = message;
    node.hidden = false;
    document.getElementById(field)?.setAttribute("aria-invalid", "true");
    shown = true;
  });
  return shown;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearFieldErrors();
  errorBox.hidden = true;

  const values = formValues(form);
  values.phone_number = values.phone_number.replace(/\s/g, "");

  if (values.password !== values.password_confirm) {
    errorBox.textContent = "Parollar mos kelmadi.";
    errorBox.hidden = false;
    return;
  }

  const done = busy($("#submit"));
  try {
    await auth.register(values);
    // Ro'yxatdan o'tish bilan birga kodni ham darrov yuboramiz —
    // foydalanuvchi qo'shimcha tugma bosishi shart bo'lmasin.
    await api.auth.sendCode(values.phone_number);
    toast.ok("Kod yuborildi. Raqamingizni tasdiqlang.");
    window.location.href = ROUTES.verify;
  } catch (error) {
    if (!showFieldErrors(error)) {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
    }
  } finally {
    done();
  }
});
