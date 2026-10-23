# -*- coding: utf-8 -*-
"""战斗档案页（Phase D1 从 site_templates.py 拆出，函数体逐字不动）。"""
from registry import FAMILY_NAME, slug_of
from theme.layout import clean_subtitle, depth_of, esc, layout


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
