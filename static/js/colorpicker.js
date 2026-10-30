/* ============================================================
   Custom HSV colour picker — replaces native <input type=color>
   Auto-enhances every colour input on the page.
   ============================================================ */
(function () {
  "use strict";

  /* ─── Colour math ─── */
  function hexToRgb(hex) {
    hex = (hex || "#000000").replace("#", "").trim();
    if (hex.length === 3) hex = hex.split("").map(c => c + c).join("");
    const n = parseInt(hex, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function rgbToHex(r, g, b) {
    const h = x => ("0" + Math.round(x).toString(16)).slice(-2);
    return "#" + h(r) + h(g) + h(b);
  }
  function rgbToHsv(r, g, b) {
    r /= 255; g /= 255; b /= 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    const d = max - min;
    let h = 0;
    if (d !== 0) {
      if (max === r) h = 60 * (((g - b) / d) % 6);
      else if (max === g) h = 60 * ((b - r) / d + 2);
      else h = 60 * ((r - g) / d + 4);
    }
    if (h < 0) h += 360;
    return [h, max === 0 ? 0 : d / max, max];
  }
  function hsvToRgb(h, s, v) {
    h = ((h % 360) + 360) % 360;
    const c = v * s;
    const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
    const m = v - c;
    let r, g, b;
    if (h < 60)       [r, g, b] = [c, x, 0];
    else if (h < 120) [r, g, b] = [x, c, 0];
    else if (h < 180) [r, g, b] = [0, c, x];
    else if (h < 240) [r, g, b] = [0, x, c];
    else if (h < 300) [r, g, b] = [x, 0, c];
    else              [r, g, b] = [c, 0, x];
    return [
      Math.round((r + m) * 255),
      Math.round((g + m) * 255),
      Math.round((b + m) * 255),
    ];
  }

  /* ─── Build modal DOM once ─── */
  let modal, canvas, ctx, marker, brightness, brightThumb, hexInput, swatchLarge;
  let currentInput = null;
  let state = { h: 160, s: 1, v: 1 };
  const SIZE = 240;
  const RADIUS = SIZE / 2 - 10;

  function buildModal() {
    if (modal) return;
    modal = document.createElement("div");
    modal.className = "cp-modal";
    modal.innerHTML = `
      <div class="cp-sheet" role="dialog" aria-modal="true" aria-label="Pick a colour">
        <div class="cp-head">
          <span>Pick a colour</span>
          <button type="button" class="cp-close" aria-label="Close">✕</button>
        </div>
        <div class="cp-body">
          <div class="cp-wheel-wrap">
            <canvas class="cp-wheel" width="${SIZE * 2}" height="${SIZE * 2}"
                    style="width:${SIZE}px;height:${SIZE}px"></canvas>
            <span class="cp-marker"></span>
          </div>
          <div class="cp-bright-row">
            <span class="cp-bright-label">Brightness</span>
            <div class="cp-bright-track">
              <div class="cp-bright-fill"></div>
              <span class="cp-bright-thumb"></span>
            </div>
          </div>
          <div class="cp-hex-row">
            <label>Hex colour</label>
            <div class="cp-hex-field">
              <span class="cp-hex-swatch"></span>
              <input type="text" class="cp-hex-input" maxlength="7" spellcheck="false"
                     placeholder="#000000">
            </div>
          </div>
          <div class="cp-presets" id="cp-presets"></div>
        </div>
        <div class="cp-foot">
          <button type="button" class="cp-btn cp-cancel">Cancel</button>
          <button type="button" class="cp-btn cp-apply">Apply</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    canvas      = modal.querySelector(".cp-wheel");
    ctx         = canvas.getContext("2d");
    marker      = modal.querySelector(".cp-marker");
    brightness  = modal.querySelector(".cp-bright-track");
    brightThumb = modal.querySelector(".cp-bright-thumb");
    hexInput    = modal.querySelector(".cp-hex-input");
    swatchLarge = modal.querySelector(".cp-hex-swatch");

    // Wire events
    modal.querySelector(".cp-close").addEventListener("click", close);
    modal.querySelector(".cp-cancel").addEventListener("click", close);
    modal.querySelector(".cp-apply").addEventListener("click", apply);
    modal.addEventListener("click", e => { if (e.target === modal) close(); });
    document.addEventListener("keydown", e => {
      if (e.key === "Escape" && modal.classList.contains("open")) close();
    });

    // Wheel interaction
    let dragging = false;
    function handleWheel(e) {
      const rect = canvas.getBoundingClientRect();
      const t = e.touches ? e.touches[0] : e;
      const x = t.clientX - rect.left - rect.width / 2;
      const y = t.clientY - rect.top - rect.height / 2;
      const dist = Math.sqrt(x * x + y * y);
      const radius = rect.width / 2 - 10;
      let angle = Math.atan2(y, x) * 180 / Math.PI;
      if (angle < 0) angle += 360;
      state.h = angle;
      state.s = Math.min(1, dist / radius);
      updateWheel();
      updateMarker();
      syncFromState();
    }
    canvas.addEventListener("mousedown", e => { dragging = true; handleWheel(e); });
    canvas.addEventListener("touchstart", e => { e.preventDefault(); dragging = true; handleWheel(e); });
    document.addEventListener("mousemove", e => { if (dragging) handleWheel(e); });
    document.addEventListener("touchmove", e => { if (dragging) { e.preventDefault(); handleWheel(e); } });
    document.addEventListener("mouseup", () => { dragging = false; });
    document.addEventListener("touchend", () => { dragging = false; });

    // Brightness slider
    let bDragging = false;
    function handleBright(e) {
      const rect = brightness.getBoundingClientRect();
      const t = e.touches ? e.touches[0] : e;
      let x = (t.clientX - rect.left) / rect.width;
      x = Math.max(0, Math.min(1, x));
      state.v = x;
      updateMarker();
      syncFromState();
    }
    brightness.addEventListener("mousedown", e => { bDragging = true; handleBright(e); });
    brightness.addEventListener("touchstart", e => { e.preventDefault(); bDragging = true; handleBright(e); });
    document.addEventListener("mousemove", e => { if (bDragging) handleBright(e); });
    document.addEventListener("touchmove", e => { if (bDragging) { e.preventDefault(); handleBright(e); } });
    document.addEventListener("mouseup", () => { bDragging = false; });
    document.addEventListener("touchend", () => { bDragging = false; });

    // Hex input
    hexInput.addEventListener("input", () => {
      let v = hexInput.value.trim();
      if (!v.startsWith("#")) v = "#" + v;
      if (/^#[0-9a-fA-F]{6}$/.test(v)) {
        const [r, g, b] = hexToRgb(v);
        const [h, s, vv] = rgbToHsv(r, g, b);
        state.h = h; state.s = s; state.v = vv;
        updateMarker();
        updateSwatch();
      }
    });
    hexInput.addEventListener("blur", () => {
      const [r, g, b] = hsvToRgb(state.h, state.s, state.v);
      hexInput.value = rgbToHex(r, g, b);
    });

    // Presets
    const presets = [
      "#0f766e", "#14b8a6", "#059669", "#0891b2",
      "#2563eb", "#7c3aed", "#db2777", "#dc2626",
      "#ea580c", "#d97706", "#65a30d", "#475569",
    ];
    const presetsWrap = modal.querySelector("#cp-presets");
    presets.forEach(hex => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "cp-preset";
      b.style.background = hex;
      b.title = hex;
      b.addEventListener("click", () => {
        const [r, g, bb] = hexToRgb(hex);
        const [h, s, vv] = rgbToHsv(r, g, bb);
        state.h = h; state.s = s; state.v = vv;
        updateMarker();
        syncFromState();
      });
      presetsWrap.appendChild(b);
    });
  }

  /* ─── Draw wheel once ─── */
  function drawWheel() {
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2, cy = h / 2;
    const R = w / 2 - 20;

    ctx.clearRect(0, 0, w, h);

    // Hue wedges
    for (let a = 0; a < 360; a++) {
      const r1 = a * Math.PI / 180;
      const r2 = (a + 1) * Math.PI / 180;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, R, r1, r2);
      ctx.closePath();
      ctx.fillStyle = "hsl(" + a + ", 100%, 50%)";
      ctx.fill();
    }

    // White radial overlay (saturation)
    const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, R);
    grad.addColorStop(0, "rgba(255,255,255,1)");
    grad.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(cx, cy, R, 0, Math.PI * 2);
    ctx.fill();

    // Dark overlay for brightness
    if (state.v < 1) {
      ctx.fillStyle = "rgba(0,0,0," + (1 - state.v) + ")";
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function updateWheel() { drawWheel(); }

  function updateMarker() {
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const w = rect.width, h = rect.height;
    const cx = w / 2, cy = h / 2;
    const radius = w / 2 - 10;
    const angle = state.h * Math.PI / 180;
    const dist = state.s * radius;
    const x = cx + Math.cos(angle) * dist;
    const y = cy + Math.sin(angle) * dist;

    marker.style.left = x + "px";
    marker.style.top  = y + "px";

    const [r, g, b] = hsvToRgb(state.h, state.s, state.v);
    marker.style.background = rgbToHex(r, g, b);

    // Brightness slider fill
    brightness.querySelector(".cp-bright-fill").style.width = (state.v * 100) + "%";
    brightThumb.style.left = (state.v * 100) + "%";
  }

  function updateSwatch() {
    const [r, g, b] = hsvToRgb(state.h, state.s, state.v);
    const hex = rgbToHex(r, g, b);
    swatchLarge.style.background = hex;
    hexInput.value = hex;
  }

  function syncFromState() {
    const [r, g, b] = hsvToRgb(state.h, state.s, state.v);
    swatchLarge.style.background = rgbToHex(r, g, b);
    hexInput.value = rgbToHex(r, g, b);
  }

  /* ─── Open / close ─── */
  function open(input) {
    buildModal();
    currentInput = input;
    const hex = input.value || "#000000";
    const [r, g, b] = hexToRgb(hex);
    const [h, s, v] = rgbToHsv(r, g, b);
    state = { h, s, v };
    drawWheel();
    updateMarker();
    syncFromState();
    modal.classList.add("open");
    document.body.style.overflow = "hidden";
  }
  function close() {
    if (!modal) return;
    modal.classList.remove("open");
    document.body.style.overflow = "";
    currentInput = null;
  }
  function apply() {
    if (!currentInput) return close();
    const [r, g, b] = hsvToRgb(state.h, state.s, state.v);
    const hex = rgbToHex(r, g, b);
    currentInput.value = hex;

    // Update any companion preview element
    const wrap = currentInput.closest(".cp-field");
    if (wrap) {
      const sw = wrap.querySelector(".cp-inline-swatch");
      const txt = wrap.querySelector(".cp-inline-hex");
      if (sw) sw.style.background = hex;
      if (txt) txt.textContent = hex;
    }

    // Fire change event so live-preview listeners update
    currentInput.dispatchEvent(new Event("input", { bubbles: true }));
    currentInput.dispatchEvent(new Event("change", { bubbles: true }));

    close();
  }

  /* ─── Auto-enhance inputs ─── */
  function enhance(input) {
    if (input.dataset.cpEnhanced) return;
    input.dataset.cpEnhanced = "1";

    // Hide the native picker completely
    input.type = "hidden";
    // Also add a data attribute we can style
    input.classList.add("cp-native-hidden");

    const initial = input.value || "#000000";

    const wrap = document.createElement("div");
    wrap.className = "cp-field";
    wrap.innerHTML = `
      <button type="button" class="cp-trigger">
        <span class="cp-inline-swatch" style="background:${initial}"></span>
        <span class="cp-inline-hex">${initial}</span>
      </button>
    `;
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    wrap.querySelector(".cp-trigger").addEventListener("click", e => {
      e.preventDefault();
      open(input);
    });
  }

  function scan() {
    document.querySelectorAll('input[type="color"]').forEach(enhance);
  }

  // Run now and after DOM mutations
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scan);
  } else {
    scan();
  }
  // Watch for dynamically added inputs
  const mo = new MutationObserver(scan);
  mo.observe(document.body, { childList: true, subtree: true });
})();
