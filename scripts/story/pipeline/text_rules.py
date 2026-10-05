# -*- coding: utf-8 -*-
"""管线 Stage 3a: 文本规则 —— 台词清洗、资源名判定、动画帧签名。

自 build_story.py 原样迁出（Phase 1c），逐行为等价；这些规则直接决定
md 产物的字节内容，是黄金对拍的对照真源之一，改动必须走显式 diff 清单。
"""
import re

from .domain import PROTAG_NAME


def clean_text(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip()


RESOURCE_NAME = re.compile(r'[a-z][a-z0-9_]*')


def is_resource_name(text):
    """Sprite/emoji asset keys are authored straight into the text field of some lines.
    In STm/STev/BBm they carry no words; in PM chat they mean a sticker send."""
    return bool(RESOURCE_NAME.fullmatch(text))


RUBY = re.compile(r'<r=([^<>]*)></r>')
# 带体 ruby <r=注音>正文</r>：base 在标签体内、可多字（交换注音/着重号排版）。
# Phase 4a 起与空体形式一样视为内容保留；此前被 blanket strip 静默吃掉注音。
RUBY_BODY = re.compile(r'<r=([^<>]*)>([^<>]+)</r>')
# The client's own inline signals, from Avg_4_TalkCtrl.lua:292-296: ==P== paragraph,
# ==B== break, ==W== wait, ==RT== newline, ==A<delay>== auto-paragraph, ==Off== drop the
# centred background. None of them carry words, and _NOT_IN_LOG_ only keeps a line out of
# the in-game log panel.
TEXT_SIGNAL = re.compile(r'==[A-Za-z0-9_.]*==')

# 强调标记（Phase 4b）：<b>/<i> 是语义标记（着重/斜体），与纯排版的
# color/size/align/margin/alpha/voffset/rotate/sprite/space（TMP 富文本标签，
# 全部剥除）不同，成对出现时原样保留。语料三种形态：成对（CG_147_02 台词
# 强调）、嵌套成对（CG_disc4055 排版帧 <i><b>Y</b></i>）、孤儿（STm06_01
# 悬空 </b>、disc4055 未闭合 <i>）——孤儿剥离并计数进诊断侧车。
EMPH = re.compile(r'<(/?)([bi])>')
EMPH_SENTINEL = {'<b>': '\x04', '</b>': '\x05', '<i>': '\x06', '</i>': '\x07'}
EMPH_RESTORE = {0x04: '<b>', 0x05: '</b>', 0x06: '<i>', 0x07: '</i>'}
# 进程内累计（build 单线程），write_diagnostics 读取写入 _diagnostics.json。
EMPH_STATS = {'paired': 0, 'orphan': 0}


def _protect_emph(s):
    """栈配对 <b>/<i>：严格嵌套的成对标记换成哨兵（躲过 blanket strip），
    孤儿与交叉标记剥离。交叉时按尽力保留原则处理：close 只与栈顶同种
    open 配对（如 <b><i>x</i> 里 i 成对保留、悬空 b 剥离）。"""
    marks = list(EMPH.finditer(s))
    if not marks:
        return s
    stack = []                      # [(mark_no, kind)]
    keep = set()
    for n, m in enumerate(marks):
        kind = m.group(2)
        if not m.group(1):          # open
            stack.append((n, kind))
        elif stack and stack[-1][1] == kind:   # close 配栈顶同种 open
            keep.add(stack.pop()[0])
            keep.add(n)
        # 其余 close：孤儿（无 open 或交叉），剥离
    EMPH_STATS['paired'] += len(keep)
    EMPH_STATS['orphan'] += len(marks) - len(keep)
    out = []
    pos = 0
    for n, m in enumerate(marks):
        out.append(s[pos:m.start()])
        if n in keep:
            out.append(EMPH_SENTINEL[m.group(0)])
        pos = m.end()
    out.append(s[pos:])
    return ''.join(out)


def clean_dialogue(s):
    if not s:
        return ""
    # ruby survives: both <r=注音></r> (anchored to the preceding char) and
    # <r=注音>正文</r> (note over the tagged body) are content. Park them behind
    # sentinels so the blanket tag strip below cannot eat them. \x00..\x07 never
    # occur in the corpus (control chars); the body sentinel keeps base and note
    # apart so the restore step can rebuild the exact original spelling.
    s = RUBY_BODY.sub(lambda m: '\x01%s\x02%s\x03' % (m.group(2), m.group(1)), s)
    s = RUBY.sub(lambda m: '\x00%s\x00' % m.group(1), s)
    s = _protect_emph(s)
    s = s.replace('<br>', ' ')
    s = re.sub(r'<[^>]*>', '', s)
    s = s.replace('==PLAYER_NAME==', PROTAG_NAME)
    s = re.sub(r'==SEX\d*==', '你', s)
    s = TEXT_SIGNAL.sub(' ', s)
    s = s.replace('_NOT_IN_LOG_', '')
    s = re.sub(r'\x01([^\x01\x02\x03]*)\x02([^\x01\x02\x03]*)\x03',
               lambda m: '<r=%s>%s</r>' % (m.group(2), m.group(1)), s)
    s = re.sub(r'\x00([^\x00]*)\x00', lambda m: '<r=%s></r>' % m.group(1), s)
    s = s.translate(EMPH_RESTORE)
    s = re.sub(r'[ \t]+', ' ', s)
    return s.strip()


NONLOG = '_NOT_IN_LOG_'


def _sig(text):
    """Animation frames that differ only by alpha/whitespace are the same line.

    The signature must be taken from the *rendered* text: a fade frame carries
    <alpha=#22> where the logged frame carries none (or #CC vs #44), so comparing
    raw markup would call every frame distinct and keep one per fade run.

    Phase 4b：<b>/<i> 同样不参与签名——它们是表现标记，若计入，渐显帧序列
    （<i><b>Y</b></i> → <i><b>Y O</b></i>）会因标签阻断子串包含关系而折叠
    失效。剥离后与 4b 之前的折叠判定口径逐字节一致（validate_story 的
    _vsig 镜像用 norm 剥全部标签，天然对称）。ruby 是内容，保留在签名里。
    """
    return re.sub(r'</?[bi]>', '', re.sub(r'\s+', '', clean_dialogue(text)))


def _related(a, b):
    """True when two frames can be sub-states of one animated visual.

    A fade-in emits the sentence with the trailing part progressively revealed, so
    frames of one visual compare equal or one is contained in the other. Anything
    else (an unrelated next line) ends the visual.
    """
    return a == b or a in b or b in a
