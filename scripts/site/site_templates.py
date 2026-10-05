# -*- coding: utf-8 -*-
"""HTML templates and page generators for StellaSora story knowledge base."""
import json
import collections
from html import escape
import render_html

FAMILIES = [
    ('main', '主线剧情', '全线剧情拓扑、分支抉择与终局推演。'),
    ('events', '活动剧情', '各期主题活动的关卡剧情全文与阶段收录。'),
    ('characters', '角色个人剧情', '旅人专属故事，好感等级逐级解锁。'),
    ('npc_bonds', '星塔 NPC 好感', '星塔驻留人员与常驻 NPC 羁绊剧情。'),
    ('discs', '秘闻', '收录秘闻剧本，附官方原版散文。'),
    ('storysets', '故事集支线', '主题故事集与日常侧写，收录支线剧情与回忆。'),
    ('prologue', '序章', '旅程开启的序幕篇章《最初的起点》。'),
    ('battles_unmounted', '存目战斗气泡', '战场独立战斗气泡与实时对白。'),
]
FAMILY_NAME = {k: n for k, n, _ in FAMILIES}

FAMILY_META = {
    'main': {
        'code': '01',
        'span': 'span-2',
        'desc': '全线剧情拓扑、分支抉择与终局推演，涵盖主线各章节及特别篇完整图景。',
    },
    'characters': {
        'code': '02',
        'span': 'span-2',
        'desc': '旅人专属故事，好感等级逐级解锁，深入角色内心世界与往事。',
    },
    'events': {
        'code': '03',
        'span': 'span-1',
        'desc': '各期主题活动的关卡剧情全文与阶段收录。',
    },
    'discs': {
        'code': '04',
        'span': 'span-1',
        'desc': '收录秘闻剧本，附官方原版散文。',
    },
    'storysets': {
        'code': '05',
        'span': 'span-1',
        'desc': '主题故事集与日常侧写，收录支线剧情与多重视角回忆。',
    },
    'npc_bonds': {
        'code': '06',
        'span': 'span-1',
        'desc': '星塔驻留人员与常驻 NPC 的日常羁绊交流剧情。',
    },
    'prologue': {
        'code': '07',
        'span': 'span-2',
        'desc': '旅程开启的序幕篇章《最初的起点》，旅人初次相遇的故事。',
    },
    'battles_unmounted': {
        'code': '08',
        'span': 'span-2',
        'desc': '战场独立战斗气泡与角色实时对白。',
    },
}

STATE_LABEL = {'battle': '战斗', 'story': '剧情'}


def slug_of(family):
    return {'main': 'main', 'events': 'events', 'characters': 'characters',
            'npc_bonds': 'npc', 'discs': 'discs', 'storysets': 'storysets',
            'prologue': 'prologue', 'battles_unmounted': 'battles'}[family]


def esc(s):
    return escape(str(s if s is not None else ''))


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



def _gate_mod():
    """release_gate lives in scripts/story; build_site puts it on sys.path."""
    import release_gate
    return release_gate


def locked_mask():
    return _gate_mod().MASK


def locked_block(item):
    """Locked placeholder for a group whose official open time is still ahead.

    Mirrors StorySetChapterItemCtrl: the chapter code / official preview banner
    stay visible, the name is replaced by the client's own ``敬请期待`` mask, the
    open time is shown, and nothing is clickable. Deliberately no group name, no
    section titles and no counts -- the placeholder must not hint at content.
    """
    gate = _gate_mod()
    open_text = item.get('open_text') or gate.fmt_open(item.get('open_time'))
    no = item.get('no') or ''
    preview = item.get('preview') or ''
    note = ('该篇章尚未在游戏内开放，预计 %s 开放' % esc(open_text)) if open_text \
        else '该篇章尚未在游戏内开放，开放时间待官方公布'
    body = ['<p class="locked-note">%s。暂不收录剧情内容，开放后自动补入。</p>' % note]
    if preview:
        body.append('<p class="locked-preview">官方预告：%s</p>' % esc(preview))
    return ('<details class="grp locked">'
            '<summary class="grp-header"><div class="grp-head-row">'
            '<h3 class="grp-title"><span class="locked-mask">%s</span>%s</h3>'
            '<div class="grp-meta-wrap"><span class="grp-count locked-tag">未开放</span>'
            '<svg class="grp-arrow" viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2.5" fill="none"><polyline points="6 9 12 15 18 9"></polyline></svg>'
            '</div></div></summary>'
            '<div class="grp-body">%s</div>'
            '</details>'
            % (esc(locked_mask()),
               ('<span class="locked-no">%s</span>' % esc(no)) if no else '',
               ''.join(body)))


