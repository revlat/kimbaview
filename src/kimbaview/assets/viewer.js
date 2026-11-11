/* kimbaview – einziges Skript im Fenster (per CSP-Nonce erlaubt).
 * Aufgaben: Inhalte austauschen (Scrollposition halten), Hinweise anzeigen,
 * Link-Klicks kontrollieren (lokale Dokument-Links an Python melden),
 * Textbreite, Drag & Drop-Navigation verhindern. */
(function () {
  'use strict';
  var content = document.getElementById('wv-content');
  var notice = document.getElementById('wv-notice');
  var restoreUntil = 0, restoreX = 0, restoreY = 0;

  function stopRestore() { restoreUntil = 0; }
  ['wheel', 'keydown', 'mousedown', 'touchstart'].forEach(function (t) {
    window.addEventListener(t, stopRestore, { passive: true, capture: true });
  });

  function keepScroll() {
    if (Date.now() < restoreUntil) window.scrollTo(restoreX, restoreY);
  }

  function setNotice(text, level) {
    if (text) {
      notice.textContent = text;            // nie als HTML interpretiert
      notice.className = 'wv-notice wv-notice-' + (level === 'error' ? 'error' : 'warn');
      notice.hidden = false;
    } else {
      notice.hidden = true;
      notice.textContent = '';
    }
  }

  function setContent(html) {
    restoreX = window.scrollX; restoreY = window.scrollY;
    // html ist bereits in Python mit nh3 bereinigt; die CSP bleibt zweite Verteidigungslinie.
    content.innerHTML = html;
    restoreUntil = Date.now() + 1500;
    keepScroll();
    // Zieladresse externer Links als Tooltip zeigen (es gibt keine Statusleiste).
    var anchors = content.querySelectorAll('a[href^="http:"], a[href^="https:"]');
    for (var k = 0; k < anchors.length; k++) {
      var h = anchors[k].getAttribute('href');
      var t = anchors[k].getAttribute('title');
      anchors[k].setAttribute('title', t ? t + '\n' + h : h);
    }
    var imgs = content.getElementsByTagName('img');
    for (var i = 0; i < imgs.length; i++) {
      if (!imgs[i].complete) imgs[i].addEventListener('load', keepScroll, { once: true });
    }
    requestAnimationFrame(keepScroll);
  }

  // ---------------------------------------------------------------- Kurzmeldung
  var toast = document.getElementById('wv-toast');
  var toastTimer = 0;
  function showToast(text) {
    toast.textContent = text;               // nie als HTML interpretiert
    toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.hidden = true; }, 6000);
  }
  toast.addEventListener('click', function () { toast.hidden = true; });

  function scrollToY(y) {
    restoreX = 0; restoreY = y; restoreUntil = Date.now() + 1500;
    window.scrollTo(0, y);
    requestAnimationFrame(keepScroll);
  }
  function scrollToAnchor(name) {
    var t = document.getElementById('wv-u-' + name);   // Dokument-IDs tragen das Präfix
    if (t && content.contains(t)) {
      t.scrollIntoView();
      scrollToY(window.scrollY);
    } else {
      scrollToY(0);
    }
  }

  function update(p) {
    if (!p || typeof p !== 'object') return;
    if (typeof p.html === 'string') setContent(p.html);
    if ('notice' in p) setNotice(typeof p.notice === 'string' ? p.notice : '', p.level);
    if (p.nav && typeof p.nav === 'object') setNav(!!p.nav.back, !!p.nav.forward);
    if (typeof p.anchor === 'string') scrollToAnchor(p.anchor);
    else if (typeof p.scroll === 'number') scrollToY(p.scroll);
    if (typeof p.toast === 'string') showToast(p.toast);
  }

  // ---------------------------------------------------------------- Navigation
  // Wunsch an Python melden: über pywebview.state (keine JS-API-Funktion).
  // Python prüft jede Anfrage (nur Dokument-Dateien im erlaubten Ordner).
  var navSeq = 0;
  function requestNav(req) {
    req.seq = ++navSeq;
    try { if (window.pywebview && window.pywebview.state) window.pywebview.state.wv_nav = req; } catch (e) {}
  }
  var navGroup = document.getElementById('wv-navgroup');
  var btnBack = document.getElementById('wv-back');
  var btnFwd = document.getElementById('wv-forward');
  function setNav(back, fwd) {
    btnBack.disabled = !back;
    btnFwd.disabled = !fwd;
    navGroup.hidden = !(back || fwd);
  }
  btnBack.addEventListener('click', function () { requestNav({ action: 'back' }); });
  btnFwd.addEventListener('click', function () { requestNav({ action: 'forward' }); });
  window.addEventListener('keydown', function (ev) {
    if (!ev.altKey || ev.ctrlKey || ev.shiftKey) return;
    if (ev.key === 'ArrowLeft') { ev.preventDefault(); requestNav({ action: 'back' }); }
    else if (ev.key === 'ArrowRight') { ev.preventDefault(); requestNav({ action: 'forward' }); }
  });
  window.addEventListener('mouseup', function (ev) {      // Maus-Seitentasten
    if (ev.button === 3) { ev.preventDefault(); requestNav({ action: 'back' }); }
    else if (ev.button === 4) { ev.preventDefault(); requestNav({ action: 'forward' }); }
  });

  function onLinkClick(ev) {
    var el = ev.target;
    var a = el && el.closest ? el.closest('a') : null;
    if (!a) return;
    var href = a.getAttribute('href') || '';
    if (ev.type === 'auxclick' && ev.button !== 1) return;  // Rechtsklick o. Ä. nicht anfassen
    if (href.charAt(0) === '#') {           // Sprung innerhalb des Dokuments
      ev.preventDefault();
      var id; try { id = decodeURIComponent(href.slice(1)); } catch (e) { return; }
      var t = document.getElementById(id);
      if (t && content.contains(t)) t.scrollIntoView();
      return;
    }
    var u = null;
    try { u = new URL(href); } catch (e) { u = null; }
    if (u && (u.protocol === 'http:' || u.protocol === 'https:')) {
      // Standardaktion zulassen: target=_blank → pywebview → geprüftes
      // webbrowser.open in Python → Standardbrowser. Nie im Reader-Fenster.
      a.setAttribute('target', '_blank');
      return;
    }
    ev.preventDefault();                    // nie im Reader-Fenster navigieren
    if (!u && href) {
      // relativer Link → evtl. anderes lokales Dokument; Python entscheidet
      var newWin = ev.type === 'auxclick' || ev.ctrlKey || ev.metaKey || ev.shiftKey;
      requestNav({ action: 'open', href: href, mode: newWin ? 'new' : 'same' });
    }
  }
  document.addEventListener('click', onLinkClick, true);
  document.addEventListener('auxclick', onLinkClick, true);

  // Fallengelassene Dateien würden sonst ungeprüft im Fenster geöffnet.
  ['dragover', 'drop'].forEach(function (t) {
    window.addEventListener(t, function (ev) { ev.preventDefault(); }, true);
  });

  // ---------------------------------------------------------------- Textbreite
  var STEPS = /*WIDTH_STEPS*/;              // in Python eingesetzt; 0 = volle Breite
  var FULL_LABEL = /*FULL_LABEL*/;          // übersetzter Text für "volle Breite"
  var btnNarrow = document.getElementById('wv-narrower');
  var btnWide = document.getElementById('wv-wider');
  var btnFull = document.getElementById('wv-full');
  var label = document.getElementById('wv-width-label');
  var width = parseInt(content.getAttribute('data-wv-width'), 10);
  if (STEPS.indexOf(width) < 0) width = 800;
  var lastFixed = width || 800;
  var fixedSteps = STEPS.filter(function (s) { return s > 0; });

  function applyWidth(w, remember) {
    width = w;
    if (w) lastFixed = w;
    // CSSOM-Zugriff ist mit der CSP vereinbar (kein style-Attribut im Markup).
    document.documentElement.style.setProperty('--wv-width', w ? w + 'px' : 'none');
    label.textContent = w ? w + ' px' : FULL_LABEL;
    btnNarrow.disabled = (w === fixedSteps[0]);
    btnWide.disabled = (w === 0);
    btnFull.setAttribute('aria-pressed', w === 0 ? 'true' : 'false');
    if (remember) {
      // Python liest den Wert beim Schließen aus (pywebview.state, keine JS-API-Funktion).
      try { if (window.pywebview && window.pywebview.state) window.pywebview.state.wv_width = w; } catch (e) {}
    }
  }
  function step(dir) {
    if (width === 0) { if (dir < 0) applyWidth(fixedSteps[fixedSteps.length - 1], true); return; }
    var i = fixedSteps.indexOf(width) + dir;
    if (i >= fixedSteps.length) applyWidth(0, true);
    else if (i >= 0) applyWidth(fixedSteps[i], true);
  }
  function toggleFull() { applyWidth(width === 0 ? lastFixed : 0, true); }

  btnNarrow.addEventListener('click', function () { step(-1); });
  btnWide.addEventListener('click', function () { step(1); });
  btnFull.addEventListener('click', toggleFull);
  window.addEventListener('keydown', function (ev) {
    if (!(ev.ctrlKey && ev.shiftKey) || ev.altKey) return;
    if (ev.key === 'ArrowLeft') { ev.preventDefault(); step(-1); }
    else if (ev.key === 'ArrowRight') { ev.preventDefault(); step(1); }
    else if (ev.key === 'F' || ev.key === 'f') { ev.preventDefault(); toggleFull(); }
  });
  applyWidth(width, false);

  Object.defineProperty(window, '__kimbaview', {
    value: Object.freeze({ update: update }),
    writable: false, configurable: false
  });
})();
