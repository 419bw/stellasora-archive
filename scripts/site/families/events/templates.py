# -*- coding: utf-8 -*-
"""活动族站点模板。

Phase D1 建包占位；D2 迁入 activity_graph_page 组装层（拓扑骨架用
theme.graph.graph_map_page）；BRANCHING_ACTS 声明在 D3 落位，取代
build_site.py 里的 10106/20101 硬编码清单。
"""
from theme.layout import depth_of, esc
from theme.graph import graph_map_page

# D3 待迁入：branching_acts 声明（id/code/name/title + 卡片与步进几何）
BRANCHING_ACTS = ()


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

    crumb = ('<a href="%sindex.html">首页</a> › <a href="%sevents/index.html">活动剧情</a> › '
             '%s 拓扑连线图' % (root, root, esc(act_name)))

    switch = ' '.join(
        '<a href="%sevents/%s/index.html"%s>%s</a>' % (
            root, a['id'], ' class="on"' if str(a['id']) == act_id else '',
            esc(a['name'])
        ) for a in all_branching_acts
    )
    switch = ('<a href="%sevents/index.html">← 全部活动</a> ' % root) + switch

    return graph_map_page(
        '%s 关卡拓扑' % act_name, crumb, d, 'events',
        '%s《%s》' % (esc(act_name), esc(act_title)),
        '活动关卡拓扑连线图　收录 %d 个剧情与战斗节点　含多分支抉择路线' % len(nodes),
        switch,
        '活动关卡拓扑分支图，支持鼠标拖拽平移与列锚点定位；点击卡片可查阅对应活动剧本。',
        nodes, g)
