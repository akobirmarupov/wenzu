/**
 * HTTP qatlami — barcha so'rovlar SHU yerdan o'tadi.
 *
 * Bu yerda uch narsa markazlashtirilgan:
 *  1. `Authorization` sarlavhasini qo'shish,
 *  2. access token eskirganda uni refresh bilan JIMGINA yangilash va
 *     so'rovni bir marta qayta yuborish,
 *  3. backend'ning yagona xato formatini (`{success, error, request_id}`)
 *     bitta `ApiError` obyektiga aylantirish.
 *
 * Shu sabab sahifa kodlarida na token, na xato tahlili takrorlanmaydi.
 */
import { API_BASE, ROUTES } from "./config.js";
import { storage } from "./storage.js";

export class ApiError extends Error {
  constructor(status, payload) {
    const message =
      payload?.error?.message ||
      payload?.detail ||
      "Kutilmagan xatolik yuz berdi.";
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = payload?.error?.code || "error";
    this.details = payload?.error?.details || null;
    this.requestId = payload?.request_id || null;
  }

  /** Maydon bo'yicha xato matni — formalarda ko'rsatish uchun. */
  fieldError(field) {
    const value = this.details?.[field];
    if (!value) return null;
    return Array.isArray(value) ? value[0] : String(value);
  }
}

let refreshPromise = null;

/**
 * Access tokenni yangilaydi.
 * Bir vaqtda bir nechta so'rov 401 olsa ham, refresh FAQAT BIR MARTA
 * yuboriladi — aks holda rotatsiya tufayli tokenlar bir-birini bekor qilardi.
 */
async function refreshAccessToken() {
  const refresh = storage.getRefresh();
  if (!refresh) return null;

  if (!refreshPromise) {
    refreshPromise = fetch(`${API_BASE}/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (!data?.access) return null;
        storage.setSession({ access: data.access, refresh: data.refresh });
        return data.access;
      })
      .catch(() => null)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

function buildUrl(path, params) {
  const url = new URL(API_BASE + path, window.location.origin);
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    if (Array.isArray(value)) value.forEach((v) => url.searchParams.append(key, v));
    else url.searchParams.set(key, value);
  });
  return url.toString();
}

async function send(path, { method = "GET", params, body, auth = true, isForm = false, retry = true } = {}) {
  const headers = {};
  if (!isForm) headers["Content-Type"] = "application/json";

  const token = storage.getAccess();
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(buildUrl(path, params), {
      method,
      headers,
      body: isForm ? body : body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    // Tarmoq uzilgan yoki server javob bermayapti.
    throw new ApiError(0, { error: { message: "Serverga ulanib bo'lmadi. Internetni tekshiring." } });
  }

  // Token eskirgan — yangilab, so'rovni bir marta qaytaramiz.
  if (response.status === 401 && auth && retry && storage.getRefresh()) {
    const fresh = await refreshAccessToken();
    if (fresh) return send(path, { method, params, body, auth, isForm, retry: false });
    storage.clear();
    if (!window.location.pathname.startsWith(ROUTES.login)) {
      window.location.href = `${ROUTES.login}?next=${encodeURIComponent(window.location.pathname)}`;
    }
  }

  if (response.status === 204) return null;

  const text = await response.text();
  const payload = text ? safeJson(text) : null;

  if (!response.ok) throw new ApiError(response.status, payload);
  return payload;
}

function safeJson(text) {
  try {
    return JSON.parse(text);
  } catch {
    return { error: { message: "Serverdan noto'g'ri javob keldi." } };
  }
}

export const http = {
  get: (path, params, options) => send(path, { method: "GET", params, ...options }),
  post: (path, body, options) => send(path, { method: "POST", body, ...options }),
  patch: (path, body, options) => send(path, { method: "PATCH", body, ...options }),
  put: (path, body, options) => send(path, { method: "PUT", body, ...options }),
  delete: (path, options) => send(path, { method: "DELETE", ...options }),

  /** Fayl yuklash — Content-Type'ni brauzer o'zi qo'yadi (boundary bilan). */
  upload: (path, formData, options) =>
    send(path, { method: "POST", body: formData, isForm: true, ...options }),
};
