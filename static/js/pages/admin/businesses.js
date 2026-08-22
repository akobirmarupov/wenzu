/**
 * Admin — bizneslarni to'liq boshqarish.
 *
 * Admin bu yerda hamma narsani qila oladi: yangi biznes ochish,
 * ma'lumotini tahrirlash, bloklash va butunlay o'chirish.
 *
 * Bloklash va o'chirish ATAYLAB ikki xil amal:
 *   bloklash  — qaytariladi, biznes qidiruvdan yo'qoladi, ma'lumot qoladi
 *   o'chirish — qaytarilmaydi, xona/menyu/sharh/bron ham ketadi
 * Shuning uchun faol broni bor biznesni server o'chirishga ruxsat
 * bermaydi va bloklashni taklif qiladi.
 */
import { api } from "../../core/api.js";
import { ROUTES } from "../../core/config.js";
import { initAdminPage } from "./shell.js";
import { $, render, delegate, esc, busy } from "../../ui/dom.js";
import { skeletonRows, errorState } from "../../ui/state.js";
import { paginationHtml } from "../../ui/pagination.js";
import { confirmDialog, openModal, modal } from "../../ui/modal.js";
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

/* ===================================================================
   Yangi biznes ochish
   =================================================================== */

/**
 * Egasi bo'ladigan foydalanuvchini tanlash uchun ro'yxat.
 *
 * Faqat hali biznesi yo'qlar chiqadi — bitta egada bitta biznes,
 * panel menyusi va obuna ham shu qoidaga tayanadi.
 */
async function selectableOwners() {
  const [plain, owners] = await Promise.all([
    api.admin.users({ role: "user", page_size: 100 }),
    api.admin.users({ role: "business", page_size: 100 }),
  ]);
  const busyOwners = new Set(
    (owners.results || []).filter((row) => row.has_business).map((row) => row.id)
  );
  return [...(plain.results || []), ...(owners.results || [])].filter(
    (row) => !busyOwners.has(row.id)
  );
}

async function openCreateModal() {
  let people = [];
  try {
    people = await selectableOwners();
  } catch (error) {
    toast.fromError(error);
    return;
  }

  if (!people.length) {
    toast.error("Biznesi yo'q foydalanuvchi topilmadi. Avval foydalanuvchi ro'yxatdan o'tsin.");
    return;
  }

  const node = openModal(
    `<h2>Yangi biznes ochish</h2>
     <p class="muted small" style="margin-bottom:var(--sp-5)">
       Biznes tanlangan foydalanuvchi nomiga ochiladi va uning roli
       avtomatik "biznes egasi"ga o'tadi. 7 kunlik bepul sinov ham
       shu zahoti boshlanadi.
     </p>

     <form class="stack stack-4" id="biz-form" novalidate>
       <div class="form-alert" id="biz-error" hidden></div>

       <div class="field">
         <label for="owner">Egasi</label>
         <select class="select" id="owner" name="owner" required>
           ${people.map((row) => `
             <option value="${esc(String(row.id))}">
               ${esc(row.full_name || row.username)} — ${esc(row.phone_number)}
             </option>`).join("")}
         </select>
       </div>

       <div class="field-row">
         <div class="field">
           <label for="business_type">Turi</label>
           <select class="select" id="business_type" name="business_type">
             <option value="restaurant">Restoran</option>
             <option value="venue">To'yxona</option>
           </select>
         </div>
         <div class="field">
           <label for="name">Nomi</label>
           <input class="input" id="name" name="name" required placeholder="Masalan: Bahor Taomxonasi">
         </div>
       </div>

       <div class="field-row">
         <div class="field">
           <label for="district">Tuman</label>
           <input class="input" id="district" name="district" placeholder="Yunusobod">
         </div>
         <div class="field">
           <label for="telegram_username">Telegram</label>
           <input class="input" id="telegram_username" name="telegram_username" placeholder="@ belgisiz">
         </div>
       </div>

       <div class="field">
         <label for="address">Manzil</label>
         <input class="input" id="address" name="address" placeholder="Ko'cha, uy raqami">
       </div>

       <label class="chip" style="cursor:pointer;align-self:flex-start">
         <input type="checkbox" id="approve" name="approve" style="margin-right:8px" checked>
         Arizani darhol tasdiqlash (obuna 30 kunga faollashadi)
       </label>

       <button class="btn btn-primary btn-block btn-lg" type="submit" id="biz-submit">
         Biznesni ochish
       </button>
     </form>`,
    { wide: true }
  );

  const form = node.querySelector("#biz-form");
  const errorBox = node.querySelector("#biz-error");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.hidden = true;
    const done = busy(node.querySelector("#biz-submit"));
    try {
      await api.admin.createBusiness({
        owner: Number(form.owner.value),
        business_type: form.business_type.value,
        name: form.name.value.trim(),
        district: form.district.value.trim(),
        address: form.address.value.trim(),
        telegram_username: form.telegram_username.value.trim(),
        approve: form.approve.checked,
      });
      modal.close();
      toast.ok("Biznes ochildi.");
      filters.page = 1;
      load();
    } catch (error) {
      errorBox.textContent =
        error.fieldError?.("owner") || error.fieldError?.("name") || error.message;
      errorBox.hidden = false;
    } finally {
      done();
    }
  });
}

