/**
 * Bron qilish oynasi — restoran va to'yxona uchun ikki xil oqim.
 *
 * Restoran: sana → soat oralig'i (grid) → mehmonlar → taom (ixtiyoriy)
 * To'yxona: sana → taom soni (1/2/3) → mehmonlar → taomlar (majburiy)
 *
 * Ikkalasi ham "tasdiqlash" qadamida yakuniy summani va depozitni
 * ko'rsatadi, chunki to'lov Telegram orqali qo'lda amalga oshadi va
 * foydalanuvchi nima to'lashini oldindan bilishi kerak.
 */
import { api } from "../core/api.js";
import { auth } from "../core/auth.js";
import { ROUTES } from "../core/config.js";
import { openModal, modal } from "../ui/modal.js";
import { toast } from "../ui/toast.js";
import { esc, busy } from "../ui/dom.js";
import { money, timeLabel, todayISO, dateLabel, imageUrl } from "../ui/format.js";

const state = {
  type: null,       // "restaurant" | "venue"
  business: null,
  room: null,
  hall: null,
  date: "",
  startHour: null,
  endHour: null,
  busyRanges: [],
  openHour: 8,
  closeHour: 23,
  guests: 2,
  dishCount: 1,
  menuIds: [],
  note: "",
  step: "form",
};

/** Bron qilishdan oldin kirish va telefon tasdig'i talab qilinadi. */
function ensureCanBook() {
  if (!auth.isAuthenticated()) {
    window.location.href = `${ROUTES.login}?next=${encodeURIComponent(window.location.pathname)}`;
    return false;
  }
  const user = auth.user();
  if (user && !user.is_phone_verified) {
    toast.error("Avval telefon raqamingizni tasdiqlang.");
    window.location.href = ROUTES.verify;
    return false;
  }
  return true;
}

