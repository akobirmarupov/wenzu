/**
 * Bron qilish oynasi — restoran va to'yxona uchun ikki xil oqim.
 *
 * Restoran: sana → vaqt oralig'i (XOHLAGANCHA davomiylik) → mehmonlar → taom
 * To'yxona: sana → taom soni (1/2/3) → mehmonlar → taomlar (majburiy)
 *
 * Menyu bu yerda MATN QATORI ko'rinishida: chapda nomi va narxi, o'ngda
 * kichik rasm. Detal sahifasidagi katta kartochkali to'r tanlash uchun
 * noqulay edi — narx rasm ostida qolib ketardi.
 */
import { api } from "../core/api.js";
import { auth } from "../core/auth.js";
import { ROUTES } from "../core/config.js";
import { openModal, modal } from "../ui/modal.js";
import { toast } from "../ui/toast.js";
import { esc, busy } from "../ui/dom.js";
import { ensurePhone } from "./phone-gate.js";
import { money, timeLabel, todayISO, dateLabel, imageUrl } from "../ui/format.js";

/** Vaqt tanlash qadami (daqiqa). 30 daqiqa — 1 soatlik ham, 5 soatlik ham bo'ladi. */
const STEP_MIN = 30;

const state = {
  type: null,       // "restaurant" | "venue"
  business: null,
  room: null,
  hall: null,
  date: "",
  startMin: null,   // yarim tundan boshlab daqiqa
  endMin: null,
  busyRanges: [],
  openHour: 8,
  closeHour: 23,
  isOpen: false,
  guests: 2,
  dishCount: 1,
  menuIds: [],
  menu: [],
  note: "",
  step: "form",
};

/* ---------- vaqt yordamchilari ---------- */
function toMin(value) {
  const [h, m] = String(value).split(":");
  return Number(h) * 60 + Number(m || 0);
}
function fromMin(minutes) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}
function rangeIsBusy(startMin, endMin) {
  return state.busyRanges.some((range) => {
    const busyStart = toMin(range.start_time);
    const busyEnd = toMin(range.end_time);
    return startMin < busyEnd && endMin > busyStart;
  });
}

/**
 * Bron qilishdan oldingi tekshiruvlar.
 *
 * Ilgari bu yerda SMS tasdig'i talab qilinardi va odam `/tasdiqlash/`
 * sahifasiga QUVIB CHIQARILARDI — tanlagan sanasi, xonasi, hammasi
 * yo'qolardi va qaytib kelgach boshidan boshlashi kerak edi.
 *
 * Endi SMS yo'q: raqam shu yerda, kichik oynada bir marta so'raladi
 * va foydalanuvchi o'z joyida qoladi.
 */
async function ensureCanBook() {
  if (!auth.isAuthenticated()) {
    window.location.href = `${ROUTES.login}?next=${encodeURIComponent(window.location.pathname)}`;
    return false;
  }
  const user = auth.user();

  // Platforma egasi bron QILMAYDI — u bronlarni boshqaradi.
  // Server ham rad etadi (`IsCustomer`); bu yerda sababni oldindan
  // aytamiz, aks holda odam formani to'ldirib, oxirida xato ko'rardi.
  if (user?.is_staff) {
    toast.error(
      "Platforma egasi bron qila olmaydi. Bronlarni boshqaruv panelidan ko'ring."
    );
    return false;
  }
  // Aloqa raqami — joy egasi mehmonga qo'ng'iroq qilishi uchun.
  // Bor bo'lsa oyna umuman ochilmaydi.
  return ensurePhone();
}

// ===================================================================
// Restoran
// ===================================================================
export async function openRoomBooking(business, room) {
  if (!(await ensureCanBook())) return;

  Object.assign(state, {
    type: "restaurant", business, room, hall: null,
    date: todayISO(1), startMin: null, endMin: null,
    guests: Math.min(2, room.capacity), menuIds: [], note: "", step: "form",
  });

  openModal("<div id='booking-body'></div>", { wide: true });
  await loadBusyHours();
  renderBody();
}

async function loadBusyHours() {
  try {
    const data = await api.rooms.busyHours(state.room.id, state.date);
    state.busyRanges = data.busy_ranges || [];
    state.openHour = data.open_time ? parseInt(data.open_time, 10) : 8;
    state.closeHour = data.close_time ? parseInt(data.close_time, 10) : 23;
    state.isOpen = data.is_open;
  } catch {
    state.busyRanges = [];
    state.isOpen = false;
  }
}

