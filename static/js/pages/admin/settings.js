/** Admin — platforma sozlamalari va tarif rejalari. */
import { api } from "../../core/api.js";
import { initAdminPage } from "./shell.js";
import { $, render, delegate, esc, busy, formValues } from "../../ui/dom.js";
import { skeletonRows, errorState } from "../../ui/state.js";
import { toast } from "../../ui/toast.js";
import { money, businessTypeLabel } from "../../ui/format.js";

const user = await initAdminPage();
if (user) init();

function formHtml(settings) {
  return `
    <div class="form-alert" id="form-error" hidden></div>

    <div class="field-row">
      <div class="field">
        <label for="admin_telegram_username">Admin Telegram (@ siz)</label>
        <input class="input" id="admin_telegram_username" name="admin_telegram_username"
               value="${esc(settings.admin_telegram_username || "")}" placeholder="uvente">
        <span class="field-hint">Ariza va bron oqimida foydalanuvchiga shu ko'rsatiladi</span>
      </div>
      <div class="field">
        <label for="support_phone">Qo'llab-quvvatlash raqami</label>
        <input class="input" id="support_phone" name="support_phone"
               value="${esc(settings.support_phone || "")}" placeholder="+998712000000">
      </div>
    </div>

    <h3 class="display h4" style="margin-top:var(--sp-4)">Depozit narxlari</h3>
    <div class="field-row">
      <div class="field">
        <label for="room_deposit_premium">Restoran — Premium xona</label>
        <input class="input" id="room_deposit_premium" name="room_deposit_premium" type="number" min="0"
               value="${Math.round(settings.room_deposit_premium || 0)}">
      </div>
      <div class="field">
        <label for="room_deposit_pro">Restoran — Pro xona</label>
        <input class="input" id="room_deposit_pro" name="room_deposit_pro" type="number" min="0"
               value="${Math.round(settings.room_deposit_pro || 0)}">
      </div>
      <div class="field">
        <label for="venue_deposit">To'yxona zali</label>
        <input class="input" id="venue_deposit" name="venue_deposit" type="number" min="0"
               value="${Math.round(settings.venue_deposit || 0)}">
      </div>
    </div>

    <h3 class="display h4" style="margin-top:var(--sp-4)">Obuna muddatlari</h3>
    <div class="field-row">
      <div class="field">
        <label for="trial_days">Bepul sinov (kun)</label>
        <input class="input" id="trial_days" name="trial_days" type="number" min="0"
               value="${settings.trial_days ?? 7}">
      </div>
      <div class="field">
        <label for="subscription_days">Bir to'lov muddati (kun)</label>
        <input class="input" id="subscription_days" name="subscription_days" type="number" min="1"
               value="${settings.subscription_days ?? 30}">
      </div>
    </div>

    <button class="btn btn-primary" style="align-self:flex-start" type="submit" id="save">Saqlash</button>`;
}

async function loadSettings() {
  const form = $("#settings-form");
  form.innerHTML = skeletonRows(3);
  try {
    const settings = await api.admin.settings();
    form.innerHTML = formHtml(settings);
  } catch (error) {
    form.innerHTML = errorState(error.message);
  }
}

async function loadPlans() {
  const container = $("#plans");
  container.innerHTML = skeletonRows(2);
  try {
    const data = await api.admin.plans();
    const plans = data.results || data;
    container.innerHTML = plans.map((plan) => `
      <div class="list-row">
        <div class="stack stack-1">
          <b>${esc(businessTypeLabel(plan.business_type))}</b>
          <span class="small muted">Bepul sinov: ${plan.trial_days} kun</span>
        </div>
        <div class="list-row-actions">
          <input class="input nums" style="width:150px" type="number" min="0"
                 value="${Math.round(plan.monthly_price)}" data-price="${esc(plan.id)}">
          <span class="small muted">so'm/oy</span>
          <button class="btn btn-sm btn-primary" data-save-plan="${esc(plan.id)}">Saqlash</button>
        </div>
      </div>`).join("");
  } catch (error) {
    container.innerHTML = errorState(error.message);
  }
}

function init() {
  loadSettings();
  loadPlans();

  $("#settings-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const errorBox = $("#form-error");
    errorBox.hidden = true;
    const done = busy($("#save"));
    try {
      await api.admin.updateSettings(formValues(event.target));
      toast.ok("Sozlamalar saqlandi.");
    } catch (error) {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
    } finally {
      done();
    }
  });

  delegate("#plans", "[data-save-plan]", async (button) => {
    const id = button.dataset.savePlan;
    const input = document.querySelector(`[data-price="${id}"]`);
    const done = busy(button);
    try {
      await api.admin.updatePlan(id, { monthly_price: input.value });
      toast.ok("Tarif narxi yangilandi.");
    } catch (error) {
      toast.fromError(error);
    } finally {
      done();
    }
  });
}
