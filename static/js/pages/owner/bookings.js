/** Panel — bronlarni boshqarish. */
import { api } from "../../core/api.js";
import { initOwnerPage } from "./shell.js";
import { $, render, delegate, esc, busy } from "../../ui/dom.js";
import { skeletonRows, emptyState, errorState } from "../../ui/state.js";
import { paginationHtml } from "../../ui/pagination.js";
import { toast } from "../../ui/toast.js";
import { confirmDialog } from "../../ui/modal.js";
import { dateLabel, timeLabel, statusSeal, money } from "../../ui/format.js";

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
      <div class="stack stack-1" style="min-width:260px">
        <b>${esc(reservation.user_name)} <span class="small muted mono">${esc(reservation.user_phone)}</span></b>
        <span class="small muted">${when} · ${reservation.guests_count} kishi${target ? ` · ${esc(target)}` : ""}</span>
        <span class="xs faint">Depozit: ${money(reservation.deposit_amount)}${
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
