/**
 * Token va sessiya saqlash.
 *
 * `localStorage` ishlatiladi, chunki backend JWT'ni sarlavhada kutadi
 * (cookie emas). Brauzer maxfiy rejimda saqlashni taqiqlashi mumkin —
 * shuning uchun har bir amal try/catch ichida va xato bo'lsa sayt
 * ishlashda davom etadi, faqat foydalanuvchi qayta kirishga majbur bo'ladi.
 */
import { LEGACY_STORAGE_KEYS, STORAGE_KEYS } from "./config.js";

function read(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

/**
 * ESKI NOMDAGI SESSIYANI YANGISIGA KO'CHIRADI.
 *
 * Loyiha WENZU'dan Feasto'ga o'tganda kalitlar ham o'zgardi. Ko'chirish
 * bo'lmasa, saytga kirgan har bir odam tizimdan chiqib qolardi va
 * qaytadan kirishga majbur bo'lardi — nom almashtirish uchun juda
 * qimmat narx.
 *
 * Bir marta ishlaydi: ko'chirgach eski kalit o'chiriladi. Yangi kalitda
 * allaqachon qiymat bo'lsa, eskisiga umuman tegilmaydi — yangi kirish
 * eski token bilan bosib ketilmasligi kerak.
 */
function migrateLegacy() {
  Object.entries(LEGACY_STORAGE_KEYS).forEach(([name, legacyKey]) => {
    const legacy = read(legacyKey);
    if (legacy === null) return;
    if (read(STORAGE_KEYS[name]) === null) write(STORAGE_KEYS[name], legacy);
    write(legacyKey, null);
  });
}

function write(key, value) {
  try {
    if (value === null || value === undefined) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    /* saqlab bo'lmadi — jim o'tamiz */
  }
}

migrateLegacy();

export const storage = {
  getAccess: () => read(STORAGE_KEYS.access),
  getRefresh: () => read(STORAGE_KEYS.refresh),

  getUser() {
    const raw = read(STORAGE_KEYS.user);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  },

  setSession({ access, refresh, user }) {
    if (access) write(STORAGE_KEYS.access, access);
    if (refresh) write(STORAGE_KEYS.refresh, refresh);
    if (user) write(STORAGE_KEYS.user, JSON.stringify(user));
  },

  setUser(user) {
    write(STORAGE_KEYS.user, user ? JSON.stringify(user) : null);
  },

  clear() {
    Object.values(STORAGE_KEYS).forEach((key) => write(key, null));
  },
};
