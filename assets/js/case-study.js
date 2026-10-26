// Case-study pages: the architecture-diagram player. No dependencies, no network.
// Reads everything from the page: steps from the list (data-title, data-nodes, data-edges), nodes and arrows from the
// SVGs (data-node, data-edge, data-step-badge), strings and timing from data attributes on [data-cs-flow].
(function () {
  'use strict';
  var NS = 'http://www.w3.org/2000/svg';
  var PLAY = 'M8 5v14l11-7z', PAUSE = 'M7 5h4v14H7zM13 5h4v14h-4z';

  function media(q) { return window.matchMedia ? window.matchMedia(q) : { matches: false }; }
  function listen(m, fn) { if (m.addEventListener) m.addEventListener('change', fn); else if (m.addListener) m.addListener(fn); }
  function all(el, sel) { return Array.prototype.slice.call(el.querySelectorAll(sel)); }
  function words(el, attr) { var v = el.getAttribute(attr); return v ? v.split(' ') : []; }
  function mark(g, on) { g.classList.toggle('on', on); g.classList.toggle('off', !on); }

  var wide = media('(min-width: 700px)');
  var reduce = media('(prefers-reduced-motion: reduce)');

  function player(box) {
    var items = all(box, '.steps > li');
    var svgs = all(box, 'svg.flow');
    if (!items.length || !svgs.length) return;
    var caption = box.querySelector('[data-cs-caption]');
    var toggle = box.querySelector('[data-cs-toggle]');
    var label = toggle && toggle.querySelector('[data-cs-toggle-label]');
    var icon = toggle && toggle.querySelector('path');
    var pattern = box.getAttribute('data-caption') || '{n}/{total} {title}';
    var interval = Number(box.getAttribute('data-interval')) || 3800;
    var buttons = [], dots = [];
    var cur = 0, playing = !reduce.matches, inView = false;
    var elapsed = 0, phase = 0, last = 0, raf = 0;

    // The steps become buttons: same content, same classes.
    items.forEach(function (li, i) {
      var plain = li.firstElementChild, b = document.createElement('button');
      b.type = 'button';
      b.className = plain.className;
      while (plain.firstChild) b.appendChild(plain.firstChild);
      li.replaceChild(b, plain);
      b.addEventListener('click', function () { playing = false; show(i); kick(); });
      buttons.push(b);
    });

    function running() { return playing && inView && !document.hidden && !reduce.matches; }

    function visible() {
      return svgs.filter(function (s) { return s.getClientRects().length > 0; })[0] || null;
    }

    function circle(g, cls, r) {
      var c = document.createElementNS(NS, 'circle');
      c.setAttribute('class', cls);
      c.setAttribute('r', r);
      g.appendChild(c);
      return c;
    }

    // Two dots per active arrow, drawn in the layout that is on screen.
    function draw() {
      svgs.forEach(function (s) { var g = s.querySelector('.dots'); while (g && g.firstChild) g.removeChild(g.firstChild); });
      dots = [];
      var svg = visible(), g = svg && svg.querySelector('.dots');
      if (!g) return;
      words(items[cur], 'data-edges').forEach(function (id) {
        var line = svg.querySelector('[data-edge="' + id + '"] .line');
        if (!line) return;
        for (var k = 0; k < 2; k++) {
          dots.push({ line: line, len: line.getTotalLength(), k: k, halo: circle(g, 'halo', 8), dot: circle(g, 'dot', 4) });
        }
      });
      place();
    }

    // Moving dots while the player runs; otherwise they rest at fixed points on the arrow.
    function place() {
      var run = running();
      dots.forEach(function (d) {
        var f = run ? (phase / 1500 + d.k / 2) % 1 : (d.k ? 0.72 : 0.3);
        var p = d.line.getPointAtLength(f * d.len);
        d.halo.setAttribute('cx', p.x); d.halo.setAttribute('cy', p.y);
        d.dot.setAttribute('cx', p.x); d.dot.setAttribute('cy', p.y);
      });
    }

    function render() {
      if (caption) {
        caption.textContent = pattern.replace('{n}', cur + 1).replace('{total}', items.length)
          .replace('{title}', items[cur].getAttribute('data-title') || '');
        caption.setAttribute('aria-live', playing ? 'off' : 'polite');
      }
      if (toggle) {
        toggle.hidden = reduce.matches;
        label.textContent = box.getAttribute(playing ? 'data-pause' : 'data-play') || '';
        icon.setAttribute('d', playing ? PAUSE : PLAY);
      }
    }

    function show(i) {
      cur = (i + items.length) % items.length;
      elapsed = 0; phase = 0;
      var nodes = words(items[cur], 'data-nodes'), edges = words(items[cur], 'data-edges');
      svgs.forEach(function (s) {
        all(s, '[data-node]').forEach(function (g) { mark(g, nodes.indexOf(g.getAttribute('data-node')) >= 0); });
        all(s, '[data-edge]').forEach(function (g) { mark(g, edges.indexOf(g.getAttribute('data-edge')) >= 0); });
        all(s, '[data-step-badge]').forEach(function (g) { g.classList.toggle('on', Number(g.getAttribute('data-step-badge')) === cur + 1); });
      });
      buttons.forEach(function (b, k) { if (k === cur) b.setAttribute('aria-current', 'step'); else b.removeAttribute('aria-current'); });
      draw();
      render();
    }

    // One animation frame loop, alive only while the player runs (playing, on screen, tab visible, motion allowed).
    function frame(now) {
      raf = 0;
      if (!running()) { last = 0; return; }
      var dt = last ? Math.min(now - last, 100) : 0;
      last = now; elapsed += dt; phase += dt;
      if (elapsed >= interval) show(cur + 1);
      place();
      raf = requestAnimationFrame(frame);
    }
    function kick() {
      if (!running()) { place(); return; }
      if (!raf) { last = 0; raf = requestAnimationFrame(frame); }
    }

    if (toggle) toggle.addEventListener('click', function () { playing = !playing; elapsed = 0; render(); kick(); });
    document.addEventListener('visibilitychange', kick);
    listen(wide, draw);
    listen(reduce, function () { if (reduce.matches) playing = false; render(); kick(); });
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        inView = entries[entries.length - 1].isIntersecting;
        kick();
      }, { threshold: 0.15 }).observe(box.querySelector('.diagram') || box);
    } else {
      inView = true;
    }
    show(0);
    kick();
  }

  all(document, '[data-cs-flow]').forEach(player);

  // site.js sets the theme button label in English; put the page's own language back.
  var theme = document.getElementById('theme-toggle');
  function themeLabel() {
    var light = document.documentElement.getAttribute('data-theme') === 'light';
    var text = theme.getAttribute(light ? 'data-label-dark' : 'data-label-light');
    if (text) theme.setAttribute('aria-label', text);
  }
  if (theme) { themeLabel(); theme.addEventListener('click', themeLabel); }
})();
