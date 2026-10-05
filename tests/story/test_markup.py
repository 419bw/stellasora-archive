# -*- coding: utf-8 -*-
"""Unit tests for scripts/story/pipeline/markup.py（markup 编译器，Phase 3）.

Pins three guarantees:
  1. serialize_md(parse_inline(t)) == t          —— Markdown 后端 pass-through 的
     形式模型对任意输入逐字节还原（含全语料）；
  2. serialize_html(parse_inline(t)) == oracle   —— HTML 输出与被删除的
     md2html.ruby_html 原实现（下方逐字复刻的 oracle）逐字节一致；
  3. 契约 M 违例（ruby 无可锚定的前置字符）抛 MarkupError，而不是渲染出
     错位的注音。
"""
import glob
import json
import os
import re
import sys
from html import escape

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'story'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'site'))

from pipeline import markup  # noqa: E402
import render_html  # noqa: E402

BEATS = os.path.join(ROOT, 'story_docs', '_beats')

# --------------------------------------------------------------- oracle（原 md2html.ruby_html，逐字复刻）
ORACLE_RUBY = re.compile(r'<r=([^<>]*)></r>')


def oracle_ruby_html(text):
    parts = ORACLE_RUBY.split(text)
    out = []
    for i in range(0, len(parts), 2):
        if i + 1 >= len(parts):
            out.append(escape(parts[i]))
            continue
        out.append(escape(parts[i][:-1]))
        out.append('<ruby>%s<rt>%s</rt></ruby>' % (escape(parts[i][-1]), escape(parts[i + 1])))
    return ''.join(out)


CASES = [
    '',
    'plain text 无标记',
    '魔<r=mowang></r>王',
    '前<r=zen></r>中间<r=chukan></r>后',
    '尾部注音<r=owari></r>',
    '<code>不是 ruby</code>',
    'a<r=>未闭合不算标记',
    '空注音<r=></r>成立',
    '未闭合的 <r=dangling 与裸 < 符号>',
    '转义字符 <>&"\'<r=note></r>后',
    '==RT== 清洗后不该出现，但出现也必须是纯文本',
]


@pytest.mark.parametrize('text', CASES)
def test_md_roundtrip_is_identity(text):
    assert markup.serialize_md(markup.parse_inline(text)) == text


@pytest.mark.parametrize('text', CASES)
def test_html_matches_deleted_md2html_oracle(text):
    assert markup.serialize_html(markup.parse_inline(text)) == oracle_ruby_html(text)


@pytest.mark.parametrize('text', CASES)
def test_render_html_ruby_html_delegates(text):
    assert render_html.ruby_html(text) == oracle_ruby_html(text)


def test_ruby_anchor_semantics():
    nodes = markup.parse_inline('魔<r=mowang></r>王')
    assert nodes == [('ruby', '魔', 'mowang'), ('text', '王')]
    assert markup.serialize_html(nodes) == '<ruby>魔<rt>mowang</rt></ruby>王'
    assert markup.serialize_md(nodes) == '魔<r=mowang></r>王'


def test_html_escapes_base_and_note():
    nodes = markup.parse_inline('<&<r=ab></r>尾')
    assert nodes == [('text', '<'), ('ruby', '&', 'ab'), ('text', '尾')]
    assert markup.serialize_html(nodes) == (
        '&lt;<ruby>&amp;<rt>ab</rt></ruby>尾')
    # 注音含 <> 时整个标记不成立，按纯文本转义（与 oracle 的 RUBY 正则同边界）
    assert render_html.ruby_html('<r=a>b</r>') == escape('<r=a>b</r>')


def test_leading_ruby_violates_contract_m():
    with pytest.raises(markup.MarkupError):
        markup.parse_inline('<r=mowang></r>王')
    with pytest.raises(markup.MarkupError):
        markup.parse_inline('背靠背<r=a></r><r=b></r>不行')


def _corpus_strings():
    """_beats 侧车里所有会流经 ruby_html/_inline 的字符串。"""
    for path in sorted(glob.glob(os.path.join(BEATS, '**', '*.json'), recursive=True)):
        d = json.load(open(path, encoding='utf-8'))
        for b in d['beats']:
            k = b['k']
            if k in ('talk', 'bubble'):
                yield path, b['text']
            elif k == 'choice':
                yield path, b['prompt'] or ''
                for t, desc, _ev in b['options']:
                    yield path, t
                    yield path, desc or ''
            elif k == 'merge':
                for s in b['silent']:
                    yield path, s
        for ln in d['info']:
            yield path, ln
        if d['recap']:
            yield path, d['recap']
        a = d.get('appendix')
        if a:
            yield path, a['note']
            yield path, a['prose']


def test_full_corpus_roundtrip_and_html_oracle():
    """全语料钉死：507 个侧车里每个字符串 md 往返恒等、HTML 与 oracle 一致。

    这条测试取代了 Phase 2a 的一次性对拍脚本，把「markup 编译器 == 被删除的
    md2html 行为」变成常设回归门（站点能建成本身就证明语料无契约 M 违例，
    parse_inline 在此不会抛）。
    """
    n = 0
    for path, s in _corpus_strings():
        n += 1
        nodes = markup.parse_inline(s)
        assert markup.serialize_md(nodes) == s, path
        assert markup.serialize_html(nodes) == oracle_ruby_html(s), path
    assert n > 40000  # 口径基线 48418 台词行 + 选项/信息/概要等
