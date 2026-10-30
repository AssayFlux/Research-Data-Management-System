/* ============================================================
   PAGEPATTERN — professional navigation layer
   Progress bar · page transitions · smart back · shortcuts
   ============================================================ */
(function () {
  "use strict";

  var path = window.location.pathname;
  var isStandalone = window.matchMedia("(display-mode: standalone)").matches
                  || window.navigator.standalone === true;

  /* ═══════════════════════════════════════════════════════════
     1) TOP PROGRESS BAR — thin teal line on every navigation
     ═══════════════════════════════════════════════════════════ */
  var bar = document.createElement("div");
  bar.id = "nav-progress";
  bar.style.cssText =
    "position:fixed;top:0;left:0;height:2.5px;width:0;z-index:9999;" +
    "background:linear-gradient(90deg,#0f766e,#14b8a6,#22d3ee);" +
    "transition:width .25s ease,opacity .3s ease;opacity:0;pointer-events:none;" +
    "box-shadow:0 0 8px rgba(20,184,166,.5)";
  document.body.appendChild(bar);

  var progressTimer = null;
  function startProgress() {
    bar.style.opacity = "1";
    bar.style.width = "0%";
    var w = 0;
    clearInterval(progressTimer);
    progressTimer = setInterval(function () {
      w += Math.max(0.5, (85 - w) / 15);
      if (w > 85) w = 85;
      bar.style.width = w + "%";
    }, 80);
  }
  function finishProgress() {
    clearInterval(progressTimer);
    bar.style.width = "100%";
    setTimeout(function () {
      bar.style.opacity = "0";
      setTimeout(function () { bar.style.width = "0%"; }, 300);
    }, 200);
  }

  /* ═══════════════════════════════════════════════════════════
     2) PAGE FADE-IN — subtle appearance on every new page
     ═══════════════════════════════════════════════════════════ */
  var mainContent = document.querySelector(".content") || document.querySelector("main");
  if (mainContent) {
    mainContent.style.opacity = "0";
    mainContent.style.transition = "opacity .18s ease";
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        mainContent.style.opacity = "1";
      });
    });
  }

  /* ═══════════════════════════════════════════════════════════
     3) LINK INTERCEPTION — progress bar on internal navigation
     ═══════════════════════════════════════════════════════════ */
  document.addEventListener("click", function (e) {
    var a = e.target.closest("a");
    if (!a) return;
    var href = a.getAttribute("href");
    if (!href || href.startsWith("#") || href.startsWith("http") ||
        href.startsWith("mailto:") || href.startsWith("javascript:")) return;
    if (a.target === "_blank") return;
    startProgress();
  });

  document.addEventListener("submit", function (e) {
    startProgress();
  });

  /* ═══════════════════════════════════════════════════════════
     4) SMART BACK — hierarchical fallback
     ═══════════════════════════════════════════════════════════ */
  // Map URL prefixes to their parent page for smart fallback
  var PARENT_MAP = {
    "/participants/":   "/participants",
    "/studies/":        "/studies",
    "/parameters/":     "/parameters",
    "/forms/":          "/forms",
    "/formulas/":       "/formulas",
    "/records/":        "/records",
    "/data/":           "/participants",
    "/adverse/":        "/adverse",
    "/visits/":         "/visits/upcoming",
    "/specimens":       "/dashboard",
    "/quality":         "/dashboard",
    "/alerts":          "/dashboard",
    "/criteria/":       "/criteria",
    "/analysis":        "/dashboard",
    "/graphs":          "/dashboard",
    "/statistics":      "/dashboard",
    "/longitudinal":    "/dashboard",
    "/reliability":     "/dashboard",
    "/print/":          "/print",
    "/export":          "/dashboard",
    "/import":          "/dashboard",
    "/data-dictionary": "/dashboard",
    "/users/":          "/users",
    "/audit":           "/dashboard",
    "/health":          "/dashboard",
    "/backups":         "/dashboard",
    "/settings":        "/settings",
    "/profile/":        "/dashboard",
    "/account/":        "/dashboard",
    "/admin/":          "/dashboard",
    "/webauthn/":       "/dashboard",
    "/learn/":          "/learn",
    "/quick-entry":     "/dashboard",
  };

  function smartBack() {
    if (history.length > 1) {
      history.back();
      return;
    }
    // No history — pick hierarchical parent
    for (var prefix in PARENT_MAP) {
      if (path.startsWith(prefix)) {
        // Handle /participants/<id> → /participants
        var parent = PARENT_MAP[prefix];
        window.location.href = parent;
        return;
      }
    }
    // Default: dashboard
    window.location.href = "/";
  }

  // Push a safe sentinel so back always has somewhere to go
  if (window.history && window.history.pushState) {
    if (!window.history.state || !window.history.state._pp) {
      try {
        history.pushState({ _pp: true }, "", location.href);
      } catch (e) {}
    }
  }

  // Detect Android hardware back
  window.addEventListener("popstate", function (e) {
    if (!e.state && path !== "/" && !isStandalone) {
      // User pressed back past our sentinel — go to hierarchical parent
      smartBack();
    }
  });

  /* ═══════════════════════════════════════════════════════════
     5) KEYBOARD SHORTCUTS
     ═══════════════════════════════════════════════════════════ */
  var SHORTCUTS = {
    "g d": "/",
    "g p": "/participants",
    "g s": "/studies",
    "g m": "/parameters",
    "g f": "/forms",
    "g r": "/records",
    "g a": "/analysis",
    "g g": "/graphs",
    "g q": "/quality",
    "g t": "/print",
    "g u": "/users",
    "g l": "/learn",
    "g e": "/quick-entry",
  };

  var gPending = false;
  var gTimer = null;

  document.addEventListener("keydown", function (e) {
    // Ignore when typing in inputs
    var tag = (e.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select" || e.target.isContentEditable) return;

    // Press "/" to focus search
    if (e.key === "/") {
      e.preventDefault();
      // Try to focus first search input on page
      var searchInput = document.querySelector(
        'input[type="search"], input[name="q"], .param-filter input, .part-filter input'
      );
      if (searchInput) {
        searchInput.focus();
        searchInput.select && searchInput.select();
      }
      return;
    }

    // Press "?" to show shortcuts help
    if (e.key === "?") {
      e.preventDefault();
      showShortcutHelp();
      return;
    }

    // Press "h" for home
    if (e.key === "h" && !e.ctrlKey && !e.metaKey && !gPending) {
      window.location.href = "/";
      return;
    }

    // g-sequences
    if (gPending) {
      var combo = "g " + e.key.toLowerCase();
      if (SHORTCUTS[combo]) {
        e.preventDefault();
        gPending = false;
        clearTimeout(gTimer);
        startProgress();
        window.location.href = SHORTCUTS[combo];
        return;
      }
      gPending = false;
    }

    if (e.key === "g") {
      gPending = true;
      clearTimeout(gTimer);
      gTimer = setTimeout(function () { gPending = false; }, 800);
    }
  });

  function showShortcutHelp() {
    var existing = document.getElementById("shortcut-help");
    if (existing) { existing.remove(); return; }

    var overlay = document.createElement("div");
    overlay.id = "shortcut-help";
    overlay.style.cssText =
      "position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:9999;" +
      "display:flex;align-items:center;justify-content:center;padding:20px;" +
      "backdrop-filter:blur(3px)";
    overlay.innerHTML = `
      <div style="background:#fff;border-radius:14px;padding:24px;max-width:520px;
                  width:100%;box-shadow:0 20px 50px rgba(0,0,0,.3)">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <h3 style="margin:0;font-size:16px;font-weight:800">Keyboard shortcuts</h3>
          <button onclick="document.getElementById('shortcut-help').remove()"
                  style="border:0;background:transparent;font-size:18px;cursor:pointer;color:#64748b">✕</button>
        </div>
        <table style="width:100%;font-size:13px;border-collapse:collapse">
          <tr><td style="padding:6px 0;color:#64748b">Go to Dashboard</td>
              <td style="text-align:right"><kbd style="background:#f1f5f9;padding:2px 6px;border-radius:4px;font-family:monospace">g</kbd> then <kbd style="background:#f1f5f9;padding:2px 6px;border-radius:4px;font-family:monospace">d</kbd></td></tr>
          <tr><td style="padding:6px 0;color:#64748b">Participants</td>
              <td style="text-align:right"><kbd style="background:#f1f5f9;padding:2px 6px;border-radius:4px;font-family:monospace">g p</kbd></td></tr>
          <tr><td style="padding:6px 0;color:#64748b">Studies</td>
              <td style="text-align:right"><kbd style="background:#f1f5f9;padding:2px 6px;border-radius:4px;font-family:monospace">g s</kbd></td></tr>
          <tr><td style="padding:6px 0;color:#64748b">Analysis</td>
              <td style="text-align:right"><kbd style="background:#f1f5f9;padding:2px 6px;border-radius:4px;font-family:monospace">g a</kbd></td></tr>
          <tr><td style="padding:6px 0;color:#64748b">Quick Entry</td>
              <td style="text-align:right"><kbd style="background:#f1f5f9;padding:2px 6px;border-radius:4px;font-family:monospace">g e</kbd></td></tr>
          <tr><td style="padding:6px 0;color:#64748b">Home</td>
              <td style="text-align:right"><kbd style="background:#f1f5f9;padding:2px 6px;border-radius:4px;font-family:monospace">h</kbd></td></tr>
          <tr><td style="padding:6px 0;color:#64748b">Focus search</td>
              <td style="text-align:right"><kbd style="background:#f1f5f9;padding:2px 6px;border-radius:4px;font-family:monospace">/</kbd></td></tr>
          <tr><td style="padding:6px 0;color:#64748b">Show this help</td>
              <td style="text-align:right"><kbd style="background:#f1f5f9;padding:2px 6px;border-radius:4px;font-family:monospace">?</kbd></td></tr>
          <tr><td style="padding:6px 0;color:#64748b">Back</td>
              <td style="text-align:right"><kbd style="background:#f1f5f9;padding:2px 6px;border-radius:4px;font-family:monospace">Esc</kbd> (in modal) or Android back</td></tr>
        </table>
        <p style="font-size:11.5px;color:#94a3b8;margin:14px 0 0;text-align:center">
          Press <b>?</b> again or tap outside to close
        </p>
      </div>
    `;
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) overlay.remove();
    });
    document.body.appendChild(overlay);
  }

  /* ═══════════════════════════════════════════════════════════
     6) MOBILE HAMBURGER STATE — persist open/closed
     ═══════════════════════════════════════════════════════════ */
  // Handled by app.js — no conflict

  /* ═══════════════════════════════════════════════════════════
     7) PAGE VISIBLE — auto-refresh stale tabs when user returns
     ═══════════════════════════════════════════════════════════ */
  var hiddenAt = null;
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      hiddenAt = Date.now();
    } else if (hiddenAt && Date.now() - hiddenAt > 30 * 60 * 1000) {
      // Tab was hidden > 30 min — soft reload to get fresh session
      // (only if not on a form page with unsaved data)
      var hasForm = document.querySelector("form input:not([type=hidden]):not([type=submit])");
      var dirty = false;
      document.querySelectorAll("input, textarea, select").forEach(function (el) {
        if (el.value && el.defaultValue !== el.value) dirty = true;
      });
      if (!dirty && !hasForm) location.reload();
    }
  });

  /* ═══════════════════════════════════════════════════════════
     8) LIGHTBOX for images in file lists
     ═══════════════════════════════════════════════════════════ */
  document.addEventListener("click", function (e) {
    var img = e.target.closest(".files-list img, .files-grid img");
    if (!img) return;
    e.preventDefault();
    var overlay = document.createElement("div");
    overlay.style.cssText =
      "position:fixed;inset:0;background:rgba(15,23,42,.9);z-index:9999;" +
      "display:flex;align-items:center;justify-content:center;padding:20px;cursor:zoom-out";
    var bigImg = document.createElement("img");
    bigImg.src = img.src;
    bigImg.style.cssText = "max-width:95%;max-height:95%;border-radius:12px;box-shadow:0 20px 50px rgba(0,0,0,.5)";
    overlay.appendChild(bigImg);
    overlay.addEventListener("click", function () { overlay.remove(); });
    document.addEventListener("keydown", function esc(e) {
      if (e.key === "Escape") { overlay.remove(); document.removeEventListener("keydown", esc); }
    });
    document.body.appendChild(overlay);
  });

  /* ═══════════════════════════════════════════════════════════
     9) FINISH PROGRESS on page load
     ═══════════════════════════════════════════════════════════ */
  window.addEventListener("load", function () {
    finishProgress();
  });

  // ── Expose smartBack globally in case pages need it ──
  window.smartBack = smartBack;
  window.startProgress = startProgress;
})();
