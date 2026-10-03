# -*- coding: utf-8 -*-
"""Convert this repo's own Markdown subset into HTML.

The Markdown in story_docs/ is the reviewed, validated artefact, so the site renders
from it instead of growing a second copy of the beat renderer. The line shapes below
are exactly what scripts/build_story.py emits; anything unrecognised falls through as
escaped text, which makes a generator change visible rather than silently dropped.

Usage: html_body, stats = convert(md_text)
"""
import re
from html import escape

LINE = re.compile(r'^\*\*(.+?)\*\*(?:（([^）]*)）)?：「(.*)」$')
STICKER = re.compile(r'^\*\*(.+?)\*\*：〔发送表情 `(.+?)`〕$')
RUBY = re.compile(r'<r=([^<>]*)></r>')
META = re.compile(r'^- \*\*(.+?)\*\*：(.*)$')
MARKER = re.compile(r'^> \*\*\[(.+?)\]\*\*$')
SCENE = re.compile(r'^> \*\*【(.+?)】\*\*$')
BULLET = re.compile(r'^> - \*\*(.+?)\*\*(?:：(.*))?$')
NOTE = re.compile(r'^> \*(.+?)\*$')
H2 = re.compile(r'^## (\d)\. (.*)$')


def _cls_for_marker(text):
    if text.startswith('若选'):
        return 'branch-open'
    if text.startswith('▲'):
        return 'merge'
    if text.startswith('战斗阶段'):
        return 'wave'
    if text.startswith('重大抉择'):
        return 'choice major-choice'
    if text.endswith('抉择') or '抉择：' in text or '抉择:' in text:
        return 'choice'
    # single-option generic replies render as the chat bubble below; classify so the
    # structure pass assigns them a choice anchor that branch-nav can jump back to
    if text == '玩家回应' or text.startswith('玩家回应：'):
        return 'choice'
    if text.startswith('通讯回复抉择'):
        return 'choice'
    return 'marker'


def _clean_opt(s):
    # Strip rubies, html tags, ellipses, and whitespace for robust option-to-branch matching
    s = re.sub(r'<[^>]*>', '', s)
    return re.sub(r'[.…—\s　]', '', s)


def _branch_nav_html(choice_id, merge_id):
    merge_btn = ''
    if merge_id:
        merge_btn = (
            f'<a class="branch-nav-btn to-merge" href="#{merge_id}" title="跳过其它互斥分支，前往剧情汇合处">'
            f'<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2">'
            f'<path d="M12 5v14M19 12l-7 7-7-7"/>'
            f'</svg><span>跳到汇合</span></a>'
        )
    return (
        f'<div class="branch-nav">'
        f'<a class="branch-nav-btn to-choice" href="#{choice_id}" title="回到抉择选项位置">'
        f'<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2">'
        f'<path d="M12 19V5M5 12l7-7 7 7"/>'
        f'</svg><span>返回抉择</span></a>'
        f'{merge_btn}'
        f'</div>'
    )


