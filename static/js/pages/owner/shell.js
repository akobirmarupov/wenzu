/**
 * Biznes egasi panelining umumiy boshlanishi.
 *
 * Har bir panel sahifasi shu funksiyani chaqiradi: huquq tekshiriladi,
 * yon menyu chiziladi, kutilayotgan bronlar soni menyuga qo'yiladi va
 * obuna tugagan bo'lsa yuqorida bloklash bloki chiqadi.
 */
import { api } from "../../core/api.js";
import { requireOwner } from "../../core/guard.js";
import { initI18n } from "../../core/i18n.js";
import { theme } from "../../core/theme.js";
import { initSidebar, setSidebarBadge } from "../../ui/sidebar.js";
import { initTopbar } from "../../ui/topbar.js";
import { $, esc } from "../../ui/dom.js";
import { money } from "../../ui/format.js";

export async function initOwnerPage() {
  theme.init();
  await initI18n();

  const session = requireOwner();
  if (!session) return null;

  initSidebar(session.user);
  initTopbar();

  // Fon rejimida: nishon va obuna holati. Sahifa ular kutmasdan chiziladi.
  loadBadges();
  const subscription = await checkSubscription();

  return { ...session, subscription };
}

async function loadBadges() {
  try {
    const data = await api.owner.reservations({ status: "pending", page_size: 1 });
    setSidebarBadge("pending", data.count || 0);
  } catch {
    /* nishon muhim emas */
  }
}

async function checkSubscription() {
  try {
    const subscription = await api.owner.subscription();
    if (subscription?.status === "expired") showLock(subscription);
    else if (subscription?.status === "trial") showTrialHint(subscription);
    return subscription;
  } catch {
    return null;
  }
}

function showLock(subscription) {
  const content = $("#dash-content");
  if (!content) return;
  const telegram = subscription.admin_telegram || "@uvente";

  const block = document.createElement("div");
  block.className = "subscription-lock";
  block.innerHTML = `
    <div class="text">
      <h3>Obunangiz tugadi</h3>
      <p class="small">Profilingiz ommaviy qidiruvda ko'rinmayapti va yangi ma'lumot
         qo'sha olmaysiz. Davom ettirish uchun ${esc(telegram)} bilan bog'laning
         (tarif: ${money(subscription.price)}).</p>
    </div>
    <a class="btn btn-primary" href="https://t.me/${esc(telegram.replace("@", ""))}"
       target="_blank" rel="noopener">✈️ Administrator bilan bog'lanish</a>`;
  content.prepend(block);
}

function showTrialHint(subscription) {
  const content = $("#dash-content");
  if (!content || subscription.days_left === null) return;
  if (subscription.days_left > 3) return; // faqat tugashiga yaqin eslatamiz

  const block = document.createElement("div");
  block.className = "subscription-lock";
  block.innerHTML = `
    <div class="text">
      <h3>Bepul sinov tugayapti</h3>
      <p class="small">Sinov muddatiga <b>${subscription.days_left} kun</b> qoldi.
         Uzluksiz ishlashi uchun oldindan to'lovni amalga oshiring.</p>
    </div>
    <a class="btn btn-primary" href="/panel/obuna/">Obuna bo'limiga</a>`;
  content.prepend(block);
}
