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
 * KATAK EMAS, QATOR
 * ===================================================================
 * Ilgari maydonlar ikki ustunli katakda turardi va har birining
 * tepasida KATTA HARFLI yorliq bor edi ("TO'LIQ ISM"). Mayda yozuv
 * bo'lsa ham, katta harf va kengaytirilgan harf oralig'i tufayli
 * yorliq o'z qiymatidan ko'proq ko'zga tashlanardi — ya'ni ekranda
 * ma'lumotning o'zi emas, uning nomi baqirardi.
 *
 * Endi bitta ustunda qatorlar: chapda sust nom, o'ngda to'q qiymat,
 * orasida ingichka chiziq. Barcha qiymatlar bitta vertikal chiziqdan
 * boshlanadi, ko'z esa faqat pastga tushib o'qiydi.
 */
import { api } from "../../../core/api.js";
import { auth } from "../../../core/auth.js";
import { t } from "../../../core/i18n.js";
import { esc, busy, formValues } from "../../../ui/dom.js";
import { modal } from "../../../ui/modal.js";
import { toast } from "../../../ui/toast.js";
import { dateLabel } from "../../../ui/format.js";
import { icon } from "../../../ui/icons.js";

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
 * Bitta qator: chapda nomi, o'ngda qiymati.
 *
 * ===================================================================
 * BO'SH MAYDON QATOR OCHMAYDI
 * ===================================================================
 * Ilgari to'ldirilmagan maydon ham qator bo'lib turardi va o'ng
 * tomonida "—" chiziqchasi ko'rinardi. Yangi hisobda bu ikki-uchta
 * bo'sh qator degani edi: odam ekranda o'zi haqida ma'lumot emas,
 * chiziqchalar ro'yxatini ko'rardi.
 *
 * Endi bo'sh maydon umuman chizilmaydi — qator faqat qiymat KIRITILSA
 * paydo bo'ladi. Maydonni to'ldirish yo'li o'zgarmadi: muqovadagi
 * "Tahrirlash" barcha maydonni bir oynada ochadi va u yerda bo'shlari
 * ham ko'rinadi.
 */
function row(label, value, { mono = false } = {}) {
  if (!value) return "";

  return `
    <div class="info-row">
      <dt>${esc(label)}</dt>
      <dd class="${mono ? "num" : ""}">${value}</dd>
    </div>`;
}

/**
 * Ishonchlilik qiymati — endi alohida kartochka emas, oddiy qator.
 *
 * Nima uchun profilda ko'rinadi: bal joy egasiga ko'rinadi va u shunga
 * qarab bronni tasdiqlaydi yoki rad etadi. Egasi ko'radigan, lekin
 * odamning o'zi ko'rmaydigan baho — yashirin qora ro'yxat bo'lardi.
 *
 * Nega kartochka emas: u sahifaning O'NG ustunida, o'z ramkasi,
 * nishoni va chizig'i bilan turardi — bitta son uchun uchta element.
 * Ostida esa yarim ekran bo'sh maydon qolardi. Son o'sha-o'sha, faqat
 * endi qolgan ma'lumot bilan bir qatorda o'qiladi.
 *
 * Eski javobda `trust` bo'lmasligi mumkin (keshlangan sahifa) — u
 * holda qator umuman chizilmaydi.
 */
function trustValue(user) {
  const trust = user.trust;
  if (!trust?.bits) return "";
  const bits = `${trust.bits} ${t("profile.bit")}`;
  return trust.level_display ? `${bits} · ${trust.level_display}` : bits;
}

