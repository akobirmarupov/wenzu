/**
 * Admin — platformadagi BARCHA bronlar.
 *
 * Bu ekran biznes egasinikidan farq qiladi: bu yerda hech narsa
 * tahrirlanmaydi (bronni faqat joy egasi tasdiqlaydi), lekin butun
 * platforma bo'ylab qidirish va holat kesimida ko'rish mumkin —
 * nizoli holatda admin nima bo'lganini shu yerdan ko'radi.
 */
import { api } from "../../core/api.js";
import { initAdminPage } from "./shell.js";
import { $, render, delegate, esc } from "../../ui/dom.js";
import { skeletonRows, errorState } from "../../ui/state.js";
import { paginationHtml } from "../../ui/pagination.js";
import { dateLabel, timeLabel, statusSeal, money } from "../../ui/format.js";

const STATUSES = [
  { value: "", label: "Barchasi" },
  { value: "pending", label: "Kutilmoqda" },
  { value: "confirmed", label: "Tasdiqlangan" },
  { value: "completed", label: "Yakunlangan" },
  { value: "cancelled", label: "Bekor qilingan" },
];

const TYPES = [
  { value: "", label: "Hammasi" },
  { value: "restaurant", label: "Restoran" },
  { value: "venue", label: "To'yxona" },
];

const filters = { status: "", business_type: "", date_from: "", page: 1 };

const user = await initAdminPage();
if (user) init();

function chips(containerId, items, key) {
  render(
    containerId,
    items.map((item) => `
      <button class="chip ${filters[key] === item.value ? "active" : ""}" type="button"
              data-value="${esc(item.value)}">${esc(item.label)}</button>`).join("")
  );
  delegate(containerId, "[data-value]", (button) => {
    filters[key] = button.dataset.value;
    filters.page = 1;
    document.querySelectorAll(`${containerId} .chip`).forEach((chip) => chip.classList.remove("active"));
    button.classList.add("active");
    load();
  });
}

function init() {
  chips("#status-filters", STATUSES, "status");
  chips("#type-filters", TYPES, "business_type");

  $("#date-from").addEventListener("change", (event) => {
    filters.date_from = event.target.value;
    filters.page = 1;
    load();
  });

  delegate("#pager", "[data-action='page']", (button) => {
    filters.page = Number(button.dataset.page);
    load();
  });

  load();
}

function row(item) {
  const when = item.business_type === "venue"
    ? dateLabel(item.date)
    : `${dateLabel(item.date)} · ${timeLabel(item.start_time)}–${timeLabel(item.end_time)}`;
  const place = item.room_name || item.hall_name || "—";

  return `
    <tr>
      <td>
        <b>${esc(item.business_name)}</b>
        <div class="xs faint">${esc(place)}</div>
      </td>
      <td>
        ${esc(item.user_name || "—")}
        <div class="xs faint mono">${esc(item.user_phone || "")}</div>
      </td>
      <td class="small">${when}</td>
      <td class="small right">${item.guests_count}</td>
      <td class="small right mono">${item.total_price ? money(item.total_price) : money(item.deposit_amount)}</td>
      <td class="right">${statusSeal(item.status)}</td>
    </tr>`;
}

async function load() {
  $("#list").innerHTML = `<tr><td colspan="6">${skeletonRows(4)}</td></tr>`;
  $("#pager").innerHTML = "";

  // Bo'sh filtrlarni yubormaymiz — backend ularni "bo'sh qiymat" deb
  // qabul qilib, hech narsa qaytarmasligi mumkin.
  const params = { page: filters.page, page_size: 20 };
  Object.entries(filters).forEach(([key, value]) => {
    if (value && key !== "page") params[key] = value;
  });

  try {
    const data = await api.admin.reservations(params);
    $("#list").innerHTML = data.results.length
      ? data.results.map(row).join("")
      : `<tr><td colspan="6"><p class="muted center" style="padding:var(--sp-8)">Bron topilmadi</p></td></tr>`;
    $("#pager").innerHTML = paginationHtml(data);
    $("#total").textContent = data.count;
  } catch (error) {
    $("#list").innerHTML = `<tr><td colspan="6">${errorState(error.message)}</td></tr>`;
  }
}
