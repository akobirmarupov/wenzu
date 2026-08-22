/**
 * Umumiy sozlamalar.
 *
 * API manzili shu yerda bir marta belgilanadi — agar backend boshqa
 * domenga ko'chsa, o'zgartiriladigan yagona joy shu.
 */
export const API_BASE = "/api";

export const STORAGE_KEYS = {
  access: "wenzu.access",
  refresh: "wenzu.refresh",
  user: "wenzu.user",
};

/** Sahifa manzillari — shablonlardagi URL'lar bilan mos bo'lishi shart. */
export const ROUTES = {
  home: "/",
  restaurants: "/restoranlar/",
  venues: "/toyxonalar/",
  detail: (id) => `/biznes/${id}/`,
  profile: "/profil/",
  myBookings: "/bronlarim/",

  // Biznes ochish va obuna — BITTA joyda, profil ichidagi "Obuna va
  // Premium" bo'limida. Ilgari alohida `/biznes-ochish/` sahifasi bor
  // edi, lekin u tarif tanlash bilan bir xil qarorni ikkiga bo'lardi:
  // odam "tarifni qayerdan tanlayman, biznesni qayerdan ochaman?" deb
  // ikkalasini ham izlab yurardi.
  premium: "/profil/?tab=premium",
  // Kirish VA ro'yxatdan o'tish — bitta sahifa: Google tugmasi hisob
  // bo'lmasa yaratadi. `register` va `verify` manzillari olib
  // tashlandi (server ularni `/kirish/` ga qaytaradi).
  login: "/kirish/",
  ownerHome: "/panel/",
  adminHome: "/boshqaruv/",
};

/** Holat kodlarini o'zbekcha matnga aylantirish. */
export const STATUS_LABELS = {
  pending: "Kutilmoqda",
  confirmed: "Tasdiqlangan",
  cancelled: "Bekor qilingan",
  completed: "Yakunlangan",
  pending_payment: "To'lov kutilmoqda",
  approved: "Tasdiqlangan",
  rejected: "Rad etilgan",
  trial: "Bepul sinov",
  active: "Faol",
  expired: "Muddati tugagan",
};

/** Holatga mos "seal" CSS klassi. */
export const STATUS_TONE = {
  pending: "seal-warn",
  pending_payment: "seal-warn",
  trial: "seal-gold",
  confirmed: "seal-ok",
  approved: "seal-ok",
  active: "seal-ok",
  completed: "seal-info",
  cancelled: "seal-bad",
  rejected: "seal-bad",
  expired: "seal-bad",
};

export const MENU_CATEGORIES = [
  { value: "starter", label: "Boshlang'ich" },
  { value: "soup", label: "Sho'rva" },
  { value: "main", label: "Asosiy taom" },
  { value: "salad", label: "Salat" },
  { value: "dessert", label: "Desert" },
  { value: "drink", label: "Ichimlik" },
  { value: "other", label: "Boshqa" },
];

export const CUISINES = [
  { value: "milliy", label: "Milliy taomlar" },
  { value: "yevropa", label: "Yevropa oshxonasi" },
  { value: "fusion", label: "Fusion" },
  { value: "sharqona", label: "Sharqona" },
  { value: "fastfood", label: "Fast food" },
  { value: "boshqa", label: "Boshqa" },
];

export const ROOM_TYPES = [
  { value: "vip", label: "VIP xona" },
  { value: "standard", label: "Oddiy zal" },
  { value: "outdoor", label: "Tashqi terrasa" },
];

/** Rasm yo'q bo'lganda ko'rsatiladigan zaxira. */
export const PLACEHOLDER_IMAGE =
  "data:image/svg+xml;charset=utf-8," +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 260">
       <rect width="400" height="260" fill="#EFE9DA"/>
       <text x="50%" y="50%" text-anchor="middle" dominant-baseline="middle"
             font-family="serif" font-size="21" fill="#B6AE97">WENZU</text>
     </svg>`
  );