function hourIsBusy(hour) {
  return rangeIsBusy(hour * 60, (hour + 1) * 60);
}

/** Gridda soat bosilishi: birinchi bosish — boshlanish, ikkinchisi — tugash. */
function clickHour(hour) {
  const clicked = hour * 60;
  if (state.startMin === null || state.endMin !== null || clicked <= state.startMin) {
    state.startMin = clicked;
    state.endMin = null;
  } else {
    const end = clicked + 60;
    if (rangeIsBusy(state.startMin, end)) {
      toast.error("Tanlangan oraliqda band vaqt bor.");
      return;
    }
    state.endMin = end;
  }
  renderBody();
}

function hourGridHtml() {
  if (!state.isOpen) {
    return `<p class="form-alert">Bu kun uchun ish jadvali ochilmagan. Boshqa sanani tanlang.</p>`;
  }
  let cells = "";
  for (let hour = state.openHour; hour < state.closeHour; hour += 1) {
    const busyCell = hourIsBusy(hour);
    const selected =
      state.startMin !== null &&
      hour * 60 >= state.startMin &&
      hour * 60 < (state.endMin ?? state.startMin + 60);
    const cls = busyCell ? "busy" : selected ? "sel" : "free";
    cells += `<button type="button" class="hour-cell ${cls}" ${busyCell ? "disabled" : ""}
                data-hour="${hour}">${String(hour).padStart(2, "0")}:00</button>`;
  }
  return `
    <div class="hour-grid">${cells}</div>
    <div class="hour-legend">
      <span><i class="l-free"></i>Bo'sh</span>
      <span><i class="l-sel"></i>Tanlangan</span>
      <span><i class="l-busy"></i>Band</span>
    </div>`;
}

/**
 * Aniq vaqt tanlagichi.
 *
 * Grid faqat soatma-soat ko'rsatadi; bu yerda esa yarim soatlik qadam
 * bilan XOHLAGANCHA davomiylikni tanlash mumkin — 1 soatdan tortib
 * kechgacha. Ilgari oraliq amalda ikki soatga qotib qolgandek edi.
 */
function timePickerHtml() {
  if (!state.isOpen) return "";

  const openMin = state.openHour * 60;
  const closeMin = state.closeHour * 60;

  const options = (selected, from, to) => {
    let html = "";
    for (let m = from; m <= to; m += STEP_MIN) {
      html += `<option value="${m}" ${selected === m ? "selected" : ""}>${fromMin(m)}</option>`;
    }
    return html;
  };

  const start = state.startMin ?? openMin;
  const duration = state.startMin !== null && state.endMin !== null
    ? state.endMin - state.startMin
    : null;

  return `
    <div class="field-row" style="margin-top:var(--sp-3)">
      <div class="field">
        <label for="bk-start">Boshlanish</label>
        <select class="select" id="bk-start">${options(state.startMin, openMin, closeMin - STEP_MIN)}</select>
      </div>
      <div class="field">
        <label for="bk-end">Tugash</label>
        <select class="select" id="bk-end">${options(state.endMin, start + STEP_MIN, closeMin)}</select>
      </div>
    </div>
    <p class="small muted">
      ${duration
        ? `Tanlangan: <b>${fromMin(state.startMin)} – ${fromMin(state.endMin)}</b>
           (${(duration / 60).toFixed(duration % 60 ? 1 : 0)} soat) ·
           <button type="button" class="link-btn" data-reset-hours>tozalash</button>`
        : "Vaqt oralig'ini xohlaganingizcha tanlashingiz mumkin — chegara yo'q."}
    </p>`;
}

// ===================================================================
// To'yxona
// ===================================================================
export async function openHallBooking(business, hall, pricing) {
  if (!(await ensureCanBook())) return;

  Object.assign(state, {
    type: "venue", business, hall, room: null,
    date: todayISO(14), guests: 100, dishCount: 1,
    menuIds: [], note: "", step: "form",
    pricing: pricing || [], busyDates: [],
  });

  openModal("<div id='booking-body'></div>", { wide: true });

  try {
    const data = await api.halls.busyDates(hall.id, { date_from: todayISO() });
    state.busyDates = data.busy_dates || [];
  } catch {
    state.busyDates = [];
  }
  renderBody();
}