def locked_notice_page(item, page):
    """Standalone "not open yet" page for a URL a locked group would occupy."""
    family = item.get('family', 'main')
    d = depth_of(page)
    root = '../' * d
    open_text = item.get('open_text') or _gate_mod().fmt_open(item.get('open_time'))
    rows = ['<div class="locked-notice-row"><span class="locked-key">状态</span>'
            '<span>未开放</span></div>',
            '<div class="locked-notice-row"><span class="locked-key">预计开放</span>'
            '<span>%s</span></div>' % (esc(open_text) if open_text else '待官方公布')]
    if item.get('preview'):
        rows.append('<div class="locked-notice-row"><span class="locked-key">官方预告</span>'
                    '<span>%s</span></div>' % esc(item['preview']))
    crumb = ('<a href="%sindex.html">首页</a> › <a href="%s%s/index.html">%s</a> › 未开放'
             % (root, root, slug_of(family), esc(FAMILY_NAME.get(family, '剧情档案'))))
    return layout('尚未开放', """
<h1>尚未开放</h1>
<p class="lede">该篇章尚未在游戏内开放，本站暂不收录其剧情内容。</p>
<div class="locked-notice">%s</div>
<p class="aside">官方开放后，本页会自动更新为完整剧情档案。</p>
""" % ''.join(rows), d, crumb)


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
    <div class="foot-meta"><span class="foot-group">交流 QQ 群：1033744346</span>%s</div>
  </div>
  <div class="foot-disclaimer">
    <p>本站为玩家自制的非官方资料整理工具，与游戏官方运营团队无任何关联。YOSTAR GAMES（悠星网络）拥有游戏的原始资产，站内涉及的游戏文案、剧本、立绘、头像、图标等版权均归原发行商及原版权方所有。本站仅供剧情研读、世界观考据与个人交流学习使用，100%% 为非盈利性粉丝项目，不以任何形式盈利，不提供素材下载与游戏客户端修改。如因使用相关内容产生任何争议或损失，本站概不负责。若官方团队或版权所有方认为本站收录内容有所不妥，请联系 1950537289@qq.com，我们会第一时间删除或配合调整。交流反馈 QQ 群：1033744346。</p>
  </div>
</footer>
<button class="back-to-top" id="backToTop" type="button" title="回到顶部" aria-label="回到顶部">
  <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2.2" fill="none"><polyline points="18 15 12 9 6 15"></polyline></svg>
</button>
<script src="%sdata/search.js"></script>
<script src="%sassets/site.js"></script>
</body></html>
""" % (esc(title), root, root,
       root, root, nav_links,
       ('<nav class="crumb">%s</nav>\n' % crumb) if crumb else '', body,
       root, ((' · ' + esc(note)) if note else ''),
       root, root)


def script_page(rec, doc, nav_info=None, branch_targets=None):
    body, _ = render_html.render_body(doc, branch_targets=branch_targets)
    g = rec['group']
    up = g.get('label') or ''
    page = rec['page']
    d = depth_of(page)
    root = '../' * d
    
    crumb_title = full_title(rec.get('code'), rec.get('title'))
    if rec['family'] == 'main':
        crumb = '<a href="%sindex.html">首页</a> › <a href="%smain/index.html">主线剧情</a> › <a href="index.html">%s</a> › %s' % (
            root, root, esc(up or '章节地图'), esc(crumb_title))
    elif rec['family'] == 'events' and str(g.get('id')) in ('10106', '20101'):
        crumb = '<a href="%sindex.html">首页</a> › <a href="%sevents/index.html">活动剧情</a> › <a href="index.html">%s 关卡拓扑</a> › %s' % (
            root, root, esc(up or '活动拓扑'), esc(crumb_title))
    else:
        crumb = '<a href="%sindex.html">首页</a> › <a href="%s%s/index.html">%s</a> › %s' % (
            root, root, slug_of(rec['family']), esc(FAMILY_NAME[rec['family']]), esc(crumb_title))
            
    facets = ' '.join('<a class="facet" href="%s%s/index.html?q=%s">%s</a>'
                      % (root, slug_of(rec['family']), esc(s), esc(s))
                      for s in rec['speakers'][:14])
                      
    extra = []
    if rec['family'] == 'characters':
        extra.append('好感等级 %s 解锁' % rec.get('affinity'))
    if rec.get('twins'):
        extra.append('同剧本档案：' + '、'.join(t for t in rec['twins'] if t))
    if rec.get('prose_lines'):
        extra.append('附官方散文 %d 行' % rec['prose_lines'])
    if rec.get('mount_note'):
        extra.append(rec['mount_note'])
    aside = ('<p class="aside meta-note">%s</p>' % esc('　·　'.join(x for x in extra if x))
             if extra else '')

    # Story Flow Navigation (Prev / Next / Branches)
    story_nav_html = ''
    if nav_info:
        prev_items = nav_info.get('prev', [])
        next_items = nav_info.get('next', [])
        if prev_items or next_items:
            prev_html = ''
            if prev_items:
                links = ''.join('<a class="nav-link" href="%s"><b>%s</b> %s</a>'
                                % (esc(it['url']), esc(it['code']), esc(clean_subtitle(it['code'], it['title'])))
                                for it in prev_items)
                prev_html = '<div class="story-nav-prev"><span class="nav-label">← 上一节 / 前置</span>%s</div>' % links
            else:
                prev_html = '<div class="story-nav-prev"><span class="nav-label">起点</span><span class="nav-link">当前篇章起始节</span></div>'

            next_html = ''
            if len(next_items) == 1:
                it = next_items[0]
                next_html = ('<div class="story-nav-next"><span class="nav-label">下一节 →</span>'
                             '<a class="nav-link" href="%s"><b>%s</b> %s</a></div>'
                             % (esc(it['url']), esc(it['code']), esc(clean_subtitle(it['code'], it['title']))))
            elif len(next_items) > 1:
                links = ''.join('<a class="nav-link" href="%s"><span class="branch-tag %s">%s</span><b>%s</b> %s</a>'
                                % (esc(it['url']), esc(it.get('cls', 'story')), esc(it.get('tag', '分支')),
                                   esc(it['code']), esc(clean_subtitle(it['code'], it['title'])))
                                for it in next_items)
                next_html = ('<div class="story-nav-branches"><span class="nav-label">后续分支路线选择 →</span>'
                             '<div class="branch-links">%s</div></div>' % links)
            else:
                next_html = '<div class="story-nav-next"><span class="nav-label">终点</span><span class="nav-link">当前路线终结</span></div>'

            story_nav_html = '<nav class="story-nav" aria-label="剧情前后导航">%s%s</nav>' % (prev_html, next_html)

    return layout(rec['title'] or page, """
