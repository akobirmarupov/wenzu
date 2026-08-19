/**
 * Profil — "Obuna va Premium" bo'limi.
 *
 * Biznes egasi uchun: joriy tarif, qolgan kun, imkoniyatlar va to'lov
 * yo'riqnomasi. Oddiy foydalanuvchi uchun: Premium nima berishini
 * tushuntirib, biznes ochishga yo'naltiradi.
 */
import { api } from "../../../core/api.js";
import { t } from "../../../core/i18n.js";
import { $, esc } from "../../../ui/dom.js";
import { skeletonRows, emptyState, errorState } from "../../../ui/state.js";
import { money, dateLabel, dateTimeLabel } from "../../../ui/format.js";

const PLAN_TONE = { trial: "premium-plan-trial", active: "premium-plan-active", expired: "premium-plan-expired" };

export function render() {
  return `<div id="premium-root">${skeletonRows(3)}</div>`;
}

function benefitsHtml() {
  return `
    <div class="premium-benefits">
      ${[1, 2, 3, 4].map((n) => `
        <div class="premium-benefit">
          <span class="tick" aria-hidden="true">✓</span>
          <span>${esc(t(`premium.benefit${n}`))}</span>
        </div>`).join("")}
    </div>`;
}

function paymentStepsHtml(telegram) {
  return `
    <div class="panel">
      <div class="panel-head"><h2 class="display h3">${esc(t("premium.howTitle"))}</h2></div>
      <div class="pay-steps">
        ${[1, 2, 3].map((n) => `
          <div class="pay-step">
            <p>${esc(t(`premium.how${n}`))}</p>
          </div>`).join("")}
      </div>
      ${telegram ? `
        <a class="btn btn-primary" style="margin-top:var(--sp-5)"
           href="https://t.me/${esc(telegram.replace("@", ""))}" target="_blank" rel="noopener">
          ✈️ ${esc(t("premium.contactAdmin"))} — ${esc(telegram)}
        </a>` : ""}
    </div>`;
}

/** Biznes egasi ko'radigan ko'rinish. */
function ownerHtml(subscription) {
  const status = subscription.status;
  const days = subscription.days_left;
  const total = status === "active" ? 30 : 7;
  const percent = days === null ? 0 : Math.max(0, Math.min(100, (days / total) * 100));
  const low = days !== null && days <= 3;

  return `
    <section class="premium-card">
      <div class="premium-head">
        <div class="stack stack-2">
          <span class="premium-plan ${PLAN_TONE[status] || ""}">
            ${status === "trial" ? "✦ " : ""}${esc(t(`status.${status}`))}
          </span>
          <div class="premium-price">
            ${money(subscription.monthly_price, { withSuffix: false })}
            <small>${esc(t("common.soum"))} / ${esc(t("premium.monthly"))}</small>
          </div>
        </div>
        <div class="stack stack-1" style="text-align:right">
          <span class="premium-plan" style="background:rgba(255,255,255,.10)">
            ${esc(subscription.business_name || "")}
          </span>
        </div>
      </div>

      <div class="premium-meta">
        <div class="item">
          <span class="k">${esc(t("premium.daysLeft"))}</span>
          <span class="v">${days !== null ? `${days} ${esc(t("premium.days"))}` : "—"}</span>
        </div>
        <div class="item">
          <span class="k">${esc(t("premium.trial"))}</span>
          <span class="v">${dateLabel(subscription.trial_ends_at)}</span>
        </div>
        ${subscription.subscription_ends_at ? `
          <div class="item">
            <span class="k">${esc(t("premium.current"))}</span>
            <span class="v">${dateLabel(subscription.subscription_ends_at)}</span>
          </div>` : ""}
      </div>

      <div class="premium-bar ${low ? "low" : ""}"><span style="width:${percent}%"></span></div>

      ${benefitsHtml()}

      <div class="premium-actions">
        ${subscription.admin_telegram ? `
          <a class="btn btn-gold btn-lg" href="https://t.me/${esc(subscription.admin_telegram.replace("@", ""))}"
             target="_blank" rel="noopener">
            ${esc(status === "expired" ? t("premium.upgrade") : t("premium.extend"))}
          </a>` : ""}
        <a class="btn btn-outline-light btn-lg" href="/panel/obuna/">${esc(t("premium.paymentHistory"))}</a>
      </div>
    </section>

    ${paymentStepsHtml(subscription.admin_telegram)}

    <div class="panel">
      <div class="panel-head"><h2 class="display h3">${esc(t("premium.paymentHistory"))}</h2></div>
      <div id="premium-payments">${skeletonRows(2)}</div>
    </div>`;
}

/** Oddiy foydalanuvchi ko'radigan ko'rinish — Premium'ga taklif. */
function guestHtml(settings) {
  const plans = settings?.plans || [];
  const telegram = settings?.admin_telegram;

  return `
    <section class="premium-card">
      <div class="premium-head">
        <div class="stack stack-2">
          <span class="premium-plan premium-plan-trial">✦ ${esc(t("premium.trialOffer"))}</span>
          <h2 class="display" style="font-size:clamp(22px,3vw,32px)">${esc(t("premium.guestTitle"))}</h2>
          <p style="color:rgba(255,255,255,.78);max-width:48ch">${esc(t("premium.guestText"))}</p>
        </div>
      </div>

      <div class="premium-meta">
        ${plans.map((plan) => `
          <div class="item">
            <span class="k">${esc(plan.business_type === "venue" ? t("nav.venues") : t("nav.restaurants"))}</span>
            <span class="v">${money(plan.monthly_price)}</span>
          </div>`).join("")}
        <div class="item">
          <span class="k">${esc(t("premium.trial"))}</span>
          <span class="v">${settings?.trial_days ?? 7} ${esc(t("premium.days"))}</span>
        </div>
      </div>

      ${benefitsHtml()}

      <div class="premium-actions">
        <button class="btn btn-gold btn-lg" data-goto-business>${esc(t("nav.business"))}</button>
        ${telegram ? `
          <a class="btn btn-outline-light btn-lg" href="https://t.me/${esc(telegram.replace("@", ""))}"
             target="_blank" rel="noopener">${esc(t("premium.contactAdmin"))}</a>` : ""}
      </div>
    </section>

    ${paymentStepsHtml(telegram)}`;
}

async function loadPayments() {
  const container = $("#premium-payments");
  if (!container) return;
  try {
    const data = await api.owner.payments();
    container.innerHTML = data.results.length
      ? data.results.map((payment) => `
          <div class="list-row">
            <div class="stack stack-1">
              <b>${money(payment.amount)}</b>
              <span class="small muted">${esc(payment.note || "—")}</span>
            </div>
            <span class="small muted nums">${dateTimeLabel(payment.created_at)}</span>
          </div>`).join("")
      : emptyState(t("premium.noPayments"), "", "🧾");
  } catch (error) {
    container.innerHTML = errorState(error.message);
  }
}

export async function load(user) {
  const root = $("#premium-root");
  if (!root) return;

  try {
    if (user.role === "business" && user.business) {
      const subscription = await api.owner.subscription();
      if (subscription.has_subscription === false) {
        root.innerHTML = emptyState(t("common.empty"), "", "💎");
        return;
      }
      root.innerHTML = ownerHtml(subscription);
      loadPayments();
    } else {
      const settings = await api.settings();
      root.innerHTML = guestHtml(settings);
    }
  } catch (error) {
    root.innerHTML = errorState(error.message);
  }
}

export function bind({ onGoToBusiness }) {
  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-goto-business]")) onGoToBusiness?.();
  });
}
