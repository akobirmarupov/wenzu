/**
 * Sahifaga kirish nazorati.
 *
 * Bu — QULAYLIK qatlami, xavfsizlik emas: haqiqiy tekshiruv serverda,
 * permission klasslarida. Bu yerda foydalanuvchi bo'sh sahifani ko'rib
 * chalkashib qolmasligi uchun oldindan yo'naltiramiz.
 */
import { ROUTES } from "./config.js";
import { auth } from "./auth.js";
import { storage } from "./storage.js";

function redirect(to) {
  window.location.replace(to);
}

/** Tizimga kirgan bo'lishi shart. */
export function requireAuth() {
  if (!auth.isAuthenticated()) {
    redirect(`${ROUTES.login}?next=${encodeURIComponent(window.location.pathname)}`);
    return null;
  }
  return storage.getUser();
}

/** `role=business` bo'lishi shart. Qaytaradi: {user, businessType}. */
export function requireOwner() {
  const user = requireAuth();
  if (!user) return null;

  if (user.is_staff && !user.business) {
    redirect(ROUTES.adminHome);
    return null;
  }
  if (user.role !== "business" || !user.business) {
    redirect(ROUTES.profile);
    return null;
  }
  return { user, businessType: user.business.type };
}

/** `is_staff` bo'lishi shart. */
export function requireAdmin() {
  const user = requireAuth();
  if (!user) return null;
  if (!user.is_staff) {
    redirect(auth.homeFor(user));
    return null;
  }
  return user;
}

/** Kirgan foydalanuvchini login sahifasidan o'z paneliga qaytaradi. */
export function redirectIfAuthenticated() {
  if (!auth.isAuthenticated()) return;
  redirect(auth.homeFor(storage.getUser()));
}
