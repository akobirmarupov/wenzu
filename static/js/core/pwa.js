/**
 * Ilovani telefonga o'rnatish (PWA).
 *
 * Nima beradi: foydalanuvchi saytni Android'da "Bosh ekranga qo'shish"
 * orqali ilova sifatida o'rnatadi — o'z ikonkasi bilan, brauzer manzil
 * qatorisiz, alohida oynada ochiladi. iPhone'da ham xuddi shunday,
 * faqat "Ulashish → Bosh ekranga qo'shish" orqali.
 *
 * Ikki qism:
 *   1. Service worker'ni ro'yxatdan o'tkazish (oflayn rejim).
 *   2. "O'rnatish" tugmasi — brauzer o'zining bildirgisini bosib
 *      turadi va uni faqat biz chaqirganda ko'rsatadi.
 */

const DISMISSED_KEY = "wenzu:install-dismissed";

/** Ilova allaqachon o'rnatilgan holda ochilganmi. */
function isStandalone() {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    // iOS Safari `display-mode` ni bilmaydi, o'zining bayrog'i bor.
    window.navigator.standalone === true
  );
}

function registerWorker() {
  if (!("serviceWorker" in navigator)) return;
  // `load` dan keyin: worker ro'yxatdan o'tishi sahifaning birinchi
  // chizilishini sekinlashtirmasin.
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {
      /* HTTPS yo'q yoki brauzer qo'llamaydi — ilova baribir ishlaydi */
    });
  });
}

/**
 * "O'rnatish" tugmasi.
 *
 * Android brauzeri `beforeinstallprompt` hodisasini yuboradi va o'zining
 * taklifini to'xtatib turadi. Biz uni saqlab qo'yamiz va faqat
 * foydalanuvchi tugmani bosganda ochamiz — kutilmaganda chiqadigan
 * oyna odamni bezovta qiladi va odatda "yo'q" bosiladi.
 *
 * Bir marta rad etilsa, tugma boshqa ko'rsatilmaydi.
 */
function setupInstallButton() {
  let deferred = null;

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferred = event;
    if (isStandalone()) return;
    try {
      if (localStorage.getItem(DISMISSED_KEY)) return;
    } catch {
      /* maxfiy rejimda localStorage yopiq bo'lishi mumkin */
    }
    showBar();
  });

  window.addEventListener("appinstalled", () => {
    deferred = null;
    document.getElementById("install-bar")?.remove();
  });

  function showBar() {
    if (document.getElementById("install-bar")) return;

    const bar = document.createElement("div");
    bar.id = "install-bar";
    bar.className = "install-bar";
    bar.innerHTML = `
      <img class="install-icon" src="/static/images/pwa/icon-192.png" alt="">
      <div class="install-text">
        <b>WENZU ilovasini o'rnating</b>
        <span>Telefoningizdan bir bosishda oching — brauzersiz, tezroq.</span>
      </div>
      <button class="btn btn-primary btn-sm" type="button" data-install>O'rnatish</button>
      <button class="icon-btn" type="button" data-dismiss aria-label="Yopish">✕</button>`;

    bar.querySelector("[data-install]").addEventListener("click", async () => {
      if (!deferred) return;
      deferred.prompt();
      await deferred.userChoice;
      deferred = null;
      bar.remove();
    });

    bar.querySelector("[data-dismiss]").addEventListener("click", () => {
      try {
        localStorage.setItem(DISMISSED_KEY, "1");
      } catch {
        /* e'tiborsiz */
      }
      bar.remove();
    });

    document.body.append(bar);
  }
}

export function initPwa() {
  registerWorker();
  setupInstallButton();
}
