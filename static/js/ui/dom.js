/**
 * DOM yordamchilari.
 *
 * Butun frontend `innerHTML` bilan shablon yozadi, shuning uchun
 * foydalanuvchi kiritgan har qanday matn `esc()` dan o'tishi SHART —
 * aks holda sharh matniga yozilgan <script> ishga tushib ketardi (XSS).
 */

/** HTML uchun xavfsiz qilib qochirish. */
export function esc(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export const $ = (selector, root = document) => root.querySelector(selector);

/** Konteynerni HTML bilan to'ldirish (avval tozalab). */
export function render(target, html) {
  const node = typeof target === "string" ? $(target) : target;
  if (node) node.innerHTML = html;
  return node;
}

/**
 * Konteyner ichidagi `[data-action]` tugmalarini bitta tinglovchi bilan
 * boshqarish (event delegation).
 *
 * Nega: ro'yxat qayta chizilganda har bir tugmaga tinglovchi qo'yish
 * xotira sizib ketishiga olib keladi. Bitta tinglovchi esa yangi
 * elementlar uchun ham avtomatik ishlaydi.
 */
export function delegate(root, selector, handler) {
  const node = typeof root === "string" ? $(root) : root;
  if (!node) return;
  node.addEventListener("click", (event) => {
    const match = event.target.closest(selector);
    if (match && node.contains(match)) handler(match, event);
  });
}

/** Forma maydonlarini oddiy obyektga aylantiradi. */
export function formValues(form) {
  const data = {};
  new FormData(form).forEach((value, key) => {
    if (key in data) {
      data[key] = Array.isArray(data[key]) ? [...data[key], value] : [data[key], value];
    } else {
      data[key] = value;
    }
  });
  return data;
}

/** Tugmani "yuklanmoqda" holatiga o'tkazadi va tiklovchi funksiya qaytaradi. */
export function busy(button) {
  if (!button) return () => {};
  button.setAttribute("aria-busy", "true");
  return () => button.removeAttribute("aria-busy");
}
