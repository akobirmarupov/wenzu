/**
 * Bildirishnoma qo'ng'irog'i — yuqori panelda, til tanlagichi yonida.
 *
 * Ikki so'rov ishlatiladi:
 *   `unread-count` — sahifa yuklanganda va har daqiqada (yengil COUNT)
 *   `list`         — faqat qo'ng'iroq BOSILGANDA (ro'yxatning o'zi)
 * Shunday qilinmasa har sahifa yuklanishida o'nlab yozuv bekorga
 * tortilardi.
 */
import { api } from "../core/api.js";
import { auth } from "../core/auth.js";
import { t } from "../core/i18n.js";
import { esc } from "./dom.js";
import { dateTimeLabel } from "./format.js";

const POLL_MS = 60000;

const ICONS = {
  reservation: "📅",
  application: "📝",
  subscription: "💎",
  review: "★",
  system: "◈",
};

export function bellHtml() {
  return `
    <div class="notif" data-notif>
      <button class="notif-trigger" type="button" aria-haspopup="true" aria-expanded="false"
              title="${esc(t("notif.title"))}" aria-label="${esc(t("notif.title"))}">
        <span class="ic" aria-hidden="true">🔔</span>
        <span class="notif-dot" data-notif-count hidden>0</span>
      </button>
      <div class="notif-panel" role="menu" hidden>
        <div class="notif-head">
          <b>${esc(t("notif.title"))}</b>
          <button type="button" class="link-btn" data-notif-read-all>${esc(t("notif.readAll"))}</button>
        </div>
        <div class="notif-body" data-notif-body></div>
      </div>
    </div>`;
}

function rowHtml(item) {
  const icon = ICONS[item.kind] || ICONS.system;
  const inner = `
    <span class="ic ${esc(item.level)}" aria-hidden="true">${icon}</span>
    <span class="text">
      <b>${esc(item.title)}</b>
      ${item.body ? `<span class="body">${esc(item.body)}</span>` : ""}
      <span class="when">${dateTimeLabel(item.created_at)}</span>
    </span>`;

  return item.link_url
    ? `<a class="notif-row ${item.is_read ? "" : "unread"}" href="${esc(item.link_url)}"
          data-notif-item="${esc(item.id)}">${inner}</a>`
    : `<div class="notif-row ${item.is_read ? "" : "unread"}"
            data-notif-item="${esc(item.id)}">${inner}</div>`;
}

/** Qo'ng'iroqni jonlantiradi. Konteyner — `bellHtml()` chizilgan joy. */
export function bindBell(container) {
  const root = container.querySelector("[data-notif]");
  if (!root || !auth.isAuthenticated()) return;

  const trigger = root.querySelector(".notif-trigger");
  const panel = root.querySelector(".notif-panel");
  const body = root.querySelector("[data-notif-body]");
  const counter = root.querySelector("[data-notif-count]");

  const setCount = (count) => {
    counter.textContent = count > 99 ? "99+" : String(count);
    counter.hidden = !count;
    trigger.classList.toggle("has-unread", Boolean(count));
  };

  const refreshCount = async () => {
    try {
      const data = await api.notifications.unreadCount();
      setCount(data.unread || 0);
    } catch {
      /* qo'ng'iroq ishlamasa sahifa baribir ishlaydi */
    }
  };

  const loadList = async () => {
    body.innerHTML = `<p class="notif-empty">${esc(t("common.loading"))}</p>`;
    try {
      const data = await api.notifications.list({ page_size: 12 });
      const items = data.results || [];
      body.innerHTML = items.length
        ? items.map(rowHtml).join("")
        : `<p class="notif-empty">${esc(t("notif.empty"))}</p>`;
    } catch {
      body.innerHTML = `<p class="notif-empty">${esc(t("common.error"))}</p>`;
    }
  };

  const close = () => {
    panel.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
  };

  trigger.addEventListener("click", (event) => {
    event.stopPropagation();
    const isOpen = !panel.hidden;
    panel.hidden = isOpen;
    trigger.setAttribute("aria-expanded", String(!isOpen));
    if (!isOpen) loadList();
  });

  panel.addEventListener("click", (event) => event.stopPropagation());

  root.querySelector("[data-notif-read-all]")?.addEventListener("click", async () => {
    try {
      await api.notifications.readAll();
      setCount(0);
      loadList();
    } catch {
      /* e'tiborsiz */
    }
  });

  // Bosilgan yozuv o'qilgan bo'lib qoladi — havolaga o'tishdan oldin
  // belgilab qo'yamiz, aks holda qaytib kelganda yana "yangi" ko'rinardi.
  body.addEventListener("click", (event) => {
    const row = event.target.closest("[data-notif-item]");
    if (!row || !row.classList.contains("unread")) return;
    row.classList.remove("unread");
    api.notifications.read(row.dataset.notifItem).catch(() => {});
    refreshCount();
  });

  document.addEventListener("click", close);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") close();
  });

  refreshCount();
  const timer = setInterval(() => {
    if (!document.hidden) refreshCount();
  }, POLL_MS);
  window.addEventListener("pagehide", () => clearInterval(timer));
}
