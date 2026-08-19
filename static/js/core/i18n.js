/**
 * Uch tilli qo'llab-quvvatlash: o'zbekcha, ruscha, inglizcha.
 *
 * Tarjimalar `i18n/<til>.js` fayllarida yotadi va DINAMIK yuklanadi —
 * foydalanuvchi faqat o'zi tanlagan tilning lug'atini yuklab oladi,
 * uchalasini birdan emas.
 *
 * Shablonlardagi matnlar `data-i18n="kalit"` bilan belgilangan; sahifa
 * ochilganda ular almashtiriladi. JS ichida yozilgan matnlar esa `t()`
 * orqali olinadi.
 */
const STORAGE_KEY = "wenzu.lang";
const SUPPORTED = ["uz", "ru", "en"];
const DEFAULT_LANG = "uz";

export const LANGUAGES = [
  { code: "uz", label: "O'zbekcha", short: "UZ" },
  { code: "ru", label: "Русский", short: "RU" },
  { code: "en", label: "English", short: "EN" },
];

let dictionary = {};
let current = DEFAULT_LANG;

/** Saqlangan yoki brauzer tili. */
export function detectLanguage() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (SUPPORTED.includes(saved)) return saved;
  } catch {
    /* localStorage yopiq */
  }
  const browser = (navigator.language || "").slice(0, 2).toLowerCase();
  return SUPPORTED.includes(browser) ? browser : DEFAULT_LANG;
}

export function getLanguage() {
  return current;
}

/**
 * Kalit bo'yicha tarjima.
 * @param {string} key - "nav.restaurants" kabi nuqtali yo'l
 * @param {object} vars - {count: 5} → "{count} ta joy"
 */
export function t(key, vars) {
  const value = key.split(".").reduce((node, part) => (node ? node[part] : undefined), dictionary);
  let text = typeof value === "string" ? value : key;
  if (vars) {
    Object.entries(vars).forEach(([name, replacement]) => {
      text = text.replaceAll(`{${name}}`, replacement);
    });
  }
  return text;
}

/** Sahifadagi `data-i18n` belgilangan barcha elementlarni tarjima qiladi. */
export function applyTranslations(root = document) {
  root.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  root.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  });
  root.querySelectorAll("[data-i18n-label]").forEach((node) => {
    node.setAttribute("aria-label", t(node.dataset.i18nLabel));
  });
  root.querySelectorAll("[data-i18n-title]").forEach((node) => {
    node.title = t(node.dataset.i18nTitle);
  });
}

/** Tilni yuklaydi va sahifani tarjima qiladi. */
export async function loadLanguage(code) {
  const lang = SUPPORTED.includes(code) ? code : DEFAULT_LANG;
  const module = await import(`../i18n/${lang}.js`);
  dictionary = module.default;
  current = lang;
  document.documentElement.lang = lang;
  applyTranslations();
  return lang;
}

/** Tilni almashtiradi va sahifani qayta yuklaydi (ma'lumot ham tarjimada kelsin). */
export async function setLanguage(code) {
  try {
    localStorage.setItem(STORAGE_KEY, code);
  } catch {
    /* saqlab bo'lmadi */
  }
  window.location.reload();
}

/** Boshlanish nuqtasi — har bir sahifa modulida birinchi chaqiriladi. */
export async function initI18n() {
  return loadLanguage(detectLanguage());
}
