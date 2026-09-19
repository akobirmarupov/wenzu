/**
 * Profil — "Ma'lumotlarim" bo'limi.
 *
 * BITTA RAMKA. Ilgari bu bo'lim ikkiga bo'lingan edi: yuqorida
 * tahrirlash shakli, pastda o'zgartirib bo'lmaydigan "hisob
 * ma'lumotlari". Natijada bir xil odam haqidagi ma'lumot ikki joyda
 * turardi va foydalanuvchi "ismim qayerda yozilgan?" deb ikkalasini
 * ham o'qib chiqishi kerak edi.
 *
 * Endi hammasi O'QISH uchun, tahrirlash esa alohida oynada. Shunda
 * ekran tinch turadi: odam odatda ma'lumotini KO'RISH uchun kiradi,
 * tahrirlash ancha kam uchraydigan amal.
 *
 * ===================================================================
 * NEGA QATOR EMAS, KATAK
 * ===================================================================
 * Ilgari har bir maydon butun enni egallagan alohida qator edi:
 * chapda nomi, o'ngda qiymati, orada uzun bo'shliq. Sakkizta maydon
 * sakkizta qator degani — ekranning yarmi. Endi ular ikki ustunli
 * katakda: nomi ustida kichik, qiymati ostida. Bir xil ma'lumot ikki
 * baravar kam joy egallaydi va ko'z chapdan o'ngga sakrab yurmaydi.
 */
import { api } from "../../../core/api.js";
import { auth } from "../../../core/auth.js";
import { t } from "../../../core/i18n.js";
import { esc, busy, formValues } from "../../../ui/dom.js";
import { modal } from "../../../ui/modal.js";
import { icon } from "../../../ui/icons.js";
import { toast } from "../../../ui/toast.js";
import { dateLabel, trustSeal, trustBar } from "../../../ui/format.js";

/**
 * Profildagi rol yozuvi.
 *
 * "Restoran egasi" / "To'yxona egasi" — faqat ARIZA TASDIQLANGANDAN
 * keyin. Ilgari ariza yuborilishi bilan shu yozuv paydo bo'lardi va
 * ariza rad etilgandan keyin ham qolib ketardi: odam profilida "Restoran
 * egasi" deb turardi, lekin hech qanday joyi yo'q edi. Tekshirilmagan
 * ariza — hali egalik emas.
 */
export function roleName(user) {
  if (user.is_staff) return t("panel.roleAdmin");
  if (user.business?.is_approved) {
    if (user.business.type === "venue") return t("panel.roleVenue");
    if (user.business.type === "restaurant") return t("panel.roleRestaurant");
  }
  return t("profile.roleUser");
}

/**
 * Bitta katak: ustida nomi, ostida qiymati.
 *
 * Qiymat bo'sh bo'lsa "—" emas, "Qo'shish" havolasi chiqadi. Chiziqcha
 * faqat "bu yerda hech narsa yo'q" deb turardi; havola esa nima qilish
 * kerakligini ko'rsatadi va bir bosishda tahrirlash oynasini ochadi.
 */
function cell(label, value, { mono = false, wide = false, addField = "" } = {}) {
  const empty = !value;
  const body = empty && addField
    ? `<button class="cell-add" type="button" data-edit-profile data-focus="${esc(addField)}">
         ${icon("plus", { size: 14 })} ${esc(t("common.add"))}
       </button>`
    : `<span class="cell-value${mono ? " mono" : ""}">${value || "—"}</span>`;

  return `
    <div class="info-cell${wide ? " is-wide" : ""}">
      <span class="cell-label">${esc(label)}</span>
      ${body}
    </div>`;
}

