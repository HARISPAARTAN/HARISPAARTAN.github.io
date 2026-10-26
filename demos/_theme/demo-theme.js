// Portfolio theme for the demos: dark by default, light when the homepage switch is set to light
// (localStorage 'hh-theme'). Each demo loads this file and its own colour sheet from demos/_theme/.
// Loaded in <head> before the app, so the first paint already has the right colours. No dependencies.
(function () {
  'use strict';
  var root = document.documentElement;
  var script = document.currentScript;
  var demo = (script && script.getAttribute('data-demo')) || '';
  var mode = 'dark';
  try { if (localStorage.getItem('hh-theme') === 'light') mode = 'light'; } catch (e) { /* storage blocked: stay dark */ }
  root.setAttribute('data-pf', mode);

  if (demo === 'crm') crmTheme(new URL('crm-shadow.css', script.src).href);
  if (demo === 'qs-baustelle') window.__pfMap = qsMap(mode === 'light');

  // The CRM draws inside a shadow root, so page styles cannot reach it: its colour sheet is attached to that
  // root the moment the app creates it. The app also restores its own saved theme on start, so that saved
  // value is pointed at the portfolio mode; its light/dark button still works for the rest of the visit.
  function crmTheme(href) {
    try { localStorage.setItem('nscrm.theme', mode); } catch (e) { /* the attribute set below still applies */ }
    var sheet = null, css = null, roots = [];
    try { sheet = new CSSStyleSheet(); } catch (e) { /* older browser: fall back to a <style> element */ }
    fetch(href).then(function (r) { return r.ok ? r.text() : ''; }).then(function (text) {
      css = text;
      if (sheet) sheet.replace(text); else roots.forEach(addStyle);
    }).catch(function () { /* the app keeps its own colours */ });
    function addStyle(sr) {
      var s = document.createElement('style'); s.textContent = css; sr.appendChild(s);
    }
    var attach = Element.prototype.attachShadow;
    Element.prototype.attachShadow = function (init) {
      var sr = attach.call(this, init);
      if (this.id === 'crm') {
        this.setAttribute('data-theme', mode);
        if (sheet) sr.adoptedStyleSheets = sr.adoptedStyleSheets.concat(sheet);
        else if (css !== null) addStyle(sr); else roots.push(sr);
      }
      return sr;
    };
  }

  function parse(c) {
    var m = /^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$/i.exec(c);
    if (m) return [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]];
    m = /^#([0-9a-f]{6})$/i.exec(c);
    if (m) { var n = parseInt(m[1], 16); return [n >> 16, (n >> 8) & 255, n & 255, 1]; }
    return null;
  }
  function lum(p) {
    var f = function (v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(p[0]) + 0.7152 * f(p[1]) + 0.0722 * f(p[2]);
  }
  function contrast(a, b) { var x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); }
  function withAlpha(hex, a) { var p = parse(hex); return 'rgba(' + p[0] + ',' + p[1] + ',' + p[2] + ',' + a + ')'; }

  // QS Baustelle: every control colour passes through the renderer's colour resolver, which calls this.
  // Colours are mapped by role (fill, text, border), by control kind and size, then text is checked
  // against the control's own fill so it never drops below 4.5:1.
  function qsMap(light) {
    var P = light ? {
      bg: '#F7F7F4', surface: '#FFFFFF', surface2: '#F3F2EE', line: '#E6E3DB', line2: '#DDD9D0',
      text: '#14181D', muted: '#5B6472', faint: '#8A929C', accent: '#B45309', accentSoft: '#FBEEDB',
      warnSoft: '#FDF3E0', danger: '#B42318', header: '#B45309', heading: '#14181D', accentText: '#B45309',
      onDark: '#FFFFFF', lime: '#FBEEDB', gold: '#8A6A2F', red: '#B42318', blue: '#1D5FB8', green: '#15803D',
      onAccent: '#FFFFFF', overlay: 0.5
    } : {
      bg: '#0B0F14', surface: '#121820', surface2: '#182130', line: '#1F2A36', line2: '#2A3646',
      text: '#E6EDF3', muted: '#93A1B0', faint: '#7D8A99', accent: '#F2A93B', accentSoft: '#2E2819',
      warnSoft: '#2A2416', danger: '#DA3633', header: '#121820', heading: '#E6EDF3', accentText: '#F2A93B',
      onDark: '#E6EDF3', lime: '#F2A93B', gold: '#E3B341', red: '#FF7B72', blue: '#6CB6FF', green: '#3DDC97',
      onAccent: '#1A1200', overlay: 0.6
    };
    var FILL = { Fill: 1, DisabledFill: 1, ScreenFill: 1, RailFill: 1, ValueFill: 1, HoverFill: 1, PressedFill: 1 };
    var TEXT = { Color: 1, DisabledColor: 1 };
    var produced = {};

    function size(ctl, r, rows) {
      if (!ctl || !r) return { w: 640, h: 1136 };
      return { w: +r.prop(ctl, 'Width', rows, 100) || 0, h: +r.prop(ctl, 'Height', rows, 40) || 0 };
    }
    function fill(key, p, ctl, name, r, rows) {
      var kind = ctl ? ctl.kind : 'screen', s, thin;
      switch (key) {
        case '255,255,255': return name === 'ScreenFill' ? P.bg : P.surface;
        case '248,248,246': case '244,242,238': return P.surface2;
        case '230,226,220': return name === 'RailFill' ? P.line2 : P.line;
        case '0,60,80': case '26,78,96':
          if (light || name === 'ValueFill' || kind === 'button' || kind === 'icon') return P.accent;
          s = size(ctl, r, rows); thin = s.w <= 12 || s.h <= 12;
          return thin ? P.accent : P.header;
        case '230,255,128': case '201,226,102':
          s = size(ctl, r, rows); thin = s.w <= 12 || s.h <= 12;
          return thin ? P.accent : P.accentSoft;
        case '253,243,224': return P.warnSoft;
        case '140,47,47': case '178,59,59': return P.danger;
        case '56,96,178': return P.blue;
        case '31,107,79': return P.green;
        case '0,0,0': return null;
      }
      if (light) return null;
      var L = lum(p);
      return L > 0.75 ? P.surface : L > 0.5 ? P.surface2 : null;
    }
    function text(key, p, ctl, r, rows) {
      switch (key) {
        case '38,44,48': case '0,0,0': case '0,18,107': return P.text;
        case '110,118,114': case '92,102,107': return P.muted;
        case '156,160,156': case '138,146,151': return P.faint;
        case '255,255,255': return P.onDark;
        case '0,60,80': case '26,78,96':
          var sz = ctl && r ? +r.prop(ctl, 'Size', rows, 13) : 13;
          return ctl && ctl.kind === 'label' && sz >= 16 ? P.heading : P.accentText;
        case '230,255,128': case '201,226,102': return P.lime;
        case '138,106,47': return P.gold;
        case '140,47,47': case '178,59,59': case '168,0,15': return P.red;
        case '56,96,178': return P.blue;
        case '31,107,79': return P.green;
      }
      if (light) return null;
      return lum(p) < 0.25 ? P.text : null;
    }
    function border(key, p) {
      switch (key) {
        case '230,226,220': case '223,218,210': case '236,232,225': return P.line2;
        case '0,60,80': case '26,78,96': return P.accent;
        case '230,255,128': return P.accent;
      }
      if (light) return null;
      return lum(p) > 0.5 ? P.line2 : null;
    }

    return function (c, ctl, name, r, rows) {
      if (typeof c !== 'string' || produced[c]) return c;
      var p = parse(c);
      if (!p || p[3] === 0) return c;
      var key = p[0] + ',' + p[1] + ',' + p[2], out = null;
      if (FILL[name]) {
        out = (key === '0,0,0' && p[3] < 1) ? 'rgba(0,0,0,' + P.overlay + ')' : fill(key, p, ctl, name, r, rows);
      } else if (TEXT[name]) {
        out = text(key, p, ctl, r, rows);
        if (ctl && r) {
          var own = parse(r.color(ctl, 'Fill', rows, 'rgba(0,0,0,0)')), rp = parse(out || c);
          if (own && own[3] > 0.5 && rp && contrast(rp, own) < 4.5) {
            var bc = 0;
            [P.text, P.onAccent, '#FFFFFF', '#14181D'].forEach(function (h) {
              var cc = contrast(parse(h), own); if (cc > bc) { bc = cc; out = h; }
            });
          }
        }
      } else if (name === 'BorderColor') {
        out = border(key, p);
      }
      if (!out) return c;
      if (p[3] < 1 && out.charAt(0) === '#') out = withAlpha(out, p[3]);
      produced[out] = 1;
      return out;
    };
  }
})();
