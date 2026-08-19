/** Admin — biznes arizalari. */
import { api } from "../../core/api.js";
import { initAdminPage } from "./shell.js";
import { $, render, delegate, esc, busy } from "../../ui/dom.js";
import { skeletonRows, emptyState, errorState } from "../../ui/state.js";
import { paginationHtml } from "../../ui/pagination.js";
import { confirmDialog } from "../../ui/modal.js";
import { toast } from "../../ui/toast.js";
import { dateTimeLabel, statusSeal } from "../../ui/format.js";

const STATUSES = [
  { value: "pending_payment", label: "Kutilmoqda" },
  { value: "approved", label: "Tasdiqlangan" },
  { value: "rejected", label: "Rad etilgan" },
  { value: "", label: "Barchasi" },
];

const filters = { status: "pending_payment", page: 1 };
const user = await initAdminPage();
if (user) init();

function init() {
  render("#filters", STATUSES.map((item) =>
    `<button class="chip ${filters.status === item.value ? "active" : ""}"
      data-status="${esc(item.value)}" type="button">${esc(item.label)}</button>`).join(""));

  delegate("#filters", "[data-status]", (button) => {
    filters.status = button.dataset.status;
    filters.page = 1;
    document.querySelectorAll("#filters .chip").forEach((c) => c.classList.remove("active"));
    button.classList.add("active");
    load();
  });

  delegate("#pager", "[data-action='page']", (button) => {
    filters.page = Number(button.dataset.page);
    load();
  });

  delegate("#list", "[data-approve]", async (button) => {
    const ok = await confirmDialog({
      title: "To'lovni tasdiqlaysizmi?",
      message: "Obuna 30 kunga faollashadi va to'lov jurnaliga yozuv tushadi.",
      confirmText: "Tasdiqlash",
    });
    if (!ok) return;
    const done = busy(button);
    try {
      await api.admin.approveApplication(button.dataset.approve);
      toast.ok("Ariza tasdiqlandi, obuna faollashtirildi.");
      load();
    } catch (error) {
      toast.fromError(error);
    } finally {
      done();
    }
  });

  delegate("#list", "[data-reject]", async (button) => {
    const ok = await confirmDialog({
      title: "Arizani rad etasizmi?",
      message: "Biznes profili qidiruvdan yashiriladi, lekin o'chirilmaydi.",
      confirmText: "Rad etish",
      danger: true,
    });
    if (!ok) return;
    const done = busy(button);
    try {
      await api.admin.rejectApplication(button.dataset.reject);
      toast.ok("Ariza rad etildi.");
      load();
    } catch (error) {
      toast.fromError(error);
    } finally {
      done();
    }
  });

  load();
}

function row(app) {
  const actions = app.status === "pending_payment"
    ? `<button class="btn btn-sm btn-primary" data-approve="${esc(app.id)}">To'lovni tasdiqlash</button>
       <button class="btn btn-sm btn-danger" data-reject="${esc(app.id)}">Rad etish</button>`
    : "";

  return `
    <div class="list-row">
      <div class="stack stack-1" style="min-width:250px">
        <b>${esc(app.business_name)}</b>
        <span class="small muted">${esc(app.business_type_display)} · ${esc(app.applicant_name)}
          (@${esc(app.applicant_username)})</span>
        <span class="xs faint mono">${esc(app.applicant_phone)} · ${dateTimeLabel(app.created_at)}</span>
      </div>
      <div class="list-row-actions">
        ${statusSeal(app.status)}
        ${actions}
      </div>
    </div>`;
}

async function load() {
  $("#list").innerHTML = skeletonRows(4);
  $("#pager").innerHTML = "";
  try {
    const data = await api.admin.applications({ ...filters, page_size: 20 });
    $("#list").innerHTML = data.results.length
      ? data.results.map(row).join("")
      : emptyState("Arizalar yo'q", "Bu filtr bo'yicha hech narsa topilmadi.", "📝");
    $("#pager").innerHTML = paginationHtml(data);
  } catch (error) {
    $("#list").innerHTML = errorState(error.message);
  }
}