%s
<div class="page" data-family="%s" data-counts='%s'>
%s
</div>
%s
<details class="cast"><summary>出场说话人（%d）</summary><div class="facets">%s</div></details>
""" % (aside, esc(rec['family']),
       json.dumps(rec['counts'], ensure_ascii=False), body,
       story_nav_html,
       len(rec['speakers']), facets), d, crumb)


def chapter_graph_page(c, all_chapters):
    """The in-game style node map: positioned cards over one flat SVG connector layer."""
    page = 'main/ch%s/index.html' % (c['no'] or 'sp')
    d = depth_of(page)
    root = '../' * d
    g = c['geometry']
    crumb = '<a href="%sindex.html">首页</a> › <a href="%smain/index.html">主线剧情</a> › %s' % (
        root, root, esc(c['name'] or '特别篇'))
    by_sid = {n['story_id']: n for n in c['nodes']}
    pad = 24
    
    switch = ' '.join('<a href="%smain/ch%s/index.html"%s>%s</a>' % (
        root, x['no'] or 'sp', ' class="on"' if x['id'] == c['id'] else '',
        esc(x['name'] or '特别篇')) for x in sorted(all_chapters, key=lambda y: y['id']))

    if g is None:                       # 特别篇
        items = []
        for n in sorted(c['nodes'], key=lambda x: x['sid']):
            t = n.get('time')
            chip = '<span class="chip">%s</span>' % esc('%s %s' % (t['date'], t['clock'])) if t else ''
            state_lbl = node_state_label(n)
            state_span = '<span class="s">%s</span>' % esc(state_lbl)
            if n['page']:
                items.append('<li><a href="%s"><span class="code">%s</span><span class="t">%s</span>%s%s</a></li>'
                             % (rel(d, n['page']), esc(n['code']), esc(n['title']), chip, state_span))
            else:
                items.append('<li><span class="code">%s</span><span class="t">%s</span>%s%s</li>'
                             % (esc(n['code']), esc(n['title']), chip, state_span))
        items_html = ''.join(items)
        unreleased = sum(1 for n in c['nodes'] if n['state'] == 'unreleased')
        lede = '%s　节点 %d　已开放 %d　战斗 %d%s' % (
            esc(c['year']), len(c['nodes']),
            sum(1 for n in c['nodes'] if n['state'] == 'released'),
            sum(1 for n in c['nodes'] if n['kind'] == 'battle'),
            '　未开放 %d' % unreleased if unreleased else '')
        body = ('<h1>%s《%s》</h1>'
                '<p class="lede">%s</p>'
                '<nav class="chapsel">%s</nav>'
                '<p class="aside">特别篇各关卡按剧情推进顺序排列展示。</p>'
                '<ul class="plain linelist">%s</ul>'
                % (esc(c['name'] or '特别篇'), esc(c['title']), lede, switch, items_html))
        return layout(c['name'] or '特别篇', body, d, crumb)

    paths = []
    for u, v in g['edges']:
        a, b = by_sid[u], by_sid[v]
        x1 = a['x'] + pad + g['card'][0]
        y1 = a['y'] + pad + g['card'][1] / 2.0
        x2 = b['x'] + pad
        y2 = b['y'] + pad + g['card'][1] / 2.0
        mx = x1 + (x2 - x1) / 2.0
        cls = node_state_class(b)
        dash = ' dash' if b['state'] == 'unreleased' else ''
        paths.append('<path class="edge %s%s" d="M%d %d C%d %d,%d %d,%d %d"/>'
                     % (cls, dash, x1, y1, mx, y1, mx, y2, x2, y2))
                     
    cards = []
    seen_col = set()
    for n in sorted(c['nodes'], key=lambda x: (x['col'], x['lane'])):
        style = 'left:%dpx;top:%dpx;width:%dpx;height:%dpx' % (
            n['x'] + pad, n['y'] + pad, g['card'][0], g['card'][1])
        t = n['time']
        chip = '<span class="chip">%s</span>' % esc('%s %s' % (t['date'], t['clock'])) if t else ''
        inner = ('<span class="code">%s</span><span class="t">%s</span>%s'
                 % (esc(n['code'] or '·'), esc(n['title']), chip))
        cid = '' if n['col'] in seen_col else ' id="col%d"' % n['col']
        seen_col.add(n['col'])
        if n['page']:
            cards.append('<a%s class="node %s" style="%s" data-col="%d" href="%s">%s'
                         '<span class="state">%s ›</span></a>'
                         % (cid, node_state_class(n), style, n['col'], rel(d, n['page']), inner,
                            esc(node_state_label(n))))
        else:
            cards.append('<div%s class="node %s" style="%s" data-col="%d">%s'
                         '<span class="state">%s</span></div>'
                         % (cid, node_state_class(n), style, n['col'], inner,
                            esc(node_state_label(n))))
                            
    anchors = ''.join('<a href="#col%d" data-scroll-to="%d">%s</a>'
                      % (col, col * g['step_x'] + pad,
                         esc(min((n['code'] or '·') for n in c['nodes'] if n['col'] == col)))
                      for col in range(g['columns']))
                      
    switch = ' '.join('<a href="%smain/ch%s/index.html"%s>%s</a>' % (
        root, x['no'] or 'sp', ' class="on"' if x['id'] == c['id'] else '',
        esc(x['name'] or '特别篇')) for x in sorted(all_chapters, key=lambda y: y['id']))
        
    unreleased = sum(1 for n in c['nodes'] if n['state'] == 'unreleased')
    return layout('%s《%s》' % (c['name'], c['title']), """