function pricePerPerson() {
  const row = (state.pricing || []).find((p) => p.dish_count === state.dishCount);
  return row ? Number(row.price_per_person) : null;
}

function totalPrice() {
  const perPerson = pricePerPerson();
  if (perPerson !== null) return perPerson * (Number(state.guests) || 0);
  return state.hall?.all_price ? Number(state.hall.all_price) : 0;
}

function depositAmount() {
  return state.type === "restaurant"
    ? Number(state.room?.deposit_amount || 0)
    : Number(state.hall?.deposit_amount || 0);
}

// ===================================================================
// Chizish
// ===================================================================
/**
 * Menyu ro'yxati — chapda nomi va narxi, o'ngda kichik rasm.
 * Bron oynasida faqat SHU ko'rinish ishlatiladi; detal sahifasidagi
 * to'liq menyu kartochkali holida qoladi.
 */
function menuPickHtml(items, { max }) {
  if (!items?.length) return "";

  const title = state.type === "venue"
    ? `Taomlarni tanlang (${state.menuIds.length}/${max})`
    : `Menyudan taom tanlash — ixtiyoriy (${state.menuIds.length} ta)`;

  return `
    <label class="small strong" style="display:block;margin:var(--sp-5) 0 var(--sp-2)">${esc(title)}</label>
    <div class="pick-list">
      ${items.map((item) => `
        <button type="button" class="pick-row ${state.menuIds.includes(item.id) ? "checked" : ""}"
                data-menu="${esc(item.id)}">
          <span class="tick" aria-hidden="true">✓</span>
          <span class="info">
            <b>${esc(item.name)}</b>
            <span>${esc(item.category_display || state.business.name)}</span>
          </span>
          <span class="price">${item.price ? money(item.price) : "—"}</span>
          <img class="thumb" src="${esc(imageUrl(item.photo))}" alt="" loading="lazy">
        </button>`).join("")}
    </div>`;
}

function renderBody() {
  const container = document.getElementById("booking-body");
  if (!container) return;

  if (state.step === "confirm") {
    container.innerHTML = confirmHtml();
  } else if (state.step === "done") {
    container.innerHTML = doneHtml();
  } else {
    container.innerHTML = state.type === "restaurant" ? restaurantFormHtml() : venueFormHtml();
  }
  bindEvents(container);
}

function restaurantFormHtml() {
  return `
    <h2>${esc(state.room.name)}</h2>
    <p class="muted small">${esc(state.business.name)} · 🕗 ${timeLabel(state.business.open_time) || "—"}–${timeLabel(state.business.close_time) || "—"}</p>

    <div class="field" style="margin-top:var(--sp-5)">
      <label for="bk-date">Sana</label>
      <input class="input" id="bk-date" type="date" value="${state.date}" min="${todayISO()}">
    </div>

    <label class="small strong" style="display:block;margin:var(--sp-4) 0 var(--sp-2)">Bo'sh vaqtni tanlang</label>
    ${hourGridHtml()}
    ${timePickerHtml()}

    <div class="field" style="margin-top:var(--sp-4)">
      <label for="bk-guests">Mehmonlar soni (${state.room.capacity} kishigacha)</label>
      <input class="input" id="bk-guests" type="number" min="1" max="${state.room.capacity}" value="${state.guests}">
    </div>

    ${menuPickHtml(state.menu, { max: 99 })}

    <div class="field" style="margin-top:var(--sp-4)">
      <label for="bk-note">Qo'shimcha istak (ixtiyoriy)</label>
      <textarea class="textarea" id="bk-note" rows="2"
        placeholder="Masalan: deraza yonidagi stol">${esc(state.note)}</textarea>
    </div>

    <button class="btn btn-primary btn-block btn-lg" style="margin-top:var(--sp-5)"
            data-next ${state.endMin === null ? "disabled" : ""}>Joyni band qilish</button>`;
}

