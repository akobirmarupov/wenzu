/** Admin — obunalar va to'lovni tasdiqlash. */
import { api } from "../../core/api.js";
import { initAdminPage } from "./shell.js";
import { $, render, delegate, esc, busy } from "../../ui/dom.js";
import { skeletonRows, emptyState, errorState } from "../../ui/state.js";
import { paginationHtml } from "../../ui/pagination.js";
import { openModal, modal, confirmDialog } from "../../ui/modal.js";
import { toast } from "../../ui/toast.js";
import { money, statusSeal, businessTypeLabel, dateTimeLabel } from "../../ui/format.js";

const STATUSES = [
  { value: "", label: "Barchasi" },
  { value: "trial", label: "Bepul sinov" },
  { value: "active", label: "Faol" },
  { value: "expired", label: "Muddati tugagan" },
];

const filters = { status: "", page: 1 };

const REQUEST_STATUSES = [
  { value: "pending_payment", label: "Kutilmoqda" },
  { value: "approved", label: "Tasdiqlangan" },
  { value: "rejected", label: "Rad etilgan" },
  { value: "", label: "Barchasi" },
];
// Standart ko'rinish — kutilayotganlar: admin bu ekranga shular uchun kiradi.
const requestFilters = { status: "pending_payment" };

const user = await initAdminPage();
if (user) init();

/* ===================================================================
   Obuna arizalari — biznes egasi yuborgan uzaytirish so'rovlari
   =================================================================== */
function requestRowHtml(row) {
  const pending = row.status === "pending_payment";
  return `
    <div class="list-row">
      <div class="stack stack-1" style="min-width:240px">
        <b>${esc(row.business_name)}</b>
        <span class="small muted">
          ${esc(businessTypeLabel(row.business_type))} · ${esc(row.owner_name || "—")}
          · <span class="mono">${esc(row.owner_phone || "")}</span>
        </span>
        <span class="xs faint">
          ${esc(row.plan_label)} — <b>${money(row.price)}</b> · ${dateTimeLabel(row.created_at)}
          ${row.note ? ` · "${esc(row.note)}"` : ""}
        </span>
      </div>
      ${pending
        ? `<div class="row row-2">
             <button class="btn btn-sm btn-outline" data-reject-request="${esc(row.id)}">Rad etish</button>
             <button class="btn btn-sm btn-primary" data-approve-request="${esc(row.id)}"
                     data-label="${esc(row.plan_label)}">Tasdiqlash</button>
           </div>`
        : statusSeal(row.status)}
    </div>`;
}

async function loadRequests() {
  const container = $("#requests");
  if (!container) return;
  container.innerHTML = skeletonRows(3);

  try {
    const params = { page_size: 20 };
    if (requestFilters.status) params.status = requestFilters.status;

    const data = await api.admin.subscriptionRequests(params);
    container.innerHTML = data.results.length
      ? data.results.map(requestRowHtml).join("")
      : emptyState(
          requestFilters.status === "pending_payment"
            ? "Kutilayotgan ariza yo'q"
            : "Ariza topilmadi",
          "Biznes egasi obunani uzaytirish arizasini yuborganda shu yerda ko'rinadi.",
          "📨"
        );

    // Nishonni yangilaymiz — menyuda ish borligi ko'rinsin.
    const badge = document.querySelector("#requests-panel .count-pill");
    if (badge) badge.textContent = data.count;
  } catch (error) {
    container.innerHTML = errorState(error.message);
  }
}

function openActivateModal(subscription) {
  const node = openModal(`
    <h2>To'lovni tasdiqlash</h2>
    <p class="muted small">${esc(subscription.business_name)} · ${esc(subscription.owner_name || "")}</p>

    <form class="stack stack-4" id="activate-form" style="margin-top:var(--sp-5)">
      <div class="form-alert" id="activate-error" hidden></div>
      <div class="field">
        <label for="amount">Summa (so'm)</label>
        <input class="input" id="amount" name="amount" type="number" min="0"
               value="${Math.round(subscription.price || 0)}">
        <span class="field-hint">Bo'sh qoldirsangiz tarif narxi olinadi</span>
      </div>
      <div class="field">
        <label for="note">Izoh</label>
        <input class="input" id="note" name="note" placeholder="Masalan: Payme orqali to'landi">
      </div>
      <button class="btn btn-primary btn-block btn-lg" type="submit" id="activate-submit">
        Tasdiqlash — obuna reja muddatiga uzayadi
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
  render("#request-filters", REQUEST_STATUSES.map((item) =>
    `<button class="chip ${requestFilters.status === item.value ? "active" : ""}"
      data-request-status="${esc(item.value)}" type="button">${esc(item.label)}</button>`).join(""));

  delegate("#request-filters", "[data-request-status]", (button) => {
    requestFilters.status = button.dataset.requestStatus;
    document.querySelectorAll("#request-filters .chip").forEach((c) => c.classList.remove("active"));
    button.classList.add("active");
    loadRequests();
  });

  delegate("#requests", "[data-approve-request]", async (button) => {
    const ok = await confirmDialog({
      title: "To'lovni tasdiqlaysizmi?",
      message: `Obuna ${button.dataset.label} muddatga uzayadi va egasiga bildirishnoma ketadi.`,
      confirmText: "Tasdiqlash",
    });
    if (!ok) return;

    const done = busy(button);
    try {
      await api.admin.approveRequest(button.dataset.approveRequest);
      toast.ok("Obuna uzaytirildi.");
      loadRequests();
      load();
    } catch (error) {
      toast.fromError(error);
    } finally {
      done();
    }
  });

  delegate("#requests", "[data-reject-request]", async (button) => {
    const ok = await confirmDialog({
      title: "Arizani rad etasizmi?",
      message: "Obuna holati o'zgarmaydi, egasiga bildirishnoma yuboriladi.",
      confirmText: "Rad etish",
      danger: true,
    });
    if (!ok) return;

    const done = busy(button);
    try {
      await api.admin.rejectRequest(button.dataset.rejectRequest);
      toast.ok("Ariza rad etildi.");
      loadRequests();
    } catch (error) {
      toast.fromError(error);
    } finally {
      done();
    }
  });

  loadRequests();

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
      <td class="nums">${money(subscription.price)}</td>
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