def _parse_choice_structure(md):
    lines = md.splitlines()
    choices = []
    branches = []
    merges = []
    stack = []
    cid = 0

    i = 0
    while i < len(lines):
        l = lines[i].rstrip()
        m = MARKER.match(l)
        if m:
            tag = m.group(1)
            cls = _cls_for_marker(tag)
            if 'choice' in cls:
                cid += 1
                c_info = {
                    'cid': cid,
                    'choice_id': f'choice-{cid}',
                    'tag': tag,
                    'options': [],
                    'branches': [],
                    'merge_id': None,
                    'line_idx': i
                }
                j = i + 1
                while j < len(lines):
                    if lines[j].startswith('> - '):
                        bm = BULLET.match(lines[j])
                        if bm:
                            c_info['options'].append(bm.group(1))
                    elif lines[j].strip() == '':
                        pass
                    else:
                        break
                    j += 1
                choices.append(c_info)
                stack.append(c_info)
                i = j
                continue
            elif tag.startswith('若选'):
                bm = re.match(r'^若选「(.*?)」↓$', tag)
                opt_name = bm.group(1) if bm else tag[2:-1]
                # The generator attributes a branch to the choice its option name
                # belongs to (the frame its jump entered), which is not always the
                # most recently opened one — e.g. a 玩家回应 opened inside branch
                # content carries no jump of its own. Match by option name from the
                # innermost frame outward, falling back to the previous stack-top rule.
                parent_c = None
                for fr in reversed(stack):
                    if any(_clean_opt(o) == _clean_opt(opt_name) for o in fr['options']):
                        parent_c = fr
                        break
                if parent_c is None and stack:
                    parent_c = stack[-1]
                # A choice that offers only one option is not a fork at all: the game
                # cannot branch there, so its 若选 markers are pure presenter noise.
                # See AI_HANDOVER_GUIDE.md 3.5 — upstream CG_126_03.lua closes choice
                # group a_10 with a_4's SetChoiceEnd, leaving the frame live and making
                # build_story.py re-emit the same 若选 for every later beat. Rendering it
                # as a branch box would show a "fork" that does not exist, so such a
                # marker is rendered as plain dialogue instead.
                single_parent = bool(parent_c) and len(parent_c['options']) <= 1
                b_idx = len(parent_c['branches']) if parent_c else len(branches)
                c_id_num = parent_c['cid'] if parent_c else 0
                b_info = {
                    'bid': f'branch-{c_id_num}-{b_idx}',
                    'b_idx': b_idx,
                    'opt_name': opt_name,
                    'parent_cid': c_id_num,
                    'choice_id': parent_c['choice_id'] if parent_c else f'choice-{c_id_num}',
                    'tag': tag,
                    'single_parent': single_parent,
                    'line_idx': i
                }
                branches.append(b_info)
                if parent_c:
                    parent_c['branches'].append(b_info)
            elif tag.startswith('▲'):
                mid = f'merge-{cid}'
                if stack:
                    if '层嵌套抉择' in tag:
                        mid = f'merge-{stack[0]["cid"]}'
                        while stack:
                            sc = stack.pop()
                            sc['merge_id'] = mid
                    else:
                        # the merge arrives when the fork structure rejoins, so it
                        # closes the innermost frame that actually owns branches —
                        # a forked-over 玩家回应 frame on top must not steal it
                        sc = next((fr for fr in reversed(stack) if fr['branches']), stack[-1])
                        stack.remove(sc)
                        mid = f'merge-{sc["cid"]}'
                        sc['merge_id'] = mid
                merges.append({'tag': tag, 'merge_id': mid, 'line_idx': i})
        i += 1

    for b in branches:
        p_cid = b['parent_cid']
        c = next((x for x in choices if x['cid'] == p_cid), None)
        b['merge_id'] = c['merge_id'] if c else None

    return choices, branches, merges


