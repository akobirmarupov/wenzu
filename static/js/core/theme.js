/**
 * Kunduzgi / tungi rejim.
 *
 * Uch holat qo'llab-quvvatlanadi: `light`, `dark` va `system` (standart).
 * `system` da hech qanday atribut qo'yilmaydi — CSS `prefers-color-scheme`
 * orqali o'zi hal qiladi. Foydalanuvchi tanlasa, `data-theme` atributi
 * qo'yiladi va u media so'rovdan ustun turadi.
 */
const STORAGE_KEY = "wenzu.theme";
const MODES = ["system", "light", "dark"];

function read() {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return MODES.includes(value) ? value : "system";
  } catch {
    return "system";
  }
}

function write(mode) {
  try {
    if (mode === "system") localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    /* saqlab bo'lmadi */
  }
}

function apply(mode) {
  const root = document.documentElement;
  if (mode === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", mode);

  // Brauzer manzil qatorining rangi ham temaga moslashsin.
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = effective(mode) === "dark" ? "#0A111C" : "#F1F4F2";
}

/** Amaldagi tema: `system` bo'lsa brauzer sozlamasidan aniqlanadi. */
export function effective(mode = read()) {
  if (mode !== "system") return mode;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export const theme = {
  get: read,
  effective,

  set(mode) {
    write(mode);
    apply(mode);
    document.dispatchEvent(new CustomEvent("themechange", { detail: { mode, effective: effective(mode) } }));
  },

  /** Kunduzgi ↔ tungi almashtirish. */
  toggle() {
    this.set(effective() === "dark" ? "light" : "dark");
  },

  init() {
    apply(read());
    // Tizim sozlamasi o'zgarsa va foydalanuvchi tanlamagan bo'lsa — ergashamiz.
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
      if (read() === "system") apply("system");
    });
  },
};

/**
 * Tema tanlagichini HTML sifatida qaytaradi.
 * Sahifa yuklanishidan oldin `theme.init()` chaqirilgan bo'lishi kerak.
 */
export function themeToggleHtml() {
  const isDark = effective() === "dark";
  return `
    <button class="icon-btn" type="button" data-theme-toggle
            aria-label="${isDark ? "Kunduzgi rejim" : "Tungi rejim"}"
            title="${isDark ? "Kunduzgi rejim" : "Tungi rejim"}">
      <span aria-hidden="true">${isDark ? "☀" : "☾"}</span>
    </button>`;
}

export function bindThemeToggle(root = document) {
  root.querySelectorAll("[data-theme-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      theme.toggle();
      const isDark = effective() === "dark";
      button.querySelector("span").textContent = isDark ? "☀" : "☾";
      button.setAttribute("aria-label", isDark ? "Kunduzgi rejim" : "Tungi rejim");
      button.title = button.getAttribute("aria-label");
    });
  });
}
