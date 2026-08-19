/**
 * Formatlash — pul, sana, vaqt, holat nishonlari.
 * Butun sayt bo'ylab bir xil ko'rinish shu yerdan keladi.
 */
import { STATUS_LABELS, STATUS_TONE, PLACEHOLDER_IMAGE } from "../core/config.js";
import { esc } from "./dom.js";

const MONTHS = [
  "yanvar", "fevral", "mart", "aprel", "may", "iyun",
  "iyul", "avgust", "sentyabr", "oktyabr", "noyabr", "dekabr",
];

/** 255000 → "255 000 so'm" */
export function money(value, { withSuffix = true } = {}) {
  const number = Number(value || 0);
  const formatted = Math.round(number)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return withSuffix ? `${formatted} so'm` : formatted;
}

/** "2026-09-14" → "14-sentyabr, 2026" */
export function dateLabel(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return `${date.getDate()}-${MONTHS[date.getMonth()]}, ${date.getFullYear()}`;
}

/** "19:00:00" → "19:00" */
export function timeLabel(value) {
  if (!value) return "";
  return String(value).slice(0, 5);
}

/** ISO sana → "14.09.2026 19:30" */
export function dateTimeLabel(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(date.getDate())}.${pad(date.getMonth() + 1)}.${date.getFullYear()} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** Bugundan boshlab YYYY-MM-DD (input[type=date] uchun). */
export function todayISO(offsetDays = 0) {
  const date = new Date();
  date.setDate(date.getDate() + offsetDays);
  return date.toISOString().slice(0, 10);
}

/** Ism-familiyadan bosh harflar: "Sardor Yusupov" → "SY" */
export function initials(name) {
  if (!name) return "?";
  return name
    .trim()
    .split(/\s+/)
    .map((word) => word[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

/** 4.8 → "★★★★★" (to'ldirilgan/bo'sh) */
export function stars(rating) {
  const filled = Math.round(Number(rating) || 0);
  let html = "";
  for (let i = 0; i < 5; i += 1) {
    html += `<span class="star">${i < filled ? "★" : "☆"}</span>`;
  }
  return html;
}

/** Holat kodidan tayyor "seal" nishoni. */
export function statusSeal(status) {
  const label = STATUS_LABELS[status] || status || "—";
  const tone = STATUS_TONE[status] || "seal-info";
  return `<span class="seal ${tone}">${esc(label)}</span>`;
}

export function statusLabel(status) {
  return STATUS_LABELS[status] || status || "—";
}

/** Rasm manzili — bo'sh bo'lsa zaxira rasm. */
export function imageUrl(value) {
  return value || PLACEHOLDER_IMAGE;
}

/** "restaurant" → "Restoran" */
export function businessTypeLabel(type) {
  return type === "venue" ? "To'yxona" : type === "restaurant" ? "Restoran" : "—";
}
