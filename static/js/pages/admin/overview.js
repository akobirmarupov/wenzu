/** Admin — umumiy statistika. */
import { api } from "../../core/api.js";
import { initAdminPage } from "./shell.js";
import { $, render, esc } from "../../ui/dom.js";
import { skeletonRows, emptyState, errorState } from "../../ui/state.js";
import { dateLabel, statusSeal } from "../../ui/format.js";

const user = await initAdminPage();
if (user) load();

function statCard(label, value, accent = false) {
  return `<div class="stat-card">
    <span class="label">${esc(label)}</span>
    <span class="value ${accent ? "accent" : ""}">${esc(String(value))}</span>
  </div>`;
}

async function load() {
  $("#recent").innerHTML = skeletonRows(3);
  try {
    const data = await api.admin.overview();
    const { stats, subscriptions } = data;

    render("#stats", [
      statCard("Foydalanuvchilar", stats.users_count),
      statCard("Bizneslar", stats.businesses_count),
      statCard("Kutilayotgan arizalar", stats.pending_applications, true),
      statCard("Jami bronlar", stats.reservations_count),
    ].join(""));

    render("#subscription-stats", [
      statCard("Bepul sinovda", subscriptions.trial),
      statCard("Faol obunalar", subscriptions.active),
      statCard("Muddati tugagan", subscriptions.expired),
    ].join(""));

    $("#recent").innerHTML = data.recent_applications.length
      ? data.recent_applications.map((app) => `
        <div class="list-row">
          <div class="stack stack-1">
            <b>${esc(app.business_name)}</b>
            <span class="small muted">${esc(app.business_type_display)} · ${esc(app.applicant_name)}
              · <span class="mono">${esc(app.applicant_phone)}</span> · ${dateLabel(app.created_at)}</span>
          </div>
          ${statusSeal(app.status)}
        </div>`).join("")
      : emptyState("Arizalar yo'q", "", "📝");
  } catch (error) {
    $("#recent").innerHTML = errorState(error.message);
  }
}
