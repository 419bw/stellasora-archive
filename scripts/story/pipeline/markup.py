# -*- coding: utf-8 -*-
"""管线 Stage 3d: markup 编译器 —— 行内标记的解析与双后端序列化。

游戏文本经 clean_dialogue 清洗后仅保留一种行内标记：<r=注音></r>（客户端
ruby 注音，全库 2694 处）。本模块把它编译成结构化节点序列，两个后端各配
一个序列化器，取代原先散落在渲染层的正则替换：

    parse_inline(text)    -> [('text', s) | ('ruby', base, note), ...]
    serialize_md(nodes)   -> 原文逐字节还原（ruby 复原为 <r=note></r>）。
                             Markdown 后端（render_md）生产上是直写原文的
                             pass-through，本序列化器即该行为的形式模型，
                             由 tests/story/test_markup.py 对全语料钉死往返。
    serialize_html(nodes) -> HTML 转义文本 + 原生 <ruby><rt>，与被删除的
                             md2html.ruby_html 逐字节一致；站点后端
                             scripts/site/render_html.py 消费。

ruby 的锚定语义（与客户端渲染一致）：注音画在插入点前一个字符上，即
魔<r=mowang></r>王 读作「魔(mowang)王」——base 字符归 ruby 节点所有。

契约 M：ruby 标签必有前置字符。前导 ruby / 背靠背 ruby（base 缺失）是
上游数据违约，parse_inline 抛 MarkupError —— 契约校验会先于渲染拦下它。
"""
import re
from html import escape

RUBY = re.compile(r'<r=([^<>]*)></r>')


class MarkupError(ValueError):
    """违反语料契约的行内标记（如没有 base 字符的 ruby）。"""


def parse_inline(text):
    """text -> 节点序列。text 节点为非标记文本段，ruby 节点为 (base, note)。"""
    parts = RUBY.split(text)
    nodes = []
    for i in range(0, len(parts), 2):
        plain = parts[i]
        if i + 1 >= len(parts):                 # 尾段，无后续注音
            if plain:
                nodes.append(('text', plain))
            break
        note = parts[i + 1]
        if not plain:
            raise MarkupError('ruby 没有可锚定的前置字符: %r' % text)
        if plain[:-1]:
            nodes.append(('text', plain[:-1]))
        nodes.append(('ruby', plain[-1], note))
    return nodes


def serialize_md(nodes):
    """节点序列 -> 原文逐字节还原（Markdown 后端 pass-through 的形式模型）。"""
    out = []
    for n in nodes:
        if n[0] == 'text':
            out.append(n[1])
        else:
            out.append('%s<r=%s></r>' % (n[1], n[2]))
    return ''.join(out)


def serialize_html(nodes):
    """节点序列 -> HTML 片段：转义文本 + 原生 <ruby><rt>。"""
    out = []
    for n in nodes:
        if n[0] == 'text':
            out.append(escape(n[1]))
        else:
            out.append('<ruby>%s<rt>%s</rt></ruby>' % (escape(n[1]), escape(n[2])))
    return ''.join(out)
