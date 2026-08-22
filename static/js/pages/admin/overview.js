/**
 * Admin — umumiy ko'rinish.
 *
 * Bu ekran "boshqaruv markazi": admin bu yerga kirib, platformada nima
 * bo'layotganini bir qarashda ko'radi va eng ko'p uchraydigan amalni
 * (arizani tasdiqlash) boshqa sahifaga o'tmasdan bajaradi.
 *
 * Ma'lumot uch manbadan keladi va ular BIR-BIRINI KUTMAYDI: statistika
 * kechiksa ham so'nggi bronlar chiqaveradi.
 */
import { api } from "../../core/api.js";
import { initAdminPage } from "./shell.js";
import { $, render, delegate, esc, busy } from "../../ui/dom.js";
import { skeletonRows, emptyState, errorState } from "../../ui/state.js";
import { toast } from "../../ui/toast.js";
import { confirmDialog } from "../../ui/modal.js";
import { dateLabel, timeLabel, statusSeal, money } from "../../ui/format.js";

const QUICK_LINKS = [
  { href: "/boshqaruv/arizalar/", icon: "📝", title: "Arizalar", text: "Yangi bizneslarni tasdiqlash" },
  { href: "/boshqaruv/bizneslar/", icon: "🏢", title: "Bizneslar", text: "Ko'rinish va bloklash" },
  { href: "/boshqaruv/bronlar/", icon: "📅", title: "Barcha bronlar", text: "Platforma bo'ylab qidirish" },
  { href: "/boshqaruv/obunalar/", icon: "💎", title: "Obunalar", text: "Faollashtirish va muddat" },
  { href: "/boshqaruv/tolovlar/", icon: "💳", title: "To'lovlar", text: "Qo'lda kelgan to'lovlar" },
  { href: "/boshqaruv/kontent/", icon: "📢", title: "Kontent", text: "Banner va yangiliklar" },
];

const user = await initAdminPage();
if (user) init();

function statCard(label, value, { accent = false, hint = "" } = {}) {
  return `
    <div class="stat-card">
      <span class="label">${esc(label)}</span>
      <span class="value ${accent ? "accent" : ""}">${esc(String(value))}</span>
      ${hint ? `<span class="small muted">${esc(hint)}</span>` : ""}
    </div>`;
}

function init() {
  render("#quick-links", QUICK_LINKS.map((link) => `
    <a class="card card-link shortcut-card" href="${link.href}">
      <span class="ic" aria-hidden="true">${link.icon}</span>
      <b>${esc(link.title)}</b>
      <span class="small muted">${esc(link.text)}</span>
      <span class="go" aria-hidden="true">→</span>
    </a>`).join(""));

  // Arizani bevosita shu ekrandan tasdiqlash/rad etish.
  delegate("#recent", "[data-approve]", async (button) => {
    const done = busy(button);
    try {
      await api.admin.approveApplication(button.dataset.approve);
      toast.ok("Ariza tasdiqlandi.");
      loadStats();
    } catch (error) {
      toast.fromError(error);
    } finally {
      done();
    }
  });

  delegate("#recent", "[data-reject]", async (button) => {
    const ok = await confirmDialog({
      title: "Arizani rad etasizmi?",
      message: "Ariza beruvchiga bildirishnoma yuboriladi.",
      confirmText: "Rad etish",
      danger: true,
    });
    if (!ok) return;
    try {
      await api.admin.rejectApplication(button.dataset.reject);
      toast.ok("Ariza rad etildi.");
      loadStats();
    } catch (error) {
      toast.fromError(error);
    }
  });

  loadStats();
  loadRecentReservations();
}

function applicationRow(app) {
  const pending = app.status === "pending_payment";
  return `
    <div class="list-row">
      <div class="stack stack-1">
        <b>${esc(app.business_name)}</b>
        <span class="small muted">${esc(app.business_type_display)} · ${esc(app.applicant_name)}
          · <span class="mono">${esc(app.applicant_phone)}</span> · ${dateLabel(app.created_at)}</span>
      </div>
      ${pending
        ? `<div class="row row-2">
             <button class="btn btn-sm btn-outline" data-reject="${esc(app.id)}">Rad etish</button>
             <button class="btn btn-sm btn-primary" data-approve="${esc(app.id)}">Tasdiqlash</button>
           </div>`
        : statusSeal(app.status)}
    </div>`;
}

async function loadStats() {
  $("#recent").innerHTML = skeletonRows(3);
  try {
    const data = await api.admin.overview();
    const { stats, subscriptions } = data;

    render("#stats", [
      statCard("Foydalanuvchilar", stats.users_count),
      statCard("Bizneslar", stats.businesses_count,
        { hint: `${stats.restaurants_count} restoran · ${stats.venues_count} to'yxona` }),
      statCard("Kutilayotgan arizalar", stats.pending_applications, { accent: true }),
      statCard("Kutilayotgan bronlar", stats.pending_reservations, { accent: true }),
    ].join(""));

    render("#secondary-stats", [
      statCard("Jami bronlar", stats.reservations_count),
      statCard("Qidiruvda ko'rinadi", stats.visible_businesses,
        { hint: `${stats.businesses_count} tadan` }),
      statCard("Bepul sinovda", subscriptions.trial),
      statCard("Faol obunalar", subscriptions.active),
      statCard("Muddati tugagan", subscriptions.expired, { accent: subscriptions.expired > 0 }),
    ].join(""));

    $("#recent").innerHTML = data.recent_applications.length
      ? data.recent_applications.map(applicationRow).join("")
      : emptyState("Arizalar yo'q", "Yangi biznes ariza berganda shu yerda ko'rinadi.", "📝");
  } catch (error) {
    render("#stats", "");
    $("#recent").innerHTML = errorState(error.message);
  }
}

async function loadRecentReservations() {
  const container = $("#recent-bookings");
  if (!container) return;
  container.innerHTML = skeletonRows(3);
  try {
    const data = await api.admin.reservations({ page_size: 6 });
    container.innerHTML = data.results.length
      ? data.results.map((item) => {
          const when = item.business_type === "venue"
            ? dateLabel(item.date)
            : `${dateLabel(item.date)} · ${timeLabel(item.start_time)}–${timeLabel(item.end_time)}`;
          return `
            <div class="list-row">
              <div class="stack stack-1">
                <b>${esc(item.business_name)}</b>
                <span class="small muted">${esc(item.user_name || "—")} · ${when}
                  · ${item.guests_count} kishi
                  ${item.total_price ? ` · ${money(item.total_price)}` : ""}</span>
              </div>
              ${statusSeal(item.status)}
            </div>`;
        }).join("")
      : emptyState("Hozircha bron yo'q", "", "📅");
  } catch (error) {
    container.innerHTML = errorState(error.message);
  }
}
