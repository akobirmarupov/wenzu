/**
 * "Taklif yuborish" oynasi.
 *
 * Sinov davrida bu platformaning eng qimmat kanali: nima ishlamayotganini
 * faqat undan foydalanayotgan odam biladi. Shuning uchun forma imkon
 * qadar past to'siqli — kirish talab qilinmaydi, majburiy maydon
 * bittagina (matn), qolgani ixtiyoriy.
 *
 * Havolaning O'ZI esa ataylab jimgina: menyuning eng pastida, kulrang
 * va kichik. Ishlayotgan odamning e'tiborini tortmaydi, lekin kerak
 * bo'lganda topiladi.
 */
import { api } from "../core/api.js";
import { auth } from "../core/auth.js";
import { t } from "../core/i18n.js";
import { modal } from "../ui/modal.js";
import { toast } from "../ui/toast.js";
import { esc, busy } from "../ui/dom.js";

const KINDS = [
  { value: "idea", key: "feedback.kindIdea" },
  { value: "problem", key: "feedback.kindProblem" },
  { value: "other", key: "feedback.kindOther" },
];

const MAX_LENGTH = 1000;

export function openFeedbackModal() {
  const signedIn = auth.isAuthenticated();
  let kind = "idea";

  const node = modal.open(`
    <h2 class="display h3">${esc(t("feedback.title"))}</h2>
    <p class="muted small">${esc(t("feedback.lead"))}</p>

    <form class="stack stack-4" id="feedback-form" style="margin-top:var(--sp-5)">
      <div class="form-alert" id="feedback-error" hidden></div>

      <div class="field">
        <label>${esc(t("feedback.kind"))}</label>
        <div class="feedback-kinds" id="feedback-kinds">
          ${KINDS.map((item) => `
            <button type="button" class="chip ${item.value === kind ? "active" : ""}"
                    data-kind="${item.value}">${esc(t(item.key))}</button>`).join("")}
        </div>
      </div>

      <div class="field">
        <label for="fb-message">${esc(t("feedback.message"))}</label>
        <textarea class="textarea" id="fb-message" rows="5" required
                  maxlength="${MAX_LENGTH}"
                  placeholder="${esc(t("feedback.placeholder"))}"></textarea>
        <span class="field-hint"><span id="fb-count">0</span>/${MAX_LENGTH}</span>
      </div>

      ${signedIn ? "" : `
        <div class="field">
          <label for="fb-contact">${esc(t("feedback.contact"))}</label>
          <input class="input" id="fb-contact" maxlength="120"
                 placeholder="${esc(t("feedback.contactHint"))}">
        </div>`}

      <button class="btn btn-primary btn-block" type="submit" id="fb-send">
        ${esc(t("feedback.send"))}
      </button>
    </form>
  `);

  const form = node.querySelector("#feedback-form");
  const message = node.querySelector("#fb-message");
  const counter = node.querySelector("#fb-count");

  message.addEventListener("input", () => {
    counter.textContent = String(message.value.length);
  });

  node.querySelectorAll("[data-kind]").forEach((button) => {
    button.addEventListener("click", () => {
      kind = button.dataset.kind;
      node.querySelectorAll("[data-kind]").forEach((other) =>
        other.classList.toggle("active", other === button));
    });
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const errorBox = node.querySelector("#feedback-error");
    errorBox.hidden = true;

    const text = message.value.trim();
    if (text.length < 10) {
      errorBox.textContent = t("feedback.tooShort");
      errorBox.hidden = false;
      return;
    }

    const done = busy(node.querySelector("#fb-send"));
    try {
      await api.feedback({
        kind,
        message: text,
        contact: node.querySelector("#fb-contact")?.value.trim() || "",
        // Qaysi ekrandan yozilgani — "tugma ishlamadi" degan fikr
        // manzilsiz deyarli foydasiz.
        page: window.location.pathname,
      });
      modal.close();
      toast.ok(t("feedback.thanks"));
    } catch (error) {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
    } finally {
      done();
    }
  });
}

/**
 * Sahifadagi "Taklif yuborish" havolalarini ulaydi.
 *
 * Hujjatga BIR MARTA ulanadi, har bir havolaga emas: yon menyu
 * sessiyaga qarab qayta chiziladi va har safar qayta ulanish kerak
 * bo'lardi — biri unutilsa havola jim qolardi.
 */
export function bindFeedbackLinks() {
  if (bindFeedbackLinks.done) return;
  bindFeedbackLinks.done = true;

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest?.("[data-feedback]");
    if (!trigger) return;
    event.preventDefault();
    openFeedbackModal();
  });
}
