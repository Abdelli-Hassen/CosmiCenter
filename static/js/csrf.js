/**
 * CosmiCenter — Protection CSRF côté client
 * Ajoute automatiquement le jeton CSRF (meta[name="csrf-token"]) :
 *  - comme champ caché dans tout formulaire POST (y compris ceux créés dynamiquement),
 *  - comme en-tête X-CSRFToken sur les requêtes fetch / XMLHttpRequest non-GET vers la même origine.
 */
(function () {
  'use strict';
  var meta = document.querySelector('meta[name="csrf-token"]');
  if (!meta) return;
  var token = meta.getAttribute('content');
  if (!token) return;

  function sameOrigin(url) {
    try { return new URL(url, window.location.href).origin === window.location.origin; }
    catch (e) { return true; }
  }

  function patchForm(form) {
    var method = (form.getAttribute('method') || 'get').toLowerCase();
    if (method !== 'post') return;
    var action = form.getAttribute('action');
    if (action && !sameOrigin(action)) return;
    if (form.querySelector('input[name="csrf_token"]')) return;
    var input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'csrf_token';
    input.value = token;
    form.appendChild(input);
  }

  function scan(root) {
    if (!root || root.nodeType !== 1) return;
    if (root.tagName === 'FORM') patchForm(root);
    var forms = root.querySelectorAll ? root.querySelectorAll('form') : [];
    for (var i = 0; i < forms.length; i++) patchForm(forms[i]);
  }

  function init() {
    scan(document.documentElement);
    new MutationObserver(function (mutations) {
      mutations.forEach(function (m) {
        for (var i = 0; i < m.addedNodes.length; i++) scan(m.addedNodes[i]);
      });
    }).observe(document.documentElement, { childList: true, subtree: true });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  // Filet de sécurité : jeton ajouté juste avant l'envoi d'un formulaire
  document.addEventListener('submit', function (e) { if (e.target && e.target.tagName === 'FORM') patchForm(e.target); }, true);

  // fetch
  if (window.fetch) {
    var nativeFetch = window.fetch;
    window.fetch = function (input, init) {
      init = init || {};
      var method = (init.method || (input && input.method) || 'GET').toUpperCase();
      var url = typeof input === 'string' ? input : (input && input.url) || '';
      if (method !== 'GET' && method !== 'HEAD' && sameOrigin(url)) {
        var headers = new Headers(init.headers || (input && input.headers) || {});
        if (!headers.has('X-CSRFToken')) headers.set('X-CSRFToken', token);
        init.headers = headers;
      }
      return nativeFetch.call(this, input, init);
    };
  }

  // XMLHttpRequest
  var nativeOpen = XMLHttpRequest.prototype.open;
  var nativeSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (method, url) {
    this._csrfMethod = (method || 'GET').toUpperCase();
    this._csrfUrl = url;
    return nativeOpen.apply(this, arguments);
  };
  XMLHttpRequest.prototype.send = function () {
    if (this._csrfMethod && this._csrfMethod !== 'GET' && this._csrfMethod !== 'HEAD' && sameOrigin(this._csrfUrl)) {
      try { this.setRequestHeader('X-CSRFToken', token); } catch (e) { /* ignore */ }
    }
    return nativeSend.apply(this, arguments);
  };
})();
