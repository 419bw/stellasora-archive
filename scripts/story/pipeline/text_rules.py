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
# The client's own inline signals, from Avg_4_TalkCtrl.lua:292-296: ==P== paragraph,
# ==B== break, ==W== wait, ==RT== newline, ==A<delay>== auto-paragraph, ==Off== drop the
# centred background. None of them carry words, and _NOT_IN_LOG_ only keeps a line out of
# the in-game log panel.
TEXT_SIGNAL = re.compile(r'==[A-Za-z0-9_.]*==')


def clean_dialogue(s):
    if not s:
        return ""
    # ruby survives: <r=注音></r> is the small reading drawn above a word, i.e. content.
    # Park it behind a sentinel so the blanket tag strip below cannot eat it.
    s = RUBY.sub(lambda m: '\x00%s\x00' % m.group(1), s)
    s = s.replace('<br>', ' ')
    s = re.sub(r'<[^>]*>', '', s)
    s = s.replace('==PLAYER_NAME==', PROTAG_NAME)
    s = re.sub(r'==SEX\d*==', '你', s)
    s = TEXT_SIGNAL.sub(' ', s)
    s = s.replace('_NOT_IN_LOG_', '')
    s = re.sub(r'\x00([^\x00]*)\x00', lambda m: '<r=%s></r>' % m.group(1), s)
    s = re.sub(r'[ \t]+', ' ', s)
    return s.strip()


NONLOG = '_NOT_IN_LOG_'


def _sig(text):
    """Animation frames that differ only by alpha/whitespace are the same line.

    The signature must be taken from the *rendered* text: a fade frame carries
    <alpha=#22> where the logged frame carries none (or #CC vs #44), so comparing
    raw markup would call every frame distinct and keep one per fade run.
    """
    return re.sub(r'\s+', '', clean_dialogue(text))


def _related(a, b):
    """True when two frames can be sub-states of one animated visual.

    A fade-in emits the sentence with the trailing part progressively revealed, so
    frames of one visual compare equal or one is contained in the other. Anything
    else (an unrelated next line) ends the visual.
    """
    return a == b or a in b or b in a
