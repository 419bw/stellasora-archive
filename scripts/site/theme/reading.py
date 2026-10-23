# -*- coding: utf-8 -*-
"""剧本阅读页（Phase D1 从 site_templates.py 拆出，函数体逐字不动）。"""
import json

import render_html

from registry import FAMILY_NAME, slug_of
from theme.layout import clean_subtitle, depth_of, esc, full_title, layout


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

    cast_html = ('\n<details class="cast"><summary>出场说话人（%d）</summary><div class="facets">%s</div></details>'
                 % (len(rec['speakers']), facets)) if rec.get('speakers') else ''

    return layout(rec['title'] or page, """
%s
<div class="page" data-family="%s" data-counts='%s'>
%s
</div>
%s%s
""" % (aside, esc(rec['family']),
       json.dumps(rec['counts'], ensure_ascii=False), body,
       story_nav_html, cast_html), d, crumb)
