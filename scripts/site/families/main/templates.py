# -*- coding: utf-8 -*-
"""主线族站点模板：章图索引覆盖页（INDEX_OVERRIDE）、章节卡与章图页组装层。

Phase D1 纯搬运（main_index / _chapter_card 函数体逐字不动）；分发注册表
（build_site.py 的 (family, kind) 分发）在 D3 上线，INDEX_OVERRIDE 即钩子。
Phase D2 迁入 chapter_graph_page 组装层（拓扑骨架用 theme.graph.graph_map_page，
特别篇平铺分支留在此层）。
"""
from theme.layout import depth_of, esc, layout, node_state_label, rel
from theme.graph import graph_map_page
from theme.gate import _locked_card


def _line_sort_key(x):
    """时间线排序键：sort_index 升序（与游戏内左侧入口一致），缺 story_line 的章
    归到末尾，同键按章 Id。chapter_switch 与 main_index 共用，防两处排序规则漂移。"""
    info = x.get('story_line') or {}
    si = info.get('sort_index')
    return (si if isinstance(si, int) else 10 ** 6, x['id'])


def chapter_switch(c, all_chapters, root):
    """章图页内的章节切换条：按时间线分段，段首是该线的官方标题。

    链接一律用 ``c['slug']``（侧车字段），不再用 ``no or 'sp'`` 推导——两个
    特别篇曾因那条推导撞进同一个 ``chsp`` 目录、后写的覆盖先写的。

    每条时间线是一个 ``<details>``：当前章所在的那条默认展开，其余收起——
    在一条时间线里时，另一条线的章节跳转按钮不占地方，点它的标签即可展开。
    开合是 details 原生行为：无 JS 可用，也不需要 js-enabled 防闪烁。
    没有时间线归属的章（活动剧情等）不分组，直接平铺。
    """
    segs = []
    for x in sorted(all_chapters, key=_line_sort_key):
        info = x.get('story_line') or {}
        lid = info.get('id')
        if not segs or segs[-1]['id'] != lid:
            segs.append({'id': lid, 'label': info.get('title') or '',
                         'items': [], 'current': False})
        if x['id'] == c['id']:
            segs[-1]['current'] = True
        segs[-1]['items'].append(
            '<a href="%smain/%s/index.html"%s>%s</a>' % (
                root, x['slug'], ' class="on"' if x['id'] == c['id'] else '',
                esc(x['name'] or '特别篇')))

    parts = []
    for seg in segs:
        if not seg['label']:
            parts.extend(seg['items'])
            continue
        parts.append(
            '<details class="chapline-seg"%s>'
            '<summary class="chapline-label">%s</summary>%s</details>'
            % (' open' if seg['current'] else '',
               esc(seg['label']), ''.join(seg['items'])))
    return ' '.join(parts)


def chapter_graph_page(c, all_chapters):
    """The in-game style node map: positioned cards over one flat SVG connector layer."""
    page = 'main/%s/index.html' % c['slug']
    d = depth_of(page)
    root = '../' * d
    g = c['geometry']
    crumb = '<a href="%sindex.html">首页</a> › <a href="%smain/index.html">主线剧情</a> › %s' % (
        root, root, esc(c['name'] or '特别篇'))

    switch = chapter_switch(c, all_chapters, root)

    if c.get('special'):              # 特别篇：无拓扑图，按推进顺序平铺
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

    unreleased = sum(1 for n in c['nodes'] if n['state'] == 'unreleased')
    lede = '%s　节点 %d　已开放 %d　战斗 %d%s' % (
        esc(c['year']), len(c['nodes']),
        sum(1 for n in c['nodes'] if n['state'] == 'released'),
        sum(1 for n in c['nodes'] if n['kind'] == 'battle'),
        '　未开放 %d' % unreleased if unreleased else '')
    return graph_map_page(
        '%s《%s》' % (c['name'], c['title']), crumb, d, 'main',
        '%s《%s》' % (esc(c['name']), esc(c['title'])), lede, switch,
        '支持拖拽平移与滚轮缩放，点击节点可查阅剧本全文；「未开放」表示该分支路线暂未开放；'
        '「无对白剧本」表示该关卡为纯战斗关卡，无剧情对白。',
        c['nodes'], g)


