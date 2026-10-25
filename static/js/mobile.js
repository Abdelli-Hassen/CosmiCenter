/**
 * CosmiCenter — tableaux en cartes sur téléphone.
 * Recopie le texte de chaque en-tête de colonne dans l'attribut data-label des cellules ;
 * mobile.css affiche alors chaque ligne du tableau comme une carte « libellé : valeur ».
 * Exclure un tableau : class="no-cards". Fonctionne aussi pour les lignes ajoutées par JavaScript.
 */
(function () {
  'use strict';

  function headerLabels(table) {
    var row = table.tHead && table.tHead.rows[0];
    if (!row) return null;
    var labels = [];
    Array.prototype.forEach.call(row.cells, function (th) {
      var text = (th.getAttribute('data-label') || th.textContent || '').replace(/\s+/g, ' ').trim();
      for (var i = 0; i < (th.colSpan || 1); i++) labels.push(text);
    });
    return labels;
  }

  function labelTable(table) {
    if (table.classList.contains('no-cards') || table.closest('.fc, .no-cards')) return;
    var labels = headerLabels(table);
    if (!labels) return;
    table.classList.add('cards-on');
    Array.prototype.forEach.call(table.tBodies, function (body) {
      Array.prototype.forEach.call(body.rows, function (tr) {
        var col = 0;
        Array.prototype.forEach.call(tr.cells, function (td) {
          if (!td.hasAttribute('data-label') && labels[col]) td.setAttribute('data-label', labels[col]);
          col += td.colSpan || 1;
        });
      });
    });
  }

  function run(root) {
    (root || document).querySelectorAll('table').forEach(labelTable);
  }

  var pending = false;
  function schedule() {
    if (pending) return;
    pending = true;
    setTimeout(function () { pending = false; run(); }, 50);
  }

  document.addEventListener('DOMContentLoaded', function () {
    run();
    // Tableaux remplis après coup (rechargement partiel, tri, filtres…)
    new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
  });
})();
