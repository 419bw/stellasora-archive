# -*- coding: utf-8 -*-
"""Inline text round trips, ruby anchors and corpus rendering."""
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

# Independent HTML projection of empty ruby markers.
ORACLE_RUBY = re.compile(r'<r=([^<>]*)></r>')
BODY_RUBY = re.compile(r'<r=[^<>]*>[^<>]+</r>')


def oracle_ruby_html(text):
    parts = ORACLE_RUBY.split(text)
    out = []
    for i in range(0, len(parts), 2):
        out.append(escape(parts[i]).replace('&lt;br&gt;', '<br>'))
        if i + 1 < len(parts):
            out.append('<ruby class="ruby-point"><rt>%s</rt></ruby>' % escape(parts[i + 1]))
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

# 原文样本：读音、交换注音和逐字着重号。
BODY_CASES = [
    '<r=Bo>魔</r>、魔<r=BOSS></r>王，你、你怎么在这里？！',
    '既然<r=亲亲>接吻</r>是“无需言语就能传递心意的方式”',
    '<r=·>非</r><r=·>常</r><r=·>规</r>',
    '妾身却仍是<r=不完整的刀>半人?</r>。',
    '行首带体<r=x>字</r>与空体混排<r=y></r>结束',
    '转义<r=a&b>base</r>与特殊字符',
    'note 含尖括号不成立<r=<&>x</r>按纯文本往返',
]

# 原样解析的强调标签在 Markdown 中保持原文。
EMPH_CASES = [
    '既然<b>我们目标一致</b>，就好好准备吧。',
    '<i><b>Y</b></i> 嵌套排版帧',
    '字<b>粗<i>粗斜</i>仍粗</b>尾',
    '孤儿</b>与<b>未闭合也照原样往返',
    '强调内 ruby：字<b>粗<r=x></r>仍粗</b>',
]


@pytest.mark.parametrize('text', CASES + BODY_CASES + EMPH_CASES)
def test_md_roundtrip_is_identity(text):
    assert markup.serialize_md(markup.parse_inline(text)) == text


@pytest.mark.parametrize('text', CASES)
def test_html_preserves_ruby_insertion_points(text):
    assert markup.serialize_html(markup.parse_inline(text)) == oracle_ruby_html(text)


@pytest.mark.parametrize('text', CASES)
def test_render_html_ruby_html_delegates(text):
    assert render_html.ruby_html(text) == oracle_ruby_html(text)


def test_ruby_anchor_semantics():
    nodes = markup.parse_inline('魔<r=mowang></r>王')
    assert nodes == [('text', '魔'), ('ruby', '', 'mowang'), ('text', '王')]
    assert markup.serialize_html(nodes) == '魔<ruby class="ruby-point"><rt>mowang</rt></ruby>王'
    assert markup.serialize_md(nodes) == '魔<r=mowang></r>王'


def test_bodied_ruby_semantics():
    """带体 ruby：base 在标签内、可多字；md 原样还原，HTML 原生 <ruby>。"""
    nodes = markup.parse_inline('既然<r=亲亲>接吻</r>是')
    assert nodes == [('text', '既然'), ('ruby_body', '接吻', '亲亲'), ('text', '是')]
    assert markup.serialize_md(nodes) == '既然<r=亲亲>接吻</r>是'
    assert markup.serialize_html(nodes) == (
        '既然<ruby>接吻<rt>亲亲</rt></ruby>是')
    # 逐字着重号各自标注标签内的字。
    nodes = markup.parse_inline('<r=·>非</r><r=·>常</r>')
    assert nodes == [('ruby_body', '非', '·'), ('ruby_body', '常', '·')]
    assert markup.serialize_md(nodes) == '<r=·>非</r><r=·>常</r>'
    # base/note 里的 HTML 敏感字符照旧转义（note 不含尖括号才构成标记）
    assert markup.serialize_html(markup.parse_inline('转义<r=a&b>base</r>!')) == (
        '转义<ruby>base<rt>a&amp;b</rt></ruby>!')


