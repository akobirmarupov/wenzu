/** Admin — bizneslar ro'yxati va bloklash. */
import { api } from "../../core/api.js";
import { ROUTES } from "../../core/config.js";
import { initAdminPage } from "./shell.js";
import { $, render, delegate, esc, busy } from "../../ui/dom.js";
import { skeletonRows, errorState } from "../../ui/state.js";
import { paginationHtml } from "../../ui/pagination.js";
import { confirmDialog } from "../../ui/modal.js";
import { toast } from "../../ui/toast.js";
import { statusSeal, businessTypeLabel } from "../../ui/format.js";

const TYPES = [
  { value: "", label: "Barchasi" },
  { value: "restaurant", label: "Restoranlar" },
  { value: "venue", label: "To'yxonalar" },
];

const filters = { type: "", search: "", page: 1 };
const user = await initAdminPage();
if (user) init();

function init() {
  render("#type-filters", TYPES.map((item) =>
    `<button class="chip ${filters.type === item.value ? "active" : ""}"
      data-type="${esc(item.value)}" type="button">${esc(item.label)}</button>`).join(""));

  delegate("#type-filters", "[data-type]", (button) => {
    filters.type = button.dataset.type;
    filters.page = 1;
    document.querySelectorAll("#type-filters .chip").forEach((c) => c.classList.remove("active"));
    button.classList.add("active");
    load();
  });

  let debounce;
  $("#q").addEventListener("input", (event) => {
    clearTimeout(debounce);
    debounce = setTimeout(() => {
      filters.search = event.target.value.trim();
      filters.page = 1;
      load();
    }, 350);
  });

  delegate("#pager", "[data-action='page']", (button) => {
    filters.page = Number(button.dataset.page);
    load();
  });

  delegate("#list", "[data-toggle]", async (button) => {
    const willBlock = button.dataset.visible === "true";
    const ok = await confirmDialog({
      title: willBlock ? "Biznesni bloklaysizmi?" : "Blokdan chiqarasizmi?",
      message: willBlock
        ? "Bloklangan biznes ommaviy qidiruvda ko'rinmaydi va yangi bron qabul qilmaydi."
        : "Biznes yana ommaviy qidiruvda ko'rinadi.",
      confirmText: willBlock ? "Bloklash" : "Ochish",
      danger: willBlock,
    });
    if (!ok) return;

    const done = busy(button);
    try {
      await api.admin.toggleBlock(button.dataset.toggle);
      toast.ok(willBlock ? "Biznes bloklandi." : "Biznes blokdan chiqarildi.");
      load();
    } catch (error) {
      toast.fromError(error);
    } finally {
      done();
    }
  });

  load();
}

function row(business) {
  return `
    <tr>
      <td>
        <a href="${ROUTES.detail(business.id)}" target="_blank" rel="noopener"><b>${esc(business.name)}</b></a>
        <div class="xs faint">${esc(business.district || business.address || "—")}</div>
      </td>
      <td>${esc(businessTypeLabel(business.business_type))}</td>
      <td>
        ${esc(business.owner_name || "—")}
        <div class="xs faint mono">${esc(business.owner_phone || "")}</div>
      </td>
      <td>${business.subscription_status ? statusSeal(business.subscription_status) : "—"}</td>
      <td>${business.is_visible
        ? '<span class="seal seal-ok">Faol</span>'
        : '<span class="seal seal-bad">Bloklangan</span>'}</td>
      <td class="right">
        <button class="btn btn-sm ${business.is_visible ? "btn-danger" : "btn-primary"}"
          data-toggle="${esc(business.id)}" data-visible="${business.is_visible}">
          ${business.is_visible ? "Bloklash" : "Ochish"}
        </button>
      </td>
    </tr>`;
}

async function load() {
  $("#list").innerHTML = `<tr><td colspan="6">${skeletonRows(4)}</td></tr>`;
  $("#pager").innerHTML = "";
  try {
    const data = await api.admin.businesses({ ...filters, page_size: 20 });
    $("#list").innerHTML = data.results.length
      ? data.results.map(row).join("")
      : `<tr><td colspan="6"><p class="muted center" style="padding:var(--sp-8)">Biznes topilmadi</p></td></tr>`;
    $("#pager").innerHTML = paginationHtml(data);
  } catch (error) {
    $("#list").innerHTML = `<tr><td colspan="6">${errorState(error.message)}</td></tr>`;
  }
}
