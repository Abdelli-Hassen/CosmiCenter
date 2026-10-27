/**
 * CosmiCenter — pièces jointes des tickets (macro templates/tickets/_attachments.html)
 *  - image : visionneuse sur la même page (Échap / clic à l'extérieur / ✕ pour fermer)
 *  - autre fichier : téléchargement sans quitter la page (les PDF/Office sont servis en téléchargement)
 *  - [data-att-remove] : coche/décoche le retrait (checkbox cachée « supprimer_pj[] » de la carte)
 */
(function () {
  'use strict';
  var box = null, img = null;

  function build() {
    box = document.createElement('div');
    box.className = 'image-lightbox';
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-modal', 'true');
    box.innerHTML =
      '<div class="lightbox-content">' +
        '<button type="button" class="lightbox-close" title="Fermer (Échap)" aria-label="Fermer">' +
          '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>' +
        '</button>' +
        '<img class="lightbox-img" alt="Aperçu">' +
        '<div class="lightbox-bar">' +
          '<div><div class="lightbox-title"></div><div class="lightbox-meta"></div></div>' +
          '<div class="lightbox-actions">' +
            '<a class="lightbox-btn" download title="Télécharger">' +
              '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> Télécharger' +
            '</a>' +
          '</div>' +
        '</div>' +
      '</div>';
    document.body.appendChild(box);
    img = box.querySelector('.lightbox-img');
    box.addEventListener('click', function (e) {
      if (e.target === box || e.target.closest('.lightbox-close')) close();
    });
  }

  function open(url, name, size) {
    if (!box) build();
    img.src = url;
    box.querySelector('.lightbox-title').textContent = name || 'Image';
    box.querySelector('.lightbox-meta').textContent = size ? 'Taille : ' + size : '';
    var dl = box.querySelector('.lightbox-btn');
    dl.href = url;
    dl.setAttribute('download', name || '');
    box.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function close() {
    if (!box) return;
    box.classList.remove('open');
    document.body.style.overflow = '';
    img.removeAttribute('src');
  }

  function download(url, name) {
    var a = document.createElement('a');
    a.href = url; a.download = name || '';
    document.body.appendChild(a); a.click(); a.remove();
  }

  function toggleRemove(btn) {
    var card = btn.closest('[data-att-img], [data-att-file]');
    var cb = card && card.querySelector('input[name="supprimer_pj[]"]');
    if (!cb) return;
    cb.checked = !cb.checked;
    card.classList.toggle('is-removed', cb.checked);
    btn.title = cb.checked ? 'Annuler le retrait' : 'Retirer cette pièce jointe';
    var form = cb.form;
    if (form) form.dispatchEvent(new Event('change', { bubbles: true }));
  }

  document.addEventListener('click', function (e) {
    var rm = e.target.closest('[data-att-remove]');
    if (rm) { e.preventDefault(); e.stopPropagation(); toggleRemove(rm); return; }
    if (e.target.closest('.attach-act')) return; // lien « Télécharger » : comportement natif
    var card = e.target.closest('[data-att-img], [data-att-file]');
    if (!card) return;
    if (card.hasAttribute('data-att-img')) open(card.dataset.url, card.dataset.name, card.dataset.size);
    else download(card.dataset.url, card.dataset.name);
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && box && box.classList.contains('open')) { close(); return; }
    if ((e.key === 'Enter' || e.key === ' ') && e.target.matches && e.target.matches('[data-att-img], [data-att-file]')) {
      e.preventDefault(); e.target.click();
    }
  });

  window.openLightbox = open;   // compatibilité avec l'ancien appel de la fiche du ticket
  window.closeLightbox = close;
})();
