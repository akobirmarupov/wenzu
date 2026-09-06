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

/* ===================================================================
 * Ishonchlilik ("Bit")
 *
 * Daraja va rang SERVERDAN keladi (`account/trust.py`) — bu yerda
 * qoida qaytadan yozilmaydi, aks holda ikkalasi bir kun bir-biriga
 * zid bo'lib qolardi. Bu funksiyalar faqat CHIZADI.
 * =================================================================== */

const TRUST_TONE_CLASS = {
  ok: "seal-ok",
  info: "seal-info",
  warn: "seal-warn",
  danger: "seal-bad",
};

/**
 * Ishonchlilik nishoni: "92 Bit · A'lo".
 *
 * `trust` — serverdagi `{bits, level, level_display, tone}` obyekti.
 * Eski javoblarda u bo'lmasligi mumkin, shunda hech narsa chizilmaydi:
 * "0 Bit" deb ko'rsatish odamni haqsiz ravishda ishonchsiz qilib
 * qo'yardi.
 */
export function trustSeal(trust, { compact = false } = {}) {
  if (!trust || trust.bits === undefined || trust.bits === null) return "";
  const tone = TRUST_TONE_CLASS[trust.tone] || "seal-info";
  const label = compact
    ? `${trust.bits} Bit`
    : `${trust.bits} Bit · ${trust.level_display || ""}`;
  return `<span class="seal ${tone} trust-seal" title="Ishonchlilik bali">🛡 ${esc(label.trim())}</span>`;
}

/** 0–100 oralig'idagi ishonchlilik chizig'i (progress). */
export function trustBar(trust) {
  if (!trust || !trust.bits) return "";
  const tone = TRUST_TONE_CLASS[trust.tone] || "seal-info";
  return `
    <span class="trust-bar ${esc(tone)}">
      <span class="fill" style="width:${Math.max(2, Math.min(100, trust.bits))}%"></span>
    </span>`;
}

/* ===================================================================
 * Bekor qilish muddati
 * =================================================================== */

/**
 * Muddatgacha qancha qolganini odam tilida aytadi.
 *
 * Nega faqat daqiqa emas: bekor qilish oynasi endi tadbirgacha bo'lgan
 * vaqtning yarmi, ya'ni u bir necha KUN bo'lishi mumkin. "4320 daqiqa
 * qoldi" degan yozuvni hech kim o'qiy olmasdi.
 */
export function timeLeftLabel(deadline) {
  const left = new Date(deadline) - Date.now();
  if (Number.isNaN(left) || left <= 0) return "";

  const minutes = Math.ceil(left / 60000);
  if (minutes < 60) return `${minutes} daqiqa`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    const rest = minutes % 60;
    return rest ? `${hours} soat ${rest} daqiqa` : `${hours} soat`;
  }

  const days = Math.floor(hours / 24);
  const restHours = hours % 24;
  return restHours ? `${days} kun ${restHours} soat` : `${days} kun`;
}
