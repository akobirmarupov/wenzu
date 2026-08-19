/**
 * Sessiya boshqaruvi.
 *
 * Foydalanuvchi kim ekani va qaysi panel unga tegishli ekani SHU yerda
 * hal qilinadi — sahifalar bu savolni o'zi hal qilmaydi.
 */
import { ROUTES } from "./config.js";
import { storage } from "./storage.js";
import { api } from "./api.js";

export const auth = {
  isAuthenticated: () => Boolean(storage.getAccess()),
  user: () => storage.getUser(),

  async login(username, password) {
    const data = await api.auth.login(username, password);
    storage.setSession({ access: data.access, refresh: data.refresh, user: data.user });
    return data.user;
  },

  async register(payload) {
    const user = await api.auth.register(payload);
    storage.setPendingPhone(payload.phone_number);
    return user;
  },

  async logout() {
    const refresh = storage.getRefresh();
    if (refresh) {
      // Server tokenni qora ro'yxatga qo'shsin. Xato bo'lsa ham
      // mijoz tomonda baribir tozalaymiz — foydalanuvchi "chiqdim" deb
      // o'ylab, aslida kirgan holda qolib ketmasligi kerak.
      try {
        await api.auth.logout(refresh);
      } catch {
        /* e'tiborsiz */
      }
    }
    storage.clear();
    window.location.href = ROUTES.home;
  },

  /** Saqlangan nusxani almashtiradi (server javobidan keyin). */
  setUser(user) {
    storage.setUser(user);
    return user;
  },

  /** Serverdan profilni qayta o'qib, saqlangan nusxani yangilaydi. */
  async refreshUser() {
    const me = await api.auth.me();
    storage.setUser(me);
    return me;
  },

  /**
   * Foydalanuvchiga tegishli boshlang'ich sahifa.
   * Login'dan keyin qayerga yuborishni shu funksiya hal qiladi.
   */
  homeFor(user) {
    if (!user) return ROUTES.home;
    if (user.is_staff) return ROUTES.adminHome;
    if (user.role === "business" && user.business) return ROUTES.ownerHome;
    return ROUTES.home;
  },

  /** Biznes turi — panel temasi va menyusi shunga qarab quriladi. */
  businessType(user) {
    return user?.business?.type || null;
  },
};