/**
 * Ishonchlilik kartochkasi — bal, daraja va chiziq.
 *
 * Nima uchun profilda ko'rinadi: bal joy egasiga ko'rinadi va u shunga
 * qarab bronni tasdiqlaydi yoki rad etadi. Egasi ko'radigan, lekin
 * odamning o'zi ko'rmaydigan baho — yashirin qora ro'yxat bo'lardi.
 * Ko'rinib turgan bal esa o'zi ogohlantiruvchi vazifasini bajaradi.
 *
 * Sahifaning YON ustunida, alohida kartochkada. Alohida, chunki bu
 * YAGONA o'zgarib turadigan ko'rsatkich:
 * qolgan maydonlar odamning o'zi kiritgan ma'lumot, bu esa uning
 * platformadagi xulqi. Ikkalasini aralashtirsak, bal oddiy qator bo'lib
 * ko'zga tashlanmay qolardi.
 *
 * Eski javobda `trust` bo'lmasligi mumkin (keshlangan sahifa) — u
 * holda kartochka umuman chizilmaydi.
 */
export function aside(user) {
  const trust = user.trust;
  if (!trust?.bits) return "";

  return `
    <section class="panel trust-card">
      <h2 class="display h3">${esc(t("profile.trust"))}</h2>
      <div class="trust-body">
        ${trustSeal(trust)}
        ${trustBar(trust)}
      </div>
      <p class="field-hint">${esc(t("profile.trustHint", { points: 5 }))}</p>
    </section>`;
}

export function render(user) {
  const phoneSeal = user.is_phone_verified
    ? `<span class="seal seal-ok">${esc(t("profile.verified"))}</span>`
    : `<span class="seal seal-warn">${esc(t("profile.notVerified"))}</span>`;

  return `
      <section class="panel info-card">
        <div class="panel-head">
          <h2 class="display h3">${esc(t("profile.personalInfo"))}</h2>
          <button class="btn btn-ghost btn-sm" type="button" data-edit-profile>
            ${icon("edit")} ${esc(t("profile.edit"))}
          </button>
        </div>

        <div class="info-cells">
          ${cell(t("auth.fullName"), esc(user.full_name || ""), { addField: "full_name" })}
          ${cell(t("auth.username"), esc(user.username), { mono: true })}
          ${cell(t("auth.phone"), `${esc(user.phone_number)} ${phoneSeal}`, { mono: true })}
          ${cell(t("profile.role"), esc(roleName(user)))}
          ${cell(t("profile.birthDate"), user.birth_date ? dateLabel(user.birth_date) : "", { addField: "birth_date" })}
          ${cell(t("profile.memberSince"), dateLabel(user.date_joined))}
          ${cell(t("profile.bio"), esc(user.bio || ""), { wide: true, addField: "bio" })}
        </div>

        <p class="field-hint">${esc(t("profile.idHint"))}</p>
      </section>`;
}

/**
 * Tahrirlash oynasi.
 *
 * Eksport qilingan, chunki uni ikki joydan ochish mumkin: shu
 * bo'limdagi tugma va muqovadagi "Tahrirlash". Ikki nusxa yozilsa,
 * bir kuni ular bir-biridan farq qila boshlardi.
 *
 * `focusField` — qaysi maydonga darrov kursor qo'yish. Bo'sh katakdagi
 * "Qo'shish" havolasi aynan shu maydonni ochadi, ya'ni odam oynani
 * ochib yana qidirib o'tirmaydi.
 */
export function openEditor(user, onUpdated, focusField = "") {
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

  if (focusField) node.querySelector(`#${CSS.escape(focusField)}`)?.focus();

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

/*
 * `bind` YO'Q — ataylab.
 *
 * Tahrirlash tugmalari (sarlavhadagi tugma ham, bo'sh katakdagi
 * "Qo'shish" havolasi ham) `profile.js` da BIR MARTA bog'lanadi.
 * Ilgari bu yerda bog'lansa, bo'lim har qayta chizilganda yangi
 * tinglovchi qo'shilib, uchinchi chizishdan keyin bitta bosishga
 * uchta oyna ochilardi.
 */
