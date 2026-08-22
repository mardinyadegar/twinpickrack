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

  // Gallery lightbox
  var galleryItems = Array.prototype.slice.call(document.querySelectorAll('.gallery-item'));
  var lightbox = document.getElementById('lightbox');
  if (galleryItems.length && lightbox) {
    var lbImg = lightbox.querySelector('.lightbox-img');
    var lbCaption = lightbox.querySelector('.lightbox-caption');
    var lbClose = lightbox.querySelector('.lightbox-close');
    var lbPrev = lightbox.querySelector('.lightbox-prev');
    var lbNext = lightbox.querySelector('.lightbox-next');
    var current = 0;

    function openLightbox(i) {
      current = (i + galleryItems.length) % galleryItems.length;
      var item = galleryItems[current];
      lbImg.src = item.getAttribute('data-full');
      lbImg.alt = item.getAttribute('data-caption') || '';
      lbCaption.textContent = item.getAttribute('data-caption') || '';
      lightbox.classList.add('is-open');
      lightbox.setAttribute('aria-hidden', 'false');
      document.body.classList.add('lightbox-open');
    }
    function closeLightbox() {
      lightbox.classList.remove('is-open');
      lightbox.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('lightbox-open');
    }

    galleryItems.forEach(function (item, i) {
      item.addEventListener('click', function () { openLightbox(i); });
    });
    if (lbClose) lbClose.addEventListener('click', closeLightbox);
    if (lbPrev) lbPrev.addEventListener('click', function () { openLightbox(current - 1); });
    if (lbNext) lbNext.addEventListener('click', function () { openLightbox(current + 1); });
    lightbox.addEventListener('click', function (e) {
      if (e.target === lightbox) closeLightbox();
    });
    document.addEventListener('keydown', function (e) {
      if (!lightbox.classList.contains('is-open')) return;
      if (e.key === 'Escape') closeLightbox();
      if (e.key === 'ArrowLeft') openLightbox(current - 1);
      if (e.key === 'ArrowRight') openLightbox(current + 1);
    });
  }

  // Dock equipment catalog explorer
  var catalogItems = Array.prototype.slice.call(document.querySelectorAll('.catalog-item'));
  var catalogPreviewImg = document.getElementById('catalogPreviewImg');
  if (catalogItems.length && catalogPreviewImg) {
    var catalogPreviewEyebrow = document.getElementById('catalogPreviewEyebrow');
    var catalogPreviewName = document.getElementById('catalogPreviewName');
    var catalogPreviewDesc = document.getElementById('catalogPreviewDesc');
    var catalogPreviewLink = document.getElementById('catalogPreviewLink');

    catalogItems.forEach(function (item) {
      item.addEventListener('click', function (e) {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
        e.preventDefault();

        catalogItems.forEach(function (i) { i.classList.remove('is-active'); });
        item.classList.add('is-active');

        catalogPreviewImg.classList.remove('is-loaded');
        catalogPreviewImg.src = item.getAttribute('data-img');
        catalogPreviewImg.alt = item.textContent;
        catalogPreviewEyebrow.textContent = item.getAttribute('data-cat') || '';
        catalogPreviewName.textContent = item.textContent;
        catalogPreviewDesc.textContent = item.getAttribute('data-desc') || '';
        catalogPreviewLink.href = item.getAttribute('href');
      });
    });
    if (catalogPreviewImg.complete) {
      catalogPreviewImg.classList.add('is-loaded');
    }
    catalogPreviewImg.addEventListener('load', function () {
      catalogPreviewImg.classList.add('is-loaded');
    });
  }
});
