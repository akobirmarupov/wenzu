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

/**
 * `role=business` bo'lishi shart. Qaytaradi: {user, businessType}.
 *
 * TASDIQLANMAGAN biznes panelga KIRITILMAYDI.
 *
 * Nega: ariza yuborilgani bilan joy hali tekshirilmagan. Panelga kirsa,
 * egasi xona/menyu/jadval kiritib qo'yadi — server ularni baribir rad
 * etadi (403), lekin foydalanuvchi buni faqat "Saqlash" bosgandan keyin
 * biladi va vaqtini bekorga sarflaydi.
 *
 * O'rniga "Biznes ochish" sahifasiga qaytariladi: u yerda arizasi qanday
 * holatda ekani va keyin nima bo'lishi yozilgan.
 */
export function requireOwner() {
  const user = requireAuth();
  if (!user) return null;

  // PLATFORMA EGASI biznes paneliga KIRMAYDI — biznesi bo'lsa ham.
  //
  // Uning ishi boshqacha: barcha ma'lumotni ko'rish, tasdiqlash,
  // o'chirish va platformani boshqarish. Ikki vazifani bir hisobda
  // aralashtirish "men hozir kim sifatida turibman?" degan chalkashlik
  // tug'dirardi. Server ham xuddi shunday rad etadi (`IsBusinessRole`).
  if (user.is_staff) {
    redirect(ROUTES.adminHome);
    return null;
  }
  if (user.role !== "business" || !user.business) {
    redirect(ROUTES.profile);
    return null;
  }
  // `is_approved` — obuna ochilganmi. Obuna faqat admin tasdig'idan
  // keyin paydo bo'ladi, ya'ni uning mavjudligi tasdiqning o'zi.
  //
  // `=== false` ataylab: eski, `is_approved` maydonisiz saqlangan
  // sessiyada qiymat `undefined` bo'ladi va odamni bekorga quvib
  // chiqarmaslik kerak — server baribir himoyalangan.
  if (user.business.is_approved === false) {
    redirect(ROUTES.premium);
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
