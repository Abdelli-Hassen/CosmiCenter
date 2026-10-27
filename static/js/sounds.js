/**
 * CosmiCenter — sons « ticket envoyé » et « ticket reçu »
 *
 * Avant : `new Audio(url).play()` au moment exact de l'affichage du toast. Le fichier n'était pas encore
 * chargé ni décodé (début coupé) et l'objet n'était référencé nulle part, donc ramassé par le navigateur
 * en plein son (fin coupée).
 *
 * Maintenant :
 *  - les deux sons sont téléchargés et décodés dès l'ouverture de la page (Web Audio) ;
 *  - chaque lecture démarre avec un court silence d'amorce (la carte son / le Bluetooth « se réveille »)
 *    et garde une référence jusqu'à la fin du son ;
 *  - un signal inaudible garde la sortie audio active ;
 *  - si le navigateur bloque le son (aucun clic encore fait sur la page), il est mis en attente et joué
 *    dès le premier clic / touche, sans être perdu ;
 *  - repli sur des éléments <audio> préchargés si Web Audio n'est pas disponible.
 *
 * API : CHUB.sound.play('sent' | 'received')
 */
(function () {
  'use strict';

  var FILES = {
    sent: '/static/ticket%20sent.mp3',
    received: '/static/new%20ticket.mp3'
  };
  var LEAD = 0.15;          // secondes de silence avant le son
  var PENDING_MAX_AGE = 20000; // ms : au-delà, un son en attente n'a plus de sens

  var AC = window.AudioContext || window.webkitAudioContext;
  var ctx = null, keepAlive = null;
  var buffers = {};
  var live = [];            // sources en cours (références gardées jusqu'à « ended »)
  var pending = [];         // {name, at}
  var loading = false;
  var loadings = {};        // promesses de décodage par son

  // Éléments <audio> préchargés (repli) — références conservées dans ce tableau
  var elements = {};
  Object.keys(FILES).forEach(function (name) {
    var a = new Audio();
    a.preload = 'auto';
    a.src = FILES[name];
    elements[name] = a;
  });

  function ensureContext() {
    if (ctx || !AC) return ctx;
    try { ctx = new AC(); } catch (e) { ctx = null; }
    return ctx;
  }

  function loadBuffers() {
    if (loading || !ensureContext()) return;
    loading = true;
    Object.keys(FILES).forEach(function (name) {
      loadings[name] = fetch(FILES[name]).then(function (r) { return r.arrayBuffer(); })
        .then(function (data) {
          return new Promise(function (ok, ko) { ctx.decodeAudioData(data, ok, ko); });
        })
        .then(function (buf) { buffers[name] = buf; })
        .catch(function () { /* le repli <audio> prendra le relais */ });
    });
  }

  // Signal quasi inaudible : empêche la sortie audio de s'endormir entre deux sons
  function startKeepAlive() {
    if (!ctx || keepAlive || ctx.state !== 'running') return;
    try {
      var osc = ctx.createOscillator(), gain = ctx.createGain();
      osc.frequency.value = 30;
      gain.gain.value = 0.0002;
      osc.connect(gain); gain.connect(ctx.destination);
      osc.start();
      keepAlive = osc;
    } catch (e) {}
  }

  function playBuffer(name) {
    var src = ctx.createBufferSource();
    src.buffer = buffers[name];
    src.connect(ctx.destination);
    live.push(src);
    src.onended = function () {
      var i = live.indexOf(src);
      if (i !== -1) live.splice(i, 1);
    };
    src.start(ctx.currentTime + LEAD);
  }

  function playElement(name) {
    var el = elements[name];
    if (!el) return;
    try { el.currentTime = 0; } catch (e) {}
    var p = el.play();
    if (p && p.catch) p.catch(function () { queue(name); });
  }

  function queue(name) {
    pending.push({ name: name, at: Date.now() });
  }

  function flushPending() {
    var now = Date.now();
    var todo = pending.filter(function (p) { return now - p.at < PENDING_MAX_AGE; });
    pending = [];
    todo.forEach(function (p) { play(p.name); });
  }

  function play(name, waited) {
    if (!FILES[name]) return;
    var c = ensureContext();
    // Son demandé pendant le décodage (ex. toast affiché dès l'ouverture de la page) : on attend la fin
    // au lieu de lancer l'élément <audio> qui, lui, coupe le début.
    if (c && !buffers[name] && loadings[name] && !waited) {
      var guard = new Promise(function (ok) { setTimeout(ok, 1500); });
      Promise.race([loadings[name], guard]).then(function () { play(name, true); });
      return;
    }
    if (c && buffers[name]) {
      if (c.state === 'running') { startKeepAlive(); playBuffer(name); return; }
      // contexte endormi : on tente de le réveiller, sinon repli <audio>
      var settled = false;
      var timer = setTimeout(function () { if (!settled) { settled = true; playElement(name); } }, 200);
      c.resume().then(function () {
        if (settled) return;
        settled = true; clearTimeout(timer);
        if (c.state === 'running') { startKeepAlive(); playBuffer(name); } else { playElement(name); }
      }).catch(function () {
        if (!settled) { settled = true; clearTimeout(timer); playElement(name); }
      });
      return;
    }
    playElement(name);
  }

  // Premier geste de l'utilisateur : le navigateur autorise le son → réveil, décodage, sons en attente
  function onGesture() {
    var c = ensureContext();
    if (c && c.state === 'suspended') c.resume().then(function () { startKeepAlive(); }).catch(function () {});
    loadBuffers();
    flushPending();
  }
  ['pointerdown', 'keydown', 'touchstart'].forEach(function (evt) {
    document.addEventListener(evt, onGesture, { passive: true });
  });

  // Décodage dès l'ouverture de la page (l'AudioContext démarre « endormi » tant qu'il n'y a pas eu de clic)
  loadBuffers();

  window.CHUB = window.CHUB || {};
  window.CHUB.sound = { play: play };
})();
