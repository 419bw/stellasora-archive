# -*- coding: utf-8 -*-
"""管线 Stage 1b: Lua 语法分析器（递归下降 → T(list) AST，带 SourcePos）。

与重构前 build_story.py 的 T/LuaReader/parse_lua 逐行为等价（以 git 4496bd1 为基准，
588 Config + AvgCharacter 预设全量对拍验证）：
- T 为 list 子类：positional items 存于 list 本体，key=value 存于 .pairs；
- parse_lua(text) 返回文件中第一个值（跳过前导 return），通常是根表 T；
- 表内键识别 = IDENT + '='（词法层排除 '=='）；分隔符 ',' 或 ';' 各吞一个；
- true/false/nil → True/False/None；裸标识符按旧行为返回字符串本身；
  字符串与数字已在词法层完成反转义/转型。

在等价之上仅做增强（语料实测零出现，字节不变，对拍记录见 .tmp_verify）：
- 词法层接受单引号串、长字符串 [[..]]/[=[..]=]、块注释、\\ddd 与 \\xNN 转义；
- 键与 '=' 之间允许跨行/注释（旧实现仅允许空格与制表符）；
- 每个 T 附 .pos 属性（SourcePos，不进入 list/pairs 内容）；
- LuaError 消息带 stem+行+列；词法错误 LuaLexError 统一包装为 LuaError 抛出。
"""
from __future__ import annotations

from .lua_lexer import LuaLexError, SourcePos, Token, tokenize


class LuaError(ValueError):
    """Lua 语法/词法错误（含位置信息）。"""


class T(list):
    """A Lua table: positional items plus any key = value pairs.

    与旧 build_story.T 完全同构；.pos 为增强属性（SourcePos 或 None），
    不参与相等比较与序列化。
    """

    def __init__(self, items=(), pairs=None):
        super().__init__(items)
        self.pairs = pairs or {}
        self.pos: SourcePos | None = None

    def get(self, key, default=None):
        return self.pairs.get(key, default)

    def text(self, i=0):
        return self[i] if i < len(self) and isinstance(self[i], str) else ""


class _Parser:
    def __init__(self, tokens: list, stem: str | None):
        self._tokens = tokens
        self._stem = stem
        self._i = 0

    # ---- 基础游标 ----
    def _peek(self) -> Token:
        return self._tokens[self._i]

    def _advance(self) -> Token:
        t = self._tokens[self._i]
        if self._i < len(self._tokens) - 1:
            self._i += 1
        return t

    def _at(self, kind: str) -> bool:
        return self._peek().kind == kind

    # ---- 值 ----
    def _value(self):
        """对应旧 LuaReader.parse()：处理 {、return 前缀与标量。"""
        if self._at('{'):
            return self._table()
        t = self._peek()
        if t.kind == 'ident' and t.value == 'return':
            self._advance()
            return self._value()
        return self._scalar()

    def _scalar(self):
        """对应旧 LuaReader.value() 的非表分支（值已由词法层反转义/转型）。"""
        t = self._peek()
        if t.kind in ('string', 'number'):
            self._advance()
            return t.value
        if t.kind == 'ident':
            self._advance()
            return {'true': True, 'false': False, 'nil': None}.get(t.value, t.value)
        raise LuaError('bad value %r at %s' % (t.value, t.pos))

    def _table(self) -> T:
        """对应旧 LuaReader.table()：返回 T(items, pairs)。"""
        open_tok = self._advance()  # '{'
        items: list = []
        pairs: dict = {}
        while True:
            if self._at('eof'):
                raise LuaError('unterminated table at %s' % open_tok.pos)
            if self._at('}'):
                self._advance()
                break
            key = None
            if self._at('ident') and self._tokens[self._i + 1].kind == '=':
                key = self._advance().value
                self._advance()  # '='
            v = self._value()
            if key is not None:
                pairs[key] = v
            else:
                items.append(v)
            if self._at(',') or self._at(';'):
                self._advance()
        tbl = T(items, pairs)
        tbl.pos = open_tok.pos
        return tbl

    def parse(self):
        """对应旧 LuaReader.parse() 的文件级入口：第一个值即结果。"""
        if self._at('eof'):
            raise LuaError('unexpected end at %s' % (self._stem or '<text>'))
        return self._value()


def parse_lua(text: str, stem: str | None = None):
    """解析 Lua 文本，返回文件中第一个值（跳过前导 return）——与旧 parse_lua 一致。"""
    try:
        tokens = tokenize(text, stem)
    except LuaLexError as e:
        raise LuaError(str(e)) from e
    return _Parser(tokens, stem).parse()
