# -*- coding: utf-8 -*-
"""拓扑图页（Phase D1 从 site_templates.py 拆出，函数体逐字不动）。

D2 再把 chapter_graph_page / activity_graph_page 的共用骨架抽成组件；
本文件先落纯搬运版（两页型各自完整，含章节切换条与时间线排序键）。
"""
from theme.layout import depth_of, esc, layout, node_state_class, node_state_label, rel


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
    by_sid = {n['story_id']: n for n in c['nodes']}
    pad = 24

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
