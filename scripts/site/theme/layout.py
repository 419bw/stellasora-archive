# -*- coding: utf-8 -*-
"""页面骨架与通用 helper（Phase D1 从 site_templates.py 拆出，函数体逐字不动）。"""
from html import escape

from registry import FAMILIES, FAMILY_NAME, STATE_LABEL, slug_of


esc = escape


def depth_of(page):
    return page.count('/')


def rel(root_depth, target):
    """Relative href from a page living at `root_depth` to `target`."""
    return ('../' * root_depth) + target if target else '#'


def full_title(code, title):
    """Combine code and title without duplicating prefix (e.g. avoid '第一话 第一话 孤独的店员')."""
    code = (code or '').strip()
    title = (title or '').strip()
    if not code:
        return title
    if title.startswith(code):
        return title
    return '%s %s' % (code, title)


def clean_subtitle(code, title):
    """Strip code from title if already prefixed, so <b>code</b> title doesn't stutter."""
    code = (code or '').strip()
    title = (title or '').strip()
    if code and title.startswith(code):
        return title[len(code):].strip()
    return title


def node_state_label(n):
    if n.get('kind') == 'battle' and not n.get('stems', {}).get('story') and not n.get('stems', {}).get('bubble') and n.get('state') == 'released':
        return '战斗档案'
    if n['state'] == 'unreleased':
        return '无对白剧本' if n['kind'] == 'battle' else '未开放'
    if n['kind'] == 'battle':
        return '战斗'
    if n['memory'] == 1:
        return '追忆'
    if n['memory'] == 2:
        return '真·终局'
    if n['is_last']:
        return '本章终幕'
    if n.get('code') == '终局':
        return '终局'
    if n.get('is_branch'):
        return '分支'
    if n['code'].startswith('幕间'):
        return '幕间'
    if n['code'].startswith('尾声'):
        return '尾声'
    return STATE_LABEL[n['kind']]


def node_state_class(n):
    if n['state'] == 'unreleased':
        return 'locked'
    if n['kind'] == 'battle':
        return 'battle'
    if n['memory']:
        return 'memory'
    if n.get('code') == '终局' or n['is_last']:
        return 'final'
    if n['code'].startswith(('幕间', '尾声')):
        return 'between'
    return 'story'


def layout(title, body, depth, crumb, note=''):
    root = '../' * depth
    nav_links = ''.join('<a href="%s%s/index.html">%s</a>' % (root, slug_of(f), n)
                        for f, n, _ in FAMILIES)
    return """<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s · 星塔旅人 剧情档案</title>
<link rel="icon" href="%sassets/icon_story.png" type="image/png">
<link rel="stylesheet" href="%sassets/tokens.css">
<script>
(function(){
  var t=localStorage.getItem('stellasora-theme')||(window.matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light');
  document.documentElement.setAttribute('data-theme',t);
  // 标记 JS 可用：时间线滚轮等"切换只做显隐"的组件靠这个类在首屏前收起
  // 未激活面板，避免 JS 初始化前两个列表同时闪现再坍缩。无 JS 时两个面板
  // 都保持可见（内容不依赖 JS）。
  document.documentElement.classList.add('js-enabled');
})();
</script>
</head><body>
<header class="top">
  <div class="top-inner">
    <a class="brand" href="%sindex.html">
      <img class="brand-icon" src="%sassets/icon_story.png" alt="" width="22" height="28">
      <span class="brand-text"><span class="brand-prefix">星塔旅人 </span><span class="brand-sub">剧情档案</span></span>
    </a>
    <nav class="nav">%s</nav>
    <div class="top-actions">
      <button class="theme-toggle" id="themeToggle" type="button" title="切换深色/浅色模式" aria-label="切换主题">
        <svg class="sun-icon" viewBox="0 0 24 24" width="15" height="15" stroke="currentColor" stroke-width="2" fill="none"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>
        <svg class="moon-icon" viewBox="0 0 24 24" width="15" height="15" stroke="currentColor" stroke-width="2" fill="none"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
      </button>
    </div>
  </div>
</header>
<main class="wrap">
%s%s
</main>
<footer class="foot">
  <div class="foot-inner">
    <div class="foot-brand"><img class="foot-icon" src="%sassets/icon_story.png" alt="" width="16" height="20"> 星塔旅人 剧情档案</div>
    <div class="foot-meta"><span class="foot-group">交流 QQ 群：1033744346</span> · <span class="foot-group">相关站点：<a href="https://www.gamekee.com/stellasora/" target="_blank" rel="noopener noreferrer">星塔旅人 Wiki（Gamekee）</a> · <a href="https://stellasora.miraheze.org/wiki/Stella_Sora_Wiki" target="_blank" rel="noopener noreferrer">Stella Sora Wiki（英文）</a></span>%s</div>
  </div>
  <div class="foot-disclaimer">
    <p>本站为玩家自制的非官方资料整理工具，与游戏官方运营团队无任何关联。YOSTAR GAMES（悠星网络）拥有游戏的原始资产，站内涉及的游戏文案、剧本、立绘、头像、图标等版权均归原发行商及原版权方所有。本站仅供剧情研读、世界观考据与个人交流学习使用，100%% 为非盈利性粉丝项目，不以任何形式盈利，不提供素材下载与游戏客户端修改。如因使用相关内容产生任何争议或损失，本站概不负责。若官方团队或版权所有方认为本站收录内容有所不妥，请联系 1950537289@qq.com，我们会第一时间删除或配合调整。交流反馈 QQ 群：1033744346。</p>
  </div>
</footer>
<button class="back-to-top" id="backToTop" type="button" title="回到顶部" aria-label="回到顶部">
  <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2.2" fill="none"><polyline points="18 15 12 9 6 15"></polyline></svg>
</button>
<script src="%sassets/site.js"></script>
</body></html>
""" % (esc(title), root, root,
       root, root, nav_links,
       ('<nav class="crumb">%s</nav>\n' % crumb) if crumb else '', body,
       root, ((' · ' + esc(note)) if note else ''),
       root)
