/** Profil — "Bronlarim" bo'limi. */
import { api } from "../../../core/api.js";
import { auth } from "../../../core/auth.js";
import { t } from "../../../core/i18n.js";
import { $, delegate, esc, busy } from "../../../ui/dom.js";
import { skeletonRows, emptyState, errorState } from "../../../ui/state.js";
import { icon } from "../../../ui/icons.js";
import { confirmDialog } from "../../../ui/modal.js";
import { toast } from "../../../ui/toast.js";
import { dateLabel, timeLabel, dateTimeLabel, money, statusSeal, timeLeftLabel } from "../../../ui/format.js";
import { mapLinksHtml } from "../../../components/map-links.js";
import { openReviewModal } from "../../../components/review-modal.js";

/**
 * Bitta bekor qilishning narxi — `account/trust.py` dagi
 * `TRUST_CANCEL_PENALTY` bilan bir xil.
 *
 * Bu yerda faqat OGOHLANTIRISH matni uchun kerak; haqiqiy hisob-kitob
 * serverda va javobda yangi bal qaytadi. Ya'ni bu son bir kun serverda
 * o'zgarib, bu yerda unutilsa ham, foydalanuvchi noto'g'ri bal
 * ko'rmaydi — faqat ogohlantirish matni eskirgan bo'ladi.
 */
const TRUST_PENALTY = 5;

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

  // Bekor qilish mumkinmi — SERVER hal qiladi (`can_cancel`).
  // Qoidani bu yerda qaytadan yozish ikki manbaga olib kelardi va
  // ular albatta bir kun bir-biriga zid bo'lib qolardi.
  const canCancel = reservation.can_cancel;
  const canReview = reservation.status === "completed";
  const blocked = !canCancel && ["pending", "confirmed"].includes(reservation.status);

  return `
    <div class="list-row">
      <div class="stack stack-1" style="min-width:230px">
        <b>${esc(reservation.business_name)}${target ? ` — ${esc(target)}` : ""}</b>
        <span class="small muted">${when} · ${reservation.guests_count} ${esc(t("common.people"))}
          ${reservation.total_price ? ` · ${money(reservation.total_price)}` : ""}</span>
        <span class="xs faint">${esc(t("detail.deposit"))}: ${money(reservation.deposit_amount)}${
          reservation.day_rent_price ? ` · ${esc(t("detail.dayRent"))}: ${money(reservation.day_rent_price)}` : ""}</span>
        ${mapLinksHtml(
          { map_links: reservation.business_map_links,
            district: reservation.business_district,
            address: reservation.business_address },
          { compact: true },
        )}
        ${cancelHintHtml(reservation, blocked)}
      </div>
      <div class="list-row-actions">
        ${statusSeal(reservation.status)}
        ${canReview ? `<button class="btn btn-sm btn-gold" data-review="${esc(reservation.id)}">${esc(t("profile.leaveReview"))}</button>` : ""}
        ${canCancel ? `<button class="btn btn-sm btn-danger" data-cancel="${esc(reservation.id)}"
                  data-deadline="${esc(reservation.cancel_deadline || "")}">${esc(t("profile.cancel"))}</button>` : ""}
      </div>
    </div>`;
}

/**
 * Bekor qilish muddati haqidagi izoh.
 *
 * ANIQ SANA ham, qolgan vaqt ham ko'rsatiladi.
 *
 * Sababi qoidada. Bekor qilish oynasi endi bron qilingan payt bilan
 * tadbir orasidagi vaqtning teng yarmi — ya'ni u bir necha kun bo'lishi
 * mumkin. "3 kun 4 soat qoldi" degan yozuv shoshilinchlikni bildiradi,
 * lekin odam kalendariga belgilab qo'ya olmaydi; aniq sana esa
 * belgilanadi, lekin qanchalik yaqin ekani sezilmaydi. Ikkalasi birga
 * kerak.
 */
function cancelHintHtml(reservation, blocked) {
  if (blocked) {
    return `<span class="xs faint">${icon("clock")} ${esc(reservation.cancel_blocked_reason || t("profile.cancelExpired"))}</span>`;
  }
  if (!reservation.cancel_deadline) return "";

  const left = timeLeftLabel(reservation.cancel_deadline);
  if (!left) return "";

  return `
    <span class="xs cancel-hint">
      ${icon("clock")} ${esc(t("profile.cancelUntil", { deadline: dateTimeLabel(reservation.cancel_deadline) }))}
      <span class="muted">· ${esc(t("profile.cancelWindow", { left }))}</span>
    </span>`;
}

export async function load() {
  const container = $("#bookings-list");
  if (!container) return;
  container.innerHTML = skeletonRows(3);

  try {
    const data = await api.reservations.mine({ page_size: 50, status: current || undefined });
    container.innerHTML = data.results.length
      ? data.results.map(row).join("")
      : emptyState(t("profile.noBookings"), t("profile.startBooking"), icon("calendar"));
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
    // Tugmani bosgan odam IKKI narsani bilishi kerak: muddat qachon
    // tugaydi va bekor qilish unga nimaga tushadi. Ikkalasi ham
    // kechikkan xabar bo'lmasligi uchun aynan shu oynada aytiladi.
    const deadline = button.dataset.deadline;
    const message = [
      t("profile.cancelText"),
      deadline ? t("profile.cancelUntil", { deadline: dateTimeLabel(deadline) }) : "",
      t("profile.cancelCost", { points: TRUST_PENALTY }),
    ].filter(Boolean).join(" ");

    const ok = await confirmDialog({
      title: t("profile.cancelTitle"),
      message,
      confirmText: t("profile.cancel"),
      danger: true,
    });
    if (!ok) return;

    const done = busy(button);
    try {
      const result = await api.reservations.cancel(button.dataset.cancel);
      // Server yangi balni qaytaradi — saqlangan nusxaga ko'chiramiz,
      // aks holda profil ekrani eski qiymatni ko'rsatib turardi.
      if (result?.trust) {
        const current = auth.user();
        if (current) auth.setUser({ ...current, trust: result.trust });
      }
      toast.ok(result?.message || t("profile.cancelled"));
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
