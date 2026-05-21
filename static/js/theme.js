/**
 * CosmittoHUB — Theme Management
 * Handles dark/light theme toggle, persistence, and system preference.
 */

(function () {
  'use strict';

  const STORAGE_KEY = 'chub-theme';
  const DARK = 'dark';
  const LIGHT = 'light';

  /**
   * Determine the initial theme:
   * 1. Saved preference in localStorage
   * 2. System preference via prefers-color-scheme
   * 3. Default to dark
   */
  function resolveInitialTheme() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === DARK || saved === LIGHT) return saved;
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      return LIGHT;
    }
    return DARK;
  }

  /**
   * Apply a theme to the document body and persist it.
   * @param {string} theme - 'dark' or 'light'
   */
  function setTheme(theme) {
    const t = theme === LIGHT ? LIGHT : DARK;
    document.body.dataset.theme = t;
    try {
      localStorage.setItem(STORAGE_KEY, t);
    } catch (e) {}
    updateToggleButton(t);
    // Dispatch a custom event so other modules can react
    document.dispatchEvent(new CustomEvent('chub:themechange', { detail: { theme: t } }));
  }

  /**
   * Return the currently active theme.
   * @returns {string}
   */
  function currentTheme() {
    return document.body.dataset.theme === LIGHT ? LIGHT : DARK;
  }

  /**
   * Toggle between dark and light.
   */
  function toggle() {
    setTheme(currentTheme() === DARK ? LIGHT : DARK);
  }

  /**
   * Update the theme toggle button icon/label if it exists.
   * @param {string} theme
   */
  function updateToggleButton(theme) {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;

    const iconEl  = btn.querySelector('.theme-toggle-icon');
    const labelEl = btn.querySelector('.theme-toggle-label');

    if (theme === LIGHT) {
      // Currently light — button offers to switch to dark
      if (iconEl)  iconEl.textContent = '🌙';
      if (labelEl) labelEl.textContent = 'Dark mode';
      btn.setAttribute('aria-label', 'Switch to dark mode');
      btn.setAttribute('data-tooltip', 'Switch to dark mode');
    } else {
      // Currently dark — button offers to switch to light
      if (iconEl)  iconEl.textContent = '☀️';
      if (labelEl) labelEl.textContent = 'Light mode';
      btn.setAttribute('aria-label', 'Switch to light mode');
      btn.setAttribute('data-tooltip', 'Switch to light mode');
    }
  }

  /**
   * Wire up the #theme-toggle button click handler.
   */
  function bindToggleButton() {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      toggle();
    });
  }

  /**
   * Initialise theme on page load.
   * The theme is applied as early as possible (even before DOMContentLoaded)
   * to avoid flash of unstyled/wrong-theme content.
   */
  function init() {
    const theme = resolveInitialTheme();
    document.body.dataset.theme = theme;

    // Bind interactive elements after DOM is ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () {
        bindToggleButton();
        updateToggleButton(theme);
      });
    } else {
      bindToggleButton();
      updateToggleButton(theme);
    }
  }

  // Run immediately so theme is applied before first paint
  init();

  // Expose on CHUB namespace
  window.CHUB = window.CHUB || {};
  window.CHUB.theme = {
    toggle:  toggle,
    current: currentTheme,
    set:     setTheme,
  };
})();
