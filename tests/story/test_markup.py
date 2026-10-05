# -*- coding: utf-8 -*-
"""Unit tests for scripts/story/pipeline/markup.py（markup 编译器，Phase 3/4a）.

Pins four guarantees:
  1. serialize_md(parse_inline(t)) == t          —— Markdown 后端 pass-through 的
     形式模型对任意输入逐字节还原（含全语料、含带体 ruby）；
  2. serialize_html(parse_inline(t)) == oracle   —— 对不含带体 ruby 的文本，HTML
     输出与被删除的 md2html.ruby_html 原实现（下方逐字复刻的 oracle）逐字节
     一致；带体 ruby 是 Phase 4a 的有意行为变更（oracle 把它当纯文本转义，
     新实现渲染成 <ruby>base<rt>），只对其断言新行为；
  3. 契约 M 违例（空体 ruby 无可锚定的前置字符，含「带体紧接空体」）抛
     MarkupError，而不是渲染出错位的注音；
  4. 带体 ruby <r=note>base</r> 的 base 可多字，双端各自还原/渲染。
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
BODY_RUBY = re.compile(r'<r=[^<>]*>[^<>]+</r>')


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

# 带体 ruby（Phase 4a）：base 在标签体内、可多字。语料三形态：
# 读音注音（CG_117_01）、交换注音（CG_144_02/STm07_09）、逐字着重号（STm05 系）。
BODY_CASES = [
    '<r=Bo>魔</r>、魔<r=BOSS></r>王，你、你怎么在这里？！',
    '既然<r=亲亲>接吻</r>是“无需言语就能传递心意的方式”',
    '<r=·>非</r><r=·>常</r><r=·>规</r>',
    '妾身却仍是<r=不完整的刀>半人?</r>。',
    '行首带体<r=x>字</r>与空体混排<r=y></r>结束',
    '转义<r=a&b>base</r>与特殊字符',
    'note 含尖括号不成立<r=<&>x</r>按纯文本往返',
]


@pytest.mark.parametrize('text', CASES + BODY_CASES)
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


def test_bodied_ruby_semantics():
    """带体 ruby：base 在标签内、可多字；md 原样还原，HTML 原生 <ruby>。"""
    nodes = markup.parse_inline('既然<r=亲亲>接吻</r>是')
    assert nodes == [('text', '既然'), ('ruby_body', '接吻', '亲亲'), ('text', '是')]
    assert markup.serialize_md(nodes) == '既然<r=亲亲>接吻</r>是'
    assert markup.serialize_html(nodes) == (
        '既然<ruby>接吻<rt>亲亲</rt></ruby>是')
    # 逐字着重号：体体相邻合法（各自带 base，不触发契约 M）
    nodes = markup.parse_inline('<r=·>非</r><r=·>常</r>')
    assert nodes == [('ruby_body', '非', '·'), ('ruby_body', '常', '·')]
    assert markup.serialize_md(nodes) == '<r=·>非</r><r=·>常</r>'
    # base/note 里的 HTML 敏感字符照旧转义（note 不含尖括号才构成标记）
    assert markup.serialize_html(markup.parse_inline('转义<r=a&b>base</r>!')) == (
        '转义<ruby>base<rt>a&amp;b</rt></ruby>!')


def test_html_escapes_base_and_note():
    nodes = markup.parse_inline('<&<r=ab></r>尾')
    assert nodes == [('text', '<'), ('ruby', '&', 'ab'), ('text', '尾')]
    assert markup.serialize_html(nodes) == (
        '&lt;<ruby>&amp;<rt>ab</rt></ruby>尾')
    # Phase 4a：带体形式不再按纯文本转义，而是渲染为原生 ruby
    assert render_html.ruby_html('<r=a>b</r>') == '<ruby>b<rt>a</rt></ruby>'


def test_leading_ruby_violates_contract_m():
    with pytest.raises(markup.MarkupError):
        markup.parse_inline('<r=mowang></r>王')
    with pytest.raises(markup.MarkupError):
        markup.parse_inline('背靠背<r=a></r><r=b></r>不行')
    # 带体自带 base，行首合法；但它会占有前文，紧跟的空体失去锚点 → 契约 M
    assert markup.parse_inline('<r=a>字</r>合法') == [('ruby_body', '字', 'a'), ('text', '合法')]
    with pytest.raises(markup.MarkupError):
        markup.parse_inline('<r=a>字</r><r=b></r>空体没有前置字符')


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
    """全语料钉死：507 个侧车里每个字符串 md 往返恒等；不含带体 ruby 的
    字符串 HTML 与 oracle 一致（Phase 3 行为永久回归门），含带体 ruby 的
    字符串按 Phase 4a 新行为渲染（往返恒等 + 带体标记数与 <ruby> 数对账）。

    站点能建成本身就证明语料无契约 M 违例，parse_inline 在此不会抛。
    """
    n = n_body = 0
    for path, s in _corpus_strings():
        n += 1
        nodes = markup.parse_inline(s)
        assert markup.serialize_md(nodes) == s, path
        if BODY_RUBY.search(s):
            n_body += 1
            html = markup.serialize_html(nodes)
            assert html.count('<ruby>') == sum(
                1 for x in nodes if x[0] in ('ruby', 'ruby_body')), path
            assert '<r=' not in html and '</r>' not in html, path
        else:
            assert markup.serialize_html(nodes) == oracle_ruby_html(s), path
    assert n > 40000  # 口径基线 48418 台词行 + 选项/信息/概要等
    # 带体 ruby：Lua 源 149 处，折叠/去挂载后语料里 59 个字符串、144 次出现
    # （与 validate_story M 契约的全树注音增量 2838-2694=144 精确对账）。
    assert n_body >= 50