def convert(md, branch_targets=None):
    """Render one script markdown to HTML.

    branch_targets: list (document order) of 重大抉择 groups; each group is a list of
    {'opt', 'code', 'title', 'url', 'cls', 'tag'} targets keyed by the option text the
    target belongs to (built by build_site from the option jump EvIds).
    """
    choices, branches, merges = _parse_choice_structure(md)
    choice_iter = iter(choices)
    branch_iter = iter(branches)
    merge_iter = iter(merges)

    out = []
    stats = {'line': 0, 'marker': 0, 'scene': 0, 'choice': 0, 'meta': 0}
    quote = []
    active_branch = None
    # branch_targets is a list of per-major-choice target groups (document order);
    # within a group each target carries the option text it belongs to.
    major_choice_seq = [0]

    def close_active_branch():
        nonlocal active_branch
        if active_branch:
            out.append(_branch_nav_html(active_branch['choice_id'], active_branch.get('merge_id')))
            active_branch = None

    def flush_quote():
        nonlocal active_branch
        if not quote:
            return
        text = list(quote)
        quote.clear()
        if all(SCENE.match(t) for t in text):
            for t in text:
                out.append('<aside class="scene">%s</aside>' % escape(SCENE.match(t).group(1)))
                stats['scene'] += 1
            return
        i = 0
        para = []
        while i < len(text):
            t = text[i]
            m = MARKER.match(t)
            if m:
                tag_content = m.group(1)
                if tag_content == '玩家回应' or tag_content.startswith('玩家回应：'):
                    # consume the matching structure entry so later choices keep their ids
                    c_obj = next(choice_iter, None)
                    if para:
                        out.append('<blockquote>%s</blockquote>'
                                   % ''.join('<p>%s</p>' % _inline(p) for p in para))
                        para = []
                    # a bare marker has no lead-in; the prompt form carries the fixed
                    # first half of the player's reply, kept as a muted line in the bubble
                    lead = tag_content[len('玩家回应'):].lstrip('：').strip()
                    resp_items = []
                    if lead:
                        resp_items.append('<p class="reply-lead">%s</p>' % _inline(lead))
                    while i + 1 < len(text) and BULLET.match(text[i + 1]):
                        w, d = BULLET.match(text[i + 1]).groups()
                        line_text = '<b>%s</b>%s' % (escape(w), _inline('：' + d if d else ''))
                        resp_items.append('<p>%s</p>' % line_text)
                        i += 1
                    id_attr = ' id="%s"' % c_obj['choice_id'] if c_obj and c_obj.get('choice_id') else ''
                    out.append('<div class="player-reply"%s><div class="reply-who">魔王 选择了</div><div class="reply-body">%s</div></div>'
                               % (id_attr, ''.join(resp_items)))
                    stats['choice'] += 1
                    i += 1
                    continue
                if para:
                    out.append('<blockquote>%s</blockquote>'
                               % ''.join('<p>%s</p>' % _inline(p) for p in para))
                    para = []
                cls = _cls_for_marker(tag_content)

                if tag_content.startswith('若选'):
                    b_obj = next(branch_iter, None)
                    if b_obj and b_obj.get('single_parent'):
                        # single-option parent: the 若选 line is not a branch header.
                        # Drop it (and its 返回抉择/跳到汇合 nav bar) so the dialogue
                        # simply continues; the iterator is consumed to keep every
                        # later branch aligned. Compromise for the upstream
                        # CG_126_03 SetChoiceEnd mix-up, see AI_HANDOVER_GUIDE.md 3.5.
                        i += 1
                        continue
                    close_active_branch()
                    bid_attr = f' id="{b_obj["bid"]}"' if b_obj else ''
                    out.append('<p class="%s"%s>%s</p>' % (cls, bid_attr, escape(tag_content)))
                    stats['marker'] += 1
                    if b_obj:
                        active_branch = {
                            'choice_id': b_obj['choice_id'],
                            'merge_id': b_obj.get('merge_id')
                        }
                    i += 1
                    continue
                elif tag_content.startswith('▲'):
                    close_active_branch()
                    m_obj = next(merge_iter, None)
                    mid_attr = f' id="{m_obj["merge_id"]}"' if m_obj else ''
                    out.append('<p class="%s"%s>%s</p>' % (cls, mid_attr, escape(tag_content)))
                    stats['marker'] += 1
                    i += 1
                    continue
                elif 'choice' in cls:
                    c_obj = next(choice_iter, None)
                    cid_attr = f' id="{c_obj["choice_id"]}"' if c_obj else ''
                    out.append('<p class="%s"%s>%s</p>' % (cls, cid_attr, escape(tag_content)))
                    stats['marker'] += 1
                    is_major = 'major-choice' in cls
                    c_targets = None
                    if is_major:
                        if branch_targets and major_choice_seq[0] < len(branch_targets):
                            c_targets = branch_targets[major_choice_seq[0]]
                        major_choice_seq[0] += 1
                    opts = []
                    # suppressed branches point at anchors that are never rendered,
                    # so the option badges must ignore them (single-option parent)
                    c_branches = [b for b in c_obj['branches'] if not b.get('single_parent')] if c_obj else []
                    c_merge_id = c_obj.get('merge_id') if c_obj else None

                    while i + 1 < len(text) and BULLET.match(text[i + 1]):
                        w, d = BULLET.match(text[i + 1]).groups()
                        # badge follows the option by name: several options may share
                        # one branch level, so index-based matching cannot be right
                        tgt = None
                        if c_targets:
                            clean_w = _clean_opt(w)
                            for cand in c_targets:
                                if clean_w == _clean_opt(cand.get('opt') or ''):
                                    tgt = cand
                                    break
                        target_badge = ''
                        if tgt and tgt.get('url'):
                            target_badge = ('<a class="opt-target" href="%s" title="前往对应分支关卡">'
                                            '<span>分支走向</span><strong>%s %s →</strong></a>'
                                            % (escape(tgt['url']), escape(tgt['code']), escape(tgt['title'])))

                        target_anchor = None
                        jump_badge = ''
                        if c_branches:
                            matched_b = None
                            clean_w = _clean_opt(w)
                            for b in c_branches:
                                clean_b = _clean_opt(b['opt_name'])
                                if clean_w == clean_b or clean_w.startswith(clean_b) or clean_b.startswith(clean_w):
                                    matched_b = b
                                    break
                            if matched_b:
                                target_anchor = f"#{matched_b['bid']}"
                                jump_badge = '<span class="opt-jump-badge">跳转分支 ↓</span>'
                            elif c_merge_id:
                                target_anchor = f"#{c_merge_id}"
                                jump_badge = '<span class="opt-jump-badge is-merge">直接汇合 ↓</span>'
                        elif c_merge_id:
                            target_anchor = f"#{c_merge_id}"
                            jump_badge = '<span class="opt-jump-badge is-merge">直接汇合 ↓</span>'

                        opt_text_html = '<div class="opt-main"><b>%s</b>%s</div>' % (escape(w), _inline('：' + d if d else ''))
                        if target_anchor:
                            title_tip = '点击直接跳转至剧情汇合处' if 'is-merge' in jump_badge else '点击跳转至分支台词'
                            item_inner = (
                                f'<a class="opt-link" href="{target_anchor}" title="{title_tip}">'
                                f'{opt_text_html}{jump_badge}</a>{target_badge}'
                            )
                            opts.append(f'<li class="has-jump">{item_inner}</li>')
                        else:
                            opts.append(f'<li>{opt_text_html}{target_badge}</li>')

                        i += 1
                    opts_cls = 'options major-options' if is_major else 'options'
                    out.append('<ul class="%s">%s</ul>' % (opts_cls, ''.join(opts)))
                    stats['choice'] += 1
                    i += 1
                    continue
                else:
                    out.append('<p class="%s">%s</p>' % (cls, escape(tag_content)))
                    stats['marker'] += 1
            elif NOTE.match(t):
                out.append('<p class="note">%s</p>' % escape(NOTE.match(t).group(1)))
            elif BULLET.match(t):
                w, d = BULLET.match(t).groups()
                out.append('<p class="meta"><b>%s</b>%s</p>' % (escape(w), _inline(d or '')))
            else:
                para.append(t[2:].strip() if t.startswith('> ') else t.lstrip('> '))
            i += 1
        if para:
            out.append('<blockquote>%s</blockquote>'
                       % ''.join('<p>%s</p>' % _inline(p) for p in para))

    in_backlog = False
    for raw in md.splitlines():
        l = raw.rstrip()
        if l.startswith('> '):
            quote.append(l)
            continue
        if l == '>':
            quote.append('>')
            continue
        flush_quote()
        if not l:
            continue
        if l.startswith('# '):
            out.append('<h1>%s</h1>' % escape(l[2:]))
        elif H2.match(l):
            n, t = H2.match(l).groups()
            if in_backlog:
                close_active_branch()
                out.append('</div></div>')
                in_backlog = False
            out.append('<h2 data-part="%s">%s</h2>' % (n, escape(t)))
            if n == '3' or '逐句台词' in t:
                out.append('<div class="backlog-board"><div class="backlog-header">'
                           '<div class="backlog-title">'
                           '<svg class="backlog-pin" viewBox="0 0 24 24" width="15" height="15" fill="currentColor">'
                           '<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>'
                           '</svg><span>紀錄</span></div>'
                           '<span class="backlog-close">✕</span></div>'
                           '<div class="backlog-body">')
                in_backlog = True
        elif l.startswith('## '):
            if in_backlog:
                close_active_branch()
                out.append('</div></div>')
                in_backlog = False
            out.append('<h2>%s</h2>' % escape(l[3:]))
        elif META.match(l):
            k, v = META.match(l).groups()
            # the label's own colon comes from CSS, so drop the one in the text
            out.append('<p class="meta"><b>%s</b>%s</p>' % (escape(k), _inline(v.lstrip('：'))))
            stats['meta'] += 1
        elif STICKER.match(l):
            who, key = STICKER.match(l).groups()
            out.append('<p class="line sticker"><b class="who">%s</b>'
                       '<span class="say">〔发送表情 <code>%s</code>〕</span></p>'
                       % (escape(who), escape(key)))
            stats['line'] += 1
        elif LINE.match(l):
            who, tag, text = LINE.match(l).groups()
            cls = 'line'
            if who == '旁白':
                cls += ' narrator'
            if tag:
                cls += ' thought' if tag == '思考' else (' chat' if tag == '短信' else ' bubble')
            out.append('<p class="%s"><b class="who">%s%s</b><span class="say">「%s」</span></p>'
                       % (cls, escape(who),
                          '<i class="tag">%s</i>' % escape(tag) if tag else '', ruby_html(text)))
            stats['line'] += 1
        else:
            out.append('<p>%s</p>' % _inline(l))
    flush_quote()
    close_active_branch()
    if in_backlog:
        out.append('</div></div>')
    return '\n'.join(out), stats


def _inline(s):
    """Ruby, then bold and code spans; the story text itself is never markup."""
    s = ruby_html(s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s)
    return s


def ruby_html(text):
    """Escape a run of story text, turning <r=注音></r> into native <ruby>.

    The client's ruby tag has an empty body: the note is drawn at the insertion point, and
    in all 2694 occurrences that point sits between the first and second character of the
    word being read (魔<r=mowang></r>王). Anchoring on the character before the tag
    reproduces it with no CSS at all. A note with nothing before it would raise here --
    contract M would already have failed on it."""
    parts = RUBY.split(text)
    out = []
    for i in range(0, len(parts), 2):
        if i + 1 >= len(parts):
            out.append(escape(parts[i]))
            continue
        out.append(escape(parts[i][:-1]))
        out.append('<ruby>%s<rt>%s</rt></ruby>' % (escape(parts[i][-1]), escape(parts[i + 1])))
    return ''.join(out)
