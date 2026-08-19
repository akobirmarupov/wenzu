/** Profil — "Bronlarim" bo'limi. */
import { api } from "../../../core/api.js";
import { t } from "../../../core/i18n.js";
import { $, delegate, esc, busy } from "../../../ui/dom.js";
import { skeletonRows, emptyState, errorState } from "../../../ui/state.js";
import { confirmDialog } from "../../../ui/modal.js";
import { toast } from "../../../ui/toast.js";
import { dateLabel, timeLabel, money, statusSeal } from "../../../ui/format.js";
import { openReviewModal } from "../../../components/review-modal.js";

const FILTERS = [
  { value: "", key: "common.all" },
  { value: "pending", key: "status.pending" },
  { value: "confirmed", key: "status.confirmed" },
  { value: "completed", key: "status.completed" },
];

let current = "";

export function render() {
  return `
    <div class="panel">
      <div class="panel-head">
        <h2 class="display h3">${esc(t("profile.bookings"))}</h2>
        <div class="row row-2 row-wrap" id="booking-filters">
          ${FILTERS.map((filter) => `
            <button class="chip ${current === filter.value ? "active" : ""}"
                    data-status="${esc(filter.value)}" type="button">${esc(t(filter.key))}</button>`).join("")}
        </div>
      </div>
      <div id="bookings-list">${skeletonRows(3)}</div>
    </div>`;
}

function row(reservation) {
  const isVenue = reservation.business_type === "venue";
  const target = reservation.room_name || reservation.hall_name || "";
  const when = isVenue
    ? dateLabel(reservation.date)
    : `${dateLabel(reservation.date)} · ${timeLabel(reservation.start_time)}–${timeLabel(reservation.end_time)}`;

  const canCancel = ["pending", "confirmed"].includes(reservation.status);
  const canReview = reservation.status === "completed";

  return `
    <div class="list-row">
      <div class="stack stack-1" style="min-width:230px">
        <b>${esc(reservation.business_name)}${target ? ` — ${esc(target)}` : ""}</b>
        <span class="small muted">${when} · ${reservation.guests_count} ${esc(t("common.people"))}
          ${reservation.total_price ? ` · ${money(reservation.total_price)}` : ""}</span>
        <span class="xs faint">${esc(t("detail.deposit"))}: ${money(reservation.deposit_amount)}</span>
      </div>
      <div class="list-row-actions">
        ${statusSeal(reservation.status)}
        ${canReview ? `<button class="btn btn-sm btn-gold" data-review="${esc(reservation.id)}">${esc(t("profile.leaveReview"))}</button>` : ""}
        ${canCancel ? `<button class="btn btn-sm btn-danger" data-cancel="${esc(reservation.id)}">${esc(t("profile.cancel"))}</button>` : ""}
      </div>
    </div>`;
}

export async function load() {
  const container = $("#bookings-list");
  if (!container) return;
  container.innerHTML = skeletonRows(3);

  try {
    const data = await api.reservations.mine({ page_size: 50, status: current || undefined });
    container.innerHTML = data.results.length
      ? data.results.map(row).join("")
      : emptyState(t("profile.noBookings"), t("profile.startBooking"), "📅");
  } catch (error) {
    container.innerHTML = errorState(error.message);
  }
}

export function bind() {
  delegate("#booking-filters", "[data-status]", (button) => {
    current = button.dataset.status;
    document.querySelectorAll("#booking-filters .chip").forEach((chip) => chip.classList.remove("active"));
    button.classList.add("active");
    load();
  });

  delegate("#bookings-list", "[data-cancel]", async (button) => {
    const ok = await confirmDialog({
      title: t("profile.cancelTitle"),
      message: t("profile.cancelText"),
      confirmText: t("profile.cancel"),
      danger: true,
    });
    if (!ok) return;

    const done = busy(button);
    try {
      await api.reservations.cancel(button.dataset.cancel);
      toast.ok(t("profile.cancelled"));
      load();
    } catch (error) {
      toast.fromError(error);
    } finally {
      done();
    }
  });

  delegate("#bookings-list", "[data-review]", async (button) => {
    try {
      const reservation = await api.reservations.detail(button.dataset.review);
      openReviewModal(reservation, { onDone: load });
    } catch (error) {
      toast.fromError(error);
    }
  });

  load();
}
