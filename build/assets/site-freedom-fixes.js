// Site Freedom fixes — tiny replacements for platform JavaScript. Safe to edit.
(function () {
  // 1. Lazy images: copy data-src / data-srcset into the real attributes
  document.querySelectorAll('img[data-src], img[data-srcset], source[data-srcset]').forEach(function (el) {
    var s = el.getAttribute('data-src');
    var cur = el.getAttribute('src') || '';
    if (s && (!cur || cur.indexOf('data:') === 0)) el.setAttribute('src', s);
    var ss = el.getAttribute('data-srcset');
    if (ss && !el.getAttribute('srcset')) el.setAttribute('srcset', ss);
  });
  document.querySelectorAll('img').forEach(function (img) { img.classList.add('loaded'); });

  // 2. Mobile menu buttons (Squarespace 7.1 burger and generic toggles)
  document.querySelectorAll('.header-burger-btn, [data-test="header-burger"], .burger, .menu-toggle').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      var open = !document.body.classList.contains('header--menu-open');
      document.body.classList.toggle('header--menu-open', open);
      var header = document.querySelector('header, #header');
      if (header) header.classList.toggle('header--menu-open', open);
      btn.classList.toggle('burger--active', open);
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  });
  document.querySelectorAll('.header-menu a').forEach(function (a) {
    a.addEventListener('click', function () {
      document.body.classList.remove('header--menu-open');
      var header = document.querySelector('header, #header');
      if (header) header.classList.remove('header--menu-open');
    });
  });

  // 3. Squarespace 7.1 masonry gallery sections: lay items into N columns, each
  //    item going to the currently shortest column (what Squarespace's JS did).
  //    Desktop uses the section's own numColumns/gutter; phones use 2 columns.
  function layoutMasonry() {
    document.querySelectorAll('.gallery-masonry').forEach(function (g) {
      var wrap = g.querySelector('.gallery-masonry-wrapper'); if (!wrap) return;
      var props = {}; try { props = JSON.parse(g.getAttribute('data-props') || '{}'); } catch (e) {}
      var mobile = window.innerWidth < 768;
      var cols = mobile ? 2 : (props.numColumns || 3);
      var gap = mobile ? 5 : Math.round((props.gutter || 50) * window.innerWidth * 0.00048);
      var items = g._sfItems || Array.prototype.slice.call(wrap.querySelectorAll('.gallery-masonry-item'));
      g._sfItems = items;
      wrap.innerHTML = '';
      wrap.style.cssText = 'display:flex;align-items:flex-start;gap:' + gap + 'px;height:auto;position:relative';
      var columns = [], heights = [];
      for (var i = 0; i < cols; i++) {
        var c = document.createElement('div');
        c.style.cssText = 'flex:1 1 0;min-width:0;display:flex;flex-direction:column;gap:' + gap + 'px';
        wrap.appendChild(c); columns.push(c); heights.push(0);
      }
      items.forEach(function (it) {
        var img = it.querySelector('img');
        var dims = img && (img.getAttribute('data-image-dimensions') || '').split('x');
        var ratio = dims && dims.length === 2 && +dims[0] ? (+dims[1] / +dims[0]) : 1;
        var k = heights.indexOf(Math.min.apply(null, heights));
        it.style.cssText = 'position:static;width:auto;height:auto;transform:none;opacity:1;margin:0';
        if (img) { img.style.cssText = 'width:100%;height:auto;position:static;opacity:1;object-fit:cover'; }
        columns[k].appendChild(it); heights[k] += ratio;
      });
    });
  }
  layoutMasonry();
  var _sfW = window.innerWidth;
  window.addEventListener('resize', function () {
    if ((window.innerWidth < 768) !== (_sfW < 768)) { _sfW = window.innerWidth; layoutMasonry(); }
  });

  // 4. Disclosure buttons (accordions) that point at a panel with aria-controls
  document.querySelectorAll('button[aria-controls]').forEach(function (btn) {
    var panel = document.getElementById(btn.getAttribute('aria-controls'));
    if (!panel || btn.closest('header')) return;
    btn.addEventListener('click', function () {
      var open = btn.getAttribute('aria-expanded') !== 'true';
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      panel.hidden = !open;
      panel.style.height = open ? 'auto' : '';
      var item = btn.closest('li, .accordion-item');
      if (item) item.classList.toggle('accordion-item--expanded', open);
    });
  });
})();
