/**
 * CosmiCenter — fenêtre de confirmation maison (remplace le confirm() du navigateur)
 * Usage : <form data-confirm="Message ?"> ou <button type="submit" data-confirm="Message ?">
 * Options : data-confirm-title, data-confirm-ok (texte du bouton), data-confirm-tone="primary|danger" (défaut : danger)
 */
(function () {
  'use strict';
  var pending = null, bypass = false, lastFocus = null, root = null;

  var ICONS = {
    danger: '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    primary: '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
  };

  function build() {
    root = document.createElement('div');
    root.className = 'cc-confirm';
    root.hidden = true;
    root.innerHTML =
      '<div class="cc-confirm-backdrop" data-close></div>' +
      '<div class="cc-confirm-card" role="alertdialog" aria-modal="true" aria-labelledby="ccConfirmTitle" aria-describedby="ccConfirmMsg">' +
        '<div class="cc-confirm-icon" id="ccConfirmIcon"></div>' +
        '<h3 class="cc-confirm-title" id="ccConfirmTitle"></h3>' +
        '<p class="cc-confirm-msg" id="ccConfirmMsg"></p>' +
        '<div class="cc-confirm-actions">' +
          '<button type="button" class="cc-confirm-btn cc-cancel" data-close>Annuler</button>' +
          '<button type="button" class="cc-confirm-btn cc-ok" id="ccConfirmOk">Confirmer</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(root);
    root.addEventListener('click', function (e) {
      if (e.target.closest('[data-close]')) close(false);
    });
    root.querySelector('#ccConfirmOk').addEventListener('click', function () { close(true); });
  }

  function open(el, onYes) {
    if (!root) build();
    var tone = el.getAttribute('data-confirm-tone') === 'primary' ? 'primary' : 'danger';
    root.setAttribute('data-tone', tone);
    root.querySelector('#ccConfirmIcon').innerHTML = ICONS[tone];
    root.querySelector('#ccConfirmTitle').textContent = el.getAttribute('data-confirm-title') || (tone === 'danger' ? 'Confirmer l’action' : 'Confirmation');
    root.querySelector('#ccConfirmMsg').textContent = el.getAttribute('data-confirm');
    root.querySelector('#ccConfirmOk').textContent = el.getAttribute('data-confirm-ok') || 'Confirmer';
    pending = onYes;
    lastFocus = document.activeElement;
    root.hidden = false;
    requestAnimationFrame(function () { root.classList.add('is-open'); });
    root.querySelector('.cc-cancel').focus();
  }

  function close(yes) {
    if (!root || root.hidden) return;
    var cb = pending; pending = null;
    root.classList.remove('is-open');
    setTimeout(function () { root.hidden = true; }, 160);
    if (lastFocus && lastFocus.focus) { try { lastFocus.focus(); } catch (e) {} }
    if (yes && cb) cb();
  }

  document.addEventListener('keydown', function (e) {
    if (!root || root.hidden) return;
    if (e.key === 'Escape') { e.preventDefault(); close(false); }
    if (e.key === 'Tab') {
      var f = root.querySelectorAll('button'); if (!f.length) return;
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });

  // Bouton (ou lien) portant data-confirm
  document.addEventListener('click', function (e) {
    if (bypass) return;
    var el = e.target.closest('button[data-confirm], a[data-confirm], input[type=submit][data-confirm]');
    if (!el) return;
    e.preventDefault(); e.stopPropagation();
    open(el, function () {
      if (el.tagName === 'A') { window.location.href = el.href; return; }
      var form = el.form;
      if (!form) return;
      bypass = true;
      try { form.requestSubmit ? form.requestSubmit(el) : form.submit(); } finally { bypass = false; }
    });
  }, true);

  // Formulaire portant data-confirm
  document.addEventListener('submit', function (e) {
    if (bypass) return;
    var form = e.target;
    if (!form.getAttribute || !form.hasAttribute('data-confirm')) return;
    e.preventDefault(); e.stopPropagation();
    var submitter = e.submitter || null;
    open(form, function () {
      bypass = true;
      try { form.requestSubmit ? form.requestSubmit(submitter || undefined) : form.submit(); } finally { bypass = false; }
    });
  }, true);
})();
