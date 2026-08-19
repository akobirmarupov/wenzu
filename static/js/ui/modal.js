/**
 * Modal oyna.
 *
 * Bitta joyda: fokusni ushlab turish, Escape bilan yopish, orqa fonni
 * bosganda yopish va sahifa orqasi aylanmasligi. Har bir modalda buni
 * qaytadan yozish — unutilgan tafsilotlar manbai.
 */
let current = null;

function close() {
  if (!current) return;
  const { overlay, onClose, lastFocus } = current;
  overlay.remove();
  document.body.style.overflow = "";
  document.removeEventListener("keydown", onKeydown);
  current = null;
  if (lastFocus?.focus) lastFocus.focus();
  if (typeof onClose === "function") onClose();
}

function onKeydown(event) {
  if (event.key === "Escape") close();
  if (event.key !== "Tab" || !current) return;

  const focusable = current.overlay.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  if (!focusable.length) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];

  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

/**
 * @param {string} html - modal ichidagi HTML
 * @param {object} options - {wide, onClose, onMount}
 * @returns {HTMLElement} modal elementi
 */
export function openModal(html, { wide = false, onClose, onMount } = {}) {
  close();

  const overlay = document.createElement("div");
  overlay.className = "overlay";
  overlay.innerHTML = `
    <div class="modal ${wide ? "modal-wide" : ""}" role="dialog" aria-modal="true">
      <button class="modal-close" type="button" data-modal-close aria-label="Yopish">✕</button>
      ${html}
    </div>`;

  overlay.addEventListener("click", (event) => {
    if (event.target === overlay || event.target.closest("[data-modal-close]")) close();
  });

  document.body.append(overlay);
  document.body.style.overflow = "hidden";
  document.addEventListener("keydown", onKeydown);

  current = { overlay, onClose, lastFocus: document.activeElement };

  const modal = overlay.querySelector(".modal");
  const firstField = modal.querySelector("input, select, textarea, button:not([data-modal-close])");
  if (firstField) firstField.focus();

  if (typeof onMount === "function") onMount(modal);
  return modal;
}

export const modal = { open: openModal, close };

/** Tasdiqlash oynasi — `confirm()` o'rniga. */
export function confirmDialog({ title, message, confirmText = "Tasdiqlash", danger = false }) {
  return new Promise((resolve) => {
    let answered = false;
    const node = openModal(
      `<h2>${title}</h2>
       <p class="muted">${message}</p>
       <div class="row row-2" style="margin-top:var(--sp-6)">
         <button class="btn btn-outline" style="flex:1" data-modal-close type="button">Bekor qilish</button>
         <button class="btn ${danger ? "btn-danger" : "btn-primary"}" style="flex:1" data-confirm type="button">${confirmText}</button>
       </div>`,
      {
        onClose: () => {
          if (!answered) resolve(false);
        },
      }
    );
    node.querySelector("[data-confirm]").addEventListener("click", () => {
      answered = true;
      close();
      resolve(true);
    });
  });
}
