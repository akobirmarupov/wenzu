/**
 * Profil rasmi — chiroyli ramkada.
 *
 * Rasm bo'lmasa bosh harflar ko'rsatiladi. Ramka oltin gradient bilan
 * chiziladi (`.avatar-ring`), shuning uchun rasm bo'lgan-bo'lmaganidan
 * qat'i nazar ko'rinish bir xil "tugallangan" bo'ladi.
 */
import { esc } from "./dom.js";
import { initials } from "./format.js";

const SIZES = { sm: "avatar-sm", md: "", lg: "avatar-lg", xl: "avatar-xl" };

/**
 * @param {object} user - {avatar, full_name, initials}
 * @param {object} options - {size: "sm"|"md"|"lg"|"xl", ring: boolean}
 */
export function avatarHtml(user, { size = "md", ring = false } = {}) {
  const sizeClass = SIZES[size] ?? "";
  const label = user?.initials || initials(user?.full_name);

  // Bosh harflar HAR DOIM chiziladi, rasm esa ularning USTIGA qo'yiladi.
  //
  // Nega shunday: rasm fayli yo'qolishi mumkin — server almashadi,
  // ombor tozalanadi, havola eskiradi. Ilgari bunday holatda brauzer
  // rasm o'rniga `alt` matnini, ya'ni odamning TO'LIQ ISMINI doira
  // ichiga sig'dirishga urinardi: doiradan toshib ketgan, kesilgan
  // yozuv chiqardi. Endi rasm yuklanmasa o'zini olib tashlaydi va
  // ostidagi bosh harflar ko'rinadi — ya'ni ko'rinish hech qachon
  // buzilmaydi. `alt` ataylab bo'sh: yonida ism allaqachon yozilgan,
  // skrinrider uni ikki marta o'qimasligi kerak.
  const inner = user?.avatar
    ? `<span class="avatar-initials">${esc(label)}</span>` +
      `<img src="${esc(user.avatar)}" alt="" loading="lazy" onerror="this.remove()">`
    : `<span class="avatar-initials">${esc(label)}</span>`;

  const avatar = `<span class="avatar ${sizeClass}">${inner}</span>`;
  return ring ? `<span class="avatar-ring ${sizeClass}">${avatar}</span>` : avatar;
}
