# -*- coding: utf-8 -*-
"""主线族站点模板：章图索引覆盖页（INDEX_OVERRIDE）与章节卡。

Phase D1 纯搬运（main_index / _chapter_card 函数体逐字不动）；分发注册表
（build_site.py 的 (family, kind) 分发）在 D3 上线，INDEX_OVERRIDE 即钩子。
"""
from registry import slug_of
from theme.layout import depth_of, esc, layout
from theme.graph import _line_sort_key, chapter_switch
from theme.gate import _locked_card


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
