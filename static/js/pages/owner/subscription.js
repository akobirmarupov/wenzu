/** Panel — obuna holati va to'lovlar. */
import { api } from "../../core/api.js";
import { initOwnerPage } from "./shell.js";
import { $, render, esc } from "../../ui/dom.js";
import { skeletonRows, emptyState, errorState } from "../../ui/state.js";
import { money, dateTimeLabel, statusSeal, statusLabel } from "../../ui/format.js";

const session = await initOwnerPage();
if (session) load();

async function load() {
  render("#subscription-root", `<div class="panel">${skeletonRows(2)}</div>`);

  try {
    const subscription = await api.owner.subscription();
    if (subscription.has_subscription === false) {
      render("#subscription-root", `<div class="panel">${emptyState("Obuna topilmadi", "", "💳")}</div>`);
      return;
    }

    const telegram = subscription.admin_telegram || "@uvente";
    const isExpired = subscription.status === "expired";

    render("#subscription-root", `
      <div class="grid grid-3">
        <div class="stat-card">
          <span class="label">Holat</span>
          <span class="value" style="font-size:var(--fs-md)">${statusSeal(subscription.status)}</span>
        </div>
        <div class="stat-card">
          <span class="label">Oylik narx</span>
          <span class="value">${money(subscription.monthly_price, { withSuffix: false })}</span>
          <span class="small muted">so'm / oy</span>
        </div>
        <div class="stat-card">
          <span class="label">${subscription.status === "trial" ? "Sinov tugashi" : "Obuna tugashi"}</span>
          <span class="value ${isExpired ? "" : "accent"}">${
            subscription.days_left !== null ? `${subscription.days_left} kun` : "—"}</span>
        </div>
      </div>

      <div class="panel" style="margin-top:var(--sp-5)">
        <div class="panel-head"><h2 class="display h3">To'lovni davom ettirish</h2></div>
        <p class="muted small">
          To'lov Telegram orqali qo'lda amalga oshiriladi: administrator bilan bog'laning,
          to'lovni qiling — u tasdiqlagach obunangiz <b>30 kunga</b> uzayadi.
        </p>
        <div class="row row-3 row-wrap" style="margin-top:var(--sp-5)">
          <a class="btn btn-primary" href="https://t.me/${esc(telegram.replace("@", ""))}"
             target="_blank" rel="noopener">✈️ ${esc(telegram)} bilan bog'lanish</a>
          <span class="small muted">Sinov: ${dateTimeLabel(subscription.trial_ends_at)}
            ${subscription.subscription_ends_at
              ? ` · Obuna: ${dateTimeLabel(subscription.subscription_ends_at)}` : ""}</span>
        </div>
      </div>`);

    renderPayments(subscription.payments || []);
  } catch (error) {
    render("#subscription-root", `<div class="panel">${errorState(error.message)}</div>`);
  }
}

function renderPayments(payments) {
  $("#payments").innerHTML = payments.length
    ? payments.map((payment) => `
      <div class="list-row">
        <div class="stack stack-1">
          <b>${money(payment.amount)}</b>
          <span class="small muted">${esc(payment.note || "—")}</span>
        </div>
        <span class="small muted nums">${dateTimeLabel(payment.created_at)}</span>
      </div>`).join("")
    : emptyState("To'lovlar yo'q", "Hali to'lov tasdiqlanmagan.", "🧾");
}
