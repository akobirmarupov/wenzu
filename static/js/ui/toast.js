/**
 * Qisqa xabarnomalar.
 * `alert()` o'rniga — u sahifani bloklaydi va mobil ilovada xunuk ko'rinadi.
 */
const DURATION = 3400;

function root() {
  let node = document.getElementById("toast-root");
  if (!node) {
    node = document.createElement("div");
    node.id = "toast-root";
    document.body.append(node);
  }
  return node;
}

function show(message, tone = "") {
  const node = document.createElement("div");
  node.className = `toast ${tone}`.trim();
  node.setAttribute("role", "status");
  node.textContent = message;
  root().append(node);

  setTimeout(() => {
    node.classList.add("leaving");
    setTimeout(() => node.remove(), 220);
  }, DURATION);
}

export const toast = {
  show,
  ok: (message) => show(message, "toast-ok"),
  error: (message) => show(message, "toast-bad"),

  /**
   * ApiError'ni to'g'ridan-to'g'ri ko'rsatish.
   * `request_id` konsolga yoziladi — foydalanuvchi murojaat qilsa,
   * log'dan aynan shu so'rovni topish uchun.
   */
  fromError(error) {
    show(error?.message || "Xatolik yuz berdi.", "toast-bad");
    if (error?.requestId) console.warn("request_id:", error.requestId);
  },
};
