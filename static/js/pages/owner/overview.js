/**
 * Panel — biznes egasining "Umumiy ko'rinish" ekrani.
 *
 * Egasi kuniga bir necha marta shu yerga kiradi, shuning uchun ekran
 * uch savolga darrov javob berishi kerak:
 *   1. Nima kutib turibdi?     → tasdiqlanmagan bronlar, shu yerdayoq
 *                                 tasdiqlanadi
 *   2. Ishlar qanday ketyapti? → raqamlar va reyting
 *   3. Keyingi qadam nima?     → bo'limlarga qisqa yo'llar
 *
 * Menyu bandlari rolga qarab o'zgaradi: restoranda "Xonalar",
 * to'yxonada "Zallar".
 */
import { api } from "../../core/api.js";
import { initOwnerPage } from "./shell.js";
import { $, render, delegate, esc, busy } from "../../ui/dom.js";
import { skeletonRows, emptyState, errorState } from "../../ui/state.js";
import { toast } from "../../ui/toast.js";
import { confirmDialog } from "../../ui/modal.js";
import { dateLabel, timeLabel, statusSeal, imageUrl, money } from "../../ui/format.js";

const session = await initOwnerPage();
let isVenue = false;

if (session) {
  isVenue = session.businessType === "venue";
  init();
}

function statCard(label, value, { accent = false, hint = "" } = {}) {
  return `
    <div class="stat-card">
      <span class="label">${esc(label)}</span>
      <span class="value ${accent ? "accent" : ""}">${esc(String(value))}</span>
      ${hint ? `<span class="small muted">${esc(hint)}</span>` : ""}
    </div>`;
}

function quickLinks() {
  const place = isVenue
    ? { href: "/panel/zallar/", icon: "🏛", title: "Zallar", text: "Sig'im va depozit" }
    : { href: "/panel/xonalar/", icon: "🪑", title: "Xonalar", text: "Stol va VIP xonalar" };

  return [
    { href: "/panel/bronlar/", icon: "📅", title: "Bronlar", text: "Tasdiqlash va bekor qilish" },
    place,
    { href: "/panel/menyu/", icon: "🍽", title: "Menyu", text: "Taom, narx va rasm" },
    { href: "/panel/jadval/", icon: "🗓", title: "Bo'sh vaqtlar", text: "Qaysi kunlar ochiq" },
    { href: "/panel/sharhlar/", icon: "★", title: "Sharhlar", text: "Mijozlar nima deydi" },
    { href: "/panel/sozlamalar/", icon: "⚙", title: "Sozlamalar", text: "Ma'lumot va galereya" },
  ];
}

/**
 * Bron qatori.
 *
 * Kutilayotgan bron ustida amal tugmalari chiqadi — egasi "Bronlar"
 * sahifasiga o'tmasdan javob bera oladi. Bu eng ko'p takrorlanadigan
 * amal, shuning uchun eng qisqa yo'lda turishi kerak.
 */
function reservationRow(reservation) {
  const when = reservation.business_type === "venue"
    ? dateLabel(reservation.date)
    : `${dateLabel(reservation.date)} · ${timeLabel(reservation.start_time)}–${timeLabel(reservation.end_time)}`;
  const target = reservation.room_name || reservation.hall_name || "";
  const pending = reservation.status === "pending";

  return `
    <div class="list-row">
      <div class="stack stack-1">
        <b>${esc(reservation.user_name || "—")}</b>
        <span class="small muted">
          ${when} · ${reservation.guests_count} kishi${target ? ` · ${esc(target)}` : ""}
          ${reservation.total_price ? ` · ${money(reservation.total_price)}` : ""}
        </span>
        ${reservation.user_phone
          ? `<span class="xs faint mono">${esc(reservation.user_phone)}</span>` : ""}
      </div>
      ${pending
        ? `<div class="row row-2">
             <button class="btn btn-sm btn-outline" data-set-status="${esc(reservation.id)}"
                     data-status="cancelled">Bekor</button>
             <button class="btn btn-sm btn-primary" data-set-status="${esc(reservation.id)}"
                     data-status="confirmed">Tasdiqlash</button>
           </div>`
        : statusSeal(reservation.status)}
    </div>`;
}

function init() {
  render("#quick-links", quickLinks().map((link) => `
    <a class="card card-link shortcut-card" href="${link.href}">
      <span class="ic" aria-hidden="true">${link.icon}</span>
      <b>${esc(link.title)}</b>
      <span class="small muted">${esc(link.text)}</span>
      <span class="go" aria-hidden="true">→</span>
    </a>`).join(""));

  delegate("#recent", "[data-set-status]", async (button) => {
    const next = button.dataset.status;
    if (next === "cancelled") {
      const ok = await confirmDialog({
        title: "Bronni bekor qilasizmi?",
        message: "Mijozga bildirishnoma yuboriladi.",
        confirmText: "Bekor qilish",
        danger: true,
      });
      if (!ok) return;
    }

    const done = busy(button);
    try {
      await api.owner.setReservationStatus(button.dataset.setStatus, next);
      toast.ok(next === "confirmed" ? "Bron tasdiqlandi." : "Bron bekor qilindi.");
      load();
    } catch (error) {
      toast.fromError(error);
    } finally {
      done();
    }
  });

  load();
}

async function load() {
  render("#stats", skeletonRows(1));
  $("#recent").innerHTML = skeletonRows(3);

  try {
    const data = await api.owner.overview();
    const { stats, business, subscription } = data;

    render("#stats", [
      statCard("Kutilayotgan", stats.pending_reservations, { accent: true, hint: "javob berish kerak" }),
      statCard("Tasdiqlangan", stats.confirmed_reservations),
      statCard("Reyting", `${Number(stats.rating_avg || 0).toFixed(1)} ★`,
        { hint: `${stats.reviews_count} sharh` }),
      statCard("Jami bronlar", stats.total_reservations,
        { hint: `${stats.completed_reservations} yakunlangan · ${stats.cancelled_reservations} bekor` }),
    ].join(""));

    $("#recent").innerHTML = data.recent_reservations.length
      ? data.recent_reservations.map(reservationRow).join("")
      : emptyState("Hozircha bronlar yo'q", "Mijozlar sizni bron qilganda shu yerda ko'rinadi.", "📅");

    render("#business-card", `
      <div class="panel-head">
        <div class="stack stack-1">
          <span class="eyebrow">${esc(isVenue ? "To'yxona" : "Restoran")}${business.district ? ` · ${esc(business.district)}` : ""}</span>
          <h2 class="display h3">${esc(business.name)}</h2>
        </div>
        <div class="row row-2">
          ${subscription?.status ? statusSeal(subscription.status) : ""}
          <a class="btn btn-ghost btn-sm" href="/panel/sozlamalar/">Tahrirlash →</a>
        </div>
      </div>
      <img src="${esc(imageUrl(business.cover_photo))}" alt=""
           style="width:100%;height:230px;object-fit:cover;border-radius:var(--radius-m)">
      <p class="muted small" style="margin-top:var(--sp-4)">
        ${esc(business.description || "Tavsif hali yozilmagan. Sozlamalar bo'limida qo'shing — mijozlar qidiruvda shuni o'qiydi.")}</p>
      <a class="btn btn-outline btn-sm" style="align-self:flex-start;margin-top:var(--sp-4)"
         href="/biznes/${esc(business.id)}/">Mijoz ko'zi bilan ko'rish →</a>
    `);
  } catch (error) {
    render("#stats", "");
    $("#recent").innerHTML = errorState(error.message);
  }
}
