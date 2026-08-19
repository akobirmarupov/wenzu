/**
 * Panel — menyu boshqaruvi.
 *
 * Restoran va to'yxona menyusi ikki xil model: restoranda taomning
 * NARXI bor, to'yxonada esa yo'q (narx paketga bog'langan). Shu farq
 * `isVenue` orqali bir joyda hal qilinadi.
 */
import { api } from "../../core/api.js";
import { MENU_CATEGORIES } from "../../core/config.js";
import { initOwnerPage } from "./shell.js";
import { $, delegate, esc, busy, formValues } from "../../ui/dom.js";
import { skeletonCards, emptyState, errorState } from "../../ui/state.js";
import { openModal, modal, confirmDialog } from "../../ui/modal.js";
import { toast } from "../../ui/toast.js";
import { money, imageUrl } from "../../ui/format.js";

const session = await initOwnerPage();
let isVenue = false;
let items = [];

if (session) {
  isVenue = session.businessType === "venue";
  $("#menu-hint").textContent = isVenue
    ? "To'yxona taomlarida narx ko'rsatilmaydi — narx «Zallar» bo'limidagi taom paketiga bog'lanadi."
    : "Mavjud bo'lmagan taomlar mijozlarga ko'rsatilmaydi, lekin ro'yxatingizda qoladi.";
  init();
}

const svc = () => (isVenue
  ? {
      list: api.owner.venueMenu,
      create: api.owner.createVenueItem,
      update: api.owner.updateVenueItem,
      remove: api.owner.deleteVenueItem,
    }
  : {
      list: api.owner.restaurantMenu,
      create: api.owner.createRestaurantItem,
      update: api.owner.updateRestaurantItem,
      remove: api.owner.deleteRestaurantItem,
    });

function card(item) {
  return `
    <div class="menu-item">
      <img src="${esc(imageUrl(item.photo))}" alt="" loading="lazy">
      <div class="body">
        <b class="small">${esc(item.name)}</b>
        <span class="xs muted">${esc(item.category_display || "")}${item.price ? ` · ${money(item.price)}` : ""}</span>
        ${!isVenue && item.is_available === false ? '<span class="seal seal-bad xs">Mavjud emas</span>' : ""}
        <div class="row row-2" style="margin-top:var(--sp-2)">
          <button class="btn btn-sm btn-outline" style="flex:1" data-edit="${esc(item.id)}">✎</button>
          <button class="btn btn-sm btn-danger" data-delete="${esc(item.id)}">🗑</button>
        </div>
      </div>
    </div>`;
}

function formHtml(item) {
  return `
    <h2>${item ? "Taomni tahrirlash" : "Yangi taom"}</h2>
    <form class="stack stack-4" id="item-form" style="margin-top:var(--sp-5)" novalidate>
      <div class="form-alert" id="item-error" hidden></div>

      <div class="field">
        <label for="name">Taom nomi</label>
        <input class="input" id="name" name="name" required value="${esc(item?.name || "")}"
               placeholder="Masalan: Osh (Toshkent usuli)">
      </div>

      <div class="field-row">
        <div class="field">
          <label for="category">Turkum</label>
          <select class="select" id="category" name="category">
            ${MENU_CATEGORIES.map((c) => `<option value="${c.value}"
              ${item?.category === c.value ? "selected" : ""}>${esc(c.label)}</option>`).join("")}
          </select>
        </div>
        ${isVenue ? "" : `
        <div class="field">
          <label for="price">Narxi (so'm)</label>
          <input class="input" id="price" name="price" type="number" min="0" required
                 value="${item?.price ? Math.round(item.price) : ""}" placeholder="45000">
        </div>`}
      </div>

      <div class="field">
        <label for="description">Tavsif (ixtiyoriy)</label>
        <textarea class="textarea" id="description" name="description" rows="2">${esc(item?.description || "")}</textarea>
      </div>

      ${isVenue ? "" : `
      <label class="checkbox">
        <input type="checkbox" id="is_available" name="is_available" ${item?.is_available !== false ? "checked" : ""}>
        <span>Hozir mavjud</span>
      </label>`}

      <div class="field">
        <label for="photo">Rasm (ixtiyoriy)</label>
        <input class="input" id="photo" name="photo" type="file" accept="image/*">
      </div>

      <button class="btn btn-primary btn-block btn-lg" type="submit" id="item-submit">
        ${item ? "Saqlash" : "Qo'shish"}
      </button>
    </form>`;
}

function openForm(item) {
  const node = openModal(formHtml(item));
  const form = node.querySelector("#item-form");
  const errorBox = node.querySelector("#item-error");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.hidden = true;
    const done = busy(node.querySelector("#item-submit"));

    try {
      const file = form.photo.files[0];
      const values = formValues(form);
      delete values.photo;
      if (!isVenue) values.is_available = Boolean(form.is_available?.checked);

      const saved = item ? await svc().update(item.id, values) : await svc().create(values);

      if (file) {
        const formData = new FormData();
        formData.append("photo", file);
        await svc().update(saved.id, formData);
      }

      modal.close();
      toast.ok(item ? "Taom yangilandi." : "Taom qo'shildi.");
      load();
    } catch (error) {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
    } finally {
      done();
    }
  });
}

function init() {
  $("#add-item").addEventListener("click", () => openForm(null));

  delegate("#list", "[data-edit]", (button) => {
    const item = items.find((i) => i.id === button.dataset.edit);
    if (item) openForm(item);
  });

  delegate("#list", "[data-delete]", async (button) => {
    const ok = await confirmDialog({
      title: "Taomni o'chirasizmi?",
      message: "Bu amalni qaytarib bo'lmaydi.",
      confirmText: "O'chirish",
      danger: true,
    });
    if (!ok) return;
    try {
      await svc().remove(button.dataset.delete);
      toast.ok("Taom o'chirildi.");
      load();
    } catch (error) {
      toast.fromError(error);
    }
  });

  load();
}

async function load() {
  $("#list").innerHTML = skeletonCards(4);
  try {
    const data = await svc().list({ page_size: 100 });
    items = data.results;
    $("#list").innerHTML = items.length
      ? items.map(card).join("")
      : emptyState("Menyu bo'sh", "Birinchi taomingizni qo'shing.", "🍽️");
  } catch (error) {
    $("#list").innerHTML = errorState(error.message);
  }
}
