{% load static %}/*
 * WENZU — Service Worker.
 *
 * Vazifasi ikkita:
 *   1. Ilova telefonga O'RNATILADIGAN bo'lsin (Android "Bosh ekranga
 *      qo'shish" faqat ishlaydigan service worker bo'lsa taklif qiladi).
 *   2. Internet uzilganda brauzerning "sahifa ochilmadi" ekrani emas,
 *      bizning tushunarli sahifamiz chiqsin.
 *
 * KESHLASH SIYOSATI ataylab EHTIYOTKOR.
 *
 * Bu — jonli ma'lumot bilan ishlaydigan ilova: bo'sh vaqtlar, bronlar,
 * arizalar. Agar sahifalar keshdan berilsa, foydalanuvchi band bo'lib
 * ketgan sanani bo'sh deb ko'rib, bron qilishga urinardi. Shuning uchun:
 *
 *   · /api/...        — HECH QACHON keshlanmaydi. Har doim tarmoqdan.
 *   · HTML sahifalar  — avval tarmoq, ishlamasa oflayn sahifa.
 *   · /static/...     — keshdan beriladi, orqa fonda yangilanadi.
 *                       Bu fayllarning manzilida `?v=` belgisi bor:
 *                       fayl o'zgarsa manzil ham o'zgaradi, ya'ni eski
 *                       nusxa hech qachon yangisi o'rniga berilmaydi.
 *   · /media/...      — suratlar keshdan (ular o'zgarmaydi).
 *
 * Kesh nomida `{{ asset_version }}` bor — kod yangilanganda nom
 * o'zgaradi va eski kesh butunlay o'chiriladi. Ya'ni "eski versiya
 * yopishib qoldi" degan holat bo'lmaydi.
 */

const VERSION = "{{ asset_version }}";
const SHELL_CACHE = `wenzu-shell-${VERSION}`;
const ASSET_CACHE = `wenzu-assets-${VERSION}`;

const OFFLINE_URL = "/oflayn/";

// O'rnatishdayoq olinadigan eng zarur fayllar. Ro'yxat ATAYLAB qisqa:
// uzun ro'yxatdagi bitta fayl yuklanmasa, butun o'rnatish bekor bo'ladi.
const PRECACHE = [
  OFFLINE_URL,
  "{% static 'images/pwa/icon-192.png' %}",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE)
      .then((cache) => cache.addAll(PRECACHE))
      // Yangi versiya kutib turmasin — darhol ishga tushsin.
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(
        names
          .filter((name) => name !== SHELL_CACHE && name !== ASSET_CACHE)
          .map((name) => caches.delete(name))
      ))
      // Ochiq turgan ilovalar ham darhol yangi worker'ga o'tsin.
      .then(() => self.clients.claim())
  );
});

/** Shu manzil keshlanadigan statik faylmi. */
function isAsset(url) {
  return url.pathname.startsWith("/static/") || url.pathname.startsWith("/media/");
}

self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Faqat GET. POST/PATCH/DELETE — bron qilish, tahrirlash: ular
  // hech qanday holatda keshdan javob olmasligi kerak.
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // Boshqa domen (masalan Google Fonts) — tegmaymiz.
  if (url.origin !== self.location.origin) return;

  // Ma'lumot API'si va adminka — doim tirik.
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/admin/")) return;

  // --- statik fayllar: keshdan ber, orqa fonda yangila ---
  if (isAsset(url)) {
    event.respondWith(
      caches.open(ASSET_CACHE).then(async (cache) => {
        const cached = await cache.match(request);
        const network = fetch(request)
          .then((response) => {
            if (response.ok) cache.put(request, response.clone());
            return response;
          })
          .catch(() => cached);
        return cached || network;
      })
    );
    return;
  }

  // --- sahifalar: avval tarmoq, ishlamasa oflayn sahifa ---
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(async () => {
        const cache = await caches.open(SHELL_CACHE);
        return (await cache.match(OFFLINE_URL)) || Response.error();
      })
    );
  }
});
