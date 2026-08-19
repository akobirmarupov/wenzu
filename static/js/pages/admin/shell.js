/**
 * Super-admin panelining umumiy boshlanishi.
 * Huquqni tekshiradi, yon menyuni chizadi va kutilayotgan arizalar
 * sonini menyuga qo'yadi.
 */
import { api } from "../../core/api.js";
import { requireAdmin } from "../../core/guard.js";
import { initI18n } from "../../core/i18n.js";
import { theme } from "../../core/theme.js";
import { initSidebar, setSidebarBadge } from "../../ui/sidebar.js";
import { initTopbar } from "../../ui/topbar.js";

export async function initAdminPage() {
  theme.init();
  await initI18n();

  const user = requireAdmin();
  if (!user) return null;

  initSidebar(user);
  initTopbar();
  loadBadges();
  return user;
}

async function loadBadges() {
  try {
    const data = await api.admin.applications({ status: "pending_payment", page_size: 1 });
    setSidebarBadge("applications", data.count || 0);
  } catch {
    /* nishon muhim emas */
  }
}
