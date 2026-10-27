/**
 * CosmiCenter — Toast Notifications & Notification Panel
 * Provides window.CHUB.toast API and notification panel toggle.
 */

(function () {
  'use strict';

  // ─── Container ────────────────────────────────────────────────────────────

  let container = null;

  function getContainer() {
    if (container && document.body.contains(container)) return container;
    container = document.getElementById('toastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toastContainer';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    return container;
  }

  // ─── Icons ─────────────────────────────────────────────────────────────────

  const ICONS = {
    success: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/><path d="M5 8l2 2 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    error: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/><path d="M5.5 5.5l5 5M10.5 5.5l-5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
    warning: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2L14 13H2L8 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M8 6v3M8 11v.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
    info: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/><path d="M8 7v4M8 5v.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  };

  const DEFAULT_DURATIONS = {
    success: 4000,
    error: 8000,
    warning: 6000,
    info: 5000,
  };

  const MAX_TOASTS = 3;

  // Track active toasts for max enforcement
  const activeToasts = [];

  // ─── Core show function ────────────────────────────────────────────────────

  /**
   * Show a toast notification.
   * @param {Object} opts
   * @param {string} opts.title
   * @param {string} [opts.message]
   * @param {string} [opts.type='info'] - 'success'|'error'|'warning'|'info'
   * @param {number} [opts.duration]
   * @param {Object} [opts.action] - { label: string, onClick: fn }
   */
  function show(opts) {
    const type = opts.type || 'info';
    const duration = (opts.duration !== undefined) ? opts.duration : (DEFAULT_DURATIONS[type] || 5000);
    const c = getContainer();
    
    // Son : « ticket envoyé » (toast « Ticket créé… ») ou « ticket reçu » (demandé par le sondage des notifications)
    try {
      let sound = opts.sound;
      if (!sound && type === 'success') {
        const txt = ((opts.title || '') + ' ' + (opts.message || '')).toLowerCase();
        if (txt.includes('ticket') && txt.includes('créé')) sound = 'sent';
      }
      if (sound && window.CHUB && window.CHUB.sound) window.CHUB.sound.play(sound);
    } catch (err) {}

    // Enforce max — dismiss oldest
    while (activeToasts.length >= MAX_TOASTS) {
      const oldest = activeToasts.shift();
      if (oldest && oldest.parentNode) {
        dismissToast(oldest, true);
      }
    }

    // Build toast element
    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');

    let actionHTML = '';
    if (opts.action && opts.action.label) {
      actionHTML = '<button class="toast-action" type="button">' +
        escapeHtml(opts.action.label) + '</button>';
    }

    toast.innerHTML =
      '<span class="toast-icon">' + (ICONS[type] || ICONS.info) + '</span>' +
      '<div class="toast-content">' +
      '<div class="toast-title">' + escapeHtml(opts.title || '') + '</div>' +
      (opts.message ? '<div class="toast-message">' + escapeHtml(opts.message) + '</div>' : '') +
      actionHTML +
      '</div>' +
      '<button class="toast-close" type="button" aria-label="Close notification">' +
      '<svg width="14" height="14" viewBox="0 0 14 14" fill="none">' +
      '<path d="M2 2l10 10M12 2L2 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>' +
      '</svg>' +
      '</button>' +
      '<div class="toast-progress"></div>';

    c.appendChild(toast);
    activeToasts.push(toast);

    // Bind action button
    if (opts.action && typeof opts.action.onClick === 'function') {
      const actionBtn = toast.querySelector('.toast-action');
      if (actionBtn) {
        actionBtn.addEventListener('click', function () {
          opts.action.onClick();
          dismissToast(toast);
        });
      }
    }

    // Bind close button
    toast.querySelector('.toast-close').addEventListener('click', function () {
      dismissToast(toast);
    });

    // Progress bar animation using requestAnimationFrame
    const progressBar = toast.querySelector('.toast-progress');
    let startTime = null;
    let pausedAt = null;
    let rafId = null;

    function animateProgress(ts) {
      if (startTime === null) startTime = ts;
      const elapsed = ts - startTime;
      const pct = Math.max(0, 100 - (elapsed / duration) * 100);
      progressBar.style.width = pct + '%';
      if (elapsed < duration) {
        rafId = requestAnimationFrame(animateProgress);
      } else {
        dismissToast(toast);
      }
    }

    function pauseProgress() {
      if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = null;
        pausedAt = performance.now();
      }
    }

    function resumeProgress() {
      if (pausedAt !== null) {
        const pauseDuration = performance.now() - pausedAt;
        if (startTime !== null) startTime += pauseDuration;
        pausedAt = null;
        rafId = requestAnimationFrame(animateProgress);
      }
    }

    toast.addEventListener('mouseenter', pauseProgress);
    toast.addEventListener('mouseleave', resumeProgress);
    toast.addEventListener('focusin', pauseProgress);
    toast.addEventListener('focusout', resumeProgress);

    if (duration > 0) {
      rafId = requestAnimationFrame(animateProgress);
    } else {
      // No auto-dismiss — hide progress bar
      progressBar.style.display = 'none';
    }

    return toast;
  }

  // ─── Dismiss helper ────────────────────────────────────────────────────────

  function dismissToast(toast, immediate) {
    if (!toast || !toast.parentNode) return;
    // Remove from tracking array
    const idx = activeToasts.indexOf(toast);
    if (idx !== -1) activeToasts.splice(idx, 1);

    if (immediate) {
      toast.parentNode.removeChild(toast);
      return;
    }

    toast.classList.add('dismissing');
    toast.addEventListener('animationend', function handler() {
      toast.removeEventListener('animationend', handler);
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    });
    // Fallback removal after animation
    setTimeout(function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 350);
  }

  // ─── Shorthand helpers ─────────────────────────────────────────────────────

  function success(title, message) {
    return show({ title: title, message: message, type: 'success' });
  }

  function error(title, message) {
    return show({ title: title, message: message, type: 'error' });
  }

  function warning(title, message) {
    return show({ title: title, message: message, type: 'warning' });
  }

  function info(title, message) {
    return show({ title: title, message: message, type: 'info' });
  }

  // ─── HTML escape utility ───────────────────────────────────────────────────

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // ─── Flask flash messages → toasts ────────────────────────────────────────

  /**
   * Map Flask alert category to toast type.
   */
  function flashCategoryToType(cat) {
    if (!cat) return 'info';
    cat = cat.toLowerCase();
    if (cat === 'danger' || cat === 'error') return 'error';
    if (cat === 'success') return 'success';
    if (cat === 'warning') return 'warning';
    return 'info';
  }

  /**
   * Find existing .alert elements in the DOM, convert them to toasts,
   * and hide the originals.
   */
  function convertFlashAlerts() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function (el) {
      // Determine type from class
      let type = 'info';
      ['success', 'warning', 'error', 'danger', 'info'].forEach(function (cls) {
        if (el.classList.contains('alert-' + cls)) {
          type = flashCategoryToType(cls);
        }
      });

      // Extract text — skip icon elements and close buttons
      let text = '';
      el.childNodes.forEach(function (node) {
        if (node.nodeType === Node.TEXT_NODE) {
          text += node.textContent;
        } else if (
          node.nodeType === Node.ELEMENT_NODE &&
          !node.classList.contains('alert-close') &&
          node.tagName !== 'I' &&
          node.tagName !== 'SVG'
        ) {
          text += node.textContent;
        }
      });
      text = text.trim();

      if (text) {
        show({ title: text, type: type });
      }

      // Hide original alert to avoid duplication
      el.style.display = 'none';
      el.setAttribute('aria-hidden', 'true');
    });
  }

  /**
   * Read data-flash-messages from body tag if present.
   * Expected format: JSON array of {message, category} or {title, type}
   */
  function processDataFlash() {
    const raw = document.body.getAttribute('data-flash-messages');
    if (!raw) return;
    try {
      const messages = JSON.parse(raw);
      if (Array.isArray(messages)) {
        messages.forEach(function (m) {
          show({
            title: m.message || m.title || '',
            message: m.detail || m.body || '',
            type: flashCategoryToType(m.category || m.type || 'info'),
          });
        });
      }
    } catch (e) {
      // Ignore malformed JSON
    }
  }

  /**
   * Read flash messages from #flashMessages div (used in base.html).
   */
  function processFlashDivs() {
    const flashContainer = document.getElementById('flashMessages');
    if (!flashContainer) return;

    const messages = flashContainer.querySelectorAll('[data-flash-type]');
    messages.forEach(function (msg) {
      const type = flashCategoryToType(msg.getAttribute('data-flash-type'));
      const text = msg.getAttribute('data-flash-message');
      if (text) {
        show({ title: text, type: type });
      }
    });
  }

  // ─── Notification Panel ────────────────────────────────────────────────────

  function initNotificationPanel() {
    const notifBtn = document.getElementById('notif-btn');
    const notifPanel = document.getElementById('notifPanel');

    if (!notifBtn || !notifPanel) return;

    notifBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      notifPanel.classList.toggle('open');
    });

    // Click outside closes panel
    document.addEventListener('click', function (e) {
      if (
        notifPanel.classList.contains('open') &&
        !notifPanel.contains(e.target) &&
        e.target !== notifBtn &&
        !notifBtn.contains(e.target)
      ) {
        notifPanel.classList.remove('open');
      }
    });

    // Mark all read button
    const markAllRead = document.getElementById('mark-all-read');
    if (markAllRead) {
      markAllRead.addEventListener('click', function () {
        fetch('/api/notifications/marquer-lues', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        }).then(res => res.json()).then(data => {
          if (data.success) {
            const unreadItems = notifPanel.querySelectorAll('.notif-item.unread');
            unreadItems.forEach(function (item) {
              item.classList.remove('unread', 'unread-info', 'unread-success', 'unread-warning');
              const dot = item.querySelector('.notif-unread-dot');
              if (dot) dot.remove();
            });

            // Update badge count
            const badge = notifBtn.querySelector('.badge-count');
            if (badge) {
              badge.textContent = '0';
              badge.style.display = 'none';
            }
          }
        }).catch(err => console.error(err));
      });
    }
  }

  // ─── Initialise on DOM ready ───────────────────────────────────────────────

  function startPollingNotifications() {
    setInterval(function () {
      fetch('/api/notifications/poll')
        .then(res => res.json())
        .then(data => {
          if (data.success && data.data) {
            const notifs = data.data.unread_notifications;
            const msgs = data.data.unread_messages;

            // Handle new notifications (Toast + Dropdown update)
            const previousNotifs = window._lastNotifsCount !== undefined ? window._lastNotifsCount : notifs;
            window._lastNotifsCount = notifs;

            if (notifs !== previousNotifs && data.data.notifications) {
              if (notifs > previousNotifs && data.data.notifications.length > 0) {
                const newest = data.data.notifications[0];
                // Only show toast for non-chat notifications
                if (newest.titre !== 'Nouveau message') {
                  const t = ((newest.titre || '') + ' ' + (newest.message || '')).toLowerCase();
                  show({ title: newest.titre, message: newest.message, type: 'info',
                         sound: (t.includes('nouveau') && t.includes('ticket')) ? 'received' : undefined });
                }
              }

              // Update dropdown HTML
              const scroll = document.getElementById('notifScroll');
              if (scroll) {
                if (data.data.notifications.length === 0) {
                  scroll.innerHTML = `
                    <div class="empty-state">
                      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                        <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
                      </svg>
                      <div>Aucune nouvelle notification</div>
                    </div>
                  `;
                } else {
                  let html = '';
                  data.data.notifications.forEach(n => {
                    html += `<a href="${n.lien || '#'}" class="notif-item unread" style="text-decoration:none;">
                      <div class="notif-unread-dot"></div>
                      <div class="notif-item-content">
                        <div class="notif-item-title">${escapeHtml(n.titre)}</div>
                        ${n.message ? `<div class="notif-item-meta" style="margin-top:2px;">${escapeHtml(n.message)}</div>` : ''}
                        <div class="notif-item-meta" style="margin-top:4px;"><span>${escapeHtml(n.date)}</span></div>
                      </div>
                    </a>`;
                  });
                  scroll.innerHTML = html;
                }
              }
            }

            // Top Bell Badge
            const topBadge = document.getElementById('notifBadge');
            if (topBadge) {
              topBadge.textContent = notifs > 99 ? '99+' : notifs;
              topBadge.style.display = notifs > 0 ? 'inline-flex' : 'none';
            }

            // Tickets nav badge
            const ticketsBadge = document.getElementById('navTicketsBadge');
            if (ticketsBadge) {
              // nombre de tickets que l'utilisateur n'a pas encore ouverts
              const unopened = data.data.unopened_tickets !== undefined ? data.data.unopened_tickets : 0;
              ticketsBadge.textContent = unopened > 99 ? '99+' : unopened;
              ticketsBadge.style.display = unopened > 0 ? 'inline-block' : 'none';
            }

            // Messagerie nav badge : nombre de messages non lus
            const msgBadge = document.getElementById('navMessagesBadge');
            if (msgBadge) {
              msgBadge.textContent = msgs > 99 ? '99+' : msgs;
              msgBadge.style.display = msgs > 0 ? 'inline-block' : 'none';
            }
          }
        }).catch(err => console.error(err));
    }, 2500); // interrogation toutes les 2,5 secondes
  }


    function init() {
      convertFlashAlerts();
      processDataFlash();
      processFlashDivs();
      initNotificationPanel();
      startPollingNotifications();
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
    } else {
      init();
    }

    // ─── Export ────────────────────────────────────────────────────────────────

    window.CHUB = window.CHUB || {};
    window.CHUB.toast = {
      show: show,
      success: success,
      error: error,
      warning: warning,
      info: info,
    };

    // Mark ticket notification as read when visiting ticket
    document.addEventListener('DOMContentLoaded', () => {
      const match = window.location.pathname.match(/\/tickets\/(\d+)/);
      if (match) {
        const ticketId = match[1];
        fetch(`/api/notifications/tickets/${ticketId}/mark-read`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
      }

      // Also mark chat messages read when visiting chat
      if (window.location.pathname.includes('/chat')) {
        fetch('/api/notifications/chat/mark-read', { method: 'POST' });
      }
    });
  }) ();
