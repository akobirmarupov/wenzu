/**
 * API xaritasi — backend endpointlarining yagona ro'yxati.
 *
 * Sahifa kodlari hech qachon `/api/...` matnini o'zi yozmaydi, faqat
 * shu funksiyalarni chaqiradi. Endpoint manzili o'zgarsa, tuzatiladigan
 * joy bitta bo'ladi.
 */
import { http } from "./http.js";

export const api = {
  // ---------------- auth ----------------
  auth: {
    register: (data) => http.post("/auth/register/", data, { auth: false }),
    sendCode: (phone_number) => http.post("/auth/send-code/", { phone_number }, { auth: false }),
    verifyPhone: (phone_number, code) =>
      http.post("/auth/verify-phone/", { phone_number, code }, { auth: false }),
    login: (username, password) => http.post("/auth/login/", { username, password }, { auth: false }),
    logout: (refresh) => http.post("/auth/logout/", { refresh }),
    me: () => http.get("/auth/me/"),
    updateMe: (data) => http.patch("/auth/me/", data),
    uploadAvatar: (formData) => http.upload("/auth/me/avatar/", formData),
    removeAvatar: () => http.delete("/auth/me/avatar/"),
  },

  // ---------------- ommaviy ----------------
  settings: () => http.get("/settings/", null, { auth: false }),

  /** Reklama / e'lon bannerlari — admin panelda boshqariladi. */
  banners: (params) => http.get("/banners/", params, { auth: false }),

  /** Yangiliklar va qiziqarli ma'lumotlar. */
  news: {
    list: (params) => http.get("/news/", params, { auth: false }),
    detail: (id, params) => http.get(`/news/${id}/`, params, { auth: false }),
  },
  plans: () => http.get("/subscription-plans/", null, { auth: false }),

  businesses: {
    list: (params) => http.get("/businesses/", params, { auth: false }),
    detail: (id) => http.get(`/businesses/${id}/`, null, { auth: false }),
    rooms: (id, params) => http.get(`/businesses/${id}/rooms/`, params, { auth: false }),
    halls: (id, params) => http.get(`/businesses/${id}/halls/`, params, { auth: false }),
    menu: (id, params) => http.get(`/businesses/${id}/menu/`, params, { auth: false }),
    venueMenu: (id, params) => http.get(`/businesses/${id}/venue-menu/`, params, { auth: false }),
    pricing: (id) => http.get(`/businesses/${id}/pricing/`, null, { auth: false }),
    photos: (id) => http.get(`/businesses/${id}/photos/`, null, { auth: false }),
    reviews: (id, params) => http.get(`/businesses/${id}/reviews/`, params, { auth: false }),
    availability: (id, params) => http.get(`/businesses/${id}/availability/`, params, { auth: false }),
  },

  rooms: {
    busyHours: (roomId, date) => http.get(`/rooms/${roomId}/busy-hours/`, { date }, { auth: false }),
  },
  halls: {
    busyDates: (hallId, params) => http.get(`/halls/${hallId}/busy-dates/`, params, { auth: false }),
  },

  // ---------------- mijoz ----------------
  reservations: {
    create: (data) => http.post("/reservations/", data),
    mine: (params) => http.get("/reservations/my/", params),
    detail: (id) => http.get(`/reservations/${id}/`),
    cancel: (id) => http.patch(`/reservations/${id}/cancel/`),
  },

  reviews: {
    create: (data) => http.post("/reviews/", data),
    mine: (params) => http.get("/reviews/my/", params),
    update: (id, data) => http.patch(`/reviews/${id}/`, data),
    remove: (id) => http.delete(`/reviews/${id}/`),
    addPhoto: (reviewId, formData) => http.upload(`/reviews/${reviewId}/photos/`, formData),
  },

  applications: {
    create: (data) => http.post("/business-applications/", data),
    mine: () => http.get("/business-applications/my/"),
  },

  // ---------------- biznes egasi ----------------
  owner: {
    overview: () => http.get("/owner/overview/"),
    business: () => http.get("/owner/business/"),
    updateBusiness: (data) => http.patch("/owner/business/", data),

    rooms: (params) => http.get("/owner/rooms/", params),
    createRoom: (data) => http.post("/owner/rooms/", data),
    updateRoom: (id, data) => http.patch(`/owner/rooms/${id}/`, data),
    deleteRoom: (id) => http.delete(`/owner/rooms/${id}/`),

    halls: (params) => http.get("/owner/halls/", params),
    createHall: (data) => http.post("/owner/halls/", data),
    updateHall: (id, data) => http.patch(`/owner/halls/${id}/`, data),
    deleteHall: (id) => http.delete(`/owner/halls/${id}/`),

    pricing: () => http.get("/owner/pricing/"),
    savePricing: (rows) => http.put("/owner/pricing/", rows),

    restaurantMenu: (params) => http.get("/owner/menu/restaurant/", params),
    createRestaurantItem: (data) => http.post("/owner/menu/restaurant/", data),
    updateRestaurantItem: (id, data) => http.patch(`/owner/menu/restaurant/${id}/`, data),
    deleteRestaurantItem: (id) => http.delete(`/owner/menu/restaurant/${id}/`),

    venueMenu: (params) => http.get("/owner/menu/venue/", params),
    createVenueItem: (data) => http.post("/owner/menu/venue/", data),
    updateVenueItem: (id, data) => http.patch(`/owner/menu/venue/${id}/`, data),
    deleteVenueItem: (id) => http.delete(`/owner/menu/venue/${id}/`),

    photos: () => http.get("/owner/photos/"),
    addPhoto: (formData) => http.upload("/owner/photos/", formData),
    deletePhoto: (id) => http.delete(`/owner/photos/${id}/`),

    availability: (params) => http.get("/owner/availability/", params),
    generateAvailability: (data) => http.post("/owner/availability/generate/", data),
    updateAvailability: (id, data) => http.patch(`/owner/availability/${id}/`, data),
    deleteAvailability: (id) => http.delete(`/owner/availability/${id}/`),

    reservations: (params) => http.get("/owner/reservations/", params),
    setReservationStatus: (id, status) =>
      http.patch(`/owner/reservations/${id}/status/`, { status }),

    reviews: (params) => http.get("/owner/reviews/", params),
    subscription: () => http.get("/owner/subscription/"),
    payments: () => http.get("/owner/payments/"),
  },

  // ---------------- super-admin ----------------
  admin: {
    overview: () => http.get("/admin/overview/"),
    applications: (params) => http.get("/admin/applications/", params),
    approveApplication: (id) => http.post(`/admin/applications/${id}/approve/`),
    rejectApplication: (id) => http.post(`/admin/applications/${id}/reject/`),

    users: (params) => http.get("/admin/users/", params),
    updateUser: (id, data) => http.patch(`/admin/users/${id}/`, data),

    businesses: (params) => http.get("/admin/businesses/", params),
    toggleBlock: (id) => http.patch(`/admin/businesses/${id}/toggle-block/`),

    subscriptions: (params) => http.get("/admin/subscriptions/", params),
    activateSubscription: (id, data) => http.post(`/admin/subscriptions/${id}/activate/`, data),
    expireSubscription: (id) => http.post(`/admin/subscriptions/${id}/expire/`),

    plans: () => http.get("/admin/subscription-plans/"),
    updatePlan: (id, data) => http.patch(`/admin/subscription-plans/${id}/`, data),

    payments: (params) => http.get("/admin/payments/", params),
    reservations: (params) => http.get("/admin/reservations/", params),

    settings: () => http.get("/admin/settings/"),
    updateSettings: (data) => http.patch("/admin/settings/", data),

    banners: (params) => http.get("/admin/banners/", params),
    createBanner: (data) => http.post("/admin/banners/", data),
    updateBanner: (id, data) => http.patch(`/admin/banners/${id}/`, data),
    deleteBanner: (id) => http.delete(`/admin/banners/${id}/`),

    news: (params) => http.get("/admin/news/", params),
    createNews: (data) => http.post("/admin/news/", data),
    updateNews: (id, data) => http.patch(`/admin/news/${id}/`, data),
    deleteNews: (id) => http.delete(`/admin/news/${id}/`),
  },
};
