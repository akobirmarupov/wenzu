/** Panel — to'yxona zallari va taom paketi narxlari. */
import { api } from "../../core/api.js";
import { initOwnerPage } from "./shell.js";
import { $, render, delegate, esc, busy, formValues } from "../../ui/dom.js";
import { skeletonCards, emptyState, errorState } from "../../ui/state.js";
import { openModal, modal, confirmDialog } from "../../ui/modal.js";
import { toast } from "../../ui/toast.js";
import { money, imageUrl } from "../../ui/format.js";

const session = await initOwnerPage();
if (session) {
  if (session.businessType !== "venue") {
    window.location.replace("/panel/xonalar/");
  } else {
    init();
  }
}

let halls = [];

function card(hall) {
  return `
    <div class="card">
      <img class="card-media card-media-sm" src="${esc(imageUrl(hall.photo))}" alt="" loading="lazy">
      <div class="card-body">
        <b>${esc(hall.name)}</b>
        <span class="small muted">${hall.people} kishigacha</span>
        <span class="seal seal-gold" style="align-self:flex-start">Depozit: ${money(hall.deposit_amount)}</span>
        <div class="row row-2" style="margin-top:var(--sp-2)">
          <button class="btn btn-sm btn-outline" style="flex:1" data-edit="${esc(hall.id)}">Tahrirlash</button>
          <button class="btn btn-sm btn-danger" data-delete="${esc(hall.id)}" aria-label="O'chirish">🗑</button>
        </div>
      </div>
    </div>`;
}

function formHtml(hall) {
  return `
    <h2>${hall ? "Zalni tahrirlash" : "Yangi zal"}</h2>
    <form class="stack stack-4" id="hall-form" style="margin-top:var(--sp-5)" novalidate>
      <div class="form-alert" id="hall-error" hidden></div>

      <div class="field-row">
        <div class="field">
          <label for="name">Zal nomi</label>
          <input class="input" id="name" name="name" required value="${esc(hall?.name || "")}"
                 placeholder="Masalan: Katta zal">
        </div>
        <div class="field">
          <label for="people">Sig'imi (kishi)</label>
          <input class="input" id="people" name="people" type="number" min="1" required
                 value="${hall?.people || ""}" placeholder="500">
        </div>
      </div>

      <div class="field-row">
        <div class="field">
          <label for="deposit_price">Depozit (ixtiyoriy)</label>
          <input class="input" id="deposit_price" name="deposit_price" type="number" min="0"
                 value="${hall?.deposit_price || ""}" placeholder="Bo'sh — platforma standarti">
        </div>
        <div class="field">
          <label for="package">Bezak paketi (ixtiyoriy)</label>
          <input class="input" id="package" name="package" value="${esc(hall?.package || "")}"
                 placeholder="Masalan: Standart bezak">
        </div>
      </div>

      <div class="field">
        <label for="photo">Rasm (ixtiyoriy)</label>
        <input class="input" id="photo" name="photo" type="file" accept="image/*">
      </div>

      <button class="btn btn-primary btn-block btn-lg" type="submit" id="hall-submit">
        ${hall ? "Saqlash" : "Qo'shish"}
      </button>
    </form>`;
}

function openForm(hall) {
  const node = openModal(formHtml(hall));
  const form = node.querySelector("#hall-form");
  const errorBox = node.querySelector("#hall-error");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.hidden = true;
    const done = busy(node.querySelector("#hall-submit"));

    try {
      const file = form.photo.files[0];
      const values = formValues(form);
      delete values.photo;
      if (!values.deposit_price) delete values.deposit_price;
      if (!values.package) delete values.package;

      const saved = hall
        ? await api.owner.updateHall(hall.id, values)
        : await api.owner.createHall(values);

      if (file) {
        const formData = new FormData();
        formData.append("photo", file);
        await api.owner.updateHall(saved.id, formData);
      }

      modal.close();
      toast.ok(hall ? "Zal yangilandi." : "Zal qo'shildi.");
      load();
    } catch (error) {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
    } finally {
      done();
    }
  });
}

/* ---------- narx paketlari ---------- */
async function loadPricing() {
  try {
    const rows = await api.owner.pricing();
    const byCount = Object.fromEntries(rows.map((row) => [row.dish_count, row.price_per_person]));

    render("#pricing-fields", [1, 2, 3].map((n) => `
      <div class="field">
        <label for="price-${n}">${n} xil taom (kishi boshiga)</label>
        <input class="input" id="price-${n}" name="price-${n}" type="number" min="0"
               value="${byCount[n] ? Math.round(byCount[n]) : ""}" placeholder="0">
      </div>`).join(""));
  } catch (error) {
    render("#pricing-fields", `<p class="form-alert">${esc(error.message)}</p>`);
  }
}

function init() {
  $("#add-hall").addEventListener("click", () => openForm(null));

  delegate("#list", "[data-edit]", (button) => {
    const hall = halls.find((h) => h.id === button.dataset.edit);
    if (hall) openForm(hall);
  });

  delegate("#list", "[data-delete]", async (button) => {
    const ok = await confirmDialog({
      title: "Zalni o'chirasizmi?",
      message: "Faol bronlari bo'lsa o'chirilmaydi.",
      confirmText: "O'chirish",
      danger: true,
    });
    if (!ok) return;
    try {
      await api.owner.deleteHall(button.dataset.delete);
      toast.ok("Zal o'chirildi.");
      load();
    } catch (error) {
      toast.fromError(error);
    }
  });

  $("#pricing-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const done = busy($("#pricing-submit"));
    try {
      const rows = [1, 2, 3]
        .map((n) => ({ dish_count: n, price_per_person: $(`#price-${n}`).value }))
        .filter((row) => row.price_per_person !== "" && Number(row.price_per_person) > 0);

      if (!rows.length) {
        toast.error("Kamida bitta paket narxini kiriting.");
        return;
      }
      await api.owner.savePricing(rows);
      toast.ok("Narxlar saqlandi.");
    } catch (error) {
      toast.fromError(error);
    } finally {
      done();
    }
  });

  load();
  loadPricing();
}

async function load() {
  $("#list").innerHTML = skeletonCards(3);
  try {
    const data = await api.owner.halls({ page_size: 100 });
    halls = data.results;
    $("#list").innerHTML = halls.length
      ? halls.map(card).join("")
      : emptyState("Zallar yo'q", "Birinchi zalingizni qo'shing.", "🏛️");
  } catch (error) {
    $("#list").innerHTML = errorState(error.message);
  }
}
