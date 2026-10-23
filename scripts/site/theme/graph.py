# -*- coding: utf-8 -*-
"""拓扑图页共用组件（Phase D2 从 chapter_graph_page / activity_graph_page 二合一）。

两页型（主线章图 / 活动分支图）的差异只剩四样：面包屑、切换条、lede 文案、
``data-family`` 与页脚提示——全部由调用方（families/main、families/events 的
组装层）以参数注入；连线层、卡片层、列锚点、map/canvas/svg 骨架在此共用，
防止两处拓扑规则漂移。

历史包袱已核对无误，统一后字节不变：
- 活动节点 ``time`` 恒为 None → 卡片 chip 恒为空串；
- 活动节点 ``page`` 恒存在 → 卡片恒为 ``<a>`` 变体；
- 活动节点 ``state`` 恒为 ``released`` → 连线恒不带 ``dash``。
"""
from theme.layout import esc, layout, node_state_class, node_state_label, rel


def _graph_paths(nodes, g, pad=24):
    """SVG 连线层：源卡片右缘 → 目标列左缘的三次贝塞尔，未开放目标加虚线。"""
    by_sid = {n['story_id']: n for n in nodes}
    out = []
    for u, v in g['edges']:
        a, b = by_sid[u], by_sid[v]
        x1 = a['x'] + pad + g['card'][0]
        y1 = a['y'] + pad + g['card'][1] / 2.0
        x2 = b['x'] + pad
        y2 = b['y'] + pad + g['card'][1] / 2.0
        mx = x1 + (x2 - x1) / 2.0
        cls = node_state_class(b)
        dash = ' dash' if b['state'] == 'unreleased' else ''
        out.append('<path class="edge %s%s" d="M%d %d C%d %d,%d %d,%d %d"/>'
                   % (cls, dash, x1, y1, mx, y1, mx, y2, x2, y2))
    return ''.join(out)


def _graph_cards(nodes, g, pad, depth):
    """绝对定位卡片层：按 (col, lane) 排序，每列首卡带 id 锚点。"""
    out = []
    seen_col = set()
    for n in sorted(nodes, key=lambda x: (x['col'], x['lane'])):
        style = 'left:%dpx;top:%dpx;width:%dpx;height:%dpx' % (
            n['x'] + pad, n['y'] + pad, g['card'][0], g['card'][1])
        t = n.get('time')
        chip = '<span class="chip">%s</span>' % esc('%s %s' % (t['date'], t['clock'])) if t else ''
        inner = ('<span class="code">%s</span><span class="t">%s</span>%s'
                 % (esc(n['code'] or '·'), esc(n['title']), chip))
        cid = '' if n['col'] in seen_col else ' id="col%d"' % n['col']
        seen_col.add(n['col'])
        if n['page']:
            out.append('<a%s class="node %s" style="%s" data-col="%d" href="%s">%s'
                       '<span class="state">%s ›</span></a>'
                       % (cid, node_state_class(n), style, n['col'], rel(depth, n['page']), inner,
                          esc(node_state_label(n))))
        else:
            out.append('<div%s class="node %s" style="%s" data-col="%d">%s'
                       '<span class="state">%s</span></div>'
                       % (cid, node_state_class(n), style, n['col'], inner,
                          esc(node_state_label(n))))
    return ''.join(out)


def _graph_anchors(nodes, g, pad=24):
    """列锚点条：每列一个跳转按钮，标签取该列最小关卡代码。"""
    return ''.join('<a href="#col%d" data-scroll-to="%d">%s</a>'
                   % (col, col * g['step_x'] + pad,
                      esc(min((n['code'] or '·') for n in nodes if n['col'] == col)))
                   for col in range(g['columns']))


def graph_map_page(title, crumb, depth, family, heading, lede, switch, aside, nodes, g, pad=24):
    """拓扑图页骨架：切换条 + 列锚点 + 平铺 SVG 连线层 + 绝对定位卡片层。

    ``family`` 同时写进 nav/anchors/map 三处 ``data-family``（CSS 作用域选择器
    的挂点）；``heading``/``lede``/``aside`` 由组装层注入，均已自行转义。
    """
    body = """
<h1>%s</h1>
<p class="lede">%s</p>
<nav class="chapsel" data-family="%s">%s</nav>
<div class="anchors-wrap"><nav class="anchors" data-family="%s">%s</nav></div>
<div class="map" data-family="%s">
<div class="canvas" style="width:%dpx;height:%dpx">
<svg class="wires" width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>
%s
</div>
</div>
<p class="aside map-note">%s</p>
""" % (heading, lede, family, switch, family, _graph_anchors(nodes, g, pad), family,
       g['width'] + pad * 2, g['height'] + pad * 2,
       g['width'] + pad * 2, g['height'] + pad * 2,
       g['width'] + pad * 2, g['height'] + pad * 2,
       _graph_paths(nodes, g, pad), _graph_cards(nodes, g, pad, depth), aside)
    return layout(title, body, depth, crumb)
