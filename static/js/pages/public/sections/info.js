/**
 * Profil — "Ma'lumotlarim" bo'limi.
 *
 * BITTA RAMKA. Ilgari bu bo'lim ikkiga bo'lingan edi: yuqorida
 * tahrirlash shakli, pastda o'zgartirib bo'lmaydigan "hisob
 * ma'lumotlari". Natijada bir xil odam haqidagi ma'lumot ikki joyda
 * turardi va foydalanuvchi "ismim qayerda yozilgan?" deb ikkalasini
 * ham o'qib chiqishi kerak edi.
 *
 * Endi hammasi bitta kartochkada, faqat O'QISH uchun. Tahrirlash
 * ramkaning chetidagi qalamcha orqali — alohida oynada ochiladi.
 * Shunda ekran tinch turadi: odam odatda ma'lumotini KO'RISH uchun
 * kiradi, tahrirlash esa ancha kam uchraydigan amal.
 */
import { api } from "../../../core/api.js";
import { auth } from "../../../core/auth.js";
import { t } from "../../../core/i18n.js";
import { $, esc, busy, formValues } from "../../../ui/dom.js";
import { modal } from "../../../ui/modal.js";
import { toast } from "../../../ui/toast.js";
import { dateLabel } from "../../../ui/format.js";

export function roleName(user) {
  if (user.is_staff) return t("panel.roleAdmin");
  if (user.business?.type === "venue") return t("panel.roleVenue");
  if (user.business?.type === "restaurant") return t("panel.roleRestaurant");
  return t("profile.roleUser");
}

/** Bitta qator: chapda nomi, o'ngda qiymati. */
function row(label, value, { mono = false, extra = "" } = {}) {
  return `
    <div class="info-row">
      <span class="k">${esc(label)}</span>
      <span class="v ${mono ? "mono" : ""}">${value}${extra}</span>
    </div>`;
}

export function render(user) {
  const phoneSeal = user.is_phone_verified
    ? `<span class="seal seal-ok" style="margin-left:8px">${esc(t("profile.verified"))}</span>`
    : `<span class="seal seal-warn" style="margin-left:8px">${esc(t("profile.notVerified"))}</span>`;

  return `
    <div class="panel">
      <div class="panel-head">
        <h2 class="display h3">${esc(t("profile.personalInfo"))}</h2>
        <button class="icon-btn" type="button" id="edit-profile"
                title="${esc(t("profile.edit"))}" aria-label="${esc(t("profile.edit"))}">✏️</button>
      </div>

      ${row(t("auth.fullName"), esc(user.full_name || "—"))}
      ${row(t("auth.username"), esc(user.username), { mono: true })}
      ${row(t("auth.phone"), esc(user.phone_number), { mono: true, extra: phoneSeal })}
      ${row(t("profile.role"), esc(roleName(user)))}
      ${row(t("profile.birthDate"), user.birth_date ? dateLabel(user.birth_date) : "—")}
      ${row(t("profile.bio"), esc(user.bio || "—"))}
      ${row(t("profile.memberSince"), dateLabel(user.date_joined))}

      <p class="field-hint" style="margin-top:var(--sp-4)">${esc(t("profile.idHint"))}</p>
    </div>`;
}

/** Qalamcha bosilganda ochiladigan tahrirlash oynasi. */
function openEditor(user, onUpdated) {
  const node = modal.open(`
    <h2 class="display h3">${esc(t("profile.editTitle"))}</h2>
    <p class="muted small">${esc(t("profile.idHint"))}</p>

    <form class="stack stack-4" id="profile-form" style="margin-top:var(--sp-5)">
      <div class="form-alert" id="profile-error" hidden></div>

      <div class="field">
        <label for="full_name">${esc(t("auth.fullName"))}</label>
        <input class="input" id="full_name" name="full_name" required
               value="${esc(user.full_name || "")}">
      </div>

      <div class="field">
        <label for="birth_date">${esc(t("profile.birthDate"))}</label>
        <input class="input" id="birth_date" name="birth_date" type="date"
               value="${esc(user.birth_date || "")}">
      </div>

      <div class="field">
        <label for="bio">${esc(t("profile.bio"))}</label>
        <input class="input" id="bio" name="bio" maxlength="200"
               value="${esc(user.bio || "")}"
               placeholder="${esc(t("profile.bioPlaceholder"))}">
      </div>

      <div class="row row-2" style="margin-top:var(--sp-2)">
        <button class="btn btn-outline" style="flex:1" type="button" data-modal-close>
          ${esc(t("profile.cancel"))}
        </button>
        <button class="btn btn-primary" style="flex:1" type="submit" id="save-profile">
          ${esc(t("profile.save"))}
        </button>
      </div>
    </form>`);

  node.querySelector("#profile-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const errorBox = node.querySelector("#profile-error");
    errorBox.hidden = true;
    const done = busy(node.querySelector("#save-profile"));

    try {
      const values = formValues(event.target);
      // Bo'sh sana yuborilsa server "noto'g'ri format" deydi — maydonni
      // umuman jo'natmaymiz, ya'ni "tegilmadi" degani.
      if (!values.birth_date) delete values.birth_date;
      await api.auth.updateMe(values);
      const fresh = await auth.refreshUser();
      modal.close();
      toast.ok(t("profile.saved"));
      onUpdated?.(fresh);
    } catch (error) {
      errorBox.textContent = error.fieldError?.("full_name") || error.message;
      errorBox.hidden = false;
    } finally {
      done();
    }
  });
}

export function bind({ user, onUpdated }) {
  $("#edit-profile")?.addEventListener("click", () => openEditor(user, onUpdated));
}
