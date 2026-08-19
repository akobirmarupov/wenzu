/**
 * Admin — banner va yangiliklarni boshqarish.
 *
 * Har bir matn uch tilda kiritiladi. O'zbekcha majburiy, qolgani
 * ixtiyoriy: to'ldirilmagan tarjima o'rniga o'zbekchasi ko'rsatiladi,
 * shuning uchun sayt hech qachon bo'sh sarlavha bilan qolmaydi.
 */
import { api } from "../../core/api.js";
import { initAdminPage } from "./shell.js";
import { $, delegate, esc, busy, formValues } from "../../ui/dom.js";
import { skeletonRows, emptyState, errorState } from "../../ui/state.js";
import { openModal, modal, confirmDialog } from "../../ui/modal.js";
import { toast } from "../../ui/toast.js";
import { dateLabel } from "../../ui/format.js";

const LANGS = [
  { code: "uz", label: "O'zbekcha", required: true },
  { code: "ru", label: "Русский" },
  { code: "en", label: "English" },
];

const NEWS_CATEGORIES = [
  { value: "news", label: "Yangilik" },
  { value: "tip", label: "Foydali maslahat" },
  { value: "event", label: "Tadbir" },
  { value: "update", label: "Platforma yangilanishi" },
];

let banners = [];
let newsItems = [];

const user = await initAdminPage();
if (user) init();

/* ---------- umumiy: uch tilli maydonlar ---------- */
function langFields(prefix, item, { textarea = false, label = "" } = {}) {
  return LANGS.map((lang) => {
    const name = `${prefix}_${lang.code}`;
    const value = esc(item?.[name] || "");
    const input = textarea
      ? `<textarea class="textarea" id="${name}" name="${name}" rows="3">${value}</textarea>`
      : `<input class="input" id="${name}" name="${name}" value="${value}">`;
    return `
      <div class="field">
        <label for="${name}">${esc(label)} · ${esc(lang.label)}${lang.required ? " *" : ""}</label>
        ${input}
      </div>`;
  }).join("");
}

/* ---------- bannerlar ---------- */
function bannerRow(banner) {
  return `
    <div class="list-row">
      <div class="stack stack-1" style="min-width:240px">
        <b>${esc(banner.title_uz)}</b>
        <span class="small muted">${esc(banner.placement)} · ${esc(banner.media_type)}
          ${banner.title_ru ? " · RU" : ""}${banner.title_en ? " · EN" : ""}</span>
        ${banner.starts_at || banner.ends_at
          ? `<span class="xs faint">${dateLabel(banner.starts_at)} — ${dateLabel(banner.ends_at)}</span>` : ""}
      </div>
      <div class="list-row-actions">
        ${banner.is_active
          ? '<span class="seal seal-ok">Faol</span>'
          : '<span class="seal seal-bad">O\'chirilgan</span>'}
        <button class="btn btn-sm btn-outline" data-edit-banner="${esc(banner.id)}">Tahrirlash</button>
        <button class="btn btn-sm btn-danger" data-delete-banner="${esc(banner.id)}">🗑</button>
      </div>
    </div>`;
}