function venueFormHtml() {
  const dateBusy = state.busyDates.includes(state.date);
  const perPerson = pricePerPerson();

  return `
    <h2>${esc(state.hall.name)}</h2>
    <p class="muted small">${esc(state.business.name)} · ${state.hall.people} kishigacha</p>

    <div class="field" style="margin-top:var(--sp-5)">
      <label for="bk-date">Sana (to'yxonada bir kunga bitta to'y)</label>
      <input class="input" id="bk-date" type="date" value="${state.date}" min="${todayISO()}">
    </div>
    ${dateBusy ? `<p class="form-alert">⛔ Bu kun band. Boshqa sanani tanlang.</p>` : ""}

    <label class="small strong" style="display:block;margin:var(--sp-4) 0 var(--sp-2)">Nechta xil taom bo'lsin?</label>
    <div class="dish-row">
      ${[1, 2, 3].map((n) => {
        const row = (state.pricing || []).find((p) => p.dish_count === n);
        return `<button type="button" class="dish-chip ${state.dishCount === n ? "active" : ""}"
                  data-dish="${n}" ${row ? "" : "disabled"}>
                  <b class="small">${n} xil taom</b>
                  <div class="p">${row ? money(row.price_per_person) + " / kishi" : "sozlanmagan"}</div>
                </button>`;
      }).join("")}
    </div>

    <div class="field" style="margin-top:var(--sp-4)">
      <label for="bk-guests">Mehmonlar soni</label>
      <input class="input" id="bk-guests" type="number" min="1" max="${state.hall.people}" value="${state.guests}">
    </div>

    ${menuPickHtml(state.menu, { max: state.dishCount })}

    <div class="total-box" style="margin-top:var(--sp-5)">
      <div class="row"><span>Kishi boshiga</span><b>${perPerson !== null ? money(perPerson) : "—"}</b></div>
      <div class="row grand"><span>Umumiy (${state.guests || 0} kishi)</span><b>${money(totalPrice())}</b></div>
    </div>

    <button class="btn btn-primary btn-block btn-lg" style="margin-top:var(--sp-5)"
            data-next ${dateBusy || perPerson === null ? "disabled" : ""}>Zalni band qilish</button>`;
}

function confirmHtml() {
  const isRestaurant = state.type === "restaurant";
  return `
    <h2>Bronni tasdiqlang</h2>
    <div class="notice">
      <p>Assalomu alaykum! 👋 ${isRestaurant ? "Stolni" : "Zalni"} band qilish uchun
         "Ariza berish" tugmasini bosing.</p>
      <p>Oldindan <b>${money(depositAmount())}</b> depozit to'lovini amalga oshirishingiz
         kerak bo'ladi${isRestaurant ? " — bu summa ovqatlanganingizga qo'shiladi" : ""}.</p>
    </div>

    <div class="total-box" style="margin-top:var(--sp-4)">
      <div class="row"><span>Sana</span><b>${dateLabel(state.date)}</b></div>
      ${isRestaurant
        ? `<div class="row"><span>Vaqt</span><b>${fromMin(state.startMin)} – ${fromMin(state.endMin)}</b></div>`
        : `<div class="row"><span>Taom soni</span><b>${state.dishCount} xil</b></div>`}
      <div class="row"><span>Mehmonlar</span><b>${state.guests} kishi</b></div>
      ${!isRestaurant ? `<div class="row grand"><span>Umumiy summa</span><b>${money(totalPrice())}</b></div>` : ""}
      <div class="row"><span>Depozit (oldindan)</span><b>${money(depositAmount())}</b></div>
    </div>

    <div class="row row-2" style="margin-top:var(--sp-5)">
      <button class="btn btn-outline" style="flex:1" data-back>← Orqaga</button>
      <button class="btn btn-primary" style="flex:2" data-submit>Ariza berish</button>
    </div>`;
}

function doneHtml() {
  const telegram = state.business.telegram_username
    ? `@${state.business.telegram_username}`
    : "@uvente";
  const handle = telegram.replace("@", "");
  return `
    <h2>Ariza yuborildi ✅</h2>
    <div class="notice">
      <p>So'rovingiz qabul qilindi va hozircha <b>«kutilmoqda»</b> holatida.</p>
      <p>Bronni yakuniy tasdiqlash uchun <b>${esc(telegram)}</b> administratoriga
         Telegram orqali murojaat qiling va <b>${money(depositAmount())}</b> depozitni to'lang.</p>
    </div>
    <a class="tg-line" style="margin-top:var(--sp-4)" href="https://t.me/${esc(handle)}"
       target="_blank" rel="noopener">
      <span class="ic" aria-hidden="true">✈️</span>
      <span>Telegram: ${esc(telegram)} — bosing va yozing</span>
    </a>
    <a class="btn btn-primary btn-block btn-lg" style="margin-top:var(--sp-5)"
       href="${ROUTES.myBookings}">Bronlarimga o'tish</a>`;
}

