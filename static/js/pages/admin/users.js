/** Admin — foydalanuvchilar. */
import { api } from "../../core/api.js";
import { initAdminPage } from "./shell.js";
import { $, render, delegate, esc, busy } from "../../ui/dom.js";
import { skeletonRows, errorState } from "../../ui/state.js";
import { paginationHtml } from "../../ui/pagination.js";
import { toast } from "../../ui/toast.js";
import { dateLabel, initials } from "../../ui/format.js";

const ROLES = [
  { value: "", label: "Barchasi" },
  { value: "user", label: "Foydalanuvchi" },
  { value: "business", label: "Biznes egasi" },
];

const filters = { role: "", search: "", page: 1 };
const user = await initAdminPage();
if (user) init();

function init() {
  render("#role-filters", ROLES.map((item) =>
    `<button class="chip ${filters.role === item.value ? "active" : ""}"
      data-role="${esc(item.value)}" type="button">${esc(item.label)}</button>`).join(""));

  delegate("#role-filters", "[data-role]", (button) => {
    filters.role = button.dataset.role;
    filters.page = 1;
    document.querySelectorAll("#role-filters .chip").forEach((c) => c.classList.remove("active"));
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

  delegate("#list", "[data-toggle-active]", async (button) => {
    const done = busy(button);
    try {
      await api.admin.updateUser(button.dataset.toggleActive, {
        is_active: button.dataset.next === "true",
      });
      toast.ok("Foydalanuvchi yangilandi.");
      load();
    } catch (error) {
      toast.fromError(error);
    } finally {
      done();
    }
  });

  load();
}

function row(item) {
  return `
    <tr>
      <td><div class="row row-2">
        <span class="avatar" style="width:28px;height:28px;font-size:11px">${esc(initials(item.full_name))}</span>
        <b>${esc(item.full_name)}</b>
      </div></td>
      <td class="mono small">${esc(item.username)}</td>
      <td class="mono small">${esc(item.phone_number)}</td>
      <td><span class="tag">${esc(item.role_display)}</span></td>
      <td>${item.is_active
        ? '<span class="seal seal-ok">Faol</span>'
        : '<span class="seal seal-bad">Bloklangan</span>'}
        ${item.is_phone_verified ? "" : '<span class="seal seal-warn">Tasdiqlanmagan</span>'}</td>
      <td class="right">
        ${item.is_staff ? '<span class="xs faint">admin</span>' : `
        <button class="btn btn-sm ${item.is_active ? "btn-danger" : "btn-primary"}"
          data-toggle-active="${item.id}" data-next="${!item.is_active}">
          ${item.is_active ? "Bloklash" : "Ochish"}
        </button>`}
      </td>
    </tr>`;
}

/**
 * Sarlavha ostidagi hisoblagich.
 *
 * Ikki xil raqam bor va ularni chalkashtirmaslik kerak:
 *   `total` — platformadagi BARCHA foydalanuvchi
 *   `count` — hozirgi filtrga tushganlar
 * Filtr yo'q bo'lsa ikkalasi teng va bitta raqam yozamiz; filtr bor
 * bo'lsa ikkalasi ham ko'rsatiladi, aks holda "20 ta foydalanuvchi"
 * degan yozuv butun platformaning soni deb tushunilardi.
 */
function countLabel(data) {
  const total = data.total ?? data.count;
  return data.count !== total
    ? `Topildi: ${data.count} ta · Platformada jami: ${total} ta foydalanuvchi`
    : `Platformada jami: ${total} ta foydalanuvchi`;
}

async function load() {
  $("#list").innerHTML = `<tr><td colspan="6">${skeletonRows(4)}</td></tr>`;
  $("#pager").innerHTML = "";
  try {
    const data = await api.admin.users({ ...filters, page_size: 20 });
    $("#user-count").textContent = countLabel(data);
    $("#list").innerHTML = data.results.length
      ? data.results.map(row).join("")
      : `<tr><td colspan="6"><p class="muted center" style="padding:var(--sp-8)">Hech kim topilmadi</p></td></tr>`;
    $("#pager").innerHTML = paginationHtml(data);
  } catch (error) {
    $("#user-count").textContent = "";
    $("#list").innerHTML = `<tr><td colspan="6">${errorState(error.message)}</td></tr>`;
  }
}
