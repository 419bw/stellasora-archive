# -*- coding: utf-8 -*-
"""Tokenize Lua data, retaining source positions and decoding string escapes."""
import re
from collections import namedtuple

Token = namedtuple('Token', ('kind', 'value', 'pos'))
# kind: '{' '}' ',' ';' '=' 'string' 'number' 'ident' 'eof'


class SourcePos:
    """Token 在源文件中的位置（stem 为剧本代号，可空）。"""
    __slots__ = ('stem', 'offset', 'line', 'col')

    def __init__(self, stem, offset, line, col):
        self.stem = stem
        self.offset = offset
        self.line = line
        self.col = col

    def __str__(self):
        return '%s line %d col %d' % (self.stem or '<text>', self.line, self.col)

    def __repr__(self):
        return 'SourcePos(%s)' % self


class LuaLexError(Exception):
    def __init__(self, msg, pos=None):
        super().__init__('%s at %s' % (msg, pos) if pos else msg)
        self.pos = pos


_IDENT = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
_NUM = re.compile(r'-?\d+(?:\.\d+)?')
_LONG_OPEN = re.compile(r'\[(=*)\[')
_ESCAPES = {'n': '\n', 't': '\t', '"': '"', "'": "'", '\\': '\\'}
_DEC = re.compile(r'\d{1,3}')
_HEX = re.compile(r'[0-9A-Fa-f]{2}')


def tokenize(text, stem=None):
    """整段源文本 → [Token]，末尾恒为 eof token。"""
    toks = []
    n = len(text)
    i = 0
    line = 1
    col = 1

    def pos(off=None, ln=None, c=None):
        return SourcePos(stem, off if off is not None else i,
                         ln if ln is not None else line,
                         c if c is not None else col)

    def bump(k):
        """前进 k 个字符（调用方保证区间内无换行时可用简单列加）。"""
        nonlocal i, line, col
        seg = text[i:i + k]
        nl = seg.count('\n')
        if nl:
            line += nl
            col = k - seg.rfind('\n')
        else:
            col += k
        i += k

    def read_long(i0, line0, col0):
        """i0 指向 '['：读长字符串/长注释体。返回 (content, 末尾下标, line, col)。"""
        m = _LONG_OPEN.match(text, i0)
        if not m:
            return None
        close = ']' + m.group(1) + ']'
        start = m.end()
        end = text.find(close, start)
        if end < 0:
            raise LuaLexError('unterminated long string/comment',
                              SourcePos(stem, i0, line0, col0))
        content = text[start:end]
        if content.startswith('\r\n'):
            content = content[2:]
        elif content[:1] in ('\n', '\r'):
            content = content[1:]
        stop = end + len(close)
        seg = text[i0:stop]
        nl = seg.count('\n')
        nline = line0 + nl
        ncol = (len(seg) - seg.rfind('\n')) if nl else col0 + len(seg)
        return content, stop, nline, ncol

    def read_quote(q, i0, line0, col0):
        """i0 指向开引号：读短字符串。返回 (value, 末尾下标, line, col)。"""
        out = []
        j = i0 + 1
        ln, c = line0, col0 + 1
        while True:
            if j >= n:
                raise LuaLexError('unterminated string',
                                  SourcePos(stem, i0, line0, col0))
            ch = text[j]
            if ch == '\\':
                if j + 1 >= n:
                    raise LuaLexError('unterminated string',
                                      SourcePos(stem, i0, line0, col0))
                e = text[j + 1]
                if e in _ESCAPES:
                    out.append(_ESCAPES[e])
                    j += 2
                    c += 2
                elif e == '\n':                     # 反斜杠续行
                    out.append('\n')
                    j += 2
                    ln += 1
                    c = 1
                elif e.isdigit():                   # \ddd
                    m = _DEC.match(text, j + 1)
                    v = int(m.group(0))
                    if v > 255:
                        raise LuaLexError('decimal escape too large: \\%s' % m.group(0),
                                          SourcePos(stem, j, ln, c))
                    out.append(chr(v))
                    j = m.end()
                    c += 1 + len(m.group(0))
                elif e == 'x':                      # \xNN
                    m = _HEX.match(text, j + 2)
                    if not m:
                        raise LuaLexError('invalid \\x escape',
                                          SourcePos(stem, j, ln, c))
                    out.append(chr(int(m.group(0), 16)))
                    j += 4
                    c += 4
                else:                               # 其余 \c 取字面 c（与原实现一致）
                    out.append(e)
                    j += 2
                    c += 2
                continue
            if ch == q:
                return ''.join(out), j + 1, ln, c + 1
            if ch == '\n':
                # 原实现允许字符串内含裸换行（不报错），保持一致
                out.append(ch)
                j += 1
                ln += 1
                c = 1
                continue
            out.append(ch)
            j += 1
            c += 1

    while i < n:
        c0 = text[i]
        if c0 in ' \t\r':
            bump(1)
            continue
        if c0 == '\n':
            bump(1)
            continue
        if c0 == '-' and text.startswith('--', i):
            p0 = pos()
            r = read_long(i + 2, line, col + 2)
            if r is not None:                       # 块注释 --[[ ... ]]
                _content, stop, nline, ncol = r
                i, line, col = stop, nline, ncol
                continue
            nl = text.find('\n', i)                 # 行注释
            stop = n if nl < 0 else nl + 1
            bump(stop - i)
            del p0
            continue
        if c0 == '{':
            toks.append(Token('{', '{', pos()))
            bump(1)
            continue
        if c0 == '}':
            toks.append(Token('}', '}', pos()))
            bump(1)
            continue
        if c0 == ',':
            toks.append(Token(',', ',', pos()))
            bump(1)
            continue
        if c0 == ']':
            toks.append(Token(']', ']', pos()))
            bump(1)
            continue
        if c0 == ';':
            toks.append(Token(';', ';', pos()))
            bump(1)
            continue
        if c0 == '=' and not text.startswith('==', i):
            toks.append(Token('=', '=', pos()))
            bump(1)
            continue
        if c0 in '"\'':
            p0 = pos()
            v, stop, nline, ncol = read_quote(c0, i, line, col)
            toks.append(Token('string', v, p0))
            i, line, col = stop, nline, ncol
            continue
        if c0 == '[':
            p0 = pos()
            r = read_long(i, line, col)
            if r is None:
                toks.append(Token('[', '[', p0))
                bump(1)
                continue
            v, stop, nline, ncol = r
            toks.append(Token('string', v, p0))
            i, line, col = stop, nline, ncol
            continue
        m = _NUM.match(text, i)
        if m and not (c0 == '-' and m.group(0) == '-'):
            t = m.group(0)
            toks.append(Token('number', float(t) if '.' in t else int(t), pos()))
            bump(len(t))
            continue
        m = _IDENT.match(text, i)
        if m:
            toks.append(Token('ident', m.group(0), pos()))
            bump(m.end() - i)
            continue
        raise LuaLexError('unexpected character %r' % c0, pos())

    toks.append(Token('eof', None, pos()))
    return toks