// ===================================================================
// Restoran
// ===================================================================
export async function openRoomBooking(business, room) {
  if (!ensureCanBook()) return;

  Object.assign(state, {
    type: "restaurant", business, room, hall: null,
    date: todayISO(1), startHour: null, endHour: null,
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
    state.openHour = data.open_time ? parseInt(data.open_time, 10) : null;
    state.closeHour = data.close_time ? parseInt(data.close_time, 10) : null;
    state.isOpen = data.is_open;
  } catch {
    state.busyRanges = [];
    state.isOpen = false;
  }
}

function hourIsBusy(hour) {
  return state.busyRanges.some((range) => {
    const start = parseInt(range.start_time, 10);
    const end = parseInt(range.end_time, 10);
    return hour >= start && hour < end;
  });
}

function clickHour(hour) {
  if (state.startHour === null || state.endHour !== null) {
    state.startHour = hour;
    state.endHour = null;
  } else if (hour <= state.startHour) {
    state.startHour = hour;
  } else {
    // Tanlangan oraliq ichida band soat bo'lmasligi kerak.
    for (let h = state.startHour; h < hour + 1; h += 1) {
      if (hourIsBusy(h)) {
        toast.error("Tanlangan oraliqda band soat bor.");
        return;
      }
    }
    state.endHour = hour + 1;
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
      state.startHour !== null &&
      hour >= state.startHour &&
      hour < (state.endHour ?? state.startHour + 1);
    const cls = busyCell ? "busy" : selected ? "sel" : "free";
    cells += `<button type="button" class="hour-cell ${cls}" ${busyCell ? "disabled" : ""}
                data-hour="${hour}">${String(hour).padStart(2, "0")}:00</button>`;
  }
  return `
    <div class="hour-grid">${cells}</div>
    <div class="hour-legend">
      <span><i style="background:#fff;border:1.5px solid var(--line)"></i>Bo'sh</span>
      <span><i style="background:var(--theme-accent)"></i>Tanlangan</span>
      <span><i style="background:var(--danger-dim)"></i>Band</span>
    </div>`;
}

// ===================================================================
// To'yxona
// ===================================================================
export async function openHallBooking(business, hall, pricing) {
  if (!ensureCanBook()) return;

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
function menuGridHtml(items, { max }) {
  if (!items?.length) return "";
  return `
    <label class="small strong" style="display:block;margin-top:var(--sp-4)">
      ${state.type === "venue"
        ? `Taomlarni tanlang (${state.menuIds.length}/${max})`
        : "Menyudan taom tanlash (ixtiyoriy)"}
    </label>
    <div class="menu-grid" style="margin-top:var(--sp-2)">
      ${items.map((item) => `
        <div class="menu-item selectable ${state.menuIds.includes(item.id) ? "checked" : ""}"
             data-menu="${esc(item.id)}">
          <div class="check">✓</div>
          <img src="${esc(imageUrl(item.photo))}" alt="${esc(item.name)}" loading="lazy">
          <div class="body">
            <b class="small">${esc(item.name)}</b>
            <span class="xs muted">${item.price ? money(item.price) : esc(item.category_display || "")}</span>
          </div>
        </div>`).join("")}
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
  const selectedLabel =
    state.startHour !== null && state.endHour !== null
      ? `${String(state.startHour).padStart(2, "0")}:00 – ${String(state.endHour).padStart(2, "0")}:00`
      : null;

  return `
    <h2>${esc(state.room.name)}</h2>
    <p class="muted small">${esc(state.business.name)} · 🕗 ${timeLabel(state.business.open_time) || "—"}–${timeLabel(state.business.close_time) || "—"}</p>

    <div class="field" style="margin-top:var(--sp-5)">
      <label for="bk-date">Sana</label>
      <input class="input" id="bk-date" type="date" value="${state.date}" min="${todayISO()}">
    </div>

    <label class="small strong" style="display:block;margin:var(--sp-4) 0 var(--sp-2)">Bo'sh vaqtni tanlang</label>
    ${hourGridHtml()}
    ${selectedLabel ? `<p class="small muted">Tanlangan: <b>${selectedLabel}</b> ·
        <button type="button" class="btn-ghost small" data-reset-hours style="text-decoration:underline">tozalash</button></p>` : ""}

    <div class="field" style="margin-top:var(--sp-4)">
      <label for="bk-guests">Mehmonlar soni (${state.room.capacity} kishigacha)</label>
      <input class="input" id="bk-guests" type="number" min="1" max="${state.room.capacity}" value="${state.guests}">
    </div>

    ${menuGridHtml(state.menu, { max: 99 })}

    <div class="field" style="margin-top:var(--sp-4)">
      <label for="bk-note">Qo'shimcha istak (ixtiyoriy)</label>
      <textarea class="textarea" id="bk-note" rows="2"
        placeholder="Masalan: deraza yonidagi stol">${esc(state.note)}</textarea>
    </div>

    <button class="btn btn-primary btn-block btn-lg" style="margin-top:var(--sp-5)"
            data-next ${state.endHour === null ? "disabled" : ""}>Joyni band qilish</button>`;
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

    ${menuGridHtml(state.menu, { max: state.dishCount })}

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
        ? `<div class="row"><span>Vaqt</span><b>${String(state.startHour).padStart(2, "0")}:00 – ${String(state.endHour).padStart(2, "0")}:00</b></div>`
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
  return `
    <h2>Ariza yuborildi ✅</h2>
    <div class="notice">
      <p>So'rovingiz qabul qilindi va hozircha <b>«kutilmoqda»</b> holatida.</p>
      <p>Bronni yakuniy tasdiqlash uchun <b>${esc(telegram)}</b> administratoriga
         Telegram orqali murojaat qiling va <b>${money(depositAmount())}</b> depozitni to'lang.</p>
    </div>
    <a class="tg-line" href="https://t.me/${esc(telegram.replace("@", ""))}" target="_blank" rel="noopener">
      ✈️ Telegram: ${esc(telegram)}
    </a>
    <a class="btn btn-primary btn-block btn-lg" style="margin-top:var(--sp-5)"
       href="${ROUTES.profile}?tab=bookings">Bronlarimga o'tish</a>`;
}

function bindEvents(container) {
  container.querySelector("#bk-date")?.addEventListener("change", async (event) => {
    state.date = event.target.value;
    state.startHour = null;
    state.endHour = null;
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

  container.querySelector("[data-reset-hours]")?.addEventListener("click", () => {
    state.startHour = null;
    state.endHour = null;
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
            start_time: `${String(state.startHour).padStart(2, "0")}:00`,
            end_time: `${String(state.endHour).padStart(2, "0")}:00`,
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
