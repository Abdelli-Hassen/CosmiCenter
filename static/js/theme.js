/**
 * Cosmicenter — Theme Management
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
    document.documentElement.dataset.theme = t;
    document.documentElement.style.colorScheme = t;
    document.documentElement.style.backgroundColor = t === DARK ? '#14122B' : '#FAF6F1';
    
    try {
      localStorage.setItem(STORAGE_KEY, t);
      document.cookie = "chub_theme=" + t + "; path=/; max-age=31536000";
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
    return document.documentElement.dataset.theme === LIGHT ? LIGHT : DARK;
  }

  /**
   * Toggle between dark and light.
   */
  function toggle() {
    const nextTheme = currentTheme() === DARK ? LIGHT : DARK;
    if (document.startViewTransition) {
      document.startViewTransition(() => setTheme(nextTheme));
    } else {
      document.documentElement.classList.add('theme-transitioning');
      setTheme(nextTheme);
      setTimeout(() => {
        document.documentElement.classList.remove('theme-transitioning');
      }, 400);
    }
  }

  /**
   * Update the theme toggle button icon/label if it exists.
   * @param {string} theme
   */
  function updateToggleButton(theme) {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;

    const darkIcon = document.getElementById('themeIconDark');
    const lightIcon = document.getElementById('themeIconLight');

    if (theme === LIGHT) {
      if (darkIcon) darkIcon.style.display = 'block'; // Sun icon for light mode
      if (lightIcon) lightIcon.style.display = 'none';
      btn.setAttribute('aria-label', 'Activer le mode sombre');
      btn.setAttribute('title', 'Activer le mode sombre');
    } else {
      if (darkIcon) darkIcon.style.display = 'none';
      if (lightIcon) lightIcon.style.display = 'block'; // Moon icon for dark mode
      btn.setAttribute('aria-label', 'Activer le mode clair');
      btn.setAttribute('title', 'Activer le mode clair');
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
    document.documentElement.dataset.theme = theme;

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