<h1>%s《%s》</h1>
<p class="lede">%s　节点 %d　已开放 %d　战斗 %d%s</p>
<nav class="chapsel" data-family="main">%s</nav>
<div class="anchors-wrap"><nav class="anchors" data-family="main">%s</nav></div>
<div class="map" data-family="main">
<div class="canvas" style="width:%dpx;height:%dpx">
<svg class="wires" width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>
%s
</div>
</div>
<p class="aside map-note">支持拖拽平移与滚轮缩放，点击节点可查阅剧本全文；「未开放」表示该分支路线暂未开放；「无对白剧本」表示该关卡为纯战斗关卡，无剧情对白。</p>
""" % (esc(c['name']), esc(c['title']), esc(c['year']), len(c['nodes']),
       sum(1 for n in c['nodes'] if n['state'] == 'released'),
       sum(1 for n in c['nodes'] if n['kind'] == 'battle'),
       '　未开放 %d' % unreleased if unreleased else '',
       switch, anchors,
       g['width'] + pad * 2, g['height'] + pad * 2,
       g['width'] + pad * 2, g['height'] + pad * 2,
       g['width'] + pad * 2, g['height'] + pad * 2, ''.join(paths), ''.join(cards)),
        d, crumb)


def main_index(chapters, locked_items=()):
    d = depth_of('main/index.html')
    cards = []
    crumb = '<a href="../index.html">首页</a> › 主线剧情'
    for c in sorted(chapters, key=lambda x: x['id']):
        cno = c['no'] or 'sp'
        unrel = sum(1 for n in c['nodes'] if n['state'] == 'unreleased')
        bt = sum(1 for n in c['nodes'] if n['kind'] == 'battle')
        cards.append("""<li><a class="chapcard" href="../main/ch%s/index.html">
  <div class="chap-top">
    <span class="chapno">%s</span>
    <span class="chapyear">%s</span>
  </div>
  <div class="chaptitle">%s</div>
  <div class="chapinfo">%d 节点 · 已开放 %d · 战斗 %d%s</div>
  <span class="chapline"></span>
  <div class="chap-arrow">→</div>
