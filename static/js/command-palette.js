/**
 * CosmittoHUB — Command Palette
 * Full ⌘K / Ctrl+K command palette with fuzzy search, keyboard navigation,
 * recent items persistence, and grouped results.
 */

(function () {
  'use strict';

  // ─── Command data ─────────────────────────────────────────────────────────

  const COMMANDS = [
    { id: 'nav-dashboard',   label: 'Dashboard',         type: 'nav',    icon: '📊', url: '/tickets/tableau-bord',    kbd: 'G D' },
    { id: 'nav-tickets',     label: 'All Tickets',        type: 'nav',    icon: '🎫', url: '/tickets/',                kbd: 'G Q' },
    { id: 'nav-new',         label: 'New Ticket',         type: 'action', icon: '＋', url: '/tickets/nouveau',         kbd: '⌘N' },
    { id: 'nav-departments', label: 'Departments',        type: 'nav',    icon: '🏢', url: '/departements/' },
    { id: 'nav-users',       label: 'Users',              type: 'nav',    icon: '👥', url: '/utilisateurs/' },
    { id: 'nav-reports',     label: 'Reports',            type: 'nav',    icon: '📈', url: '/rapports/' },
    { id: 'nav-kb',          label: 'Knowledge Base',     type: 'nav',    icon: '📚', url: '/base-connaissance/' },
    { id: 'nav-settings',    label: 'Settings',           type: 'nav',    icon: '⚙',  url: '/parametres/profil' },
    { id: 'action-theme',    label: 'Toggle Theme',       type: 'action', icon: '🌓', kbd: '⌘⇧L' },
    { id: 'action-shortcuts',label: 'Keyboard Shortcuts', type: 'action', icon: '⌨',  kbd: '?' },
  ];

  const RECENT_KEY   = 'chub-recent';
  const RECENT_LIMIT = 5;

  // ─── State ────────────────────────────────────────────────────────────────

  let overlay      = null;
  let inputEl      = null;
  let resultsEl    = null;
  let focusedIndex = -1;
  let currentItems = [];
  let isOpen       = false;

  // ─── Recent items ─────────────────────────────────────────────────────────

  function getRecent() {
    try {
      return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
    } catch (e) {
      return [];
    }
  }

  function saveRecent(item) {
    try {
      let recents = getRecent();
      // Remove duplicate by id or url
      recents = recents.filter(function (r) {
        return r.id !== item.id && r.url !== item.url;
      });
      recents.unshift(item);
      if (recents.length > RECENT_LIMIT) recents = recents.slice(0, RECENT_LIMIT);
      localStorage.setItem(RECENT_KEY, JSON.stringify(recents));
    } catch (e) {}
  }

  // ─── Fuzzy / substring match ──────────────────────────────────────────────

  /**
   * Returns a score > 0 if query matches label. Higher = better match.
   * Prefers exact prefix > word start > substring > individual chars.
   */
  function matchScore(label, query) {
    if (!query) return 1;
    const l = label.toLowerCase();
    const q = query.toLowerCase().trim();
    if (!q) return 1;

    if (l === q) return 100;
    if (l.startsWith(q)) return 80;

    // All words in label that start with query words
    const labelWords = l.split(/\s+/);
    const queryWords = q.split(/\s+/);
    let allFound = queryWords.every(function (qw) {
      return labelWords.some(function (lw) { return lw.startsWith(qw); });
    });
    if (allFound) return 60;

    // Substring anywhere
    if (l.includes(q)) return 40;

    // Each character in query must appear in order in label (fuzzy)
    let li = 0;
    for (let qi = 0; qi < q.length; qi++) {
      li = l.indexOf(q[qi], li);
      if (li === -1) return 0;
      li++;
    }
    return 10;
  }

  // ─── Build & render results ───────────────────────────────────────────────

  function renderResults(query) {
    resultsEl.innerHTML = '';
    currentItems = [];
    focusedIndex = -1;

    if (!query || !query.trim()) {
      renderDefaultView();
    } else {
      renderSearchView(query);
    }

    // Focus first item automatically
    if (currentItems.length > 0) {
      setFocus(0);
    }
  }

  function renderDefaultView() {
    const recents = getRecent();

    if (recents.length > 0) {
      appendSectionLabel('Recent');
      recents.forEach(function (item) {
        appendItem(item, true);
      });
    }

    appendSectionLabel('Navigation');
    COMMANDS.filter(function (c) { return c.type === 'nav'; }).forEach(function (c) {
      appendItem(c, false);
    });

    appendSectionLabel('Actions');
    COMMANDS.filter(function (c) { return c.type === 'action'; }).forEach(function (c) {
      appendItem(c, false);
    });
  }

  function renderSearchView(query) {
    const scored = COMMANDS.map(function (cmd) {
      return { cmd: cmd, score: matchScore(cmd.label, query) };
    }).filter(function (x) { return x.score > 0; })
      .sort(function (a, b) { return b.score - a.score; });

    if (scored.length === 0) {
      const empty = document.createElement('div');
      empty.style.cssText = 'padding:32px 16px;text-align:center;color:var(--text-faint);font-size:13px;';
      empty.textContent = 'No results for "' + escapeHtml(query) + '"';
      resultsEl.appendChild(empty);
      return;
    }

    // Group by type
    const navItems    = scored.filter(function (x) { return x.cmd.type === 'nav'; });
    const actionItems = scored.filter(function (x) { return x.cmd.type === 'action'; });

    if (navItems.length > 0) {
      appendSectionLabel('Navigation');
      navItems.forEach(function (x) { appendItem(x.cmd, false); });
    }
    if (actionItems.length > 0) {
      appendSectionLabel('Actions');
      actionItems.forEach(function (x) { appendItem(x.cmd, false); });
    }
  }

  function appendSectionLabel(text) {
    const label = document.createElement('div');
    label.className = 'cmd-section-label';
    label.textContent = text;
    resultsEl.appendChild(label);
  }

  function appendItem(item, isRecent) {
    const idx = currentItems.length;
    currentItems.push(item);

    const el = document.createElement('div');
    el.className = 'cmd-item';
    el.setAttribute('data-index', String(idx));
    el.setAttribute('role', 'option');
    el.setAttribute('tabindex', '-1');

    const iconEl = document.createElement('span');
    iconEl.className = 'cmd-item-icon';
    iconEl.textContent = item.icon || (item.type === 'nav' ? '→' : '⚡');

    const labelEl = document.createElement('span');
    labelEl.className = 'cmd-item-label';
    labelEl.textContent = item.label;

    el.appendChild(iconEl);
    el.appendChild(labelEl);

    if (item.kbd) {
      const kbdEl = document.createElement('span');
      kbdEl.className = 'cmd-item-kbd';
      kbdEl.textContent = item.kbd;
      el.appendChild(kbdEl);
    }

    if (isRecent) {
      const metaEl = document.createElement('span');
      metaEl.className = 'cmd-item-meta';
      metaEl.textContent = 'recent';
      el.appendChild(metaEl);
    }

    el.addEventListener('mouseenter', function () {
      setFocus(idx);
    });

    el.addEventListener('click', function (e) {
      e.preventDefault();
      activateItem(item);
    });

    resultsEl.appendChild(el);
    return el;
  }

  // ─── Focus management ─────────────────────────────────────────────────────

  function setFocus(idx) {
    if (idx < 0) idx = 0;
    if (idx >= currentItems.length) idx = currentItems.length - 1;

    // Remove focused from previous
    const prev = resultsEl.querySelector('.cmd-item.focused');
    if (prev) prev.classList.remove('focused');

    focusedIndex = idx;

    const el = resultsEl.querySelector('[data-index="' + idx + '"]');
    if (el) {
      el.classList.add('focused');
      // Scroll into view if needed
      el.scrollIntoView({ block: 'nearest' });
    }
  }

  function moveFocus(delta) {
    // Skip section labels — find next/prev .cmd-item
    const items = resultsEl.querySelectorAll('.cmd-item');
    if (items.length === 0) return;

    let next = focusedIndex + delta;
    if (next < 0) next = items.length - 1;
    if (next >= items.length) next = 0;

    setFocus(next);
  }

  // ─── Activate item ────────────────────────────────────────────────────────

  function activateItem(item) {
    if (!item) return;

    // Save to recent if it has a URL
    if (item.url) {
      saveRecent({
        id:    item.id,
        label: item.label,
        url:   item.url,
        type:  item.type,
        icon:  item.icon || '',
      });
    }

    close();

    // Execute action or navigate
    if (item.id === 'action-theme') {
      if (window.CHUB && window.CHUB.theme) {
        window.CHUB.theme.toggle();
      }
      return;
    }

    if (item.id === 'action-shortcuts') {
      if (window.CHUB && window.CHUB.keyboard) {
        window.CHUB.keyboard.showShortcuts();
      }
      return;
    }

    if (item.url) {
      window.location.href = item.url;
    }
  }

  // ─── Open / close ─────────────────────────────────────────────────────────

  function open() {
    if (isOpen) return;
    isOpen = true;
    ensureDOM();
    overlay.classList.remove('hidden');
    inputEl.value = '';
    renderResults('');
    requestAnimationFrame(function () {
      inputEl.focus();
    });
    document.body.style.overflow = 'hidden';
  }

  function close() {
    if (!isOpen) return;
    isOpen = false;
    if (overlay) overlay.classList.add('hidden');
    document.body.style.overflow = '';
    currentItems = [];
    focusedIndex = -1;
  }

  function toggle() {
    isOpen ? close() : open();
  }

  // ─── DOM construction ─────────────────────────────────────────────────────

  function ensureDOM() {
    if (overlay) return;

    overlay = document.createElement('div');
    overlay.id = 'cmdPalette';
    overlay.className = 'cmd-overlay hidden';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', 'Command palette');

    const box = document.createElement('div');
    box.className = 'cmd-box';

    // Input row
    const inputWrap = document.createElement('div');
    inputWrap.className = 'cmd-input-wrap';

    const searchIcon = document.createElement('span');
    searchIcon.className = 'cmd-input-icon';
    searchIcon.innerHTML =
      '<svg width="16" height="16" viewBox="0 0 16 16" fill="none">' +
      '<circle cx="6.5" cy="6.5" r="5" stroke="currentColor" stroke-width="1.5"/>' +
      '<path d="M10.5 10.5L14 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>' +
      '</svg>';

    inputEl = document.createElement('input');
    inputEl.id = 'cmdInput';
    inputEl.type = 'text';
    inputEl.className = 'cmd-input';
    inputEl.placeholder = 'Search commands, navigate pages…';
    inputEl.setAttribute('autocomplete', 'off');
    inputEl.setAttribute('autocorrect', 'off');
    inputEl.setAttribute('spellcheck', 'false');
    inputEl.setAttribute('aria-label', 'Command search');
    inputEl.setAttribute('role', 'combobox');
    inputEl.setAttribute('aria-expanded', 'true');
    inputEl.setAttribute('aria-autocomplete', 'list');

    const escHint = document.createElement('kbd');
    escHint.className = 'cmd-close-hint';
    escHint.textContent = 'Esc';

    inputWrap.appendChild(searchIcon);
    inputWrap.appendChild(inputEl);
    inputWrap.appendChild(escHint);

    // Results
    resultsEl = document.createElement('div');
    resultsEl.className = 'cmd-results';
    resultsEl.setAttribute('role', 'listbox');

    // Footer hints
    const footer = document.createElement('div');
    footer.className = 'cmd-footer';
    footer.innerHTML =
      '<span class="cmd-footer-hint"><kbd>↑↓</kbd> navigate</span>' +
      '<span class="cmd-footer-hint"><kbd>↵</kbd> select</span>' +
      '<span class="cmd-footer-hint"><kbd>Esc</kbd> close</span>';

    box.appendChild(inputWrap);
    box.appendChild(resultsEl);
    box.appendChild(footer);
    overlay.appendChild(box);
    document.body.appendChild(overlay);

    // ── Event listeners ──

    // Click outside box closes
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) close();
    });

    // Input: filter results
    var debouncedRender = (window.CHUB && window.CHUB.debounce)
      ? window.CHUB.debounce(function () { renderResults(inputEl.value); }, 60)
      : function () { renderResults(inputEl.value); };

    inputEl.addEventListener('input', debouncedRender);

    // Keyboard navigation
    inputEl.addEventListener('keydown', function (e) {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          moveFocus(1);
          break;
        case 'ArrowUp':
          e.preventDefault();
          moveFocus(-1);
          break;
        case 'Enter':
          e.preventDefault();
          if (focusedIndex >= 0 && focusedIndex < currentItems.length) {
            activateItem(currentItems[focusedIndex]);
          }
          break;
        case 'Escape':
          e.preventDefault();
          close();
          break;
      }
    });
  }

  // ─── Global keyboard trigger ───────────────────────────────────────────────

  document.addEventListener('keydown', function (e) {
    // Don't steal shortcuts from inputs
    var tag = (e.target && e.target.tagName) ? e.target.tagName.toUpperCase() : '';
    var isEditable = (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') ||
                     (e.target && e.target.isContentEditable);

    // Allow Esc even inside inputs to close palette
    if (e.key === 'Escape' && isOpen) {
      e.preventDefault();
      close();
      return;
    }

    if (isEditable && !isOpen) return;

    // ⌘K / Ctrl+K
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      toggle();
    }
  });

  // ─── Helper ───────────────────────────────────────────────────────────────

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // ─── Initialise ───────────────────────────────────────────────────────────

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', ensureDOM);
  } else {
    ensureDOM();
  }

  // ─── Export ───────────────────────────────────────────────────────────────

  window.CHUB = window.CHUB || {};
  window.CHUB.cmdPalette = {
    open:   open,
    close:  close,
    toggle: toggle,
  };
})();