function bannerForm(banner) {
  return `
    <h2>${banner ? "Bannerni tahrirlash" : "Yangi banner"}</h2>
    <form class="stack stack-4" id="banner-form" style="margin-top:var(--sp-5)">
      <div class="form-alert" id="banner-error" hidden></div>

      <div class="field-row">
        <div class="field">
          <label for="placement">Joylashuv</label>
          <select class="select" id="placement" name="placement">
            <option value="hero" ${banner?.placement === "hero" ? "selected" : ""}>Bosh banner</option>
            <option value="inline" ${banner?.placement === "inline" ? "selected" : ""}>Sahifa ichida</option>
            <option value="sidebar" ${banner?.placement === "sidebar" ? "selected" : ""}>Yon panelda</option>
          </select>
        </div>
        <div class="field">
          <label for="media_type">Media turi</label>
          <select class="select" id="media_type" name="media_type">
            <option value="none" ${banner?.media_type === "none" ? "selected" : ""}>Faqat matn</option>
            <option value="image" ${banner?.media_type === "image" ? "selected" : ""}>Rasm</option>
            <option value="video" ${banner?.media_type === "video" ? "selected" : ""}>Video</option>
          </select>
        </div>
        <div class="field">
          <label for="order">Tartib</label>
          <input class="input" id="order" name="order" type="number" min="0" value="${banner?.order ?? 0}">
        </div>
      </div>

      <div class="field">
        <label for="image">Rasm (media turi «Rasm» bo'lsa)</label>
        <input class="input" id="image" name="image" type="file" accept="image/*">
      </div>
      <div class="field">
        <label for="video_url">Video havolasi (media turi «Video» bo'lsa)</label>
        <input class="input" id="video_url" name="video_url" value="${esc(banner?.video_url || "")}"
               placeholder="https://.../reklama.mp4">
      </div>

      ${langFields("title", banner, { label: "Sarlavha" })}
      ${langFields("subtitle", banner, { label: "Yuqori yozuv" })}
      ${langFields("body", banner, { textarea: true, label: "Matn" })}
      ${langFields("cta_label", banner, { label: "Tugma matni" })}

      <div class="field-row">
        <div class="field">
          <label for="cta_url">Tugma havolasi</label>
          <input class="input" id="cta_url" name="cta_url" value="${esc(banner?.cta_url || "")}"
                 placeholder="/restoranlar/">
        </div>
        <div class="field">
          <label for="starts_at">Boshlanish (ixtiyoriy)</label>
          <input class="input" id="starts_at" name="starts_at" type="datetime-local"
                 value="${(banner?.starts_at || "").slice(0, 16)}">
        </div>
        <div class="field">
          <label for="ends_at">Tugash (ixtiyoriy)</label>
          <input class="input" id="ends_at" name="ends_at" type="datetime-local"
                 value="${(banner?.ends_at || "").slice(0, 16)}">
        </div>
      </div>

      <label class="checkbox">
        <input type="checkbox" id="is_active" name="is_active" ${banner?.is_active !== false ? "checked" : ""}>
        <span>Faol (saytda ko'rinadi)</span>
      </label>

      <button class="btn btn-primary btn-block btn-lg" type="submit" id="banner-submit">
        ${banner ? "Saqlash" : "Qo'shish"}
      </button>
    </form>`;
}

function openBannerForm(banner) {
  const node = openModal(bannerForm(banner), { wide: true });
  const form = node.querySelector("#banner-form");
  const errorBox = node.querySelector("#banner-error");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.hidden = true;
    const done = busy(node.querySelector("#banner-submit"));

    try {
      const file = form.image.files[0];
      const values = formValues(form);
      delete values.image;
      values.is_active = form.is_active.checked;
      ["starts_at", "ends_at"].forEach((key) => {
        if (!values[key]) delete values[key];
      });

      const saved = banner
        ? await api.admin.updateBanner(banner.id, values)
        : await api.admin.createBanner(values);

      if (file) {
        const formData = new FormData();
        formData.append("image", file);
        await api.admin.updateBanner(saved.id, formData);
      }

      modal.close();
      toast.ok(banner ? "Banner yangilandi." : "Banner qo'shildi.");
      loadBanners();
    } catch (error) {
      errorBox.textContent = error.fieldError?.("title_uz") || error.message;
      errorBox.hidden = false;
    } finally {
      done();
    }
  });
}

async function loadBanners() {
  const container = $("#banner-list");
  container.innerHTML = skeletonRows(2);
  try {
    const data = await api.admin.banners({ page_size: 50 });
    banners = data.results;
    container.innerHTML = banners.length
      ? banners.map(bannerRow).join("")
      : emptyState("Banner yo'q", "Bosh sahifada banner ko'rinishi uchun bittasini qo'shing.", "📢");
  } catch (error) {
    container.innerHTML = errorState(error.message);
  }
}

/* ---------- yangiliklar ---------- */
function newsRow(item) {
  return `
    <div class="list-row">
      <div class="stack stack-1" style="min-width:240px">
        <b>${item.is_pinned ? "📌 " : ""}${esc(item.title_uz)}</b>
        <span class="small muted">${esc(item.category)}
          ${item.title_ru ? " · RU" : ""}${item.title_en ? " · EN" : ""} · ${dateLabel(item.created_at)}</span>
      </div>
      <div class="list-row-actions">
        ${item.is_active
          ? '<span class="seal seal-ok">Faol</span>'
          : '<span class="seal seal-bad">O\'chirilgan</span>'}
        <button class="btn btn-sm btn-outline" data-edit-news="${esc(item.id)}">Tahrirlash</button>
        <button class="btn btn-sm btn-danger" data-delete-news="${esc(item.id)}">🗑</button>
      </div>
    </div>`;
}

