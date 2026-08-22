/**
 * Admin — to'lovlar jurnali.
 *
 * To'lov Telegram orqali QO'LDA qabul qilinadi, shuning uchun uni
 * tizimga ham qo'lda kiritish kerak: kim, qancha, qaysi obuna uchun.
 * Bu jurnal keyinchalik "kim to'ladi, kim to'lamadi" degan savolga
 * yagona javob manbai bo'ladi.
 */
import { api } from "../../core/api.js";
import { initAdminPage } from "./shell.js";
import { $, render, delegate, esc, busy } from "../../ui/dom.js";
import { skeletonRows, errorState } from "../../ui/state.js";
import { paginationHtml } from "../../ui/pagination.js";
import { openModal, modal } from "../../ui/modal.js";
import { toast } from "../../ui/toast.js";
import { dateTimeLabel, money, businessTypeLabel } from "../../ui/format.js";

const filters = { page: 1 };
let subscriptions = [];

const user = await initAdminPage();
if (user) init();

function init() {
  delegate("#pager", "[data-action='page']", (button) => {
    filters.page = Number(button.dataset.page);
    load();
  });

  $("#add-payment").addEventListener("click", openPaymentModal);
  load();
  loadSubscriptions();
}

/** Modaldagi "qaysi obuna" ro'yxati uchun. */
async function loadSubscriptions() {
  try {
    const data = await api.admin.subscriptions({ page_size: 100 });
    subscriptions = data.results || [];
  } catch {
    subscriptions = [];
  }
}

function openPaymentModal() {
  if (!subscriptions.length) {
    toast.error("Avval obunalar ro'yxati yuklansin.");
    return;
  }

  const node = openModal(
    `<h2>To'lovni qayd etish</h2>
     <form class="stack stack-4" id="payment-form" novalidate>
       <div class="form-alert" id="payment-error" hidden></div>

       <div class="field">
         <label for="subscription">Obuna</label>
         <select class="select" id="subscription" name="subscription" required>
           ${subscriptions.map((item) => `
             <option value="${esc(item.id)}">
               ${esc(item.business_name)} — ${esc(item.owner_name || "")} (${esc(item.status_display)})
             </option>`).join("")}
         </select>
       </div>

       <div class="field">
         <label for="amount">Summa (so'm)</label>
         <input class="input" id="amount" name="amount" type="number" min="0" step="1000" required
                placeholder="Masalan: 299000">
       </div>

       <div class="field">
         <label for="note">Izoh</label>
         <textarea class="textarea" id="note" name="note" rows="2"
           placeholder="Masalan: Telegram orqali Click bilan to'landi"></textarea>
       </div>

       <button class="btn btn-primary btn-block btn-lg" type="submit" id="payment-submit">
         Saqlash
       </button>
     </form>`,
    { wide: true }
  );

  const form = node.querySelector("#payment-form");
  const errorBox = node.querySelector("#payment-error");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.hidden = true;
    const done = busy(node.querySelector("#payment-submit"));
    try {
      await api.admin.createPayment({
        subscription: form.subscription.value,
        amount: form.amount.value,
        note: form.note.value.trim(),
      });
      modal.close();
      toast.ok("To'lov qayd etildi.");
      filters.page = 1;
      load();
    } catch (error) {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
    } finally {
      done();
    }
  });
}

function row(item) {
  return `
    <tr>
      <td>
        <b>${esc(item.business_name || "—")}</b>
        <div class="xs faint">${esc(businessTypeLabel(item.business_type))}
          ${item.owner_phone ? `· <span class="mono">${esc(item.owner_phone)}</span>` : ""}</div>
      </td>
      <td class="right mono strong">${money(item.amount)}</td>
      <td class="small">${esc(item.confirmed_by_name || "—")}</td>
      <td class="small">${esc(item.note || "—")}</td>
      <td class="small right">${dateTimeLabel(item.created_at)}</td>
    </tr>`;
}

async function load() {
  $("#list").innerHTML = `<tr><td colspan="5">${skeletonRows(4)}</td></tr>`;
  $("#pager").innerHTML = "";
  try {
    const data = await api.admin.payments({ page: filters.page, page_size: 20 });
    const rows = data.results || [];
    $("#list").innerHTML = rows.length
      ? rows.map(row).join("")
      : `<tr><td colspan="5"><p class="muted center" style="padding:var(--sp-8)">To'lov yozuvi yo'q</p></td></tr>`;
    $("#pager").innerHTML = paginationHtml(data);

    const total = rows.reduce((sum, item) => sum + Number(item.amount || 0), 0);
    render("#summary", `
      <div class="stat-card"><span class="label">Jami yozuv</span><span class="value">${data.count}</span></div>
      <div class="stat-card"><span class="label">Shu sahifadagi summa</span>
        <span class="value accent">${money(total, { withSuffix: false })}</span></div>`);
  } catch (error) {
    $("#list").innerHTML = `<tr><td colspan="5">${errorState(error.message)}</td></tr>`;
  }
}
