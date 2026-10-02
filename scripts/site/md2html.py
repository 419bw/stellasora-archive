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
    if text.startswith('通讯回复抉择'):
        return 'choice'
    return 'marker'


def convert(md, branch_targets=None):
    out = []
    stats = {'line': 0, 'marker': 0, 'scene': 0, 'choice': 0, 'meta': 0}
    quote = []

    def flush_quote():
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
                if tag_content == '玩家回应':
                    if para:
                        out.append('<blockquote>%s</blockquote>'
                                   % ''.join('<p>%s</p>' % _inline(p) for p in para))
                        para = []
                    resp_items = []
                    while i + 1 < len(text) and BULLET.match(text[i + 1]):
                        w, d = BULLET.match(text[i + 1]).groups()
                        line_text = '<b>%s</b>%s' % (escape(w), _inline('：' + d if d else ''))
                        resp_items.append('<p>%s</p>' % line_text)
                        i += 1
                    out.append('<div class="player-reply"><div class="reply-who">魔王 选择了</div><div class="reply-body">%s</div></div>'
                               % ''.join(resp_items))
                    stats['choice'] += 1
                    i += 1
                    continue
                if para:
                    out.append('<blockquote>%s</blockquote>'
                               % ''.join('<p>%s</p>' % _inline(p) for p in para))
                    para = []
                cls = _cls_for_marker(tag_content)
                out.append('<p class="%s">%s</p>' % (cls, escape(tag_content)))
                stats['marker'] += 1
                if 'choice' in cls:
                    is_major = 'major-choice' in cls
                    opts = []
                    opt_idx = 0
                    while i + 1 < len(text) and BULLET.match(text[i + 1]):
                        w, d = BULLET.match(text[i + 1]).groups()
                        target_badge = ''
                        if is_major and branch_targets and opt_idx < len(branch_targets):
                            tgt = branch_targets[opt_idx]
                            target_badge = ('<a class="opt-target" href="%s" title="前往对应分支关卡">'
                                            '<span>分支走向</span><strong>%s %s →</strong></a>'
                                            % (escape(tgt['url']), escape(tgt['code']), escape(tgt['title'])))
                        opts.append('<li><div class="opt-main"><b>%s</b>%s</div>%s</li>'
                                    % (escape(w), _inline('：' + d if d else ''), target_badge))
                        opt_idx += 1
                        i += 1
                    opts_cls = 'options major-options' if is_major else 'options'
                    out.append('<ul class="%s">%s</ul>' % (opts_cls, ''.join(opts)))
                    stats['choice'] += 1
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
