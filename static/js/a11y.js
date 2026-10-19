/**
 * CosmiCenter — Accessibilité clavier
 *  - Les lignes / cartes cliquables (élément non interactif portant un onclick) deviennent focalisables
 *    (tabindex=0, role=link) et s'activent avec Entrée ou Espace.
 *  - Les boutons qui n'ont qu'une icône reprennent leur attribut title comme nom accessible (aria-label).
 */
(function () {
  'use strict';
  var INTERACTIVE = { A: 1, BUTTON: 1, INPUT: 1, SELECT: 1, TEXTAREA: 1, SUMMARY: 1, LABEL: 1 };

  function enhance(root) {
    if (!root || root.nodeType !== 1) return;
    var nodes = root.querySelectorAll ? root.querySelectorAll('[onclick]') : [];
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (INTERACTIVE[el.tagName] || el.hasAttribute('tabindex') || el.hasAttribute('role')) continue;
      el.setAttribute('tabindex', '0');
      el.setAttribute('role', 'link');
    }
    var buttons = root.querySelectorAll ? root.querySelectorAll('button:not([aria-label])') : [];
    for (var j = 0; j < buttons.length; j++) {
      var b = buttons[j];
      if (!b.textContent.trim() && b.getAttribute('title')) b.setAttribute('aria-label', b.getAttribute('title'));
    }
  }

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var el = e.target;
    if (!el || el.getAttribute('role') !== 'link' || INTERACTIVE[el.tagName] || !el.hasAttribute('onclick')) return;
    e.preventDefault();
    el.click();
  });

  function init() {
    enhance(document.body);
    new MutationObserver(function (mutations) {
      mutations.forEach(function (m) {
        for (var i = 0; i < m.addedNodes.length; i++) enhance(m.addedNodes[i]);
      });
    }).observe(document.body, { childList: true, subtree: true });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
