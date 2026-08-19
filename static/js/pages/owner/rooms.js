/** Panel — restoran xonalari (faqat restoran egasiga). */
import { api } from "../../core/api.js";
import { ROOM_TYPES } from "../../core/config.js";
import { initOwnerPage } from "./shell.js";
import { $, delegate, esc, busy, formValues } from "../../ui/dom.js";
import { skeletonCards, emptyState, errorState } from "../../ui/state.js";
import { openModal, modal, confirmDialog } from "../../ui/modal.js";
import { toast } from "../../ui/toast.js";
import { money, imageUrl } from "../../ui/format.js";

const session = await initOwnerPage();
if (session) {
  if (session.businessType !== "restaurant") {
    // To'yxona egasi bu sahifaga tushib qolmasin.
    window.location.replace("/panel/zallar/");
  } else {
    init();
  }
}

function card(room) {
  return `
    <div class="card">
      <img class="card-media card-media-sm" src="${esc(imageUrl(room.photo))}" alt="" loading="lazy">
      <div class="card-body">
        <b>${esc(room.name)}</b>
        <span class="small muted">${esc(room.room_type_display)} · ${room.capacity} kishigacha</span>
        <span class="seal ${room.deposit_tier === "premium" ? "seal-gold" : "seal-ok"}" style="align-self:flex-start">
          Depozit: ${money(room.deposit_amount)}
        </span>
        <div class="row row-2" style="margin-top:var(--sp-2)">
          <button class="btn btn-sm btn-outline" style="flex:1" data-edit="${esc(room.id)}">Tahrirlash</button>
          <button class="btn btn-sm btn-danger" data-delete="${esc(room.id)}" aria-label="O'chirish">🗑</button>
        </div>
      </div>
    </div>`;
}

function formHtml(room) {
  return `
    <h2>${room ? "Xonani tahrirlash" : "Yangi xona"}</h2>
    <form class="stack stack-4" id="room-form" style="margin-top:var(--sp-5)" novalidate>
      <div class="form-alert" id="room-error" hidden></div>

      <div class="field">
        <label for="name">Nomi</label>
        <input class="input" id="name" name="name" required
               value="${esc(room?.name || "")}" placeholder="Masalan: VIP xona — 6 kishilik">
      </div>

      <div class="field-row">
        <div class="field">
          <label for="room_type">Toifasi</label>
          <select class="select" id="room_type" name="room_type">
            ${ROOM_TYPES.map((type) => `<option value="${type.value}"
              ${room?.room_type === type.value ? "selected" : ""}>${esc(type.label)}</option>`).join("")}
          </select>
        </div>
        <div class="field">
          <label for="capacity">Sig'imi (kishi)</label>
          <input class="input" id="capacity" name="capacity" type="number" min="1" required
                 value="${room?.capacity || ""}" placeholder="6">
        </div>
      </div>

      <div class="field-row">
        <div class="field">
          <label for="deposit_tier">Depozit tarifi</label>
          <select class="select" id="deposit_tier" name="deposit_tier">
            <option value="pro" ${room?.deposit_tier === "pro" ? "selected" : ""}>Pro</option>
            <option value="premium" ${room?.deposit_tier === "premium" ? "selected" : ""}>Premium</option>
          </select>
          <span class="field-hint">Narx platforma sozlamalaridan olinadi</span>
        </div>
        <div class="field">
          <label for="deposit_price">O'z narxingiz (ixtiyoriy)</label>
          <input class="input" id="deposit_price" name="deposit_price" type="number" min="0"
                 value="${room?.deposit_price || ""}" placeholder="Bo'sh qoldirsangiz tarif narxi">
        </div>
      </div>

      <div class="field">
        <label for="photo">Rasm (ixtiyoriy)</label>
        <input class="input" id="photo" name="photo" type="file" accept="image/*">
      </div>

      <button class="btn btn-primary btn-block btn-lg" type="submit" id="room-submit">
        ${room ? "Saqlash" : "Qo'shish"}
      </button>
    </form>`;
}

let rooms = [];

function openForm(room) {
  const node = openModal(formHtml(room));
  const form = node.querySelector("#room-form");
  const errorBox = node.querySelector("#room-error");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.hidden = true;
    const done = busy(node.querySelector("#room-submit"));

    try {
      const file = form.photo.files[0];
      const values = formValues(form);
      delete values.photo;
      if (!values.deposit_price) delete values.deposit_price;

      let saved;
      if (room) {
        saved = await api.owner.updateRoom(room.id, values);
      } else {
        saved = await api.owner.createRoom(values);
      }

      if (file) {
        // Rasm alohida form-data bilan yuboriladi.
        const formData = new FormData();
        formData.append("photo", file);
        await api.owner.updateRoom(saved.id, formData);
      }

      modal.close();
      toast.ok(room ? "Xona yangilandi." : "Xona qo'shildi.");
      load();
    } catch (error) {
      errorBox.textContent = error.fieldError?.("deposit_tier") || error.message;
      errorBox.hidden = false;
    } finally {
      done();
    }
  });
}

function init() {
  $("#add-room").addEventListener("click", () => openForm(null));

  delegate("#list", "[data-edit]", (button) => {
    const room = rooms.find((r) => r.id === button.dataset.edit);
    if (room) openForm(room);
  });

  delegate("#list", "[data-delete]", async (button) => {
    const ok = await confirmDialog({
      title: "Xonani o'chirasizmi?",
      message: "Faol bronlari bo'lsa o'chirilmaydi.",
      confirmText: "O'chirish",
      danger: true,
    });
    if (!ok) return;

    try {
      await api.owner.deleteRoom(button.dataset.delete);
      toast.ok("Xona o'chirildi.");
      load();
    } catch (error) {
      toast.fromError(error);
    }
  });

  load();
}

async function load() {
  $("#list").innerHTML = skeletonCards(3);
  try {
    const data = await api.owner.rooms({ page_size: 100 });
    rooms = data.results;
    $("#list").innerHTML = rooms.length
      ? rooms.map(card).join("")
      : emptyState("Xonalar yo'q", "Birinchi xonangizni qo'shing — mijozlar shuni bron qiladi.", "🪑");
  } catch (error) {
    $("#list").innerHTML = errorState(error.message);
  }
}