</a></li>""" % (
            cno, esc(c['name'] or '特别篇'), esc(c['year']),
            esc(c['title']), len(c['nodes']),
            sum(1 for n in c['nodes'] if n['state'] == 'released'),
            bt, (' · 待开放 %d' % unrel) if unrel else ''
        ))
    for item in locked_items:
        open_text = item.get('open_text') or _gate_mod().fmt_open(item.get('open_time'))
        preview = item.get('preview') or ''
        info = ('预计 %s 开放' % esc(open_text)) if open_text else '开放时间待官方公布'
        if preview:
            info += '<br>官方预告：%s' % esc(preview)
        cards.append("""<li><div class="chapcard locked">
  <div class="chap-top">
    <span class="chapno">%s</span>
    <span class="chapyear locked-tag">未开放</span>
  </div>
  <div class="chaptitle">%s</div>
  <div class="chapinfo">%s</div>
  <span class="chapline"></span>
</div></li>""" % (esc(item.get('no') or ''), esc(locked_mask()), info))
    return layout('主线剧情', """
<h1>主线剧情</h1>
<p class="lede">主线全章节关卡拓扑与剧情档案，支持点击卡片查阅剧情对话与战斗对白。</p>
<ul class="chaplist">%s</ul>
""" % ''.join(cards), d, crumb)


def battle_archive_page(stage, nav_info=None):
    """Render an independent archive page for a battle-only stage."""
    code = stage.get('code') or ''
    title = stage.get('title') or ''
    page_title = ('%s %s' % (code, title)).strip() if code else title
    page = stage['page']
    d = depth_of(page)
    root = '../' * d
    
    family = stage.get('family', 'main')
    chapter_name = stage.get('chapter_name') or stage.get('group', {}).get('label') or '活动剧情'
    gid = str(stage.get('group', {}).get('id', ''))
    
    if family == 'main':
        cname = stage.get('chapter_name') or '特别篇'
        ctitle = stage.get('chapter_title') or '谜影的序曲'
        c_label = ('%s《%s》' % (cname, ctitle)) if ctitle else cname
        crumb = ('<a href="%sindex.html">首页</a> › <a href="%smain/index.html">主线剧情</a> › '
                 '<a href="index.html">%s</a> › %s'
                 % (root, root, esc(cname), esc(page_title)))
        lede_text = '主线%s · 独立战斗关卡档案' % esc(c_label)
        section_field = '篇章'
        section_val = '主线%s' % esc(c_label)
        notice_desc = '本关卡为纯战斗关卡，不包含剧情对话与战场气泡对白。'
    elif gid in ('10106', '20101'):
        crumb = ('<a href="%sindex.html">首页</a> › <a href="%sevents/index.html">活动剧情</a> › '
                 '<a href="index.html">%s 关卡拓扑</a> › %s'
                 % (root, root, esc(chapter_name), esc(page_title)))
        lede_text = '活动剧情《%s》· 独立战斗关卡档案' % esc(chapter_name)
        section_field = '活动'
        section_val = esc(chapter_name)
        notice_desc = '本关卡为活动纯战斗关卡，不包含剧情对话。'
    else:
        crumb = ('<a href="%sindex.html">首页</a> › <a href="%sevents/index.html">活动剧情</a> › '
                 '%s › %s'
                 % (root, root, esc(chapter_name), esc(page_title)))
        lede_text = '活动剧情《%s》· 独立战斗关卡档案' % esc(chapter_name)
        section_field = '活动'
        section_val = esc(chapter_name)
        notice_desc = '本关卡为活动纯战斗关卡，不包含剧情对话。'
        
    story_nav_html = ''
    if nav_info:
        prev_items = nav_info.get('prev', [])
        next_items = nav_info.get('next', [])
        prev_html = ''
        if prev_items:
            links = ''.join('<a class="nav-link" href="%s"><b>%s</b> %s</a>'
                            % (esc(it['url']), esc(it['code']), esc(clean_subtitle(it['code'], it['title'])))
                            for it in prev_items)
            prev_html = '<div class="story-nav-prev"><span class="nav-label">← 上一关卡 / 前置</span>%s</div>' % links
        else:
            prev_html = '<div class="story-nav-prev"><span class="nav-label">起点</span><span class="nav-link">当前篇章起始关卡</span></div>'

        next_html = ''
        if len(next_items) == 1:
            it = next_items[0]
            next_html = ('<div class="story-nav-next"><span class="nav-label">下一关卡 →</span>'
                         '<a class="nav-link" href="%s"><b>%s</b> %s</a></div>'
                         % (esc(it['url']), esc(it['code']), esc(clean_subtitle(it['code'], it['title']))))
        elif len(next_items) > 1:
            links = ''.join('<a class="nav-link" href="%s"><span class="branch-tag %s">%s</span><b>%s</b> %s</a>'
                            % (esc(it['url']), esc(it.get('cls', 'battle')), esc(it.get('tag', '分支')),
                               esc(it['code']), esc(clean_subtitle(it['code'], it['title'])))
                            for it in next_items)
            next_html = ('<div class="story-nav-branches"><span class="nav-label">后续关卡路线 →</span>'
                         '<div class="branch-links">%s</div></div>' % links)
        else:
            next_html = '<div class="story-nav-next"><span class="nav-label">终点</span><span class="nav-link">当前路线终结</span></div>'

        story_nav_html = '<nav class="story-nav" aria-label="关卡前后导航">%s%s</nav>' % (prev_html, next_html)

    cond_display = stage.get('condition_text') or stage.get('condition') or '初始开放'
    body = """
