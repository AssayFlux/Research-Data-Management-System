/* ============================================================
   Research DMS — unified app.js
   Handles: sidebar, user dropdown, collapsible groups,
            active links, overlay, auto-close.
   ============================================================ */
(function () {
  "use strict";

  function $(sel, ctx) { return (ctx || document).querySelector(sel); }
  function $$(sel, ctx) { return [...(ctx || document).querySelectorAll(sel)]; }

  /* ═══════════════════════════════════════════════════════
     1) SIDEBAR TOGGLE (mobile hamburger)
     ═══════════════════════════════════════════════════════ */
  const side    = document.getElementById("sidebar");
  const overlay = document.getElementById("overlay");
  const menu    = document.getElementById("menu");
  const closeBtn= document.getElementById("sidebar-close");

  function openSidebar() {
    if (!side) return;
    side.classList.add("open");
    if (overlay) overlay.classList.add("show");
    document.body.style.overflow = "hidden";
  }
  function closeSidebar() {
    if (!side) return;
    side.classList.remove("open");
    if (overlay) overlay.classList.remove("show");
    document.body.style.overflow = "";
  }
  function toggleSidebar() {
    if (!side) return;
    side.classList.contains("open") ? closeSidebar() : openSidebar();
  }

  if (menu)     menu.addEventListener("click", e => { e.preventDefault(); toggleSidebar(); });
  if (overlay)  overlay.addEventListener("click", closeSidebar);
  if (closeBtn) closeBtn.addEventListener("click", closeSidebar);

  document.addEventListener("keydown", e => {
    if (e.key === "Escape") {
      closeSidebar();
      closeUserMenu();
    }
  });

  // Auto-close sidebar on nav click (mobile)
  $$(".sb-nav a").forEach(a => {
    const href = a.getAttribute("href") || "";
    if (href && href !== "#" && !href.startsWith("javascript")) {
      a.addEventListener("click", () => {
        if (window.matchMedia("(max-width: 900px)").matches) {
          setTimeout(closeSidebar, 80);
        }
      });
    }
  });

  /* ═══════════════════════════════════════════════════════
     2) USER DROPDOWN (top-right chip)
     ═══════════════════════════════════════════════════════ */
  const chip = document.getElementById("userchip");
  const umenu = document.getElementById("user-menu");

  function openUserMenu() {
    if (!chip) return;
    chip.classList.add("open");
  }
  function closeUserMenu() {
    if (!chip) return;
    chip.classList.remove("open");
  }

  if (chip && umenu) {
    chip.addEventListener("click", e => {
      // Don't trigger if clicking inside a form/button/link inside menu
      const target = e.target;
      if (target.closest(".user-menu a")) return;
      e.stopPropagation();
      chip.classList.toggle("open");
    });

    // Clicking a menu item closes the menu
    umenu.addEventListener("click", e => {
      const a = e.target.closest("a");
      if (a) {
        // Let the link work naturally, just close the dropdown
        setTimeout(closeUserMenu, 50);
      }
      e.stopPropagation();
    });
  }

  // Click anywhere else closes dropdown
  document.addEventListener("click", e => {
    if (!chip) return;
    if (!e.target.closest("#userchip")) closeUserMenu();
  });

  /* ═══════════════════════════════════════════════════════
     3) COLLAPSIBLE SIDEBAR GROUPS
     ═══════════════════════════════════════════════════════ */
  const GROUPS = $$(".sb-group");
  const STORAGE_KEY = "rdm-sidebar-groups";
  const path = location.pathname;

  function getStored() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; }
    catch (e) { return {}; }
  }
  function saveStored(obj) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(obj)); }
    catch (e) {}
  }

  // Find the group containing the current path — longest match wins
  function findActiveGroup() {
    let best = null, bestLen = 0;
    GROUPS.forEach(g => {
      $$("a[data-path]", g).forEach(a => {
        const p = a.dataset.path;
        const exact = a.dataset.exact === "1";
        const matches = exact
          ? path === p
          : (path === p || path.startsWith(p + "/") || path.startsWith(p + "?"));
        if (matches && p.length > bestLen) {
          bestLen = p.length;
          best = g;
        }
      });
    });
    return best;
  }

  const activeGroup = findActiveGroup();
  const stored = getStored();

  GROUPS.forEach(g => {
    const name = g.dataset.group;
    const head = $(".sb-group-head", g);

    let shouldOpen;
    if (stored[name] === true)       shouldOpen = true;
    else if (stored[name] === false) shouldOpen = false;
    else if (activeGroup === g)      shouldOpen = true;
    else if (name === "workspace")   shouldOpen = true;   // default open
    else                             shouldOpen = false;

    if (shouldOpen) g.classList.add("open");

    if (head) {
      head.addEventListener("click", e => {
        e.preventDefault();
        const now = !g.classList.contains("open");
        g.classList.toggle("open", now);
        const cur = getStored();
        cur[name] = now;
        saveStored(cur);
      });
    }
  });

  /* ═══════════════════════════════════════════════════════
     4) ACTIVE LINK HIGHLIGHT (longest-match)
     ═══════════════════════════════════════════════════════ */
  const allLinks = $$(".sb-nav a[data-path]");
  allLinks.sort((a, b) => b.dataset.path.length - a.dataset.path.length);

  let winner = null;
  for (const a of allLinks) {
    const p = a.dataset.path;
    const exact = a.dataset.exact === "1";
    const matches = exact
      ? path === p
      : (path === p || path.startsWith(p + "/") || path.startsWith(p + "?"));
    if (matches) { winner = a; break; }
  }
  if (winner) winner.classList.add("active");

})();

