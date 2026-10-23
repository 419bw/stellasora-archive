# -*- coding: utf-8 -*-
"""未开放门控占位（Phase D1 从 site_templates.py 拆出，函数体逐字不动）。"""
from registry import FAMILY_NAME, slug_of
from theme.layout import depth_of, esc, layout


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


def _locked_card(item):
    open_text = item.get('open_text') or _gate_mod().fmt_open(item.get('open_time'))
    preview = item.get('preview') or ''
    info = ('预计 %s 开放' % esc(open_text)) if open_text else '开放时间待官方公布'
    if preview:
        info += '<br>官方预告：%s' % esc(preview)
    return """<li><div class="chapcard locked">
  <div class="chap-top">
    <span class="chapno">%s</span>
    <span class="chapyear locked-tag">未开放</span>
  </div>
  <div class="chaptitle">%s</div>
  <div class="chapinfo">%s</div>
  <span class="chapline"></span>
</div></li>""" % (esc(item.get('no') or ''), esc(locked_mask()), info)