<div class="page" data-family="%s">
  <h1>%s</h1>
  <p class="lede">%s</p>
  
  <h2 data-part="1">关卡信息</h2>
  <p class="meta"><b>%s</b>%s</p>
  <p class="meta"><b>关卡代号</b><code>%s</code></p>
  <p class="meta"><b>关卡 ID</b><code>%s</code></p>
  <p class="meta"><b>关卡类型</b>战斗关卡</p>
  <p class="meta"><b>解锁条件</b><code>%s</code></p>
  <p class="meta"><b>关卡状态</b>已收录独立档案</p>
  
  <h2 data-part="2">官方简介</h2>
  <blockquote>
    <p>%s</p>
  </blockquote>
  
  <h2 data-part="3">关卡说明</h2>
  <div style="margin: 16px 0; padding: 14px 18px; background: var(--card-bg-subtle); border-left: 3px solid var(--battle); border-radius: 0 var(--radius-md) var(--radius-md) 0;">
    <p style="margin: 0 0 6px 0; font-size: 13.5px; font-weight: 700; color: var(--text-main);">✦ 纯战斗关卡档案</p>
    <p style="margin: 0; font-size: 13.5px; line-height: 1.7; color: var(--text-muted);">
      %s
      此独立档案页收录关卡官方简介、解锁条件与前后流程导航。
    </p>
  </div>
</div>
%s
""" % (esc(family), esc(page_title), lede_text, section_field, section_val,
       esc(code), esc(stage.get('story_id') or stage.get('sid') or ''),
       esc(cond_display), esc(stage.get('desc') or '暂无简介'),
       esc(notice_desc), story_nav_html)
       
    return layout(page_title, body, d, crumb)


def activity_graph_page(act_info, all_branching_acts):
    """Render in-game style SVG DAG topology map for branching activity stories."""
    act_id = str(act_info['id'])
    act_name = act_info['name']
    act_title = act_info['title']
    nodes = act_info['nodes']
    g = act_info['geometry']
    page = 'events/%s/index.html' % act_id
    d = depth_of(page)
    root = '../' * d
    pad = 24
    
    crumb = ('<a href="%sindex.html">首页</a> › <a href="%sevents/index.html">活动剧情</a> › '
             '%s 拓扑连线图' % (root, root, esc(act_name)))
             
    switch = ' '.join(
        '<a href="%sevents/%s/index.html"%s>%s</a>' % (
            root, a['id'], ' class="on"' if str(a['id']) == act_id else '',
            esc(a['name'])
        ) for a in all_branching_acts
    )
    switch = ('<a href="%sevents/index.html">← 全部活动</a> ' % root) + switch
    
    by_sid = {n['story_id']: n for n in nodes}
    paths = []
    for u, v in g['edges']:
        a, b = by_sid[u], by_sid[v]
        x1 = a['x'] + pad + g['card'][0]
        y1 = a['y'] + pad + g['card'][1] / 2.0
        x2 = b['x'] + pad
        y2 = b['y'] + pad + g['card'][1] / 2.0
        mx = x1 + (x2 - x1) / 2.0
        cls = node_state_class(b)
        paths.append('<path class="edge %s" d="M%d %d C%d %d,%d %d,%d %d"/>'
                     % (cls, x1, y1, mx, y1, mx, y2, x2, y2))
                     
    cards = []
    seen_col = set()
    for n in sorted(nodes, key=lambda x: (x['col'], x['lane'])):
        style = 'left:%dpx;top:%dpx;width:%dpx;height:%dpx' % (
            n['x'] + pad, n['y'] + pad, g['card'][0], g['card'][1])
        inner = ('<span class="code">%s</span><span class="t">%s</span>'
                 % (esc(n['code'] or '·'), esc(n['title'])))
        cid = '' if n['col'] in seen_col else ' id="col%d"' % n['col']
        seen_col.add(n['col'])
        cards.append('<a%s class="node %s" style="%s" data-col="%d" href="%s">%s'
                     '<span class="state">%s ›</span></a>'
                     % (cid, node_state_class(n), style, n['col'], rel(d, n['page']), inner,
                        esc(node_state_label(n))))

    anchors = ''.join('<a href="#col%d" data-scroll-to="%d">%s</a>'
                      % (col, col * g['step_x'] + pad,
                         esc(min((n['code'] or '·') for n in nodes if n['col'] == col)))
                      for col in range(g['columns']))

    body = """
