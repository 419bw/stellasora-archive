# -*- coding: utf-8 -*-
"""Parse Lua data tables with positional, named and bracketed scalar keys."""
from __future__ import annotations

from .lua_lexer import LuaLexError, SourcePos, Token, tokenize


class LuaError(ValueError):
    """Lua 语法/词法错误（含位置信息）。"""


class T(list):
    """Lua table items, keyed values and source position."""

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
    def _expect(self, kind):
        token = self._advance()
        if token.kind != kind:
            raise LuaError('expected %s at %s' % (kind, token.pos))

    def _value(self):
        """Read a table or scalar value, accepting a leading return."""
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
            elif self._at('['):
                self._advance()
                key = self._scalar()
                self._expect(']')
                self._expect('=')
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
