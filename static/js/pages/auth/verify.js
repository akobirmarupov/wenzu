/** SMS kodni tasdiqlash sahifasi. */
import { api } from "../../core/api.js";
import { ROUTES } from "../../core/config.js";
import { storage } from "../../core/storage.js";
import { $, $$, busy, esc } from "../../ui/dom.js";
import { toast } from "../../ui/toast.js";
import { initI18n } from "../../core/i18n.js";
import { theme } from "../../core/theme.js";
import { renderControls } from "../../ui/controls.js";

theme.init();
await initI18n();
renderControls("#auth-controls");

const phone = storage.getPendingPhone();
if (!phone) {
  // Bu sahifaga to'g'ridan-to'g'ri kirib bo'lmaydi — avval ro'yxatdan o'tiladi.
  window.location.replace(ROUTES.register);
}

$("#phone-label").innerHTML = `<span class="mono strong">${esc(phone || "")}</span> raqamiga`;

const inputs = $$("#code-inputs input");
const form = $("#verify-form");
const errorBox = $("#form-error");

/** Kataklar orasida avtomatik o'tish va joylashtirishni qo'llab-quvvatlash. */
inputs.forEach((input, index) => {
  input.addEventListener("input", () => {
    input.value = input.value.replace(/\D/g, "");
    if (input.value && index < inputs.length - 1) inputs[index + 1].focus();
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Backspace" && !input.value && index > 0) inputs[index - 1].focus();
  });
  input.addEventListener("paste", (event) => {
    const text = (event.clipboardData.getData("text") || "").replace(/\D/g, "").slice(0, 6);
    if (!text) return;
    event.preventDefault();
    text.split("").forEach((char, i) => {
      if (inputs[i]) inputs[i].value = char;
    });
    inputs[Math.min(text.length, inputs.length - 1)].focus();
  });
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.hidden = true;

  const code = inputs.map((input) => input.value).join("");
  if (code.length !== 6) {
    errorBox.textContent = "6 xonali kodni to'liq kiriting.";
    errorBox.hidden = false;
    return;
  }

  const done = busy($("#submit"));
  try {
    await api.auth.verifyPhone(phone, code);
    toast.ok("Raqam tasdiqlandi! Endi tizimga kiring.");
    window.location.href = ROUTES.login;
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.hidden = false;
    inputs.forEach((input) => (input.value = ""));
    inputs[0].focus();
  } finally {
    done();
  }
});

$("#resend").addEventListener("click", async () => {
  try {
    await api.auth.sendCode(phone);
    toast.ok("Yangi kod yuborildi.");
  } catch (error) {
    toast.fromError(error);
  }
});