<h1>%s《%s》</h1>
<p class="lede">活动关卡拓扑连线图　收录 %d 个剧情与战斗节点　含多分支抉择路线</p>
<nav class="chapsel" data-family="events">%s</nav>
<div class="anchors-wrap"><nav class="anchors" data-family="events">%s</nav></div>
<div class="map" data-family="events">
<div class="canvas" style="width:%dpx;height:%dpx">
<svg class="wires" width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>
%s
</div>
</div>
<p class="aside map-note">活动关卡拓扑分支图，支持鼠标拖拽平移与列锚点定位；点击卡片可查阅对应活动剧本。</p>
""" % (esc(act_name), esc(act_title), len(nodes), switch, anchors,
       g['width'] + pad * 2, g['height'] + pad * 2,
       g['width'] + pad * 2, g['height'] + pad * 2,
       g['width'] + pad * 2, g['height'] + pad * 2, ''.join(paths), ''.join(cards))

    return layout('%s 关卡拓扑' % act_name, body, d, crumb)


def family_index(family, intro, pages_in_family, locked_items=()):
    recs = sorted(pages_in_family, key=lambda r: (str(r['group'].get('id', '')), r['id']))
    page = '%s/index.html' % slug_of(family)
    d = depth_of(page)
    groups = collections.OrderedDict()
    for r in recs:
        key = (r['group'].get('label') or '未分组', r['group'].get('id'))
        groups.setdefault(key, []).append(r)
    blocks = []
    total_stages = 0
    for (label, gid), items in groups.items():
        total_stages += len(items)
        topo_badge = ''
        if family == 'events' and str(gid) in ('10106', '20101'):
            topo_badge = '<div class="grp-topo-wrap"><a class="grp-topo-btn" href="%s/index.html">✦ 查看本活动关卡拓扑图（含分支路线） →</a></div>' % gid
        links = []
        for it in items:
            is_battle = it.get('kind') == 'battle'
            sub = ('战斗关卡' if is_battle
                   else ('%d 句' % it['counts'].get('talk', 0)
                         + (' / %d 气泡' % it['counts']['bubble'] if it['counts'].get('bubble') else '')))
            display_title = full_title(it.get('code'), it.get('title'))
            links.append('<li><a class="plain-link" href="%s"><span class="link-title">%s</span><span class="sub">%s</span></a></li>'
                         % (rel(d, it['page']), esc(display_title), esc(sub)))
        count_label = '%d 关' if family == 'events' else '%d 篇'
        blocks.append('<details class="grp">'
                      '<summary class="grp-header">'
                      '<div class="grp-head-row">'
                      '<h3 class="grp-title">%s</h3>'
                      '<div class="grp-meta-wrap">'
                      '<span class="grp-count">%s</span>'
                      '<svg class="grp-arrow" viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2.5" fill="none"><polyline points="6 9 12 15 18 9"></polyline></svg>'
                      '</div>'
                      '</div>'
                      '</summary>'
                      '<div class="grp-body">%s<ul class="plain">%s</ul></div>'
                      '</details>'
                      % (esc(label), count_label % len(items), topo_badge, ''.join(links)))
    for item in locked_items:
        blocks.append(locked_block(item))

    crumb = '<a href="%sindex.html">首页</a> › %s' % ('../' * d, FAMILY_NAME[family])
    unit_name = '个活动' if family == 'events' else ('位角色' if family == 'characters' else '个分类')
    stage_unit = '关' if family == 'events' else '篇'
    toolbar = """<div class="grp-toolbar">
  <div class="grp-toolbar-info">收录 %d %s · 共 %d %s%s</div>
  <div class="grp-toolbar-actions">
    <button type="button" class="btn-grp-toggle" id="expandAllBtn">全部展开</button>
    <button type="button" class="btn-grp-toggle" id="collapseAllBtn">全部收起</button>
  </div>
