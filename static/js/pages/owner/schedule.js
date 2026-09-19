/** Panel — bo'sh vaqtlar (Availability) jadvali. */
import { api } from "../../core/api.js";
import { initOwnerPage } from "./shell.js";
import { $, render, delegate, esc, busy } from "../../ui/dom.js";
import { skeletonRows, errorState } from "../../ui/state.js";
import { paginationHtml } from "../../ui/pagination.js";
import { confirmDialog } from "../../ui/modal.js";
import { toast } from "../../ui/toast.js";
import { dateLabel, timeLabel, todayISO } from "../../ui/format.js";

const MONTHS = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
                "Iyul", "Avgust", "Sentyabr", "Oktyabr", "Noyabr", "Dekabr"];

const session = await initOwnerPage();
let isVenue = false;
const filters = { page: 1, date_from: todayISO() };

if (session) {
  isVenue = session.businessType === "venue";
  init();
}

async function buildTargetField() {
  if (isVenue) {
    render("#target-fields", `
      <p class="field-hint" style="grid-column:1/-1">
        To'yxonada bo'sh vaqt butun biznes darajasida hisoblanadi — zal tanlanmaydi,
        chunki bir kunda faqat bitta to'y bo'ladi.
      </p>`);
    $("#time-hint").textContent = "00:00 — yarim tungacha (butun kun) degani.";
    return;
  }

  try {
    const data = await api.owner.rooms({ page_size: 100 });
    if (!data.results.length) {
      render("#target-fields", `
        <p class="form-alert" style="grid-column:1/-1">
          Avval <a href="/panel/xonalar/" class="strong">xona qo'shing</a> — jadval har bir xona uchun alohida ochiladi.
        </p>`);
      $("#generate").disabled = true;
      return;
    }
    render("#target-fields", `
      <div class="field">
        <label for="room">Xona</label>
        <select class="select" id="room" name="room" required>
          ${data.results.map((room) => `<option value="${esc(room.id)}">${esc(room.name)}</option>`).join("")}
        </select>
      </div>`);
  } catch (error) {
    render("#target-fields", `<p class="form-alert">${esc(error.message)}</p>`);
  }
}

function buildYearAndMonths() {
  const now = new Date();
  const year = now.getFullYear();

  render("#year", [year, year + 1, year + 2]
    .map((y) => `<option value="${y}">${y}</option>`).join(""));

  render("#months", MONTHS.map((label, index) => `
    <label class="chip" style="cursor:pointer">
      <input type="checkbox" name="months" value="${index + 1}"
        ${index + 1 === now.getMonth() + 1 ? "checked" : ""} style="margin-right:6px">
      ${esc(label)}
    </label>`).join(""));

  // Tanlanganini vizual belgilash
  document.querySelectorAll('#months input[name="months"]').forEach((input) => {
    const sync = () => input.closest(".chip").classList.toggle("active", input.checked);
    sync();
    input.addEventListener("change", sync);
  });
}

function init() {
  buildTargetField();
  buildYearAndMonths();

  $("#generate-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const months = Array.from(document.querySelectorAll('#months input:checked')).map((i) => Number(i.value));

    if (!months.length) {
      toast.error("Kamida bitta oyni tanlang.");
      return;
    }

    const payload = {
      start_time: $("#start_time").value,
      end_time: $("#end_time").value,
      year: Number($("#year").value),
      months,
    };
    if (!isVenue) payload.room = $("#room")?.value;

    const done = busy($("#generate"));
    try {
      const result = await api.owner.generateAvailability(payload);
      toast.ok(result.detail);
      load();
    } catch (error) {
      toast.fromError(error);
    } finally {
      done();
    }
  });

  render("#schedule-filters", `
    <button class="chip active" data-scope="upcoming" type="button">Kelgusi kunlar</button>
    <button class="chip" data-scope="booked" type="button">Faqat band</button>`);

  delegate("#schedule-filters", "[data-scope]", (button) => {
    document.querySelectorAll("[data-scope]").forEach((b) => b.classList.remove("active"));
    button.classList.add("active");
    filters.is_booked = button.dataset.scope === "booked" ? "true" : undefined;
    filters.page = 1;
    load();
  });

  delegate("#pager", "[data-action='page']", (button) => {
    filters.page = Number(button.dataset.page);
    load();
  });

  // Qo'lda band qilish/bo'shatish.
  //
  // Kerak bo'ladi: to'y yoki katta ziyofat ba'zan telefon orqali,
  // saytdan tashqarida kelishiladi. Egasi o'sha kunni qo'lda band deb
  // belgilamasa, mijoz shu kunga bron qilib qo'yardi va ikki to'y bir
  // kunga tushib qolardi.
  delegate("#schedule-list", "[data-toggle]", async (button) => {
    const nowBooked = button.dataset.booked === "true";
    const done = busy(button);
    try {
      await api.owner.updateAvailability(button.dataset.toggle, { is_booked: !nowBooked });
      toast.ok(nowBooked ? "Kun bo'shatildi." : "Kun band deb belgilandi.");
      load();
    } catch (error) {
      toast.fromError(error);
    } finally {
      done();
    }
  });

  delegate("#schedule-list", "[data-delete]", async (button) => {
    const ok = await confirmDialog({
      title: "Bu kunni yopasizmi?",
      message: "Kun jadvaldan olib tashlanadi va mijozlar bron qila olmaydi.",
      confirmText: "Yopish",
      danger: true,
    });
    if (!ok) return;
    try {
      await api.owner.deleteAvailability(button.dataset.delete);
      toast.ok("Kun yopildi.");
      load();
    } catch (error) {
      toast.fromError(error);
    }
  });

  load();
}

async function load() {
  $("#schedule-list").innerHTML = `<tr><td colspan="5">${skeletonRows(3)}</td></tr>`;
  try {
    const data = await api.owner.availability({ ...filters, page_size: 30 });
    $("#schedule-list").innerHTML = data.results.length
      ? data.results.map((row) => `
        <tr>
          <td class="nums">${dateLabel(row.date)}</td>
          <td>${esc(row.room_name || "Butun to'yxona")}</td>
          <td class="nums">${timeLabel(row.start_time)}–${timeLabel(row.end_time)}</td>
          <td>${row.is_booked
            ? '<span class="seal seal-bad">Band</span>'
            : '<span class="seal seal-ok">Bo\'sh</span>'}</td>
          <td class="right">
            <div class="row row-2" style="justify-content:flex-end">
              <button class="btn btn-sm btn-outline" data-toggle="${esc(row.id)}"
                      data-booked="${row.is_booked}">
                ${row.is_booked ? "Bo'shatish" : "Band qilish"}
              </button>
              ${row.is_booked ? "" :
                `<button class="btn btn-sm btn-danger" data-delete="${esc(row.id)}">Yopish</button>`}
            </div>
          </td>
        </tr>`).join("")
      : `<tr><td colspan="5"><p class="muted center" style="padding:var(--sp-8)">
           Hali kun ochilmagan — yuqoridagi forma orqali yarating.</p></td></tr>`;
    $("#pager").innerHTML = paginationHtml(data);
  } catch (error) {
    $("#schedule-list").innerHTML = `<tr><td colspan="5">${errorState(error.message)}</td></tr>`;
  }
}
