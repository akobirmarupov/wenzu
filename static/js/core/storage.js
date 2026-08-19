/**
 * Token va sessiya saqlash.
 *
 * `localStorage` ishlatiladi, chunki backend JWT'ni sarlavhada kutadi
 * (cookie emas). Brauzer maxfiy rejimda saqlashni taqiqlashi mumkin —
 * shuning uchun har bir amal try/catch ichida va xato bo'lsa sayt
 * ishlashda davom etadi, faqat foydalanuvchi qayta kirishga majbur bo'ladi.
 */
import { STORAGE_KEYS } from "./config.js";

function read(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key, value) {
  try {
    if (value === null || value === undefined) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    /* saqlab bo'lmadi — jim o'tamiz */
  }
}

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

  setPendingPhone(phone) {
    write(STORAGE_KEYS.pendingPhone, phone);
  },
  getPendingPhone: () => read(STORAGE_KEYS.pendingPhone),

  clear() {
    Object.values(STORAGE_KEYS).forEach((key) => write(key, null));
  },
};