def test_html_escapes_base_and_note():
    nodes = markup.parse_inline('<&<r=ab></r>尾')
    assert nodes == [('text', '<&'), ('ruby', '', 'ab'), ('text', '尾')]
    assert markup.serialize_html(nodes) == (
        '&lt;&amp;<ruby class="ruby-point"><rt>ab</rt></ruby>尾')
    assert render_html.ruby_html('<r=a>b</r>') == '<ruby>b<rt>a</rt></ruby>'


def test_empty_ruby_preserves_its_insertion_point():
    for text in ('<r=x></r>字', '字<r=a></r><r=b></r>', '<r=a>字</r><r=b></r>'):
        nodes = markup.parse_inline(text)
        assert markup.serialize_md(nodes) == text
        assert all(n[1] == '' for n in nodes if n[0] == 'ruby')


def test_emph_html_mapping():
    """Render emphasis and nested ruby without changing text."""
    nodes = markup.parse_inline('既然<b>我们目标一致</b>，走吧')
    assert nodes == [('text', '既然'), ('tag', '<b>'), ('text', '我们目标一致'),
                     ('tag', '</b>'), ('text', '，走吧')]
    assert markup.serialize_md(nodes) == '既然<b>我们目标一致</b>，走吧'
    assert markup.serialize_html(nodes) == (
        '既然<b class="emph">我们目标一致</b>，走吧')
    assert markup.serialize_html(markup.parse_inline('<i><b>Y</b></i>')) == (
        '<i class="emph"><b class="emph">Y</b></i>')
    assert markup.serialize_html(markup.parse_inline('字<b>粗<r=x></r>仍粗</b>')) == (
        '字<b class="emph">粗<ruby class="ruby-point"><rt>x</rt></ruby>仍粗</b>')
    assert render_html.ruby_html('既然<b>目标</b>一致') == (
        '既然<b class="emph">目标</b>一致')


def _corpus_strings():
    """_beats 侧车里所有会流经 ruby_html/_inline 的字符串。"""
    for path in sorted(glob.glob(os.path.join(BEATS, '**', '*.json'), recursive=True)):
        d = markup.project(json.load(open(path, encoding='utf-8')))
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
    """Check every published text retains its markup and annotation count."""
    emph = re.compile(r'</?[bi]>')
    n = n_body = n_emph = 0
    for path, s in _corpus_strings():
        n += 1
        s = s.replace('\n', '<br>')
        nodes = markup.parse_inline(s)
        assert markup.serialize_md(nodes) == s, path
        has_body = bool(BODY_RUBY.search(s))
        has_emph = bool(emph.search(s))
        if has_body or has_emph:
            n_body += has_body
            n_emph += has_emph
            html = markup.serialize_html(nodes)
            assert html.count('<ruby') == sum(
                1 for x in nodes if x[0] in ('ruby', 'ruby_body')), path
            assert html.count(' class="emph">') == sum(
                1 for x in nodes if x[0] == 'tag' and x[1] in ('<b>', '<i>')), path
            assert '<r=' not in html and '</r>' not in html, path
        else:
            assert markup.serialize_html(nodes) == oracle_ruby_html(s), path
    assert n > 40000
    assert n_body >= 50
    assert n_emph >= 1


def test_storage_keeps_text_readable():
    compiler = markup.TextCompiler({'==SEX1==': ['她', '他']})
    assert markup.encode_text(compiler.compile('魔<r=BOSS></r>王==RT==来了')) == \
        '魔<r=BOSS></r>王\n来了'
    assert markup.encode_text(compiler.compile('==SEX1==来了')) == \
        {'cn_f': '她来了', 'cn_m': '他来了'}


def test_stored_variants_preserve_projections():
    text = markup.TextCompiler({'==SEX1==': ['她', '他']}).compile(
        '==SEX1==叫魔<r=BOSS></r>王==RT==来了', '男主文案\n第二行', '<b>日文女</b>==RT==第二行', '日文男')
    stored = markup.encode_text(text)
    restored = markup.decode_text(json.loads(json.dumps(stored)))
    assert all(isinstance(value, str) for value in stored.values())
    assert markup.html(text) == markup.html(restored)
    assert markup.alternatives(text) == markup.alternatives(restored)
    for sex in ('female', 'male'):
        assert markup.markdown(text, sex) == markup.markdown(restored, sex)
