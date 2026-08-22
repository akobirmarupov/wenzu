/**
 * Panel — obuna holati, tarif tanlash va to'lovlar tarixi.
 *
 * Ekran uch savolga javob beradi:
 *   1. Obunam qanday holatda va qachon tugaydi?
 *   2. Uzaytirish uchun nima qilishim kerak?  → tarif kartochkalari
 *   3. Ilgari nima to'laganman?               → to'lovlar tarixi
 *
 * To'lov platformada emas, Telegram orqali qo'lda amalga oshadi —
 * shuning uchun bu yerda pul emas, ARIZA aylanadi: egasi rejani
 * tanlaydi, ariza ketadi, admin to'lovni ko'rib tasdiqlaydi.
 */
import { api } from "../../core/api.js";
import { initOwnerPage } from "./shell.js";
import { $, render, esc } from "../../ui/dom.js";
import { skeletonRows, emptyState, errorState } from "../../ui/state.js";
import { money, dateLabel, dateTimeLabel, statusSeal } from "../../ui/format.js";
import { pricingHtml, bindPricing } from "../../components/pricing.js";

const session = await initOwnerPage();
if (session) load();

/**
 * Joriy tarif muddati ("1 oy" / "3 oy").
 *
 * Obuna javobida rejaning o'zi `plan` ID sifatida keladi, muddat esa
 * `plans` ro'yxatida — shundan topamiz.
 */
function planLabel(subscription) {
  const plan = (subscription.plans || []).find((row) => row.id === subscription.plan);
  return plan?.duration_label || "1 oy";
}

function statusCardsHtml(subscription) {
  // Tasdiq kutilayotgan holat — obuna hali umuman yo'q.
  if (subscription.has_subscription === false) {
    return `
      <div class="price-pending">
        <span class="ic" aria-hidden="true">🕓</span>
        <span>
          <b>Arizangiz administrator tekshiruvida</b>
          <span class="small">
            Tasdiqlangach <b>7 kunlik bepul sinov</b> boshlanadi va barcha
            bo'limlar ochiladi. Tezlashtirish uchun
            ${esc(subscription.admin_telegram || "@uvente")} ga yozing.
          </span>
        </span>
      </div>`;
  }

  const isExpired = subscription.status === "expired";
  const isTrial = subscription.status === "trial";
  const endsAt = isTrial ? subscription.trial_ends_at : subscription.subscription_ends_at;

  return `
    <div class="grid grid-3">
      <div class="stat-card">
        <span class="label">Holat</span>
        <span class="value" style="font-size:var(--fs-md)">${statusSeal(subscription.status)}</span>
      </div>
      <div class="stat-card">
        <span class="label">Joriy tarif</span>
        <span class="value">${money(subscription.price, { withSuffix: false })}</span>
        <span class="small muted">so'm / ${esc(planLabel(subscription))}</span>
      </div>
      <div class="stat-card">
        <span class="label">${isTrial ? "Sinov tugashi" : "Obuna tugashi"}</span>
        <span class="value ${isExpired ? "" : "accent"}">${
          subscription.days_left !== null && subscription.days_left !== undefined
            ? `${subscription.days_left} kun`
            : "—"}</span>
        <span class="small muted">${endsAt ? dateLabel(endsAt) : "—"}</span>
      </div>
    </div>

    ${isExpired ? `
      <div class="price-pending" style="margin-top:var(--sp-4);border-color:var(--danger);background:var(--danger-dim)">
        <span class="ic" aria-hidden="true">⛔</span>
        <span>
          <b>Obunangiz tugagan</b>
          <span class="small">Joyingiz ommaviy qidiruvda ko'rinmayapti va yangi bron
            qabul qilmayapti. Quyidan tarifni tanlang.</span>
        </span>
      </div>` : ""}`;
}

async function load() {
  render("#subscription-root", `<div class="panel">${skeletonRows(2)}</div>`);

  let subscription;
  try {
    subscription = await api.owner.subscription();
  } catch (error) {
    render("#subscription-root", `<div class="panel">${errorState(error.message)}</div>`);
    return;
  }

  const telegram = subscription.admin_telegram || "@uvente";
  const plans = subscription.plans || [];
  const businessType =
    subscription.business_type || session.businessType || "restaurant";

  render("#subscription-root", `
    ${statusCardsHtml(subscription)}

    <div class="panel" style="margin-top:var(--sp-5)">
      <div class="panel-head">
        <div class="stack stack-1">
          <h2 class="display h3">Obunani uzaytirish</h2>
          <span class="small muted">
            Tarifni tanlang — ariza administratorga ketadi. To'lovni Telegram
            orqali amalga oshirasiz, u tasdiqlagach muddat uzayadi.
          </span>
        </div>
      </div>

      <div id="pricing">
        ${pricingHtml({
          plans,
          status: subscription.has_subscription === false
            ? "awaiting_approval"
            : subscription.status,
          pending: subscription.pending_request,
          ownedType: businessType,
        })}
      </div>

      <div class="row row-2 row-wrap" style="margin-top:var(--sp-5)">
        <a class="btn btn-outline" href="https://t.me/${esc(telegram.replace("@", ""))}"
           target="_blank" rel="noopener">✈️ ${esc(telegram)} bilan bog'lanish</a>
      </div>
    </div>`);

  bindPricing("#pricing", { plans, telegram, onSent: load });
  renderPayments(subscription.payments || []);
  renderRequests();
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

/** Yuborilgan arizalar tarixi — "arizam qayerda qoldi?" degan savolga javob. */
async function renderRequests() {
  const container = $("#requests");
  if (!container) return;
  container.innerHTML = skeletonRows(2);

  try {
    const data = await api.owner.subscriptionRequests({ page_size: 10 });
    container.innerHTML = data.results.length
      ? data.results.map((row) => `
        <div class="list-row">
          <div class="stack stack-1">
            <b>${esc(row.plan_label)} — ${money(row.price)}</b>
            <span class="small muted">${dateTimeLabel(row.created_at)}
              ${row.admin_note ? ` · ${esc(row.admin_note)}` : ""}</span>
          </div>
          ${statusSeal(row.status)}
        </div>`).join("")
      : emptyState("Ariza yuborilmagan", "Tarifni tanlasangiz shu yerda ko'rinadi.", "📨");
  } catch (error) {
    container.innerHTML = errorState(error.message);
  }
}
