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
    if text.endswith('抉择') or '抉择：' in text or '抉择:' in text:
        return 'choice'
    if text.startswith('通讯回复抉择'):
        return 'choice'
    return 'marker'


def convert(md):
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
                if para:
                    out.append('<blockquote>%s</blockquote>'
                               % ''.join('<p>%s</p>' % _inline(p) for p in para))
                    para = []
                cls = _cls_for_marker(m.group(1))
                out.append('<p class="%s">%s</p>' % (cls, escape(m.group(1))))
                stats['marker'] += 1
                if cls == 'choice':
                    opts = []
                    while i + 1 < len(text) and BULLET.match(text[i + 1]):
                        w, d = BULLET.match(text[i + 1]).groups()
                        opts.append('<li><b>%s</b>%s</li>'
                                    % (escape(w), _inline('：' + d if d else '')))
                        i += 1
                    out.append('<ul class="options">%s</ul>' % ''.join(opts))
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
            out.append('<h2 data-part="%s">%s</h2>' % (n, escape(t)))
        elif l.startswith('## '):
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
            if tag:
                cls += ' thought' if tag == '思考' else (' chat' if tag == '短信' else ' bubble')
            out.append('<p class="%s"><b class="who">%s</b>%s<span class="say">「%s」</span></p>'
                       % (cls, escape(who),
                          '<i class="tag">%s</i>' % escape(tag) if tag else '', escape(text)))
            stats['line'] += 1
        else:
            out.append('<p>%s</p>' % _inline(l))
    flush_quote()
    return '\n'.join(out), stats


def _inline(s):
    """Bold and code spans only; the story text itself is never markup."""
    s = escape(s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s)
    return s


def dialogue(html_body):
    """The spoken-line sequence, read back out of generated HTML (used by the validator)."""
    return [m.group(1) for m in re.finditer(
        r'<p class="line[^"]*"><b class="who">.*?</b>(?:<i class="tag">.*?</i>)?'
        r'<span class="say">「(.*?)」</span>', html_body)]
