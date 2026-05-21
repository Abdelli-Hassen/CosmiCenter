/**
 * CosmittoHUB — Ticket-specific Interactions
 * Handles checkbox selection & bulk bar, inline status changes,
 * reply composer, filter auto-submit, and SLA countdowns.
 */

(function () {
  'use strict';

  // ─── Helpers ──────────────────────────────────────────────────────────────

  function toast() {
    return (window.CHUB && window.CHUB.toast) ? window.CHUB.toast : {
      success: function (t, m) { console.info(t, m); },
      error:   function (t, m) { console.error(t, m); },
      info:    function (t, m) { console.info(t, m); },
      warning: function (t, m) { console.warn(t, m); },
    };
  }

  function debounce(fn, delay) {
    if (window.CHUB && window.CHUB.debounce) return window.CHUB.debounce(fn, delay);
    var timer = null;
    return function () {
      var ctx = this; var args = arguments;
      clearTimeout(timer);
      timer = setTimeout(function () { fn.apply(ctx, args); }, delay);
    };
  }

  // ─── 1. Checkbox selection & bulk action bar ──────────────────────────────

  var lastCheckedCheckbox = null;

  function initBulkSelection() {
    var bulkBar    = document.getElementById('bulkBar');
    var bulkCount  = document.getElementById('bulkCount');
    var bulkClear  = document.getElementById('bulkClear');
    var selectAll  = document.getElementById('selectAll');

    if (!bulkBar) return;

    function getCheckboxes() {
      return Array.from(document.querySelectorAll('input.ticket-select[data-id]'));
    }

    function getSelected() {
      return getCheckboxes().filter(function (cb) { return cb.checked; });
    }

    function updateBulkBar() {
      var selected = getSelected();
      var count    = selected.length;

      if (bulkCount) bulkCount.textContent = count + ' selected';

      if (count >= 2) {
        bulkBar.classList.add('visible');
      } else {
        bulkBar.classList.remove('visible');
      }

      // Update select-all state
      if (selectAll) {
        var all = getCheckboxes();
        if (count === 0) {
          selectAll.checked       = false;
          selectAll.indeterminate = false;
        } else if (count === all.length) {
          selectAll.checked       = true;
          selectAll.indeterminate = false;
        } else {
          selectAll.checked       = false;
          selectAll.indeterminate = true;
        }
      }

      // Highlight selected rows
      getCheckboxes().forEach(function (cb) {
        var row = cb.closest('tr');
        if (row) row.classList.toggle('selected', cb.checked);
      });
    }

    // Individual checkbox change (with shift-click range support)
    document.addEventListener('change', function (e) {
      if (!e.target.classList.contains('ticket-select')) return;

      var current = e.target;

      // Shift-click range selection
      if (e.shiftKey && lastCheckedCheckbox && lastCheckedCheckbox !== current) {
        var checkboxes = getCheckboxes();
        var startIdx   = checkboxes.indexOf(lastCheckedCheckbox);
        var endIdx     = checkboxes.indexOf(current);

        if (startIdx !== -1 && endIdx !== -1) {
          var from = Math.min(startIdx, endIdx);
          var to   = Math.max(startIdx, endIdx);
          var targetState = current.checked;

          for (var i = from; i <= to; i++) {
            checkboxes[i].checked = targetState;
          }
        }
      }

      lastCheckedCheckbox = current;
      updateBulkBar();
    });

    // Shift-click on checkbox (mousedown to capture before change fires)
    document.addEventListener('click', function (e) {
      if (!e.target.classList.contains('ticket-select')) return;
      // The change event above handles the range logic; this just ensures
      // lastCheckedCheckbox is updated on simple clicks too (change does it).
    });

    // Select all
    if (selectAll) {
      selectAll.addEventListener('change', function () {
        getCheckboxes().forEach(function (cb) {
          cb.checked = selectAll.checked;
        });
        lastCheckedCheckbox = null;
        updateBulkBar();
      });
    }

    // Clear selection
    if (bulkClear) {
      bulkClear.addEventListener('click', function () {
        getCheckboxes().forEach(function (cb) { cb.checked = false; });
        lastCheckedCheckbox = null;
        updateBulkBar();
      });
    }

    // Initial state
    updateBulkBar();
  }

  // ─── 2. Inline status change via API ─────────────────────────────────────

  function initInlineStatusChange() {
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-ticket-status-btn]');
      if (!btn) return;

      var ticketId  = btn.getAttribute('data-ticket-id')     || btn.closest('[data-ticket-id]') && btn.closest('[data-ticket-id]').getAttribute('data-ticket-id');
      var newStatus = btn.getAttribute('data-ticket-status-btn');

      if (!ticketId || !newStatus) return;

      e.preventDefault();

      // Show loading state
      var originalText     = btn.textContent;
      var originalDisabled = btn.disabled;
      btn.classList.add('btn-loading');
      btn.disabled = true;

      fetch('/api/tickets/' + encodeURIComponent(ticketId) + '/statut', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({ statut: newStatus }),
      })
      .then(function (res) {
        if (!res.ok) {
          return res.json().then(function (data) {
            throw new Error(data.message || data.error || ('HTTP ' + res.status));
          });
        }
        return res.json();
      })
      .then(function (data) {
        // Update status badge in the same row
        var row = btn.closest('tr, .ticket-card, [data-ticket-id]');
        if (row) {
          var badge = row.querySelector('.badge[data-status-badge], .status-badge, td .badge');
          if (badge) {
            // Remove all status classes and set new one
            badge.className = badge.className.replace(/\bbadge-\S+/g, '').trim();
            badge.classList.add('badge', 'badge-' + slugifyStatus(newStatus));
            badge.textContent = newStatus.replace(/_/g, ' ');
          }
        }
        toast().success('Status updated', 'Ticket status changed to "' + newStatus + '".');
      })
      .catch(function (err) {
        toast().error('Update failed', err.message || 'Could not update ticket status.');
      })
      .finally(function () {
        btn.classList.remove('btn-loading');
        btn.disabled = originalDisabled;
        btn.textContent = originalText;
      });
    });
  }

  function slugifyStatus(status) {
    // Map French status names to badge class suffixes
    var map = {
      'nouveau':      'new',
      'new':          'new',
      'en_cours':     'progress',
      'in_progress':  'progress',
      'en cours':     'progress',
      'en attente':   'waiting',
      'waiting':      'waiting',
      'resolu':       'resolved',
      'resolved':     'resolved',
      'ferme':        'closed',
      'closed':       'closed',
      'annule':       'cancelled',
      'cancelled':    'cancelled',
    };
    return map[(status || '').toLowerCase()] || (status || '').toLowerCase().replace(/\s+/g, '-');
  }

  function getCsrfToken() {
    // Try meta tag first (Flask-WTF pattern)
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');
    // Try hidden input
    var input = document.querySelector('input[name="csrf_token"]');
    if (input) return input.value;
    return '';
  }

  // ─── 3. Reply composer ────────────────────────────────────────────────────

  function initReplyComposer() {
    var replyTextarea = document.getElementById('replyContent');
    if (!replyTextarea) {
      // Also try common class names
      replyTextarea = document.querySelector('.reply-textarea, textarea[name="contenu"]');
    }
    if (!replyTextarea) return;

    // Tab in empty textarea → AI draft request
    replyTextarea.addEventListener('keydown', function (e) {
      if (e.key !== 'Tab') return;
      if (replyTextarea.value.trim() !== '') return;
      // keyboard.js fires this too (capture phase), but we also handle here
      // for pages that don't have page-ticket-detail class
      e.preventDefault();
      document.dispatchEvent(new CustomEvent('ai:draft-request', {
        bubbles: true,
        detail: { textarea: replyTextarea },
      }));
    });

    // Listen for AI draft complete → typewriter effect
    document.addEventListener('ai:draft-complete', function (e) {
      if (!e.detail || !e.detail.text) return;
      var targetTextarea = (e.detail.textarea) || replyTextarea;
      typewriterEffect(targetTextarea, e.detail.text);
    });

    // Reply tab switching (Reply / Internal Note / Call Log)
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-reply-tab]');
      if (!btn) return;

      var tabName      = btn.getAttribute('data-reply-tab');
      var tabContainer = btn.closest('[data-reply-tabs], .reply-tabs-bar, .tabs') || document;

      // Deactivate sibling tab buttons
      tabContainer.querySelectorAll('[data-reply-tab]').forEach(function (b) {
        b.classList.remove('active');
      });
      btn.classList.add('active');

      // Show matching panel, hide others
      var panels = document.querySelectorAll('[data-reply-panel]');
      panels.forEach(function (panel) {
        var panelName = panel.getAttribute('data-reply-panel');
        panel.style.display = (panelName === tabName) ? '' : 'none';
        panel.classList.toggle('active', panelName === tabName);
      });

      // Adapt textarea placeholder
      var ta = document.querySelector('#replyContent, .reply-textarea');
      if (ta) {
        var placeholders = {
          'reply':    'Write a reply to the customer…',
          'internal': 'Add an internal note (not visible to customer)…',
          'call':     'Log a phone call…',
        };
        ta.placeholder = placeholders[tabName] || 'Write a reply…';
      }
    });
  }

  // ─── Typewriter effect ────────────────────────────────────────────────────

  function typewriterEffect(textarea, text) {
    if (!textarea || !text) return;

    // Disable the textarea while typing
    textarea.disabled = true;
    textarea.value = '';

    var chars   = text.split('');
    var idx     = 0;
    var DELAY   = 8; // ms per character ≈ 400 chars/sec

    function typeNext() {
      if (idx >= chars.length) {
        textarea.disabled = false;
        textarea.focus();
        // Place cursor at end
        textarea.setSelectionRange(textarea.value.length, textarea.value.length);
        return;
      }
      textarea.value += chars[idx];
      idx++;
      // Auto-scroll textarea
      textarea.scrollTop = textarea.scrollHeight;
      setTimeout(typeNext, DELAY);
    }

    typeNext();
  }

  // ─── 4. Filter form auto-submit ───────────────────────────────────────────

  function initTicketFilters() {
    var filterForm = document.getElementById('ticketFilterForm');
    if (!filterForm) {
      // Also pick up generic filter forms on ticket list pages
      filterForm = document.querySelector('.filter-form, form.ticket-filters');
    }
    if (!filterForm) return;

    // Auto-submit on any select change
    filterForm.querySelectorAll('select').forEach(function (sel) {
      sel.addEventListener('change', function () {
        filterForm.submit();
      });
    });

    // Pre-fill selects from URL search params
    try {
      var params = new URLSearchParams(window.location.search);
      params.forEach(function (value, key) {
        var el = filterForm.querySelector('[name="' + key + '"]');
        if (el && el.tagName === 'SELECT') {
          el.value = value;
        } else if (el && el.tagName === 'INPUT') {
          el.value = value;
        }
      });
    } catch (e) {}
  }

  // ─── 5. SLA countdown ────────────────────────────────────────────────────

  var slaElements = [];

  function initSlaCountdowns() {
    var elements = document.querySelectorAll('[data-sla-deadline]');
    if (!elements.length) return;

    slaElements = Array.from(elements).map(function (el) {
      var deadline = new Date(el.getAttribute('data-sla-deadline'));
      // Find the bar fill if present
      var barFill = el.querySelector('.sla-bar-fill') ||
                    (el.nextElementSibling && el.nextElementSibling.querySelector && el.nextElementSibling.querySelector('.sla-bar-fill'));
      return { el: el, deadline: deadline, barFill: barFill };
    });

    updateSlaAll();

    // Update every 30 seconds
    setInterval(updateSlaAll, 30000);
  }

  function updateSlaAll() {
    var now = Date.now();
    slaElements.forEach(function (item) {
      updateSlaElement(item, now);
    });
  }

  function updateSlaElement(item, now) {
    var deadline = item.deadline;
    if (!deadline || isNaN(deadline.getTime())) return;

    var deadlineMs  = deadline.getTime();
    var remaining   = deadlineMs - now;

    // Remove all SLA classes
    item.el.classList.remove('sla-ok', 'sla-warning', 'sla-danger', 'sla-overdue');

    if (remaining <= 0) {
      item.el.textContent = 'OVERDUE';
      item.el.classList.add('sla-overdue');
      if (item.barFill) {
        item.barFill.style.width = '100%';
        item.barFill.className = item.barFill.className.replace(/\b(ok|warning|danger)\b/g, '').trim();
        item.barFill.classList.add('danger');
      }
      return;
    }

    // Format remaining time
    item.el.textContent = formatSlaTime(remaining);

    // Determine urgency — use creation date if available, else use a default 8h window
    var totalMs = getSlaTotal(item.el, deadline);
    var pctLeft = totalMs > 0 ? (remaining / totalMs) : 1;

    var statusClass;
    var barClass;
    if (pctLeft > 0.5) {
      statusClass = 'sla-ok';
      barClass    = 'ok';
    } else if (pctLeft > 0.25) {
      statusClass = 'sla-warning';
      barClass    = 'warning';
    } else {
      statusClass = 'sla-danger';
      barClass    = 'danger';
    }

    item.el.classList.add(statusClass);

    if (item.barFill) {
      item.barFill.style.width = Math.min(100, Math.round(pctLeft * 100)) + '%';
      item.barFill.className   = item.barFill.className.replace(/\b(ok|warning|danger)\b/g, '').trim();
      item.barFill.classList.add(barClass);
    }
  }

  function getSlaTotal(el, deadline) {
    // Try data-sla-total-ms attribute for explicit total window
    var totalAttr = el.getAttribute('data-sla-total-ms');
    if (totalAttr) return parseInt(totalAttr, 10);

    // Try data-sla-created for creation date
    var created = el.getAttribute('data-sla-created') || el.getAttribute('data-created');
    if (created) {
      var createdDate = new Date(created);
      if (!isNaN(createdDate.getTime())) {
        return deadline.getTime() - createdDate.getTime();
      }
    }

    // Default to 8-hour SLA window
    return 8 * 60 * 60 * 1000;
  }

  function formatSlaTime(ms) {
    if (ms <= 0) return 'OVERDUE';

    var totalSec = Math.floor(ms / 1000);
    var totalMin = Math.floor(totalSec / 60);
    var totalHr  = Math.floor(totalMin / 60);
    var days     = Math.floor(totalHr / 24);
    var hrs      = totalHr % 24;
    var mins     = totalMin % 60;

    if (days > 0) {
      return days + 'd ' + hrs + 'h';
    }
    if (totalHr > 0) {
      return totalHr + 'h ' + mins + 'm';
    }
    return mins + 'm';
  }

  // ─── Init ─────────────────────────────────────────────────────────────────

  function init() {
    initBulkSelection();
    initInlineStatusChange();
    initReplyComposer();
    initTicketFilters();
    initSlaCountdowns();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
