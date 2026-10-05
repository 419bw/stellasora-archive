# -*- coding: utf-8 -*-
"""管线 Stage 3d: markup 编译器 —— 行内标记的解析与双后端序列化。

游戏文本经 clean_dialogue 清洗后保留两类行内标记：

    ruby 注音，两种形式：
    空体形式  魔<r=mowang></r>王      注音画在插入点前一个字符上（客户端
                                      锚定语义），全库 2694 处；
    带体形式  <r=亲亲>接吻</r>        注音画在标签体内的文字上，base 可多字
                                      （交换注音/着重号等排版），全库 149 处，
                                      Phase 4a 起不再被静默剥掉。
    强调标记（Phase 4b）：
    <b>/<i>                           语义强调（着重/斜体），clean_dialogue
                                      已做栈配对过滤——进入本模块的文本里
                                      不会出现孤儿/交叉标记；md 后端原样
                                      保留，HTML 后端映射 <b class="emph">/
                                      <i class="emph">（原生粗体/斜体渲染，
                                      class 作样式钩子）。

本模块把它编译成结构化节点序列，两个后端各配一个序列化器：

    parse_inline(text)    -> [('text', s) | ('ruby', base, note)
                              | ('ruby_body', base, note) | ('tag', t), ...]
    serialize_md(nodes)   -> 原文逐字节还原（ruby 双形式、tag 各复原原样）。
                             Markdown 后端（render_md）生产上是直写原文的
                             pass-through，本序列化器即该行为的形式模型，
                             由 tests/story/test_markup.py 对全语料钉死往返。
    serialize_html(nodes) -> HTML 转义文本 + 原生 <ruby><rt>（base 可多字）
                             + <b class="emph">/<i class="emph">，站点后端
                             scripts/site/render_html.py 消费。

契约 M：空体 ruby 必有前置字符。前导空体 ruby / 背靠背空体 ruby（base
缺失）是上游数据违约，parse_inline 抛 MarkupError —— 契约校验会先于渲染
拦下它。带体 ruby 自带 base，行首/相邻均合法；但「带体 ruby 紧接空体
ruby」会让空体失去可锚定字符（base 已被带体节点占有），同样抛 MarkupError
（语料 0 处，防御性契约）。强调标签不是字符，不能充当 ruby 锚点：
<b> 后紧跟空体 ruby 同样抛 MarkupError（语料 0 处，防御性契约）。
"""
import re
from html import escape

# 带体分支在前：`<r=a></r>` 不会被它误吞（体要求至少一个非尖括号字符）。
INLINE = re.compile(r'<r=([^<>]*)>([^<>]+)</r>|<r=([^<>]*)></r>|(</?[bi]>)')
RUBY = re.compile(r'<r=([^<>]*)></r>')

EMPH_HTML = {'<b>': '<b class="emph">', '</b>': '</b>',
             '<i>': '<i class="emph">', '</i>': '</i>'}


class MarkupError(ValueError):
    """违反语料契约的行内标记（如没有 base 字符的空体 ruby）。"""


def parse_inline(text):
    """text -> 节点序列。

    text 节点为非标记文本段；ruby 节点 (base, note) 为空体形式（base 是
    标签前一个字符）；ruby_body 节点 (base, note) 为带体形式（base 是
    标签体内文字，可多字）；tag 节点为原样的 <b>/</b>/<i>/</i>。
    """
    nodes = []
    buf = ''
    pos = 0
    for m in INLINE.finditer(text):
        buf += text[pos:m.start()]
        pos = m.end()
        if m.group(4) is not None:          # 强调标记 <b>/</b>/<i>/</i>
            if buf:
                nodes.append(('text', buf))
                buf = ''
            nodes.append(('tag', m.group(4)))
        elif m.group(2) is not None:        # 带体 <r=note>base</r>
            if buf:
                nodes.append(('text', buf))
                buf = ''
            nodes.append(('ruby_body', m.group(2), m.group(1)))
        else:                               # 空体 <r=note></r>，锚定前一字符
            if not buf:
                raise MarkupError('ruby 没有可锚定的前置字符: %r' % text)
            if buf[:-1]:
                nodes.append(('text', buf[:-1]))
            nodes.append(('ruby', buf[-1], m.group(3)))
            buf = ''
    buf += text[pos:]
    if buf:
        nodes.append(('text', buf))
    return nodes


def serialize_md(nodes):
    """节点序列 -> 原文逐字节还原（Markdown 后端 pass-through 的形式模型）。"""
    out = []
    for n in nodes:
        if n[0] == 'text':
            out.append(n[1])
        elif n[0] == 'ruby':
            out.append('%s<r=%s></r>' % (n[1], n[2]))
        elif n[0] == 'ruby_body':
            out.append('<r=%s>%s</r>' % (n[2], n[1]))
        else:
            out.append(n[1])
    return ''.join(out)


def serialize_html(nodes):
    """节点序列 -> HTML 片段：转义文本 + 原生 <ruby><rt>（base 可多字）
    + <b class="emph">/<i class="emph">。"""
    out = []
    for n in nodes:
        if n[0] == 'text':
            out.append(escape(n[1]))
        elif n[0] == 'tag':
            out.append(EMPH_HTML[n[1]])
        else:
            out.append('<ruby>%s<rt>%s</rt></ruby>' % (escape(n[1]), escape(n[2])))
    return ''.join(out)
