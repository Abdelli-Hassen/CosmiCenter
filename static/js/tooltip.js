/**
 * CosmiCenter — info-bulles d'aide (.info-tip)
 * La bulle est dessinée dans un calque flottant attaché à <body> (position: fixed) : aucune carte ou conteneur
 * en `overflow: hidden` ne peut donc la rogner. Elle s'affiche au-dessus de l'icône, ou en dessous s'il n'y a
 * pas assez de place, et reste toujours dans la fenêtre.
 */
(function () {
  'use strict';
  var pop = null;
  var current = null;

  function ensurePop() {
    if (pop) return pop;
    pop = document.createElement('div');
    pop.className = 'info-tip-pop';
    pop.setAttribute('role', 'tooltip');
    pop.innerHTML = '<span class="info-tip-pop-text"></span><span class="info-tip-pop-arrow"></span>';
    document.body.appendChild(pop);
    return pop;
  }

  function show(el) {
    var text = el.getAttribute('data-tip');
    if (!text) return;
    current = el;
    var p = ensurePop();
    // Une fenêtre modale (<dialog>) est dessinée au-dessus de tout le reste : la bulle doit être dedans pour rester visible
    var host = el.closest('dialog[open]') || document.body;
    if (p.parentNode !== host) host.appendChild(p);
    p.querySelector('.info-tip-pop-text').textContent = text;
    p.style.visibility = 'hidden';
    p.style.display = 'block';
    p.classList.remove('below');

    var margin = 10;
    var r = el.getBoundingClientRect();
    var w = p.offsetWidth;
    var h = p.offsetHeight;
    var vw = document.documentElement.clientWidth;

    // au-dessus par défaut ; en dessous si la place manque
    var top = r.top - h - margin;
    var below = false;
    if (top < 8) { top = r.bottom + margin; below = true; }

    // centrée sur l'icône, mais gardée dans la fenêtre
    var left = r.left + r.width / 2 - w / 2;
    left = Math.max(8, Math.min(left, vw - w - 8));

    p.style.top = Math.round(top) + 'px';
    p.style.left = Math.round(left) + 'px';
    p.classList.toggle('below', below);
    var arrow = p.querySelector('.info-tip-pop-arrow');
    arrow.style.left = Math.round(r.left + r.width / 2 - left - 5) + 'px';
    p.style.visibility = 'visible';
    p.classList.add('open');
  }

  function hide() {
    current = null;
    if (pop) { pop.classList.remove('open'); pop.style.display = 'none'; }
  }

  function tipFrom(target) {
    return target && target.closest ? target.closest('.info-tip') : null;
  }

  document.addEventListener('mouseover', function (e) { var t = tipFrom(e.target); if (t) show(t); });
  document.addEventListener('mouseout', function (e) { var t = tipFrom(e.target); if (t && !t.contains(e.relatedTarget)) hide(); });
  document.addEventListener('focusin', function (e) { var t = tipFrom(e.target); if (t) show(t); });
  document.addEventListener('focusout', function (e) { if (tipFrom(e.target)) hide(); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') hide(); });
  window.addEventListener('scroll', function () { if (current) hide(); }, true);
  window.addEventListener('resize', hide);
})();
