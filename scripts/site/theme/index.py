# -*- coding: utf-8 -*-
"""族二级索引默认页（Phase D1 从 site_templates.py 拆出，函数体逐字不动）。"""
import collections

from registry import FAMILY_NAME, slug_of
from theme.layout import depth_of, esc, full_title, layout, rel
from theme.gate import locked_block


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
    total_notes = 0
    for (label, gid), items in groups.items():
        total_stages += len(items)
        topo_badge = ''
        if family == 'events' and str(gid) in ('10106', '20101'):
            topo_badge = '<div class="grp-topo-wrap"><a class="grp-topo-btn" href="%s/index.html">✦ 查看本活动关卡拓扑图（含分支路线） →</a></div>' % gid
        links = []
        grp_notes = 0
        for it in items:
            if family == 'anecdotes' and it.get('notes'):
                for nt in it['notes']:
                    grp_notes += 1
                    total_notes += 1
                    links.append(
                        '<li><a class="plain-link" href="%s#note-%s">'
                        '<span class="link-title">%s</span>'
                        '<span class="sub">%s</span></a></li>'
                        % (rel(d, it['page']), nt['id'], esc(nt['title']), esc(nt['source']))
                    )
                continue
            is_battle = it.get('kind') == 'battle'
            if it.get('table_refs'):
                sub = '终局文本 · %d 字' % it.get('text_chars', 0)
            elif is_battle:
                sub = '战斗关卡'
            else:
                sub = ('%d 句' % it['counts'].get('talk', 0)
                       + (' / %d 气泡' % it['counts']['bubble'] if it['counts'].get('bubble') else ''))
            display_title = full_title(it.get('code'), it.get('title'))
            links.append('<li><a class="plain-link" href="%s"><span class="link-title">%s</span><span class="sub">%s</span></a></li>'
                         % (rel(d, it['page']), esc(display_title), esc(sub)))
        if family == 'anecdotes':
            badge_text = '%d 篇' % (grp_notes or len(items))
        elif family == 'events':
            badge_text = '%d 关' % len(items)
        else:
            badge_text = '%d 篇' % len(items)
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
                      % (esc(label), badge_text, topo_badge, ''.join(links)))
    for item in locked_items:
        blocks.append(locked_block(item))

    crumb = '<a href="%sindex.html">首页</a> › %s' % ('../' * d, FAMILY_NAME[family])
    unit_name = '个活动' if family == 'events' else ('位角色' if family == 'characters' else '个分类')
    stage_unit = '关' if family == 'events' else '篇'
    display_total = total_notes if (family == 'anecdotes' and total_notes) else total_stages
    toolbar = """<div class="grp-toolbar">
  <div class="grp-toolbar-info">收录 %d %s · 共 %d %s%s</div>
  <div class="grp-toolbar-actions">
    <button type="button" class="btn-grp-toggle" id="expandAllBtn">全部展开</button>
    <button type="button" class="btn-grp-toggle" id="collapseAllBtn">全部收起</button>
  </div>
</div>""" % (len(groups), unit_name, display_total, stage_unit,
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
