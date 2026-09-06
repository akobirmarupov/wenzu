/** Panel — bronlarni boshqarish. */
import { api } from "../../core/api.js";
import { initOwnerPage } from "./shell.js";
import { $, render, delegate, esc, busy } from "../../ui/dom.js";
import { skeletonRows, emptyState, errorState } from "../../ui/state.js";
import { paginationHtml } from "../../ui/pagination.js";
import { toast } from "../../ui/toast.js";
import { confirmDialog } from "../../ui/modal.js";
import { dateLabel, timeLabel, statusSeal, money, trustSeal, initials } from "../../ui/format.js";

const STATUSES = [
  { value: "", label: "Barchasi" },
  { value: "pending", label: "Kutilmoqda" },
  { value: "confirmed", label: "Tasdiqlangan" },
  { value: "completed", label: "Yakunlangan" },
  { value: "cancelled", label: "Bekor qilingan" },
];

const filters = { status: "", page: 1 };
const session = await initOwnerPage();
if (session) init();

function init() {
  render("#status-filters", STATUSES.map((item) =>
    `<button class="chip ${filters.status === item.value ? "active" : ""}"
       data-status="${esc(item.value)}" type="button">${esc(item.label)}</button>`).join(""));

  delegate("#status-filters", "[data-status]", (button) => {
    filters.status = button.dataset.status;
    filters.page = 1;
    load();
  });

  delegate("#pager", "[data-action='page']", (button) => {
    filters.page = Number(button.dataset.page);
    load();
  });

  delegate("#list", "[data-set-status]", async (button) => {
    const { id, setStatus } = button.dataset;

    if (setStatus === "cancelled") {
      const ok = await confirmDialog({
        title: "Bronni bekor qilasizmi?",
        message: "Mijozga xabar bermasdan bekor qilinadi — avval u bilan bog'laning.",
        confirmText: "Bekor qilish",
        danger: true,
      });
      if (!ok) return;
    }

    const done = busy(button);
    try {
      await api.owner.setReservationStatus(id, setStatus);
      toast.ok("Bron holati yangilandi.");
      load();
    } catch (error) {
      toast.fromError(error);
    } finally {
      done();
    }
  });

  load();
}

/**
 * Bron yuborgan MIJOZNING kartochkasi.
 *
 * Joy egasi bron so'rovini ko'rganda bitta savolga javob izlaydi:
 * "bu odam kelmaydimi?". Band qilingan, lekin kelinmagan kun uning
 * uchun to'g'ridan-to'g'ri zarar — u o'sha kunga boshqa mijozlarni
 * rad etgan bo'ladi.
 *
 * Shuning uchun bu yerda faqat ism va raqam emas, ISHONCHLILIK BALI
 * ham bor: 100 Bitdan boshlanadi va har bir bekor qilingan bronda
 * 5 Bitga kamayadi. Bal ostida esa "necha marta bekor qilgan" —
 * bitta raqam ba'zan darajadan ko'ra ko'proq narsa aytadi.
 */
function customerHtml(customer, fallbackName, fallbackPhone) {
  // Eski javob `customer` bermasligi mumkin (keshlangan sahifa, mobil
  // ilovaning eski versiyasi) — u holda kamida ism va raqam ko'rinsin.
  if (!customer) {
    return `<b>${esc(fallbackName || "—")}
      <span class="small muted mono">${esc(fallbackPhone || "")}</span></b>`;
  }

  const avatar = customer.avatar
    ? `<img class="cust-photo" src="${esc(customer.avatar)}" alt="" loading="lazy">`
    : `<span class="cust-photo initials">${esc(customer.initials || initials(customer.full_name))}</span>`;

  const cancelled = customer.cancelled_reservations_count || 0;

  return `
    <div class="customer-card">
      ${avatar}
      <div class="stack stack-1" style="min-width:0">
        <b>${esc(customer.full_name || "—")}</b>
        <a class="small mono" href="tel:${esc(customer.phone_number || "")}">${esc(customer.phone_number || "—")}</a>
        <span class="row row-2 row-wrap" style="gap:6px">
          ${trustSeal({
            bits: customer.trust_bits,
            level_display: customer.trust_level_display,
            tone: customer.trust_tone,
          })}
          ${cancelled
            ? `<span class="xs faint">${cancelled} marta bekor qilgan</span>`
            : `<span class="xs faint">Bekor qilmagan</span>`}
        </span>
      </div>
    </div>`;
}

function row(reservation) {
  const isVenue = reservation.business_type === "venue";
  const when = isVenue
    ? dateLabel(reservation.date)
    : `${dateLabel(reservation.date)} · ${timeLabel(reservation.start_time)}–${timeLabel(reservation.end_time)}`;
  const target = reservation.room_name || reservation.hall_name || "";
  const menu = (reservation.selected_menu || []).map((item) => item.name).join(", ");

  const actions = [];
  if (reservation.status === "pending") {
    actions.push(`<button class="btn btn-sm btn-primary" data-set-status="confirmed" data-id="${esc(reservation.id)}">Tasdiqlash</button>`);
    actions.push(`<button class="btn btn-sm btn-danger" data-set-status="cancelled" data-id="${esc(reservation.id)}">Rad etish</button>`);
  } else if (reservation.status === "confirmed") {
    actions.push(`<button class="btn btn-sm btn-outline" data-set-status="completed" data-id="${esc(reservation.id)}">Yakunlash</button>`);
    actions.push(`<button class="btn btn-sm btn-danger" data-set-status="cancelled" data-id="${esc(reservation.id)}">Bekor qilish</button>`);
  }

  return `
    <div class="list-row">
      <div class="stack stack-2" style="min-width:260px">
        ${customerHtml(reservation.customer, reservation.user_name, reservation.user_phone)}
        <span class="small muted">${when} · ${reservation.guests_count} kishi${target ? ` · ${esc(target)}` : ""}</span>
        <span class="xs faint">Depozit: ${money(reservation.deposit_amount)}${
          reservation.day_rent_price ? ` · Ijara: ${money(reservation.day_rent_price)}` : ""}${
          reservation.total_price ? ` · Umumiy: ${money(reservation.total_price)}` : ""}</span>
        ${menu ? `<span class="xs faint">🍽️ ${esc(menu)}</span>` : ""}
        ${reservation.special_request ? `<span class="xs faint">💬 ${esc(reservation.special_request)}</span>` : ""}
      </div>
      <div class="list-row-actions">
        ${statusSeal(reservation.status)}
        ${actions.join("")}
      </div>
    </div>`;
}

async function load() {
  $("#list").innerHTML = skeletonRows(4);
  $("#pager").innerHTML = "";
  try {
    const data = await api.owner.reservations(filters);
    $("#list").innerHTML = data.results.length
      ? data.results.map(row).join("")
      : emptyState("Bronlar yo'q", "Bu filtr bo'yicha hech narsa topilmadi.", "📅");
    $("#pager").innerHTML = paginationHtml(data);
  } catch (error) {
    $("#list").innerHTML = errorState(error.message);
  }
}
