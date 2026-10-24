// Theme toggle, mobile menu, scroll reveal. No dependencies, no network.
(function () {
  'use strict';
  var root = document.documentElement;
  var KEY = 'hh-theme';

  function current() { return root.getAttribute('data-theme') === 'light' ? 'light' : 'dark'; }
  function apply(theme) {
    if (theme === 'light') root.setAttribute('data-theme', 'light'); else root.removeAttribute('data-theme');
    var btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.setAttribute('aria-label', theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme');
      btn.setAttribute('aria-pressed', theme === 'light' ? 'true' : 'false');
    }
  }
  var toggle = document.getElementById('theme-toggle');
  if (toggle) {
    apply(current());
    toggle.addEventListener('click', function () {
      var next = current() === 'light' ? 'dark' : 'light';
      apply(next);
      try { localStorage.setItem(KEY, next); } catch (e) { /* storage unavailable: theme stays for this view */ }
    });
  }

  var menu = document.getElementById('menu-toggle');
  var links = document.getElementById('nav-links');
  if (menu && links) {
    menu.addEventListener('click', function () {
      var open = links.classList.toggle('open');
      menu.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    links.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') { links.classList.remove('open'); menu.setAttribute('aria-expanded', 'false'); }
    });
  }

  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var items = document.querySelectorAll('.reveal');
  if (!reduced && 'IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) { entry.target.classList.add('in'); io.unobserve(entry.target); }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });
    items.forEach(function (el) { io.observe(el); });
    // Fail-safe: anything still hidden after 2.5 s is shown.
    setTimeout(function () { items.forEach(function (el) { el.classList.add('in'); }); }, 2500);
  } else {
    items.forEach(function (el) { el.classList.add('in'); });
  }

  var year = document.getElementById('year');
  if (year) year.textContent = String(new Date().getFullYear());
})();