function newsForm(item) {
  return `
    <h2>${item ? "Yangilikni tahrirlash" : "Yangi yangilik"}</h2>
    <form class="stack stack-4" id="news-form" style="margin-top:var(--sp-5)">
      <div class="form-alert" id="news-error" hidden></div>

      <div class="field-row">
        <div class="field">
          <label for="category">Turkum</label>
          <select class="select" id="category" name="category">
            ${NEWS_CATEGORIES.map((c) => `<option value="${c.value}"
              ${item?.category === c.value ? "selected" : ""}>${esc(c.label)}</option>`).join("")}
          </select>
        </div>
        <div class="field">
          <label for="order">Tartib</label>
          <input class="input" id="order" name="order" type="number" min="0" value="${item?.order ?? 0}">
        </div>
        <div class="field">
          <label for="cover">Rasm</label>
          <input class="input" id="cover" name="cover" type="file" accept="image/*">
        </div>
      </div>

      ${langFields("title", item, { label: "Sarlavha" })}
      ${langFields("excerpt", item, { label: "Qisqacha" })}
      ${langFields("body", item, { textarea: true, label: "To'liq matn" })}

      <div class="field">
        <label for="link_url">Havola (ixtiyoriy)</label>
        <input class="input" id="link_url" name="link_url" value="${esc(item?.link_url || "")}">
      </div>

      <div class="row row-4 row-wrap">
        <label class="checkbox">
          <input type="checkbox" id="is_active" name="is_active" ${item?.is_active !== false ? "checked" : ""}>
          <span>Faol</span>
        </label>
        <label class="checkbox">
          <input type="checkbox" id="is_pinned" name="is_pinned" ${item?.is_pinned ? "checked" : ""}>
          <span>📌 Mahkamlash (birinchi turadi)</span>
        </label>
      </div>

      <button class="btn btn-primary btn-block btn-lg" type="submit" id="news-submit">
        ${item ? "Saqlash" : "Qo'shish"}
      </button>
    </form>`;
}

function openNewsForm(item) {
  const node = openModal(newsForm(item), { wide: true });
  const form = node.querySelector("#news-form");
  const errorBox = node.querySelector("#news-error");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.hidden = true;
    const done = busy(node.querySelector("#news-submit"));

    try {
      const file = form.cover.files[0];
      const values = formValues(form);
      delete values.cover;
      values.is_active = form.is_active.checked;
      values.is_pinned = form.is_pinned.checked;

      const saved = item
        ? await api.admin.updateNews(item.id, values)
        : await api.admin.createNews(values);

      if (file) {
        const formData = new FormData();
        formData.append("cover", file);
        await api.admin.updateNews(saved.id, formData);
      }

      modal.close();
      toast.ok(item ? "Yangilik yangilandi." : "Yangilik qo'shildi.");
      loadNews();
    } catch (error) {
      errorBox.textContent = error.fieldError?.("title_uz") || error.message;
      errorBox.hidden = false;
    } finally {
      done();
    }
  });
}

async function loadNews() {
  const container = $("#news-list");
  container.innerHTML = skeletonRows(3);
  try {
    const data = await api.admin.news({ page_size: 50 });
    newsItems = data.results;
    container.innerHTML = newsItems.length
      ? newsItems.map(newsRow).join("")
      : emptyState("Yangilik yo'q", "Bosh sahifadagi lenta bo'sh qolmasligi uchun qo'shing.", "📰");
  } catch (error) {
    container.innerHTML = errorState(error.message);
  }
}

/* ---------- bog'lash ---------- */
function init() {
  $("#add-banner").addEventListener("click", () => openBannerForm(null));
  $("#add-news").addEventListener("click", () => openNewsForm(null));

  delegate("#banner-list", "[data-edit-banner]", (button) => {
    const banner = banners.find((b) => b.id === button.dataset.editBanner);
    if (banner) openBannerForm(banner);
  });
  delegate("#news-list", "[data-edit-news]", (button) => {
    const item = newsItems.find((n) => n.id === button.dataset.editNews);
    if (item) openNewsForm(item);
  });

  delegate("#banner-list", "[data-delete-banner]", async (button) => {
    const ok = await confirmDialog({
      title: "Bannerni o'chirasizmi?", message: "Bu amalni qaytarib bo'lmaydi.",
      confirmText: "O'chirish", danger: true,
    });
    if (!ok) return;
    try {
      await api.admin.deleteBanner(button.dataset.deleteBanner);
      toast.ok("Banner o'chirildi.");
      loadBanners();
    } catch (error) {
      toast.fromError(error);
    }
  });

  delegate("#news-list", "[data-delete-news]", async (button) => {
    const ok = await confirmDialog({
      title: "Yangilikni o'chirasizmi?", message: "Bu amalni qaytarib bo'lmaydi.",
      confirmText: "O'chirish", danger: true,
    });
    if (!ok) return;
    try {
      await api.admin.deleteNews(button.dataset.deleteNews);
      toast.ok("Yangilik o'chirildi.");
      loadNews();
    } catch (error) {
      toast.fromError(error);
    }
  });

  loadBanners();
  loadNews();
}
