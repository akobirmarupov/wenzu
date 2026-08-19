/**
 * "Biznes ochish" — alohida sahifa.
 *
 * Uch holatni o'zi hal qiladi: biznesi bor / arizasi ko'rib chiqilmoqda /
 * hali yo'q. Profil ichidan ham shu sahifaga havola bor.
 */
import { requireAuth } from "../../core/guard.js";
import { initI18n } from "../../core/i18n.js";
import { theme } from "../../core/theme.js";
import { auth } from "../../core/auth.js";
import { render } from "../../ui/dom.js";
import { initPublicNav } from "../../ui/public-nav.js";
import { initTopbar } from "../../ui/topbar.js";
import * as businessSection from "./sections/business.js";

theme.init();
await initI18n();
initPublicNav();
initTopbar();

let user = requireAuth();
if (user) start();

async function start() {
  // Ariza yuborilgach rol o'zgaradi — eng so'nggi holatni olamiz.
  try {
    user = await auth.refreshUser();
  } catch {
    /* eski nusxa bilan davom etamiz */
  }
  render("#business-root", businessSection.render());
  businessSection.bind();
  await businessSection.load(user);
}