/* ══════════════════════════════════════════════════════════════
   Settings — simple picker behaviour
   ══════════════════════════════════════════════════════════════ */
(function() {
  // Live: hex input updates the swatch + underlying colour input
  window.simpHexInput = function(input, field) {
    var v = input.value.trim();
    if (!v.startsWith('#')) v = '#' + v;
    if (!/^#[0-9a-fA-F]{6}$/.test(v)) return;
    var swatch = input.closest('.simp').querySelector('input[type=color]');
    var view = input.closest('.simp').querySelector('.simp-swatch-view');
    if (swatch) swatch.value = v;
    if (view) view.style.background = v;
  };

  // Live: colour input updates the hex + swatch
  document.querySelectorAll('.simp-swatch input[type=color]').forEach(function(wheel) {
    wheel.addEventListener('input', function() {
      var simp = this.closest('.simp');
      var hex = simp.querySelector('.simp-hex');
      var view = simp.querySelector('.simp-swatch-view');
      if (hex) hex.value = this.value.toUpperCase();
      if (view) view.style.background = this.value;
    });
  });

  // Gradient modal
  var currentField = null;
  var modal = null;

  window.simpOpenGrad = function(field) {
    currentField = field;
    if (!modal) {
      modal = document.createElement('div');
      modal.className = 'simp-grad-modal';
      modal.innerHTML = '<div class="simp-grad-card">' +
        '<div class="simp-grad-head"><h3>Choose a gradient</h3>' +
        '<button class="simp-grad-close" type="button">✕</button></div>' +
        '<input type="search" class="simp-grad-search" placeholder="Search gradients…">' +
        '<div class="simp-grad-grid"></div></div>';
      document.body.appendChild(modal);

      // Load all 3900 gradients
      var grid = modal.querySelector('.simp-grad-grid');
      var cells = [];
      for (var i = 1; i <= 3900; i++) {
        var c = document.createElement('div');
        c.className = 'simp-grad-cell g-' + String(i).padStart(4, '0');
        c.dataset.css = '';  // filled on first paint
        c.dataset.num = i;
        cells.push(c);
      }
      cells.forEach(function(c) { grid.appendChild(c); });

      // Read computed CSS once
      requestAnimationFrame(function() {
        cells.forEach(function(c) {
          c.dataset.css = getComputedStyle(c).backgroundImage;
        });
      });

      // Click cell → set gradient
      grid.addEventListener('click', function(e) {
        var cell = e.target.closest('.simp-grad-cell');
        if (!cell || !currentField) return;
        var inp = document.getElementById('grad_in_' + currentField);
        if (inp) inp.value = cell.dataset.css;

        // Show the active-gradient bar
        var simp = inp.closest('.simp');
        var oldBar = simp.querySelector('.simp-active-grad');
        if (oldBar) oldBar.remove();
        var bar = document.createElement('div');
        bar.className = 'simp-active-grad';
        bar.id = 'ag_' + currentField;
        bar.style.background = cell.dataset.css;
        bar.innerHTML = '<button type="button" class="simp-grad-clear" title="Remove">✕</button>';
        simp.appendChild(bar);
        bar.querySelector('.simp-grad-clear').onclick = function() {
          simpClearGrad(currentField);
        };
        modal.classList.remove('open');
      });

      // Close on backdrop / X
      modal.addEventListener('click', function(e) {
        if (e.target === modal || e.target.classList.contains('simp-grad-close')) {
          modal.classList.remove('open');
        }
      });

      // Search
      modal.querySelector('.simp-grad-search').addEventListener('input', function() {
        var q = this.value.trim().toLowerCase();
        var visible = 0;
        grid.querySelectorAll('.simp-grad-cell').forEach(function(c) {
          var show = !q || c.dataset.num.indexOf(q) !== -1;
          c.style.display = show ? '' : 'none';
          if (show) visible++;
        });
      });
    }
    modal.classList.add('open');
    modal.querySelector('.simp-grad-search').value = '';
    modal.querySelector('.simp-grad-search').focus();
  };

  window.simpClearGrad = function(field) {
    var inp = document.getElementById('grad_in_' + field);
    if (inp) inp.value = '';
    var simp = inp.closest('.simp');
    var bar = simp.querySelector('.simp-active-grad');
    if (bar) bar.remove();
  };
})();