</div>""" % (len(groups), unit_name, total_stages, stage_unit,
               (' · 待开放 %d 个' % len(locked_items)) if locked_items else '')

    return layout(FAMILY_NAME[family], """
<h1>%s</h1>
<p class="lede">%s</p>
<div class="searchbox"><div class="search-input-wrap">
  <svg class="search-icon" viewBox="0 0 24 24" width="15" height="15" stroke="currentColor" stroke-width="2" fill="none"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
  <input type="search" placeholder="检索标题、概要、说话人…" data-scope="%s" data-root="%s">
</div><div class="results" hidden></div></div>
%s
<div class="grp-grid" data-family="%s">%s</div>
""" % (FAMILY_NAME[family], esc(intro), slug_of(family), '../' * d, toolbar, slug_of(family), ''.join(blocks)),
        d, crumb)


def home_page(pages, personality_data):
    counts = collections.Counter(p['family'] for p in pages)
    lines = sum(p['counts'].get('talk', 0) + p['counts'].get('bubble', 0) for p in pages)
    
    bento_items = []
    ordered_families = sorted(FAMILIES, key=lambda x: FAMILY_META.get(x[0], {}).get('code', '99'))
    for f, n, _ in ordered_families:
        meta = FAMILY_META.get(f, {})
        cnt = counts.get(f, 0)
        slug = slug_of(f)
        bento_items.append("""<li class="bento-item %s">
<article class="bento-card" data-slug="%s">
  <a class="bento-card-link" href="%s/index.html" aria-label="%s"></a>
  <div class="bento-top">
    <span class="bento-num">%s</span>
  </div>
  <div class="bento-body">
    <h3 class="bento-title">%s</h3>
    <p class="bento-desc">%s</p>
  </div>
  <div class="bento-foot">
    <span class="bento-count">%d 篇</span>
    <span class="bento-arrow">→</span>
  </div>
</article></li>""" % (
            meta.get('span', ''), slug, slug, esc(n),
            meta.get('code', '00'),
            esc(n), meta.get('desc', ''), cnt
        ))

    return layout('首页', """
<div class="hero">
  <h1 class="hero-title">星塔旅人 剧情档案</h1>
  <p class="hero-desc">官方剧本全文、分支抉择与关卡拓扑。</p>
  <div class="hero-badge-wrap">
    <a class="hero-update-pill" href="#updates">
      <span class="pill-dot"></span>
      <span class="pill-date">2026-10-05</span>
      <span class="pill-sep">·</span>
      <span class="pill-text">上次更新：同步 1 项代码更新</span>
      <span class="pill-arrow">↓</span>
    </a>
  </div>
  
  <div class="hero-notice-banner">
    <div class="notice-pill notice-spoiler">
      <span class="notice-tag tag-spoiler">剧透提醒</span>
      <span class="notice-msg">本站默认完整展开所有主线及活动的分支抉择与结局走向，包含全流程剧透，请谨慎阅读。</span>
    </div>
    <div class="notice-pill notice-scope">
      <span class="notice-tag tag-scope">收录说明</span>
      <span class="notice-msg">游戏内仅有 CG 动画演示而无文本字幕的片段不会出现在这里，本站仅收录官方剧本中有台词文本的剧情。如需查看详细的剧情插画 CG、角色立绘与音频等资源，可参考英文 Wiki 站：<a href="https://stellasora.miraheze.org/wiki/Stella_Sora_Wiki" target="_blank" rel="noopener noreferrer">Stella Sora Wiki</a>。</span>
    </div>
  </div>
  
  <div class="searchbox hero-search">
    <div class="search-input-wrap">
      <svg class="search-icon" viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
      <input type="search" placeholder="检索剧情标题、概要、说话人、关卡代号…" data-scope="_all" data-root="">
    </div>
    <div class="results" hidden></div>
  </div>
</div>

<ul class="bento tiles">
  %s
</ul>

<section class="update-section" id="updates">
  <div class="update-card">
    <div class="update-header">
      <div class="update-title">
        <svg class="update-icon" viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
        <span>最近更新</span>
      </div>
      <div class="update-date-badge">
        <span class="dot"></span>
        <span>更新时间：2026-10-05</span>
      </div>
    </div>
    <div class="update-summary">同步 1 项代码更新</div>
  </div>
</section>
""" % ''.join(bento_items), 0, '')