function bindEvents(container) {
  container.querySelector("#bk-date")?.addEventListener("change", async (event) => {
    state.date = event.target.value;
    state.startMin = null;
    state.endMin = null;
    if (state.type === "restaurant") await loadBusyHours();
    renderBody();
  });

  container.querySelector("#bk-guests")?.addEventListener("input", (event) => {
    state.guests = Number(event.target.value) || 1;
    if (state.type === "venue") renderBody();
  });

  container.querySelector("#bk-note")?.addEventListener("input", (event) => {
    state.note = event.target.value;
  });

  container.querySelectorAll("[data-hour]").forEach((button) => {
    button.addEventListener("click", () => clickHour(Number(button.dataset.hour)));
  });

  container.querySelector("#bk-start")?.addEventListener("change", (event) => {
    state.startMin = Number(event.target.value);
    if (state.endMin !== null && state.endMin <= state.startMin) state.endMin = null;
    renderBody();
  });

  container.querySelector("#bk-end")?.addEventListener("change", (event) => {
    const end = Number(event.target.value);
    const start = state.startMin ?? state.openHour * 60;
    if (rangeIsBusy(start, end)) {
      toast.error("Tanlangan oraliqda band vaqt bor.");
      return;
    }
    state.startMin = start;
    state.endMin = end;
    renderBody();
  });

  container.querySelector("[data-reset-hours]")?.addEventListener("click", () => {
    state.startMin = null;
    state.endMin = null;
    renderBody();
  });

  container.querySelectorAll("[data-dish]").forEach((button) => {
    button.addEventListener("click", () => {
      state.dishCount = Number(button.dataset.dish);
      if (state.menuIds.length > state.dishCount) state.menuIds = state.menuIds.slice(0, state.dishCount);
      renderBody();
    });
  });

  container.querySelectorAll("[data-menu]").forEach((node) => {
    node.addEventListener("click", () => {
      const id = node.dataset.menu;
      const index = state.menuIds.indexOf(id);
      if (index >= 0) {
        state.menuIds.splice(index, 1);
      } else {
        const max = state.type === "venue" ? state.dishCount : 99;
        if (state.menuIds.length >= max) {
          toast.error(`Eng ko'pi ${max} ta taom tanlash mumkin.`);
          return;
        }
        state.menuIds.push(id);
      }
      renderBody();
    });
  });

  container.querySelector("[data-next]")?.addEventListener("click", () => {
    if (state.type === "venue" && state.menuIds.length && state.menuIds.length !== state.dishCount) {
      toast.error(`${state.dishCount} xil taom tanlanishi kerak.`);
      return;
    }
    state.step = "confirm";
    renderBody();
  });

  container.querySelector("[data-back]")?.addEventListener("click", () => {
    state.step = "form";
    renderBody();
  });

  container.querySelector("[data-submit]")?.addEventListener("click", async (event) => {
    const done = busy(event.currentTarget);
    try {
      const payload = state.type === "restaurant"
        ? {
            room: state.room.id,
            date: state.date,
            start_time: fromMin(state.startMin),
            end_time: fromMin(state.endMin),
            guests_count: state.guests,
            menu_items: state.menuIds,
            special_request: state.note,
          }
        : {
            hall: state.hall.id,
            date: state.date,
            guests_count: state.guests,
            dish_count: state.dishCount,
            menu_items: state.menuIds,
            special_request: state.note,
          };

      await api.reservations.create(payload);
      state.step = "done";
      renderBody();
    } catch (error) {
      toast.fromError(error);
      if (error.status === 409) {
        state.step = "form";
        if (state.type === "restaurant") await loadBusyHours();
        renderBody();
      }
    } finally {
      done();
    }
  });
}

/** Menyu ro'yxatini oynaga uzatish (detal sahifasi allaqachon yuklab olgan). */
export function setBookingMenu(items) {
  state.menu = items || [];
}