export function render(user) {
  const trust = trustValue(user);

  // Telefon yonidagi "Tasdiqlangan" nishoni OLIB TASHLANDI: aynan shu
  // holat muqovada, ism ostida allaqachon yozilgan. Bir ekranda bir
  // xil javobni ikki marta ko'rsatish — takror, ma'lumot emas.
  return `
      <section class="info-block">
        <h2 class="block-title">${esc(t("profile.personalInfo"))}</h2>

        <dl class="info-rows">
          ${row(t("auth.fullName"), esc(user.full_name || ""))}
          ${row(t("auth.username"), `@${esc(user.username)}`, { mono: true })}
          ${row(t("auth.phone"), esc(user.phone_number), { mono: true })}
          ${row(t("profile.role"), esc(roleName(user)))}
          ${row(t("profile.birthDate"), user.birth_date ? dateLabel(user.birth_date) : "", { mono: true })}
          ${row(t("profile.memberSince"), dateLabel(user.date_joined), { mono: true })}
          ${row(t("profile.bio"), esc(user.bio || ""))}
          ${trust ? row(t("profile.trust"), esc(trust), { mono: true }) : ""}
        </dl>

        <p class="info-hint">${esc(t("profile.idHint"))}</p>
      </section>`;
}

/**
 * Tahrirlash oynasi.
 *
 * Sozlamalardagi "Tahrirlash" satri ochadi. Ichida hisobga tegishli
 * HAMMA narsa bor:
 *   · rasm amallari — almashtirish va olib tashlash;
 *   · o'zgartirsa bo'ladigan maydonlar — ism, tug'ilgan sana, qisqacha;
 *   · o'zgartirib bo'lmaydigan maydon — telefon raqami.
 *
 * Telefon raqami ham TAHRIRLANADI. Ilgari u qulflangan edi va
 * o'zgartirish uchun administratorga murojaat qilish kerak bo'lardi —
 * server qoidasi o'zgargach (`account/routes/serializers.py`), qulf
 * bu yerdan ham olib tashlandi. Format serverda tekshiriladi va xato
 * bo'lsa maydon ustida ko'rsatiladi.
 *
 * @param {object} user
 * @param {object} actions - {onUpdated, onRemoveAvatar}
 */
export function openEditor(user, { onUpdated, onRemoveAvatar } = {}) {
  const node = modal.open(`
    <h2 class="display h3">${esc(t("profile.editTitle"))}</h2>

    <div class="edit-photo">
      <label class="btn btn-outline btn-sm" for="avatar-input">
        ${icon("camera")} ${esc(t("profile.changePhoto"))}
        <input type="file" id="avatar-input" accept="image/*" hidden>
      </label>
      ${user.avatar
        ? `<button class="btn btn-ghost btn-sm" type="button" id="editor-remove-avatar">
             ${icon("trash")} ${esc(t("profile.removePhoto"))}
           </button>`
        : ""}
    </div>

    <form class="stack stack-4" id="profile-form" style="margin-top:var(--sp-4)">
      <div class="form-alert" id="profile-error" hidden></div>

      <div class="field">
        <label for="full_name">${esc(t("auth.fullName"))}</label>
        <input class="input" id="full_name" name="full_name" required
               value="${esc(user.full_name || "")}">
      </div>

      <div class="field">
        <label for="phone_number">${esc(t("auth.phone"))}</label>
        <input class="input" id="phone_number" name="phone_number" type="tel"
               inputmode="tel" placeholder="+998901234567"
               value="${esc(user.phone_number || "")}">
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

      <p class="field-hint">${esc(t("profile.idHint"))}</p>

      <div class="row row-2" style="margin-top:var(--sp-2)">
        <button class="btn btn-outline" style="flex:1" type="button" data-modal-close>
          ${esc(t("profile.cancel"))}
        </button>
        <button class="btn btn-primary" style="flex:1" type="submit" id="save-profile">
          ${esc(t("profile.save"))}
        </button>
      </div>
    </form>`);

  node.querySelector("#editor-remove-avatar")?.addEventListener("click", () => {
    modal.close();
    onRemoveAvatar?.();
  });

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
      // Xato qaysi maydonga tegishli bo'lsa, o'shanisi ko'rsatiladi.
      // Ilgari faqat `full_name` qaralardi va telefon formati noto'g'ri
      // bo'lganda odam umumiy "Xatolik yuz berdi" ni ko'rardi.
      errorBox.textContent = error.fieldError?.("phone_number")
        || error.fieldError?.("full_name")
        || error.message;
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
