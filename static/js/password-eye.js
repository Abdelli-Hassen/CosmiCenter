/* Bouton « œil » (afficher / masquer) sur tous les champs mot de passe.
   La page de connexion (.auth-input-wrap) a déjà le sien. */
(function () {
  'use strict';

  var EYE = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">' +
    '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
  var EYE_OFF = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">' +
    '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>' +
    '<path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';

  function addEye(input) {
    if (input.closest('.auth-input-wrap, .pw-wrap')) return;

    var wrap = document.createElement('span');
    wrap.className = 'pw-wrap';
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'pw-eye';
    wrap.appendChild(button);

    function render() {
      var hidden = input.type === 'password';
      var label = hidden ? 'Afficher le mot de passe' : 'Masquer le mot de passe';
      button.innerHTML = hidden ? EYE : EYE_OFF;
      button.title = label;
      button.setAttribute('aria-label', label);
      button.setAttribute('aria-pressed', String(!hidden));
    }

    button.addEventListener('click', function () {
      input.type = input.type === 'password' ? 'text' : 'password';
      render();
    });

    // Remasquer à l'envoi : le navigateur doit toujours voir un champ mot de passe
    if (input.form) {
      input.form.addEventListener('submit', function () {
        input.type = 'password';
        render();
      });
    }

    render();
  }

  function init() {
    document.querySelectorAll('input[type="password"]').forEach(addEye);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
