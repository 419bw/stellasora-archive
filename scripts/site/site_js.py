# -*- coding: utf-8 -*-
"""Client-side interactions and search engine script for StellaSora story knowledge base."""

JS = """(function() {
  // Theme management
  var themeToggle = document.getElementById('themeToggle');
  function setTheme(t) {
    document.documentElement.setAttribute('data-theme', t);
    localStorage.setItem('stellasora-theme', t);
  }
  if (themeToggle) {
    themeToggle.addEventListener('click', function() {
      var cur = document.documentElement.getAttribute('data-theme') || 'light';
      setTheme(cur === 'dark' ? 'light' : 'dark');
    });
  }

  // Back to top button
  var btt = document.getElementById('backToTop');
  if (btt) {
    window.addEventListener('scroll', function() {
      if (window.scrollY > 300) btt.classList.add('visible');
      else btt.classList.remove('visible');
    }, { passive: true });
    btt.addEventListener('click', function() {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // Search Engine
  var IDX = (window.STORY_INDEX || { entries: [] }).entries;
  var FAM = { npc: 'npc_bonds', battles: 'battles_unmounted' };
  function norm(s) { return (s || '').toLowerCase(); }
  function score(e, q) {
    var s = 0, t = norm(e.title + ' ' + e.code + ' ' + e.group), h = norm(e.hay), sp = norm(e.speakers.join(' '));
    if (t.indexOf(q) >= 0) s += 6;
    if (sp.indexOf(q) >= 0) s += 4;
    if (h.indexOf(q) >= 0) s += 2;
    for (var i = 0; i + 2 <= q.length; i++) {
      var g = q.substr(i, 2);
      if (h.indexOf(g) >= 0) s += 1;
      if (sp.indexOf(g) >= 0) s += 1;
    }
    return s;
  }
  function run(box, pane, scope, root, q) {
    var hits = [];
    for (var i = 0; i < IDX.length; i++) {
      var e = IDX[i];
      if (scope !== '_all' && (e.family !== (FAM[scope] || scope))) continue;
      var s = score(e, q);
      if (s > 0) hits.push([s, e]);
    }
    hits.sort(function(a, b) { return b[0] - a[0] || String(a[1].title).localeCompare(b[1].title); });
    pane.hidden = false;
    if (!hits.length) {
      pane.innerHTML = '<p class="aside" style="padding:10px 0;">未检索到匹配的剧情档案。</p>';
      return;
    }
    var out = ['<div class="results-header"><span>匹配到 ' + hits.length + ' 篇档案（最多显示 40 篇）</span></div><ul class="hits">'];
    hits.slice(0, 40).forEach(function(h) {
      var e = h[1];
      var displayTitle = (e.code && e.title && e.title.indexOf(e.code) === 0) ? e.title : [e.code, e.title].filter(Boolean).join(' ');
      out.push('<li><a class="hit-link" href="' + root + e.page + '">'
        + '<div class="hit-top"><b class="hit-title">' + displayTitle + '</b>'
        + '<span class="hit-group">' + e.group + '</span></div>'
        + '<div class="hit-speakers">' + (e.speakers.slice(0, 5).join('、') || '旁白') + '</div>'
        + '</a></li>');
    });
    pane.innerHTML = out.join('') + '</ul>';
  }

  [].slice.call(document.querySelectorAll('.searchbox input')).forEach(function(box) {
    var pane = box.closest('.searchbox').querySelector('.results');
    var scope = box.getAttribute('data-scope'), root = box.getAttribute('data-root') || '';
    var groups = [].slice.call(document.querySelectorAll('.grp, .chaplist li, .bento-item, .tiles li'));
    box.addEventListener('input', function() {
      var q = box.value.trim().toLowerCase();
      groups.forEach(function(g) {
        g.style.display = (!q || g.textContent.toLowerCase().indexOf(q) >= 0) ? '' : 'none';
      });
      if (q.length >= 1 && IDX.length) run(box, pane, scope, root, q);
      else pane.hidden = true;
    });
  });

  // Global Ctrl+K / Cmd+K to focus search
  window.addEventListener('keydown', function(e) {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      var box = document.querySelector('.searchbox input');
      if (box) {
        e.preventDefault();
        box.focus();
        box.select();
      }
    }
  });

  // Interactive Drag-to-Scroll on Node Map
  var map = document.querySelector('.map');
  if (map) {
    var isDown = false, startX, scrollLeft;
    map.addEventListener('mousedown', function(e) {
      if (e.target.closest('a')) return;
      isDown = true;
      startX = e.pageX - map.offsetLeft;
      scrollLeft = map.scrollLeft;
    });
    window.addEventListener('mouseup', function() { isDown = false; });
    map.addEventListener('mousemove', function(e) {
      if (!isDown) return;
      e.preventDefault();
      var x = e.pageX - map.offsetLeft;
      var walk = (x - startX) * 1.5;
      map.scrollLeft = scrollLeft - walk;
    });
  }

  // Smooth jump to anchor in map
  [].slice.call(document.querySelectorAll('[data-scroll-to]')).forEach(function(a) {
    a.addEventListener('click', function(e) {
      if (!map || window.innerWidth <= 900) return;
      e.preventDefault();
      map.scrollTo({ left: parseInt(a.getAttribute('data-scroll-to'), 10) - 40, behavior: 'smooth' });
    });
  });

  // Choice & Branch smooth scroll jump with highlight pulse
  document.addEventListener('click', function(e) {
    var link = e.target.closest('.opt-link, .branch-nav-btn');
    if (!link) return;
    var href = link.getAttribute('href');
    if (!href || href.charAt(0) !== '#') return;
    var target = document.querySelector(href);
    if (!target) return;
    e.preventDefault();
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    if (history.pushState) {
      history.pushState(null, '', href);
    } else {
      location.hash = href;
    }
    target.classList.remove('target-flash');
    void target.offsetWidth;
    target.classList.add('target-flash');
  });
})();
"""
