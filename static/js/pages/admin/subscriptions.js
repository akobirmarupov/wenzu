/** Admin — obunalar va to'lovni tasdiqlash. */
import { api } from "../../core/api.js";
import { initAdminPage } from "./shell.js";
import { $, render, delegate, esc, busy } from "../../ui/dom.js";
import { skeletonRows, errorState } from "../../ui/state.js";
import { paginationHtml } from "../../ui/pagination.js";
import { openModal, modal, confirmDialog } from "../../ui/modal.js";
import { toast } from "../../ui/toast.js";
import { money, statusSeal, businessTypeLabel } from "../../ui/format.js";

const STATUSES = [
  { value: "", label: "Barchasi" },
  { value: "trial", label: "Bepul sinov" },
  { value: "active", label: "Faol" },
  { value: "expired", label: "Muddati tugagan" },
];

const filters = { status: "", page: 1 };
const user = await initAdminPage();
if (user) init();

function openActivateModal(subscription) {
  const node = openModal(`
    <h2>To'lovni tasdiqlash</h2>
    <p class="muted small">${esc(subscription.business_name)} · ${esc(subscription.owner_name || "")}</p>

    <form class="stack stack-4" id="activate-form" style="margin-top:var(--sp-5)">
      <div class="form-alert" id="activate-error" hidden></div>
      <div class="field">
        <label for="amount">Summa (so'm)</label>
        <input class="input" id="amount" name="amount" type="number" min="0"
               value="${Math.round(subscription.monthly_price || 0)}">
        <span class="field-hint">Bo'sh qoldirsangiz tarif narxi olinadi</span>
      </div>
      <div class="field">
        <label for="note">Izoh</label>
        <input class="input" id="note" name="note" placeholder="Masalan: Payme orqali to'landi">
      </div>
      <button class="btn btn-primary btn-block btn-lg" type="submit" id="activate-submit">
        Tasdiqlash — obuna 30 kunga uzayadi
      </button>
    </form>`);

  node.querySelector("#activate-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const errorBox = node.querySelector("#activate-error");
    errorBox.hidden = true;
    const done = busy(node.querySelector("#activate-submit"));

    try {
      await api.admin.activateSubscription(subscription.id, {
        amount: node.querySelector("#amount").value || undefined,
        note: node.querySelector("#note").value,
      });
      modal.close();
      toast.ok("Obuna faollashtirildi.");
      load();
    } catch (error) {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
    } finally {
      done();
    }
  });
}

let subscriptions = [];

function init() {
  render("#status-filters", STATUSES.map((item) =>
    `<button class="chip ${filters.status === item.value ? "active" : ""}"
      data-status="${esc(item.value)}" type="button">${esc(item.label)}</button>`).join(""));

  delegate("#status-filters", "[data-status]", (button) => {
    filters.status = button.dataset.status;
    filters.page = 1;
    document.querySelectorAll("#status-filters .chip").forEach((c) => c.classList.remove("active"));
    button.classList.add("active");
    load();
  });

  delegate("#pager", "[data-action='page']", (button) => {
    filters.page = Number(button.dataset.page);
    load();
  });

  delegate("#list", "[data-activate]", (button) => {
    const subscription = subscriptions.find((s) => s.id === button.dataset.activate);
    if (subscription) openActivateModal(subscription);
  });

  delegate("#list", "[data-expire]", async (button) => {
    const ok = await confirmDialog({
      title: "Obunani tugatasizmi?",
      message: "Biznes ommaviy qidiruvdan yashiriladi va yozish taqiqlanadi.",
      confirmText: "Tugatish",
      danger: true,
    });
    if (!ok) return;
    const done = busy(button);
    try {
      await api.admin.expireSubscription(button.dataset.expire);
      toast.ok("Obuna tugatildi.");
      load();
    } catch (error) {
      toast.fromError(error);
    } finally {
      done();
    }
  });

  load();
}

function row(subscription) {
  return `
    <tr>
      <td><b>${esc(subscription.business_name)}</b>
        <div class="xs faint">${esc(businessTypeLabel(subscription.business_type))}</div></td>
      <td>${esc(subscription.owner_name || "—")}
        <div class="xs faint mono">${esc(subscription.owner_phone || "")}</div></td>
      <td class="nums">${money(subscription.monthly_price)}</td>
      <td>${statusSeal(subscription.status)}</td>
      <td class="nums">${subscription.days_left !== null ? `${subscription.days_left} kun` : "—"}</td>
      <td class="right">
        <button class="btn btn-sm btn-primary" data-activate="${esc(subscription.id)}">To'lovni tasdiqlash</button>
        ${subscription.status !== "expired"
          ? `<button class="btn btn-sm btn-danger" data-expire="${esc(subscription.id)}">Tugatish</button>` : ""}
      </td>
    </tr>`;
}

async function load() {
  $("#list").innerHTML = `<tr><td colspan="6">${skeletonRows(4)}</td></tr>`;
  $("#pager").innerHTML = "";
  try {
    const data = await api.admin.subscriptions({ ...filters, page_size: 20 });
    subscriptions = data.results;
    $("#list").innerHTML = subscriptions.length
      ? subscriptions.map(row).join("")
      : `<tr><td colspan="6"><p class="muted center" style="padding:var(--sp-8)">Obuna topilmadi</p></td></tr>`;
    $("#pager").innerHTML = paginationHtml(data);
  } catch (error) {
    $("#list").innerHTML = `<tr><td colspan="6">${errorState(error.message)}</td></tr>`;
  }
}
