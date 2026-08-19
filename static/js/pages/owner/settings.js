/** Panel — biznes sozlamalari va galereya. */
import { api } from "../../core/api.js";
import { CUISINES } from "../../core/config.js";
import { initOwnerPage } from "./shell.js";
import { $, render, delegate, esc, busy, formValues } from "../../ui/dom.js";
import { skeletonRows, skeletonCards, emptyState, errorState } from "../../ui/state.js";
import { confirmDialog } from "../../ui/modal.js";
import { toast } from "../../ui/toast.js";

const session = await initOwnerPage();
let isVenue = false;

if (session) {
  isVenue = session.businessType === "venue";
  init();
}

function formHtml(business) {
  return `
    <div class="form-alert" id="form-error" hidden></div>

    <div class="field-row">
      <div class="field">
        <label for="name">Nomi</label>
        <input class="input" id="name" name="name" required value="${esc(business.name || "")}">
      </div>
      <div class="field">
        <label for="district">Tuman</label>
        <input class="input" id="district" name="district" value="${esc(business.district || "")}"
               placeholder="Masalan: Yunusobod">
        <span class="field-hint">Qidiruvda nom bilan birga ishlatiladi</span>
      </div>
    </div>

    <div class="field">
      <label for="address">Manzil</label>
      <input class="input" id="address" name="address" value="${esc(business.address || "")}"
             placeholder="Ko'cha, uy raqami">
    </div>

    <div class="field">
      <label for="description">Tavsif</label>
      <textarea class="textarea" id="description" name="description" rows="4"
        placeholder="Mijozlarga joyingiz haqida qisqacha ayting">${esc(business.description || "")}</textarea>
    </div>

    ${isVenue ? "" : `
    <div class="field-row">
      <div class="field">
        <label for="cuisine">Oshxona turi</label>
        <select class="select" id="cuisine" name="cuisine">
          <option value="">Tanlanmagan</option>
          ${CUISINES.map((c) => `<option value="${c.value}"
            ${business.cuisine === c.value ? "selected" : ""}>${esc(c.label)}</option>`).join("")}
        </select>
      </div>
      <div class="field">
        <label for="open_time">Ish boshlanishi</label>
        <input class="input" id="open_time" name="open_time" type="time"
               value="${(business.open_time || "").slice(0, 5)}">
      </div>
      <div class="field">
        <label for="close_time">Ish tugashi</label>
        <input class="input" id="close_time" name="close_time" type="time"
               value="${(business.close_time || "").slice(0, 5)}">
      </div>
    </div>`}

    <div class="field-row">
      <div class="field">
        <label for="telegram_username">Telegram username</label>
        <input class="input" id="telegram_username" name="telegram_username"
               value="${esc(business.telegram_username || "")}" placeholder="@ belgisiz">
        <span class="field-hint">Mijoz depozit to'lovi uchun shu manzilga yozadi</span>
      </div>
      <div class="field">
        <label for="cover">Asosiy rasm</label>
        <input class="input" id="cover" name="cover_photo" type="file" accept="image/*">
      </div>
    </div>

    <div class="field-row">
      <div class="field">
        <label for="latitude">Kenglik (latitude)</label>
        <input class="input" id="latitude" name="latitude" type="number" step="0.000001"
               value="${business.latitude || ""}" placeholder="41.311081">
      </div>
      <div class="field">
        <label for="longitude">Uzunlik (longitude)</label>
        <input class="input" id="longitude" name="longitude" type="number" step="0.000001"
               value="${business.longitude || ""}" placeholder="69.240562">
        <span class="field-hint">Koordinatalarsiz "yaqinimda" qidiruvida chiqmaysiz</span>
      </div>
      <div class="field" style="justify-content:flex-end">
        <button class="btn btn-outline" type="button" id="detect-location">📍 Joriy joylashuvni olish</button>
      </div>
    </div>

    <button class="btn btn-primary" style="align-self:flex-start" type="submit" id="save">Saqlash</button>`;
}

async function loadBusiness() {
  const form = $("#business-form");
  form.innerHTML = skeletonRows(3);
  try {
    const business = await api.owner.business();
    form.innerHTML = formHtml(business);
  } catch (error) {
    form.innerHTML = errorState(error.message);
  }
}

async function loadGallery() {
  const gallery = $("#gallery");
  gallery.innerHTML = skeletonCards(3);
  try {
    const photos = await api.owner.photos();
    gallery.innerHTML = photos.length
      ? photos.map((photo) => `
        <div class="card">
          <img class="card-media card-media-sm" src="${esc(photo.image)}" alt="" loading="lazy">
          <div class="card-body">
            <button class="btn btn-sm btn-danger btn-block" data-delete-photo="${esc(photo.id)}">🗑 O'chirish</button>
          </div>
        </div>`).join("")
      : emptyState("Galereya bo'sh", "Rasm qo'shsangiz detal sahifasida karusel paydo bo'ladi.", "🖼️");
  } catch (error) {
    gallery.innerHTML = errorState(error.message);
  }
}

function init() {
  loadBusiness();
  loadGallery();

  $("#business-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.target;
    const errorBox = $("#form-error");
    errorBox.hidden = true;
    const done = busy($("#save"));

    try {
      const file = form.cover_photo.files[0];
      const values = formValues(form);
      delete values.cover_photo;
      Object.keys(values).forEach((key) => {
        if (values[key] === "") delete values[key];
      });

      await api.owner.updateBusiness(values);

      if (file) {
        const formData = new FormData();
        formData.append("cover_photo", file);
        await api.owner.updateBusiness(formData);
      }
      toast.ok("Sozlamalar saqlandi.");
    } catch (error) {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
    } finally {
      done();
    }
  });

  delegate("#business-form", "#detect-location", () => {
    if (!navigator.geolocation) {
      toast.error("Brauzeringiz joylashuvni qo'llab-quvvatlamaydi.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        $("#latitude").value = coords.latitude.toFixed(6);
        $("#longitude").value = coords.longitude.toFixed(6);
        toast.ok("Joylashuv olindi. Saqlashni unutmang.");
      },
      () => toast.error("Joylashuvga ruxsat berilmadi.")
    );
  });

  $("#photo-input").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("image", file);
    formData.append("order", "0");
    try {
      await api.owner.addPhoto(formData);
      toast.ok("Rasm qo'shildi.");
      loadGallery();
    } catch (error) {
      toast.fromError(error);
    } finally {
      event.target.value = "";
    }
  });

  delegate("#gallery", "[data-delete-photo]", async (button) => {
    const ok = await confirmDialog({
      title: "Rasmni o'chirasizmi?",
      message: "Rasm galereyadan butunlay olib tashlanadi.",
      confirmText: "O'chirish",
      danger: true,
    });
    if (!ok) return;
    try {
      await api.owner.deletePhoto(button.dataset.deletePhoto);
      toast.ok("Rasm o'chirildi.");
      loadGallery();
    } catch (error) {
      toast.fromError(error);
    }
  });
}
