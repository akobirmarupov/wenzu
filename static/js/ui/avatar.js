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
  const inner = user?.avatar
    ? `<img src="${esc(user.avatar)}" alt="${esc(user?.full_name || "")}" loading="lazy">`
    : `<span>${esc(label)}</span>`;

  const avatar = `<span class="avatar ${sizeClass}">${inner}</span>`;
  return ring ? `<span class="avatar-ring ${sizeClass}">${avatar}</span>` : avatar;
}
