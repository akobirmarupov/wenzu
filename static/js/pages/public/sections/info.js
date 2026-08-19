/** Profil — "Ma'lumotlarim" bo'limi. */
import { api } from "../../../core/api.js";
import { auth } from "../../../core/auth.js";
import { t } from "../../../core/i18n.js";
import { $, esc, busy, formValues } from "../../../ui/dom.js";
import { toast } from "../../../ui/toast.js";
import { dateLabel } from "../../../ui/format.js";

export function roleName(user) {
  if (user.is_staff) return t("panel.roleAdmin");
  if (user.business?.type === "venue") return t("panel.roleVenue");
  if (user.business?.type === "restaurant") return t("panel.roleRestaurant");
  return t("profile.roleUser");
}

export function render(user) {
  return `
    <div class="panel">
      <div class="panel-head">
        <h2 class="display h3">${esc(t("profile.personalInfo"))}</h2>
      </div>

      <form class="stack stack-4" id="profile-form">
        <div class="form-alert" id="profile-error" hidden></div>

        <div class="field-row">
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
        </div>

        <div class="field">
          <label for="bio">${esc(t("profile.bio"))}</label>
          <input class="input" id="bio" name="bio" maxlength="200"
                 value="${esc(user.bio || "")}"
                 placeholder="${esc(t("profile.bioPlaceholder"))}">
        </div>

        <button class="btn btn-primary" style="align-self:flex-start"
                type="submit" id="save-profile">${esc(t("profile.save"))}</button>
      </form>
    </div>

    <div class="panel">
      <div class="panel-head">
        <h2 class="display h3">${esc(t("profile.account"))}</h2>
      </div>
      <div class="info-row">
        <span class="k">${esc(t("auth.username"))}</span>
        <span class="v mono">${esc(user.username)}</span>
      </div>
      <div class="info-row">
        <span class="k">${esc(t("auth.phone"))}</span>
        <span class="v mono">${esc(user.phone_number)}
          ${user.is_phone_verified
            ? `<span class="seal seal-ok" style="margin-left:8px">${esc(t("profile.verified"))}</span>`
            : `<span class="seal seal-warn" style="margin-left:8px">${esc(t("profile.notVerified"))}</span>`}
        </span>
      </div>
      <div class="info-row">
        <span class="k">${esc(t("profile.role"))}</span>
        <span class="v">${esc(roleName(user))}</span>
      </div>
      <div class="info-row">
        <span class="k">${esc(t("profile.memberSince"))}</span>
        <span class="v">${dateLabel(user.date_joined)}</span>
      </div>
      <p class="field-hint" style="margin-top:var(--sp-4)">${esc(t("profile.idHint"))}</p>
    </div>`;
}

export function bind({ onUpdated }) {
  $("#profile-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const errorBox = $("#profile-error");
    errorBox.hidden = true;
    const done = busy($("#save-profile"));

    try {
      const values = formValues(event.target);
      if (!values.birth_date) delete values.birth_date;
      await api.auth.updateMe(values);
      const fresh = await auth.refreshUser();
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