/* ===================================================================
   Tahrirlash
   =================================================================== */
function openEditModal(business) {
  const node = openModal(
    `<h2>Biznesni tahrirlash</h2>
     <form class="stack stack-4" id="edit-form" novalidate>
       <div class="form-alert" id="edit-error" hidden></div>

       <div class="field">
         <label for="e-name">Nomi</label>
         <input class="input" id="e-name" name="name" required value="${esc(business.name || "")}">
       </div>

       <div class="field-row">
         <div class="field">
           <label for="e-type">Turi</label>
           <select class="select" id="e-type" name="business_type">
             <option value="restaurant" ${business.business_type === "restaurant" ? "selected" : ""}>Restoran</option>
             <option value="venue" ${business.business_type === "venue" ? "selected" : ""}>To'yxona</option>
           </select>
         </div>
         <div class="field">
           <label for="e-district">Tuman</label>
           <input class="input" id="e-district" name="district" value="${esc(business.district || "")}">
         </div>
       </div>

       <div class="field">
         <label for="e-address">Manzil</label>
         <input class="input" id="e-address" name="address" value="${esc(business.address || "")}">
       </div>

       <button class="btn btn-primary btn-block btn-lg" type="submit" id="edit-submit">Saqlash</button>
     </form>`,
    { wide: true }
  );

  const form = node.querySelector("#edit-form");
  const errorBox = node.querySelector("#edit-error");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.hidden = true;
    const done = busy(node.querySelector("#edit-submit"));
    try {
      await api.admin.updateBusiness(business.id, {
        name: form.name.value.trim(),
        business_type: form.business_type.value,
        district: form.district.value.trim(),
        address: form.address.value.trim(),
      });
      modal.close();
      toast.ok("Saqlandi.");
      load();
    } catch (error) {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
    } finally {
      done();
    }
  });
}

/* ===================================================================
   Sahifa
   =================================================================== */
let rows = [];

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

  $("#add-business").addEventListener("click", openCreateModal);

  delegate("#list", "[data-edit]", (button) => {
    const business = rows.find((item) => item.id === button.dataset.edit);
    if (business) openEditModal(business);
  });

  delegate("#list", "[data-toggle]", async (button) => {
    const willBlock = button.dataset.visible === "true";
    const ok = await confirmDialog({
      title: willBlock ? "Biznesni bloklaysizmi?" : "Blokdan chiqarasizmi?",
      message: willBlock
        ? "Bloklangan biznes ommaviy qidiruvda ko'rinmaydi va yangi bron qabul qilmaydi. Ma'lumotlari saqlanib qoladi."
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

  delegate("#list", "[data-delete]", async (button) => {
    const name = button.dataset.name || "";
    const ok = await confirmDialog({
      title: "Butunlay o'chirasizmi?",
      message: `"${name}" bilan birga uning xonalari, menyusi, sharhlari va bron `
             + `tarixi ham o'chadi. Buni QAYTARIB BO'LMAYDI. Vaqtincha yopish uchun `
             + `"Bloklash" tugmasidan foydalaning.`,
      confirmText: "O'chirish",
      danger: true,
    });
    if (!ok) return;

    const done = busy(button);
    try {
      await api.admin.deleteBusiness(button.dataset.delete);
      toast.ok("Biznes o'chirildi.");
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
        <div class="row row-2" style="justify-content:flex-end">
          <button class="btn btn-sm btn-outline" data-edit="${esc(business.id)}">Tahrirlash</button>
          <button class="btn btn-sm ${business.is_visible ? "btn-outline" : "btn-primary"}"
            data-toggle="${esc(business.id)}" data-visible="${business.is_visible}">
            ${business.is_visible ? "Bloklash" : "Ochish"}
          </button>
          <button class="btn btn-sm btn-danger" data-delete="${esc(business.id)}"
                  data-name="${esc(business.name)}">🗑</button>
        </div>
      </td>
    </tr>`;
}

async function load() {
  $("#list").innerHTML = `<tr><td colspan="6">${skeletonRows(4)}</td></tr>`;
  $("#pager").innerHTML = "";
  try {
    const data = await api.admin.businesses({ ...filters, page_size: 20 });
    rows = data.results || [];
    $("#list").innerHTML = rows.length
      ? rows.map(row).join("")
      : `<tr><td colspan="6"><p class="muted center" style="padding:var(--sp-8)">Biznes topilmadi</p></td></tr>`;
    $("#pager").innerHTML = paginationHtml(data);
  } catch (error) {
    $("#list").innerHTML = `<tr><td colspan="6">${errorState(error.message)}</td></tr>`;
  }
}
