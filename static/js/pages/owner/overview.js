/** Panel — umumiy ko'rinish. */
import { api } from "../../core/api.js";
import { initOwnerPage } from "./shell.js";
import { $, render, esc } from "../../ui/dom.js";
import { skeletonRows, emptyState, errorState } from "../../ui/state.js";
import { dateLabel, timeLabel, statusSeal, imageUrl, money } from "../../ui/format.js";

const session = await initOwnerPage();
if (session) load();

function statCard(label, value, accent = false) {
  return `<div class="stat-card">
    <span class="label">${esc(label)}</span>
    <span class="value ${accent ? "accent" : ""}">${esc(String(value))}</span>
  </div>`;
}

function reservationRow(reservation) {
  const when = reservation.business_type === "venue"
    ? dateLabel(reservation.date)
    : `${dateLabel(reservation.date)} · ${timeLabel(reservation.start_time)}–${timeLabel(reservation.end_time)}`;
  const target = reservation.room_name || reservation.hall_name || "";

  return `<div class="list-row">
    <div class="stack stack-1">
      <b>${esc(reservation.user_name)}</b>
      <span class="small muted">${when} · ${reservation.guests_count} kishi${target ? ` · ${esc(target)}` : ""}</span>
    </div>
    ${statusSeal(reservation.status)}
  </div>`;
}

async function load() {
  render("#stats", skeletonRows(1));
  $("#recent").innerHTML = skeletonRows(3);

  try {
    const data = await api.owner.overview();
    const { stats, business, subscription } = data;

    render("#stats", [
      statCard("Jami bronlar", stats.total_reservations),
      statCard("Kutilayotgan", stats.pending_reservations, true),
      statCard("Reyting", `${Number(stats.rating_avg || 0).toFixed(1)} ★`),
      statCard("Sharhlar", stats.reviews_count),
    ].join(""));

    $("#recent").innerHTML = data.recent_reservations.length
      ? data.recent_reservations.map(reservationRow).join("")
      : emptyState("Hozircha bronlar yo'q", "Mijozlar sizni bron qilganda shu yerda ko'rinadi.", "📅");

    render("#business-card", `
      <div class="panel-head">
        <h2 class="display h3">${esc(business.name)}</h2>
        <a class="btn btn-ghost btn-sm" href="/panel/sozlamalar/">Tahrirlash →</a>
      </div>
      <img src="${esc(imageUrl(business.cover_photo))}" alt=""
           style="width:100%;height:210px;object-fit:cover;border-radius:var(--radius-m)">
      <p class="muted small" style="margin-top:var(--sp-4)">
        ${esc(business.description || "Tavsif hali yozilmagan. Sozlamalar bo'limida qo'shing.")}</p>
      ${subscription?.status ? `<div class="row row-2" style="margin-top:var(--sp-4)">
        ${statusSeal(subscription.status)}
      </div>` : ""}
    `);
  } catch (error) {
    render("#stats", "");
    $("#recent").innerHTML = errorState(error.message);
  }
}
