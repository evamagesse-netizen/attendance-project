(function () {
  "use strict";

  const SCAN_URL = "/scan-barcode/";
  const COOLDOWN_MS = 2200;

  function getCookie(name) {
    let value = null;
    if (document.cookie && document.cookie !== "") {
      const parts = document.cookie.split(";");
      for (let i = 0; i < parts.length; i++) {
        const cookie = parts[i].trim();
        if (cookie.startsWith(name + "=")) {
          value = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return value;
  }

  function playSuccessSound() {
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      const ctx = new Ctx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.value = 880;
      gain.gain.setValueAtTime(0.1, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.15);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.15);
    } catch (e) {
      /* ignore */
    }
  }

  function bindModeHint() {
    const hint = document.getElementById("mode-hint");
    const radios = document.querySelectorAll('input[name="scan-mode"]');
    function update() {
      if (!hint) return;
      if (getScanMode() === "check-out") {
        hint.textContent = "Scanning will record check-out (leave).";
      } else {
        hint.textContent = "Scanning will record check-in (arrival).";
      }
    }
    radios.forEach(function (r) {
      r.addEventListener("change", update);
    });
    update();
  }

  function formatClock() {
    const el = document.getElementById("clock");
    if (!el) return;
    const tick = function () {
      const now = new Date();
      el.textContent = now.toLocaleString(undefined, {
        weekday: "short",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    };
    tick();
    setInterval(tick, 1000);
  }

  const resultEl = document.getElementById("result");
  const resultTitle = document.getElementById("result-title");
  const resultDetail = document.getElementById("result-detail");
  const resultIcon = document.getElementById("result-icon");
  const loadingEl = document.getElementById("loading");

  let lastScanAt = 0;
  let busy = false;

  function showResult(success, title, detail) {
    if (!resultEl || !resultTitle || !resultDetail || !resultIcon) return;
    resultEl.hidden = false;
    resultEl.className = "result-panel " + (success ? "result-panel--success" : "result-panel--error");
    resultIcon.textContent = success ? "✓" : "✕";
    resultTitle.textContent = title;
    resultDetail.textContent = detail || "";
  }

  function hideLoading() {
    if (loadingEl) loadingEl.hidden = true;
  }

  function showLoading() {
    if (loadingEl) loadingEl.hidden = false;
  }

  function getScanMode() {
    const el = document.querySelector('input[name="scan-mode"]:checked');
    return el && el.value ? el.value : "check-in";
  }

  async function postBarcode(barcode, mode) {
    const token = getCookie("csrftoken");
    let res;
    try {
      res = await fetch(SCAN_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": token || "",
          Accept: "application/json",
        },
        credentials: "same-origin",
        body: JSON.stringify({
          barcode: String(barcode).trim(),
          mode: mode,
        }),
      });
    } catch (e) {
      throw new Error("Network error. Check your connection.");
    }
    let data = {};
    try {
      data = await res.json();
    } catch (e) {
      throw new Error("Invalid server response.");
    }
    if (!res.ok) {
      const msg = data.message || res.statusText || "Request failed.";
      throw new Error(msg);
    }
    return data;
  }

  async function onScanSuccess(decodedText) {
    const now = Date.now();
    if (now - lastScanAt < COOLDOWN_MS || busy) return;
    lastScanAt = now;
    busy = true;

    try {
      const mode = getScanMode();
      const data = await postBarcode(decodedText, mode);
      const name = data.employee_name || "Employee";
      if (data.status === "success" && data.action === "check-in") {
        playSuccessSound();
        showResult(true, "Welcome " + name + " (Checked In)", data.message || "");
      } else if (data.status === "success" && data.action === "check-out") {
        playSuccessSound();
        showResult(true, "Goodbye " + name + " (Checked Out)", data.message || "");
      } else {
        showResult(false, "Something went wrong", data.message || "");
      }
    } catch (err) {
      showResult(false, "Scan failed", err.message || "Unknown error.");
    } finally {
      busy = false;
    }
  }

  function initScanner() {
    const readerEl = document.getElementById("reader");
    if (!readerEl || typeof Html5Qrcode === "undefined") {
      hideLoading();
      showResult(false, "Scanner unavailable", "Could not load camera library. Check your connection.");
      return;
    }

    const html5QrCode = new Html5Qrcode("reader");
    const config = { fps: 10, qrbox: { width: 260, height: 260 } };

    function onDecode(decodedText) {
      onScanSuccess(decodedText);
    }

    function onScanFailure() {
      /* per-frame; ignore */
    }

    html5QrCode
      .start({ facingMode: "environment" }, config, onDecode, onScanFailure)
      .then(function () {
        hideLoading();
      })
      .catch(function () {
        return html5QrCode.start({ facingMode: "user" }, config, onDecode, onScanFailure);
      })
      .then(function () {
        hideLoading();
      })
      .catch(function (err) {
        hideLoading();
        showResult(false, "Camera error", (err && err.message) || String(err));
      });
  }

  bindModeHint();
  formatClock();
  showLoading();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initScanner);
  } else {
    initScanner();
  }
})();
