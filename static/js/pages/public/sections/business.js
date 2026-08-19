/**
 * Profil — "Biznes" bo'limi.
 *
 * Uch holat: biznesi bor / arizasi ko'rib chiqilmoqda / hali yo'q.
 * Har biriga o'z ekrani — foydalanuvchi qaysi bosqichda ekanini
 * darrov tushunishi kerak.
 */
import { api } from "../../../core/api.js";
import { t } from "../../../core/i18n.js";
import { ROUTES } from "../../../core/config.js";
import { $, delegate, esc } from "../../../ui/dom.js";
import { skeletonRows, errorState } from "../../../ui/state.js";
import { dateLabel, statusSeal } from "../../../ui/format.js";
import { openApplyModal } from "../../../components/apply-modal.js";

export function render() {
  return `<div id="business-root">${skeletonRows(2)}</div>`;
}

function ownerHtml(user) {
  const isVenue = user.business.type === "venue";
  const links = isVenue
    ? [["/panel/zallar/", "🏛", t("panel.halls")], ["/panel/menyu/", "🍽", t("panel.menu")]]
    : [["/panel/xonalar/", "🪑", t("panel.rooms")], ["/panel/menyu/", "🍽", t("panel.menu")]];

  return `
    <div class="panel stack stack-5">
      <div class="panel-head" style="margin-bottom:0">
        <div class="stack stack-1">
          <span class="eyebrow">${esc(isVenue ? t("panel.roleVenue") : t("panel.roleRestaurant"))}</span>
          <h2 class="display h2">${esc(user.business.name)}</h2>
        </div>
        ${user.business.is_visible
          ? `<span class="seal seal-ok">${esc(t("business.visible"))}</span>`
          : `<span class="seal seal-bad">${esc(t("business.hidden"))}</span>`}
      </div>

      <p class="muted small">${esc(t("business.ownerHint"))}</p>

      <div class="grid grid-auto-sm">
        <a class="card card-link" href="${ROUTES.ownerHome}" style="padding:var(--sp-5)">
          <div style="font-size:26px">◈</div>
          <b style="display:block;margin-top:var(--sp-2)">${esc(t("panel.overview"))}</b>
        </a>
        <a class="card card-link" href="/panel/bronlar/" style="padding:var(--sp-5)">
          <div style="font-size:26px">📅</div>
          <b style="display:block;margin-top:var(--sp-2)">${esc(t("panel.bookings"))}</b>
        </a>
        ${links.map(([href, icon, label]) => `
          <a class="card card-link" href="${href}" style="padding:var(--sp-5)">
            <div style="font-size:26px">${icon}</div>
            <b style="display:block;margin-top:var(--sp-2)">${esc(label)}</b>
          </a>`).join("")}
      </div>

      <a class="btn btn-primary" style="align-self:flex-start"
         href="${ROUTES.ownerHome}">${esc(t("business.goToPanel"))}</a>
    </div>`;
}

function pendingHtml(application) {
  return `
    <div class="panel stack stack-4">
      <h2 class="display h3">${esc(t("business.pendingTitle"))}</h2>
      <div class="list-row">
        <div class="stack stack-1">
          <b>${esc(application.business_name)}</b>
          <span class="small muted">${esc(application.business_type_display)} · ${dateLabel(application.created_at)}</span>
        </div>
        ${statusSeal(application.status)}
      </div>
      <p class="small muted">${esc(t("business.pendingText"))}</p>
    </div>`;
}

function chooseHtml() {
  return `
    <div class="panel stack stack-5">
      <div class="stack stack-2">
        <span class="eyebrow">${esc(t("home.ctaEyebrow"))}</span>
        <h2 class="display h2">${esc(t("business.chooseTitle"))}</h2>
        <p class="muted small">${esc(t("business.chooseText"))}</p>
      </div>

      <div class="biz-choice">
        <button class="opt" type="button" data-apply="restaurant">
          <div class="ic">🍽️</div>
          <h3 class="display h4" style="margin-top:var(--sp-2)">${esc(t("business.openRestaurant"))}</h3>
          <p class="small muted" style="margin-top:var(--sp-2)">${esc(t("business.openRestaurantText"))}</p>
        </button>
        <button class="opt" type="button" data-apply="venue">
          <div class="ic">🎉</div>
          <h3 class="display h4" style="margin-top:var(--sp-2)">${esc(t("business.openVenue"))}</h3>
          <p class="small muted" style="margin-top:var(--sp-2)">${esc(t("business.openVenueText"))}</p>
        </button>
      </div>

      <p class="small muted">✦ ${esc(t("business.trialNote"))}</p>
    </div>`;
}

export async function load(user) {
  const root = $("#business-root");
  if (!root) return;

  if (user.business) {
    root.innerHTML = ownerHtml(user);
    return;
  }

  try {
    const applications = await api.applications.mine();
    const pending = applications.find((app) => app.status === "pending_payment");
    root.innerHTML = pending ? pendingHtml(pending) : chooseHtml();
  } catch (error) {
    root.innerHTML = errorState(error.message);
  }
}

export function bind() {
  delegate("#business-root", "[data-apply]", (button) => openApplyModal(button.dataset.apply));
}
