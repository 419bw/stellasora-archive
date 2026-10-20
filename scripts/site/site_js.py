# -*- coding: utf-8 -*-
"""Client-side interactions and search engine script for StellaSora story knowledge base."""

JS = """(function() {
  document.querySelectorAll('.text-variants').forEach(function(variants) {
    var controls = variants.querySelector('.text-variant-controls');
    var card = variants.closest('.line, .player-reply');
    if (card) {
      var heading = card.querySelector('.who, .reply-who');
      var header = document.createElement('span');
      header.className = 'line-header';
      heading.before(header);
      header.append(heading, controls);
    }
    controls.addEventListener('click', function(event) {
      event.preventDefault();
      event.stopPropagation();
      var button = event.target.closest('button[data-version]');
      if (!button) return;
      var key = button.getAttribute('data-version');
      controls.querySelectorAll('button').forEach(function(item) {
        item.setAttribute('aria-pressed', item === button ? 'true' : 'false');
      });
      variants.querySelectorAll('[data-text-version]').forEach(function(text) {
        text.hidden = text.getAttribute('data-text-version') !== key;
      });
    });
  });

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
  var IDX = null, indexPromise = null;
  var FAM = { npc: 'npc_bonds', battles: 'battles_unmounted' };
  function norm(s) { return (s || '').toLowerCase(); }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function score(e, q) {
    var h = norm(e.hay), t = norm(e.title + ' ' + e.code + ' ' + e.group),
        sp = norm(e.speakers.join(' '));
    var cover = 0;
    if (q.length >= 2) {
      var hit = 0, total = q.length - 1;
      for (var i = 0; i + 2 <= q.length; i++) if (h.indexOf(q.substr(i, 2)) >= 0) hit++;
      var ratio = hit / total;
      // 阈值 0.5：实测 10 字台词查询下，非真命页二元组覆盖率 ≤0.33、真命页 1.0
      if (ratio >= 0.5) cover = ratio * 10 + (h.indexOf(q) >= 0 ? 2 : 0);
    } else if (h.indexOf(q) >= 0) {
      cover = 1;
    }
    // 分层：标题/组名命中=页面主题（角色个人剧情的组名就是角色名，人名查询时应置顶）
    //       > 说话人命中=角色在场 > 仅全文提及；档内用覆盖率微调
    if (t.indexOf(q) >= 0) return 100 + cover;
    if (sp.indexOf(q) >= 0) return 50 + cover;
    return cover;
  }
  function wrapMatches(text, q, tag, cls) {
    var lower = text.toLowerCase(), lq = q.toLowerCase(), out = '', pos = 0, at;
    while ((at = lower.indexOf(lq, pos)) >= 0) {
      out += escapeHtml(text.slice(pos, at)) + '<' + tag + ' class="' + cls + '">'
           + escapeHtml(text.slice(at, at + lq.length)) + '</' + tag + '>';
      pos = at + lq.length;
    }
    return out + escapeHtml(text.slice(pos));
  }
  function snippet(hay, q) {
    var lh = hay.toLowerCase(), lq = q.toLowerCase();
    var at = lh.indexOf(lq);
    if (at < 0 && lq.length >= 2) {
      // 整句不在 hay（错字查询靠覆盖率命中）：退回首个命中的二元组位置
      for (var i = 0; i + 2 <= lq.length; i++) {
        var p = lh.indexOf(lq.substr(i, 2));
        if (p >= 0) { at = p; break; }
      }
    }
    if (at < 0) return '';
    var from = Math.max(0, at - 40), to = Math.min(hay.length, at + lq.length + 40);
    return (from > 0 ? '…' : '') + hay.slice(from, to) + (to < hay.length ? '…' : '');
  }
  function run(pane, scope, root, q) {
    var hits = [];
    for (var i = 0; i < IDX.length; i++) {
      var e = IDX[i];
      if (scope !== '_all' && (e.family !== (FAM[scope] || scope))) continue;
      var s = score(e, q);
      if (s > 0) hits.push([s, e]);
    }
    hits.sort(function (a, b) { return b[0] - a[0] || String(a[1].title).localeCompare(b[1].title); });
    pane.hidden = false;
    if (!hits.length) {
      pane.innerHTML = '<p class="aside" style="padding:10px 0;">未检索到匹配的剧情档案。</p>';
      return;
    }
    var out = ['<div class="results-header"><span>匹配到 ' + hits.length
      + ' 篇档案（含全文检索，最多显示 40 篇）</span></div><ul class="hits">'];
    hits.slice(0, 40).forEach(function (h) {
      var e = h[1];
      var displayTitle = (e.code && e.title && e.title.indexOf(e.code) === 0) ? e.title : [e.code, e.title].filter(Boolean).join(' ');
      var snip = snippet(e.hay, q);
      out.push('<li><a class="hit-link" href="' + root + e.page + '?q=' + encodeURIComponent(q) + '">'
        + '<div class="hit-top"><b class="hit-title">' + escapeHtml(displayTitle) + '</b>'
        + '<span class="hit-group">' + escapeHtml(e.group) + '</span></div>'
        + '<div class="hit-speakers">' + escapeHtml(e.speakers.slice(0, 5).join('、') || (e.family === 'anecdotes' ? '逸闻笔记' : '旁白')) + '</div>'
        + (snip ? '<div class="hit-snippet">' + wrapMatches(snip, q, 'em', 'hit-mark') + '</div>' : '')
        + '</a></li>');
    });
    pane.innerHTML = out.join('') + '</ul>';
  }

  // 动态注入而非 fetch：file:// 下 fetch 被 CORS 拦，classic script 不受限
  function loadIndex(root) {
    if (IDX) return Promise.resolve(IDX);
    if (indexPromise) return indexPromise;
    indexPromise = new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = root + 'data/search.js';
      s.onload = function () {
        IDX = (window.STORY_INDEX || { entries: [] }).entries;
        if (IDX.length) resolve(IDX); else reject(new Error('empty index'));
      };
      s.onerror = function () { indexPromise = null; reject(new Error('index load failed')); };
      document.head.appendChild(s);
    });
    return indexPromise;
  }

  // Multi-column Masonry for Group Grid (.grp-grid)
  function setupMasonry() {
    var grids = document.querySelectorAll('.grp-grid');
    grids.forEach(function(grid) {
      var rawItems = [].slice.call(grid.querySelectorAll(':scope > details.grp, :scope > .grp-col > details.grp'));
      if (!rawItems.length) return;

      var currentCols = 0;

      function relayout() {
        var w = grid.parentElement ? grid.parentElement.clientWidth : grid.clientWidth;
        var colsCount = w >= 980 ? 3 : (w >= 600 ? 2 : 1);
        if (colsCount === currentCols) return;
        currentCols = colsCount;

        grid.classList.add('has-masonry');
        grid.innerHTML = '';
        if (colsCount === 1) {
          grid.classList.add('masonry-1col');
          rawItems.forEach(function(it) { grid.appendChild(it); });
        } else {
          grid.classList.remove('masonry-1col');
          var colDivs = [];
          for (var i = 0; i < colsCount; i++) {
            var col = document.createElement('div');
            col.className = 'grp-col';
            grid.appendChild(col);
            colDivs.push(col);
          }
          rawItems.forEach(function(it, idx) {
            colDivs[idx % colsCount].appendChild(it);
          });
        }
      }

      relayout();
      window.addEventListener('resize', function() {
        clearTimeout(grid._rzt);
        grid._rzt = setTimeout(relayout, 60);
      });
    });
  }
  setupMasonry();

  [].slice.call(document.querySelectorAll('.searchbox input')).forEach(function(box) {
    var pane = box.closest('.searchbox').querySelector('.results');
    var scope = box.getAttribute('data-scope'), root = box.getAttribute('data-root') || '';
    var groups = [].slice.call(document.querySelectorAll('.grp, .chaplist li, .bento-item, .tiles li'));
    var armed = false;
    // 加载态做在搜索框内联（spinner + 小字 + 置灰），不弹结果面板
    var hint = document.createElement('span');
    hint.className = 'index-hint';
    hint.hidden = true;
    box.closest('.search-input-wrap').appendChild(hint);
    function state(cls, text) {
      var sb = box.closest('.searchbox');
      sb.classList.remove('index-loading', 'index-error');
      if (cls) sb.classList.add(cls);
      hint.textContent = text || '';
      hint.hidden = !cls;
    }
    function kick() {
      if (IDX) {
        state(null);
        var v = box.value.trim().toLowerCase();
        if (v.length >= 1) run(pane, scope, root, v); else pane.hidden = true;
        return;
      }
      state('index-loading', '索引加载中…');
      armed = true;
      loadIndex(root).then(function() {
        armed = false;
        kick();
      }).catch(function() {
        armed = false;
        state('index-error', '索引加载失败，点击重试');
      });
    }
    function ensure() { if (!armed) kick(); }
    box.addEventListener('pointerdown', ensure);
    box.addEventListener('focus', ensure);
    box.addEventListener('input', function() {
      var q = box.value.trim().toLowerCase();
      groups.forEach(function(g) {
        var match = !q || g.textContent.toLowerCase().indexOf(q) >= 0;
        g.style.display = match ? '' : 'none';
      });
      if (IDX) {
        if (q.length >= 1) run(pane, scope, root, q); else pane.hidden = true;
      } else ensure();
    });
  });

  // Expand / Collapse all groups
  var expBtn = document.getElementById('expandAllBtn');
  var colBtn = document.getElementById('collapseAllBtn');
  if (expBtn && colBtn) {
    expBtn.addEventListener('click', function() {
      document.querySelectorAll('.grp-grid details.grp').forEach(function(d) { d.open = true; });
    });
    colBtn.addEventListener('click', function() {
      document.querySelectorAll('.grp-grid details.grp').forEach(function(d) { d.open = false; });
    });
  }

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
    var link = e.target.closest('.opt-link, .branch-nav-btn, .anecdote-tab');
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

  // ?q= 落地高亮：从检索结果跳进正文时标出匹配位置并滚动到首处
  (function() {
    var q = new URLSearchParams(location.search).get('q');
    if (!q || q.length < 2) return;
    var lq = q.toLowerCase(), root = document.querySelector('main') || document.body;
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function(node) {
        if (!node.parentElement || node.parentElement.closest('script, style')) return NodeFilter.FILTER_REJECT;
        return node.nodeValue.toLowerCase().indexOf(lq) >= 0 ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    var nodes = [];
    while (walker.nextNode() && nodes.length < 200) nodes.push(walker.currentNode);
    nodes.forEach(function(node) {
      var text = node.nodeValue, lower = text.toLowerCase();
      var frag = document.createDocumentFragment(), pos = 0, at;
      while ((at = lower.indexOf(lq, pos)) >= 0) {
        frag.appendChild(document.createTextNode(text.slice(pos, at)));
        var mark = document.createElement('mark');
        mark.className = 'q-hit';
        mark.textContent = text.slice(at, at + lq.length);
        frag.appendChild(mark);
        pos = at + lq.length;
      }
      frag.appendChild(document.createTextNode(text.slice(pos)));
      node.parentNode.replaceChild(frag, node);
    });
    var first = document.querySelector('mark.q-hit');
    if (first) first.scrollIntoView({ behavior: 'smooth', block: 'center' });
  })();

  // 时间线滚轮（主线索引页）：wheel picker。
  // 唯一状态源是"滚轮里居中的那一项"——点击只负责把该项滚到居中
  // （scrollIntoView），由滚动触发 Observer 切面板，避免"点击改状态"和
  // "滚动改状态"两条路径互相打架。无 IntersectionObserver 时退回点击直改。
  (function() {
    var wheel = document.getElementById('linewheel');
    if (!wheel) return;
    var items = [].slice.call(wheel.querySelectorAll('.linewheel-item'));
    var panes = [].slice.call(document.querySelectorAll('.linepane'));
    if (!items.length || !panes.length) return;

    function activate(key, pushHash) {
      items.forEach(function(item) {
        var on = item.getAttribute('data-line') === key;
        item.classList.toggle('is-active', on);
        // ARIA 选中态与视觉状态同步（读屏器播报用，零视觉影响）
        item.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      panes.forEach(function(pane) {
        pane.classList.toggle('is-active', pane.getAttribute('data-line') === key);
      });
      if (pushHash && history.replaceState) {
        history.replaceState(null, '', '#line-' + key);
      }
    }

    items.forEach(function(item) {
      item.addEventListener('click', function(e) {
        e.preventDefault();
        // 先落 hash（无 Observer 的浏览器也能分享/刷新），再驱动滚动。
        activate(item.getAttribute('data-line'), true);
        if (typeof item.scrollIntoView === 'function') {
          item.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      });
    });

    if (typeof IntersectionObserver === 'function') {
      var observer = new IntersectionObserver(function(entries) {
        // 只认真正穿过居中观测线的那一项；阈值 0.6 防止边缘项误触发。
        var hit = entries.filter(function(en) {
          return en.isIntersecting && en.intersectionRatio >= 0.6;
        });
        if (!hit.length) return;
        hit.sort(function(a, b) { return b.intersectionRatio - a.intersectionRatio; });
        var key = hit[0].target.getAttribute('data-line');
        if (key) activate(key, true);
      }, { root: wheel, threshold: [0.6], rootMargin: '0px' });
      items.forEach(function(item) { observer.observe(item); });
    }

    // 落地状态：URL hash 指定哪条线就把那一项滚到居中（瞬时，不触发平滑动画）。
    var wanted = (location.hash || '').replace('#line-', '');
    if (wanted) {
      var target = items.filter(function(i) { return i.getAttribute('data-line') === wanted; })[0];
      if (target && typeof target.scrollIntoView === 'function') {
        target.scrollIntoView({ block: 'center' });
        activate(wanted, false);
      }
    }
  })();
})();
"""
