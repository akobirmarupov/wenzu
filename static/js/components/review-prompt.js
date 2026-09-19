/**
 * Tashrifdan keyin sharh so'rovi — O'ZI ochiladi.
 *
 * ===================================================================
 * NIMA UCHUN KERAK
 * ===================================================================
 * Reyting — bu platformadagi eng qimmat ma'lumot: mijoz joyni shunga
 * qarab tanlaydi. Lekin sharh yozish ilgari faqat QO'LDA bo'lardi:
 * odam "Bronlarim" ni ochishi, kerakli bronni topishi va tugmani
 * bosishi kerak edi. Amalda buni deyarli hech kim qilmasdi — joylar
 * o'nlab tashrifdan keyin ham sharhsiz turardi.
 *
 * Endi bron vaqti tugashi bilan (masalan 18:00–20:00 bronida soat
 * 20:00 da) server uni "yakunlangan" qiladi, va foydalanuvchi saytga
 * kirganda shu modul unga sharh oynasini o'zi ochadi.
 *
 * ===================================================================
 * BEZOVTA QILMASLIK QOIDALARI
 * ===================================================================
 * O'zi ochiladigan oyna — chegara bilan ishlatiladigan narsa. Shuning
 * uchun:
 *
 *   1. SEANSDA BIR MARTA. Har sahifa almashganda chiqsa, odam saytdan
 *      ketib qoladi.
 *   2. RAD ETILSA — QAYTA SO'RAMAYMIZ. Yopib qo'yilgan bron
 *      `localStorage` ga yoziladi va boshqa ko'rsatilmaydi. Sharh
 *      yozishni xohlagan odam uni "Bronlarim" dan baribir topadi.
 *   3. KECHIKTIRIB ochiladi. Sahifa endigina ochilganda chiqsa, odam
 *      nima qilmoqchi bo'lganini unutadi.
 *   4. FAQAT so'nggi ikki hafta ichidagi tashrif (server shunday
 *      qaytaradi) — bir oy oldingi kechki ovqat haqida so'rash ham
 *      bezovta qiladi, ham javobi ishonchsiz bo'ladi.
 *
 * Xato bo'lsa modul JIMGINA to'xtaydi: sharh so'rash — qo'shimcha
 * imkoniyat, u saytning ishlashiga xalaqit bermasligi kerak.
 */
import { api } from "../core/api.js";
import { auth } from "../core/auth.js";
import { t } from "../core/i18n.js";
import { openReviewModal } from "./review-modal.js";

const SESSION_KEY = "feasto.reviewAsked";
const DISMISSED_KEY = "feasto.reviewDismissed";
const DELAY_MS = 2500;

/** Rad etilgan bronlar ro'yxati (brauzerda saqlanadi). */
function dismissedIds() {
  try {
    const raw = localStorage.getItem(DISMISSED_KEY);
    return new Set(raw ? JSON.parse(raw) : []);
  } catch {
    return new Set();
  }
}

function rememberDismissed(id) {
  try {
    const ids = dismissedIds();
    ids.add(id);
    // Ro'yxat cheksiz o'smasligi uchun oxirgi 50 tasi saqlanadi —
    // eski bronlar server javobida baribir qaytmaydi.
    localStorage.setItem(DISMISSED_KEY, JSON.stringify([...ids].slice(-50)));
  } catch {
    /* localStorage yopiq — keyingi safar yana so'raladi, falokat emas */
  }
}

/**
 * Sharh kutayotgan bronni topib, oynani ochadi.
 *
 * Har qanday sahifadan chaqirilishi mumkin: o'zi tekshiradi va kerak
 * bo'lmasa hech narsa qilmaydi.
 */
export async function initReviewPrompt() {
  if (!auth.isAuthenticated()) return;

  try {
    if (sessionStorage.getItem(SESSION_KEY)) return;
  } catch {
    return; // maxfiy rejim — so'ramaymiz, aks holda har sahifada chiqardi
  }

  let pending = [];
  try {
    pending = await api.reservations.pendingReview();
  } catch {
    return; // tarmoq yoki sessiya muammosi — jimgina to'xtaymiz
  }
  if (!Array.isArray(pending) || !pending.length) return;

  const skipped = dismissedIds();
  const reservation = pending.find((item) => !skipped.has(item.id));
  if (!reservation) return;

  try {
    sessionStorage.setItem(SESSION_KEY, "1");
  } catch {
    /* e'tiborsiz */
  }

  window.setTimeout(() => {
    openReviewModal(reservation, {
      intro: t("review.autoIntro"),
      // Yopilsa ham, yuborilsa ham qayta so'ramaymiz: yuborilgan bron
      // server ro'yxatidan baribir chiqib ketadi, yopilgani esa shu
      // yerda belgilanadi.
      onClose: () => rememberDismissed(reservation.id),
    });
  }, DELAY_MS);
}
