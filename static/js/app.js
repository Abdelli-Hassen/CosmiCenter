/**
 * CosmittoHUB — Main Entry Point
 * Initializes all modules, sets up global UI behaviours, and exposes
 * the window.CHUB namespace with shared utilities.
 */

(function () {
  'use strict';

  // ─── Utility: debounce ────────────────────────────────────────────────────

  /**
   * Returns a debounced version of fn that fires after `delay` ms of silence.
   * @param {Function} fn
   * @param {number} delay - milliseconds
   * @returns {Function}
   */
  function debounce(fn, delay) {
    var timer = null;
    return function () {
      var ctx = this;
      var args = arguments;
      clearTimeout(timer);
      timer = setTimeout(function () {
        fn.apply(ctx, args);
      }, delay);
    };
  }

  // ─── Utility: formatRelativeTime ──────────────────────────────────────────

  /**
   * Format a Date (or ISO string) as a human-friendly relative time string.
   * Returns strings like "2m ago", "1h ago", "3d ago", "just now".
   * @param {Date|string|number} date
   * @returns {string}
   */
  function formatRelativeTime(date) {
    var d = (date instanceof Date) ? date : new Date(date);
    var now = Date.now();
    var diffMs = now - d.getTime();

    if (isNaN(diffMs)) return '';

    var diffSec = Math.floor(diffMs / 1000);
    var diffMin = Math.floor(diffSec / 60);
    var diffHr  = Math.floor(diffMin / 60);
    var diffDay = Math.floor(diffHr / 24);
    var diffWk  = Math.floor(diffDay / 7);
    var diffMo  = Math.floor(diffDay / 30);
    var diffYr  = Math.floor(diffDay / 365);

    if (diffSec < 30)  return 'just now';
    if (diffMin < 60)  return diffMin + 'm ago';
    if (diffHr  < 24)  return diffHr  + 'h ago';
    if (diffDay < 7)   return diffDay + 'd ago';
    if (diffWk  < 5)   return diffWk  + 'w ago';
    if (diffMo  < 12)  return diffMo  + 'mo ago';
    return diffYr + 'y ago';
  }

  // ─── Theme initialisation (before DOM ready to avoid FOUC) ───────────────

  (function initThemeEarly() {
    try {
      var saved = localStorage.getItem('chub-theme');
      if (saved === 'light' || saved === 'dark') {
        document.body.dataset.theme = saved;
      } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
        document.body.dataset.theme = 'light';
      } else {
        document.body.dataset.theme = 'dark';
      }
    } catch (e) {
      document.body.dataset.theme = 'dark';
    }
  })();

  // ─── Ripple effect ────────────────────────────────────────────────────────

  function createRipple(e) {
    var btn = e.currentTarget;
    var rect = btn.getBoundingClientRect();
    var size = Math.max(rect.width, rect.height) * 2;
    var x = e.clientX - rect.left - size / 2;
    var y = e.clientY - rect.top  - size / 2;

    var ripple = document.createElement('span');
    ripple.className = 'ripple';
    ripple.style.cssText =
      'width:' + size + 'px;height:' + size + 'px;' +
      'left:' + x + 'px;top:' + y + 'px;';

    btn.appendChild(ripple);
    ripple.addEventListener('animationend', function () {
      if (ripple.parentNode) ripple.parentNode.removeChild(ripple);
    });
  }

  function setupRipples() {
    // Use event delegation on document for dynamically added buttons
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.btn');
      if (btn) createRipple({ currentTarget: btn, clientX: e.clientX, clientY: e.clientY });
    });
  }

  // ─── Auto-dismiss alerts ──────────────────────────────────────────────────

  function setupAutoDismissAlerts() {
    var alerts = document.querySelectorAll('.alert[data-auto-dismiss], .alert-dismissible');
    alerts.forEach(function (el) {
      var delay = parseInt(el.getAttribute('data-auto-dismiss') || '5000', 10);
      if (!isNaN(delay) && delay > 0) {
        setTimeout(function () {
          el.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
          el.style.opacity = '0';
          el.style.transform = 'translateY(-8px)';
          setTimeout(function () {
            if (el.parentNode) el.parentNode.removeChild(el);
          }, 300);
        }, delay);
      }

      // Bind close button inside alert if present
      var closeBtn = el.querySelector('.alert-close, [data-dismiss="alert"]');
      if (closeBtn) {
        closeBtn.addEventListener('click', function () {
          el.style.transition = 'opacity 0.2s ease';
          el.style.opacity = '0';
          setTimeout(function () {
            if (el.parentNode) el.parentNode.removeChild(el);
          }, 200);
        });
      }
    });
  }


  // ─── Mobile sidebar overlay ───────────────────────────────────────────────

  function setupMobileSidebar() {
    var mobileToggle = document.getElementById('mobile-nav-toggle');
    var sidebar      = document.querySelector('.sidebar');
    if (!mobileToggle || !sidebar) return;

    // Create backdrop overlay
    var backdrop = document.createElement('div');
    backdrop.id = 'mobileSidebarBackdrop';
    backdrop.style.cssText =
      'position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:299;display:none;';
    document.body.appendChild(backdrop);

    function openMobileSidebar() {
      sidebar.classList.add('mobile-open');
      backdrop.style.display = 'block';
      document.body.style.overflow = 'hidden';
    }

    function closeMobileSidebar() {
      sidebar.classList.remove('mobile-open');
      backdrop.style.display = 'none';
      document.body.style.overflow = '';
    }

    mobileToggle.addEventListener('click', function () {
      if (sidebar.classList.contains('mobile-open')) {
        closeMobileSidebar();
      } else {
        openMobileSidebar();
      }
    });

    backdrop.addEventListener('click', closeMobileSidebar);

    // Close on Esc
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && sidebar.classList.contains('mobile-open')) {
        closeMobileSidebar();
      }
    });
  }

  // ─── Dropdown menus ───────────────────────────────────────────────────────

  function closeAllDropdowns(except) {
    document.querySelectorAll('.dropdown.open').forEach(function (dd) {
      if (dd !== except) {
        dd.classList.remove('open');
        dd.style.display = 'none';
      }
    });
  }

  function setupDropdowns() {
    // Use event delegation — triggers have data-dropdown="<dropdownId>"
    document.addEventListener('click', function (e) {
      var trigger = e.target.closest('[data-dropdown]');

      if (!trigger) {
        closeAllDropdowns(null);
        return;
      }

      e.stopPropagation();
      var targetId = trigger.getAttribute('data-dropdown');
      var dropdown = document.getElementById(targetId);
      if (!dropdown) return;

      var isOpen = dropdown.classList.contains('open');
      closeAllDropdowns(null);

      if (!isOpen) {
        dropdown.classList.add('open');
        dropdown.style.display = 'block';

        // Position: prevent overflow right
        var rect = trigger.getBoundingClientRect();
        var viewportW = window.innerWidth;
        dropdown.style.left = 'auto';
        dropdown.style.right = 'auto';
        if (rect.left + 200 > viewportW - 8) {
          dropdown.style.right = (viewportW - rect.right) + 'px';
        } else {
          dropdown.style.left = '0';
        }
      }
    });
  }

  // ─── Tab switching ────────────────────────────────────────────────────────

  function setupTabs() {
    // Buttons with [data-tab-btn] attribute, value is the tab panel id to activate
    // Also looks for a parent [data-tabs] container to scope sibling tabs
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-tab-btn]');
      if (!btn) return;

      var targetTabId = btn.getAttribute('data-tab-btn');
      var container   = btn.closest('[data-tabs]') || btn.closest('.tabs')
                        || (btn.parentElement && btn.parentElement.closest('[data-tabs]'))
                        || document;

      // Deactivate all sibling tab buttons
      var allBtns = container.querySelectorAll('[data-tab-btn]');
      allBtns.forEach(function (b) { b.classList.remove('active'); });

      // Activate clicked button
      btn.classList.add('active');

      // Find associated panel — look in closest common ancestor
      var panel = document.getElementById(targetTabId);
      if (!panel) {
        // Try relative lookup
        panel = container.querySelector('[data-tab-panel="' + targetTabId + '"]');
      }

      if (panel) {
        // Deactivate sibling panels
        var panelParent = panel.parentElement;
        if (panelParent) {
          panelParent.querySelectorAll('.tab-panel').forEach(function (p) {
            p.classList.remove('active');
          });
        }
        panel.classList.add('active');
      }
    });
  }

  // ─── Main init ────────────────────────────────────────────────────────────

  function init() {
    setupRipples();
    setupAutoDismissAlerts();
    setupMobileSidebar();
    setupDropdowns();
    setupTabs();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // ─── Export namespace ──────────────────────────────────────────────────────

  window.CHUB = window.CHUB || {};
  window.CHUB.debounce         = debounce;
  window.CHUB.formatRelativeTime = formatRelativeTime;

})();
