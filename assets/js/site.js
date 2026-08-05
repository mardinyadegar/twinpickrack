document.addEventListener('DOMContentLoaded', function () {
  // Footer year
  document.querySelectorAll('.js-year').forEach(function (el) {
    el.textContent = new Date().getFullYear();
  });

  // Mobile nav toggle
  var toggle = document.querySelector('.nav-toggle');
  var navList = document.querySelector('.nav-list');
  var scrim = document.querySelector('.nav-scrim');
  function closeNav() {
    if (!toggle || !navList) return;
    toggle.classList.remove('open');
    toggle.setAttribute('aria-expanded', 'false');
    navList.classList.remove('is-open');
    if (scrim) scrim.classList.remove('is-open');
  }
  if (toggle && navList) {
    toggle.addEventListener('click', function () {
      var open = navList.classList.toggle('is-open');
      toggle.classList.toggle('open', open);
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (scrim) scrim.classList.toggle('is-open', open);
    });
  }
  if (scrim) scrim.addEventListener('click', closeNav);

  // Mobile submenu expand (Solutions dropdown)
  document.querySelectorAll('.nav-list > li').forEach(function (li) {
    var link = li.querySelector(':scope > a');
    var sub = li.querySelector('.dropdown');
    if (!sub || !link) return;
    link.addEventListener('click', function (e) {
      if (window.innerWidth <= 900) {
        e.preventDefault();
        li.classList.toggle('is-open');
      }
    });
  });

  // Hero crossfade slider
  var hero = document.querySelector('.hero');
  if (hero) {
    var slides = Array.prototype.slice.call(hero.querySelectorAll('.hero-slide'));
    var dots = Array.prototype.slice.call(hero.querySelectorAll('.hero-dot'));
    var index = 0;
    var timer;
    function show(i) {
      slides.forEach(function (s, si) { s.classList.toggle('is-active', si === i); });
      dots.forEach(function (d, di) { d.classList.toggle('is-active', di === i); });
      index = i;
    }
    function next() { show((index + 1) % slides.length); }
    function start() { timer = setInterval(next, 6500); }
    function stop() { clearInterval(timer); }
    dots.forEach(function (d, i) {
      d.addEventListener('click', function () { stop(); show(i); start(); });
    });
    if (slides.length) { show(0); start(); }
  }

  // Scroll reveal
  var revealEls = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && revealEls.length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    revealEls.forEach(function (el) { io.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add('is-visible'); });
  }
});