def _chapter_card(c):
    unrel = sum(1 for n in c['nodes'] if n['state'] == 'unreleased')
    bt = sum(1 for n in c['nodes'] if n['kind'] == 'battle')
    return """<li><a class="chapcard" href="../main/%s/index.html">
  <div class="chap-top">
    <span class="chapno">%s</span>
    <span class="chapyear">%s</span>
  </div>
  <div class="chaptitle">%s</div>
  <div class="chapinfo">%d 节点 · 已开放 %d · 战斗 %d%s</div>
  <span class="chapline"></span>
  <div class="chap-arrow">→</div>
</a></li>""" % (
        c['slug'], esc(c['name'] or '特别篇'), esc(c['year']),
        esc(c['title']), len(c['nodes']),
        sum(1 for n in c['nodes'] if n['state'] == 'released'),
        bt, (' · 待开放 %d' % unrel) if unrel else '')


def main_index(chapters, locked_items=()):
    d = depth_of('main/index.html')
    crumb = '<a href="../index.html">首页</a> › 主线剧情'

    # 时间线分组：滚轮顺序见 _line_sort_key（sort_index 升序，与游戏内左侧入口
    # 一致，时间线 2 在上）。默认激活章节数最多的那条线（当前即时间线 1 主线）。
    groups = []
    for c in sorted(chapters, key=_line_sort_key):
        info = c.get('story_line') or {}
        key = info.get('id')
        if not groups or groups[-1]['id'] != key:
            groups.append({'id': key, 'info': info, 'cards': []})
        groups[-1]['cards'].append(_chapter_card(c))

    # 尚未开放的章节卡没有时间线归属（门控项不带 StoryLineId），挂到默认那条线上，
    # 避免它们从页面上消失。当前上游没有未开放的主线章，此分支暂不触发。
    if locked_items and groups:
        default_idx = max(range(len(groups)), key=lambda i: len(groups[i]['cards']))
        groups[default_idx]['cards'].extend(_locked_card(it) for it in locked_items)

    default_idx = 0
    if groups:
        default_idx = max(range(len(groups)), key=lambda i: len(groups[i]['cards']))

    wheel = []
    panes = []
    for i, g in enumerate(groups):
        info = g['info']
        key = 'none' if g['id'] is None else str(g['id'])
        title = info.get('title') or '主线'
        active = ' is-active' if i == default_idx else ''
        sel = 'true' if i == default_idx else 'false'
        # ARIA 补全：容器声明了 tablist，子项就得有 role="tab" + aria-selected，
        # 面板配 role="tabpanel" + aria-labelledby；aria-selected 由 site_js 的
        # activate() 随视觉状态同步。全部是读屏元数据，零视觉影响。
        wheel.append(
            '<a class="linewheel-item%s" href="#line-%s" data-line="%s"'
            ' role="tab" id="linetab-%s" aria-selected="%s" aria-controls="line-%s">'
            '<span class="lw-title">%s</span>'
            '<span class="lw-sub">%s</span>'
            '<span class="lw-count">%d 章</span>'
            '</a>' % (active, key, key, key, sel, key,
                      esc(title), esc(info.get('subtitle') or ''),
                      len(g['cards'])))
        panes.append(
            '<section class="linepane%s" id="line-%s" data-line="%s"'
            ' role="tabpanel" aria-labelledby="linetab-%s">'
            '<h2 class="linepane-title">%s%s</h2>'
            '<ul class="chaplist">%s</ul>'
            '</section>' % (active, key, key, key, esc(title),
                            ('　%s' % esc(info.get('subtitle'))) if info.get('subtitle') else '',
                            ''.join(g['cards'])))

    body = """
<h1>主线剧情</h1>
<p class="lede">主线全章节关卡拓扑与剧情档案，支持点击卡片查阅剧情对话与战斗对白。</p>
<div class="linewheel-wrap">
<div class="linewheel" id="linewheel" role="tablist" aria-label="时间线">
<div class="linewheel-pad" aria-hidden="true"></div>
%s
<div class="linewheel-pad" aria-hidden="true"></div>
</div>
<div class="linepanes">
%s
</div>
</div>
""" % ('\n'.join(wheel), '\n'.join(panes))
    return layout('主线剧情', body, d, crumb)


# 覆盖默认二级索引（D3 分发注册表读这个钩子；main 用时间线轮盘索引）
INDEX_OVERRIDE = main_index
