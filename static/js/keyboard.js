/**
 * CosmittoHUB — Global Keyboard Shortcuts
 * Handles application-wide keyboard shortcuts, chord sequences, and
 * page-specific behaviours for ticket list and detail pages.
 */

(function () {
  'use strict';

  // ─── State ────────────────────────────────────────────────────────────────

  let shortcutsEnabled = true;
  let chordFirstKey    = null;   // 'g' while waiting for second key in a chord
  let chordTimer       = null;   // setTimeout handle for chord window
  const CHORD_WINDOW   = 300;    // ms to press second key after first

  // ─── Page detection ───────────────────────────────────────────────────────

  const isTicketList   = document.body.classList.contains('page-tickets-list');
  const isTicketDetail = document.body.classList.contains('page-ticket-detail');

  // ─── Helpers ──────────────────────────────────────────────────────────────

  /**
   * Returns true if the event target is an editable field.
   * Shortcuts (except palette/Esc) should not fire while typing.
   */
  function isInEditableField(e) {
    const tag = (e.target && e.target.tagName) ? e.target.tagName.toUpperCase() : '';
    return (
      tag === 'INPUT' ||
      tag === 'TEXTAREA' ||
      tag === 'SELECT' ||
      (e.target && e.target.isContentEditable)
    );
  }

  /**
   * Close all open modals, panels, dropdowns visible in the DOM.
   */
  function closeAll() {
    // Dropdowns
    document.querySelectorAll('.dropdown.open').forEach(function (el) {
      el.classList.remove('open');
    });

    // Modal overlays
    document.querySelectorAll('.modal-overlay:not(.hidden), .panel-overlay:not(.hidden)')
      .forEach(function (el) {
        el.classList.add('hidden');
        el.classList.remove('open');
      });

    // Slide-over panels
    document.querySelectorAll('.panel.open').forEach(function (el) {
      el.classList.remove('open');
    });

    // Notification panel
    const notifPanel = document.getElementById('notifPanel');
    if (notifPanel) notifPanel.classList.remove('open');

    // Command palette
    if (window.CHUB && window.CHUB.cmdPalette) {
      window.CHUB.cmdPalette.close();
    }

    // Shortcuts modal (created by this module)
    const shortcutsModal = document.getElementById('shortcutsModal');
    if (shortcutsModal) shortcutsModal.classList.add('hidden');

    // Mobile sidebar
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
      sidebar.classList.remove('mobile-open');
      document.body.style.overflow = '';
    }
    const backdrop = document.getElementById('mobileSidebarBackdrop');
    if (backdrop) backdrop.style.display = 'none';
  }

  // ─── Keyboard shortcuts modal ─────────────────────────────────────────────

  const SHORTCUT_REFERENCE = [
    { category: 'Global',
      items: [
        { keys: ['⌘K', 'Ctrl+K'],    desc: 'Open command palette' },
        { keys: ['⌘N', 'Ctrl+N'],    desc: 'New ticket' },
        { keys: ['?'],               desc: 'Show this help' },
        { keys: ['Esc'],             desc: 'Close panel / modal' },
        { keys: ['⌘⇧L'],            desc: 'Toggle theme' },
      ],
    },
    { category: 'Navigation (chord)',
      items: [
        { keys: ['G', 'D'],  desc: 'Go to Dashboard' },
        { keys: ['G', 'Q'],  desc: 'Go to Ticket queue' },
        { keys: ['G', 'K'],  desc: 'Go to Knowledge base' },
        { keys: ['G', 'R'],  desc: 'Go to Reports' },
      ],
    },
    { category: 'Ticket list',
      items: [
        { keys: ['J'], desc: 'Focus next ticket' },
        { keys: ['K'], desc: 'Focus previous ticket' },
        { keys: ['X'], desc: 'Toggle row selection' },
        { keys: ['↵'], desc: 'Open focused ticket' },
      ],
    },
    { category: 'Ticket detail',
      items: [
        { keys: ['S'], desc: 'Open status picker' },
        { keys: ['A'], desc: 'Open assignee picker' },
        { keys: ['Tab (empty reply)'], desc: 'Request AI draft' },
      ],
    },
  ];

  function buildShortcutsModal() {
    let modal = document.getElementById('shortcutsModal');
    if (modal) return modal;

    modal = document.createElement('div');
    modal.id = 'shortcutsModal';
    modal.className = 'modal-overlay hidden';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-label', 'Keyboard shortcuts');

    const box = document.createElement('div');
    box.className = 'modal modal-md';

    const header = document.createElement('div');
    header.className = 'modal-header';
    header.innerHTML =
      '<h2 class="modal-title">⌨ Keyboard Shortcuts</h2>' +
      '<button class="modal-close" id="shortcutsModalClose" aria-label="Close">' +
        '<svg width="14" height="14" viewBox="0 0 14 14" fill="none">' +
        '<path d="M2 2l10 10M12 2L2 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>' +
        '</svg>' +
      '</button>';

    const body = document.createElement('div');
    body.className = 'modal-body';
    body.style.cssText = 'display:grid;grid-template-columns:1fr 1fr;gap:24px;';

    SHORTCUT_REFERENCE.forEach(function (section) {
      const section_el = document.createElement('div');

      const catTitle = document.createElement('div');
      catTitle.style.cssText =
        'font-size:11px;font-weight:700;color:var(--text-faint);text-transform:uppercase;' +
        'letter-spacing:0.6px;margin-bottom:8px;';
      catTitle.textContent = section.category;

      section_el.appendChild(catTitle);

      section.items.forEach(function (item) {
        const row = document.createElement('div');
        row.style.cssText =
          'display:flex;align-items:center;justify-content:space-between;' +
          'padding:4px 0;border-bottom:1px solid var(--border-subtle);gap:8px;';

        const desc = document.createElement('span');
        desc.style.cssText = 'font-size:13px;color:var(--text-secondary);flex:1;';
        desc.textContent = item.desc;

        const kbdGroup = document.createElement('span');
        kbdGroup.style.cssText = 'display:flex;align-items:center;gap:4px;flex-shrink:0;';
        item.keys.forEach(function (k, i) {
          if (i > 0) {
            const sep = document.createElement('span');
            sep.style.cssText = 'font-size:11px;color:var(--text-faint);';
            sep.textContent = ' ';
            kbdGroup.appendChild(sep);
          }
          const kbd = document.createElement('kbd');
          kbd.style.cssText =
            'display:inline-block;padding:2px 6px;border-radius:4px;' +
            'background:var(--surface-4);border:1px solid var(--border-default);' +
            'font-family:var(--font-mono);font-size:11px;color:var(--text-muted);' +
            'white-space:nowrap;';
          kbd.textContent = k;
          kbdGroup.appendChild(kbd);
        });

        row.appendChild(desc);
        row.appendChild(kbdGroup);
        section_el.appendChild(row);
      });

      body.appendChild(section_el);
    });

    box.appendChild(header);
    box.appendChild(body);
    modal.appendChild(box);
    document.body.appendChild(modal);

    // Close handlers
    modal.addEventListener('click', function (e) {
      if (e.target === modal) closeShortcutsModal();
    });
    const closeBtn = document.getElementById('shortcutsModalClose');
    if (closeBtn) {
      closeBtn.addEventListener('click', closeShortcutsModal);
    }

    return modal;
  }

  function showShortcutsModal() {
    const modal = buildShortcutsModal();
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  function closeShortcutsModal() {
    const modal = document.getElementById('shortcutsModal');
    if (modal) modal.classList.add('hidden');
    document.body.style.overflow = '';
  }

  // ─── Ticket list navigation ───────────────────────────────────────────────

  let focusedRow = null;

  function getTicketRows() {
    // Selects rows in the main ticket table; both .table tbody tr and tr.ticket-row
    return Array.from(
      document.querySelectorAll(
        '.table tbody tr:not([hidden]), table tbody tr.ticket-row:not([hidden])'
      )
    );
  }

  function getFocusedRowIndex() {
    const rows = getTicketRows();
    if (!focusedRow) return -1;
    return rows.indexOf(focusedRow);
  }

  function focusTicketRow(row) {
    if (focusedRow) {
      focusedRow.classList.remove('keyboard-focused');
      focusedRow.removeAttribute('tabindex');
    }
    focusedRow = row;
    if (row) {
      row.classList.add('keyboard-focused');
      row.setAttribute('tabindex', '0');
      row.focus();
      row.scrollIntoView({ block: 'nearest' });
    }
  }

  function focusNextRow() {
    const rows = getTicketRows();
    if (!rows.length) return;
    const idx = getFocusedRowIndex();
    const next = (idx < 0 || idx >= rows.length - 1) ? 0 : idx + 1;
    focusTicketRow(rows[next]);
  }

  function focusPrevRow() {
    const rows = getTicketRows();
    if (!rows.length) return;
    const idx = getFocusedRowIndex();
    const prev = (idx <= 0) ? rows.length - 1 : idx - 1;
    focusTicketRow(rows[prev]);
  }

  function toggleRowSelection(row) {
    if (!row) row = focusedRow;
    if (!row) return;
    const cb = row.querySelector('input.ticket-select');
    if (cb) {
      cb.checked = !cb.checked;
      // Trigger change event so bulk bar updates
      cb.dispatchEvent(new Event('change', { bubbles: true }));
    } else {
      row.classList.toggle('selected');
    }
  }

  function openFocusedTicket() {
    if (!focusedRow) return;
    const link = focusedRow.querySelector('a[href]');
    if (link) {
      window.location.href = link.href;
    }
  }

  // ─── Ticket detail interactions ───────────────────────────────────────────

  function openStatusPicker() {
    // Try to find and click a status button / picker trigger
    const statusTrigger =
      document.querySelector('[data-status-picker-trigger], #statusPickerBtn, .status-picker-btn');
    if (statusTrigger) {
      statusTrigger.click();
    } else {
      // Fallback: open first select named statut
      const select = document.querySelector('select[name="statut"], select[name="status"]');
      if (select) select.focus();
    }
  }

  function openAssigneePicker() {
    const assigneeTrigger =
      document.querySelector('[data-assignee-picker-trigger], #assigneePickerBtn, .assignee-picker-btn');
    if (assigneeTrigger) {
      assigneeTrigger.click();
    } else {
      const select = document.querySelector('select[name="assigne_a"], select[name="assigned_to"]');
      if (select) select.focus();
    }
  }

  // ─── Chord navigation ─────────────────────────────────────────────────────

  function startChord(key) {
    chordFirstKey = key;
    clearTimeout(chordTimer);
    chordTimer = setTimeout(function () {
      chordFirstKey = null;
    }, CHORD_WINDOW);
  }

  function handleChordSecond(secondKey) {
    const chord = chordFirstKey + secondKey;
    chordFirstKey = null;
    clearTimeout(chordTimer);

    const destinations = {
      'gd': '/tickets/tableau-bord',
      'gq': '/tickets/',
      'gk': '/base-connaissance/',
      'gr': '/rapports/',
    };

    const url = destinations[chord];
    if (url) {
      window.location.href = url;
    }
  }

  // ─── Main keydown handler ─────────────────────────────────────────────────

  document.addEventListener('keydown', function (e) {
    if (!shortcutsEnabled) return;

    const inEditable = isInEditableField(e);
    const key = e.key;

    // ── Esc: close everything (fires even in inputs/palette) ──
    if (key === 'Escape') {
      closeAll();
      return;
    }

    // ── ⌘K / Ctrl+K: command palette ──
    if ((e.metaKey || e.ctrlKey) && key === 'k') {
      e.preventDefault();
      if (window.CHUB && window.CHUB.cmdPalette) {
        window.CHUB.cmdPalette.toggle();
      }
      return;
    }

    // ── ⌘N / Ctrl+N: new ticket ──
    if ((e.metaKey || e.ctrlKey) && key === 'n') {
      e.preventDefault();
      window.location.href = '/tickets/nouveau';
      return;
    }

    // ── ⌘⇧L: toggle theme ──
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && (key === 'l' || key === 'L')) {
      e.preventDefault();
      if (window.CHUB && window.CHUB.theme) {
        window.CHUB.theme.toggle();
      }
      return;
    }

    // Everything below does not fire while user is typing
    if (inEditable) return;

    // ── ? : keyboard shortcuts help ──
    if (key === '?') {
      e.preventDefault();
      showShortcutsModal();
      return;
    }

    // ── Chord handling ──
    if (chordFirstKey !== null) {
      // Waiting for second key
      handleChordSecond(key.toLowerCase());
      return;
    }

    if (key.toLowerCase() === 'g') {
      e.preventDefault();
      startChord('g');
      return;
    }

    // ── Ticket list shortcuts ──
    if (isTicketList) {
      if (key === 'j') { e.preventDefault(); focusNextRow();            return; }
      if (key === 'k') { e.preventDefault(); focusPrevRow();            return; }
      if (key === 'x') { e.preventDefault(); toggleRowSelection(null);  return; }
      if (key === 'Enter' && focusedRow) { e.preventDefault(); openFocusedTicket(); return; }
    }

    // ── Ticket detail shortcuts ──
    if (isTicketDetail) {
      if (key === 's') { e.preventDefault(); openStatusPicker();   return; }
      if (key === 'a') { e.preventDefault(); openAssigneePicker(); return; }
    }
  });

  // ─── Tab in empty reply textarea → AI draft (detail page) ─────────────────

  if (isTicketDetail) {
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Tab') return;
      const ta = e.target;
      if (!ta || ta.tagName !== 'TEXTAREA') return;
      if (ta.id !== 'replyContent' && !ta.classList.contains('reply-textarea')) return;
      if (ta.value.trim() !== '') return;

      // Empty textarea + Tab → AI draft
      e.preventDefault();
      document.dispatchEvent(new CustomEvent('ai:draft-request', {
        bubbles: true,
        detail: { textarea: ta },
      }));
    }, true); // use capture so it fires before tickets.js
  }

  // ─── Expose ───────────────────────────────────────────────────────────────

  window.CHUB = window.CHUB || {};
  window.CHUB.keyboard = {
    enabled:       shortcutsEnabled,
    disable:       function () { shortcutsEnabled = false; },
    enable:        function () { shortcutsEnabled = true; },
    showShortcuts: showShortcutsModal,
  };
})();
