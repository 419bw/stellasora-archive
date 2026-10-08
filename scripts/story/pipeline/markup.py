# -*- coding: utf-8 -*-
"""Inline syntax, localized story text, and Markdown/HTML projections."""
import json
import logging
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path

from .domain import PROTAG_NAME
from .lua_parser import parse_lua

INLINE = re.compile(
    r'<r=(?P<ruby_note>[^<>]*)>(?P<ruby_base>[^<>]*)</r>'
    r'|(?P<emphasis></?[bi]>)|(?P<tag><[^<>]*>)'
    r'|(?P<control>==[^=\r\n]+==)|(?P<nonlog>_NOT_IN_LOG_)')
STYLE = re.compile(
    r'</?(?:color|size|align|margin|margin-left|margin-right|alpha|voffset|rotate'
    r'|sprite|space|mspace|indent|line-height|cspace)(?:[= >])')
CONTROL = re.compile(r'==(?:P|B|W|Off|A-?\d+(?:\.\d+)?)==')
EMPH_HTML = {'<b>': '<b class="emph">', '</b>': '</b>',
             '<i>': '<i class="emph">', '</i>': '</i>'}
VERSION_KEYS = ('cn_f', 'cn_m', 'jp_f', 'jp_m')
VERSION_LABELS = {'cn_f': '中文女', 'cn_m': '中文男', 'jp_f': '日文女', 'jp_m': '日文男'}


logger = logging.getLogger(__name__)


def parse_inline(text, *, game=False, presets=None, diagnostics=None):
    """Parse ruby, emphasis and game markers into inline nodes."""
    if game:
        text = re.sub(r'\$\d{4}', lambda m: presets.words.get(m[0][1:], m[0]), text)
    nodes, buf = [], ''
    pos = 0
    for m in INLINE.finditer(text):
        buf += text[pos:m.start()]
        pos = m.end()
        if m['ruby_note'] is not None:
            if buf:
                nodes.append(('text', buf))
                buf = ''
            base = m['ruby_base']
            nodes.append(('ruby_body' if base else 'ruby', base, m['ruby_note']))
        elif m['emphasis']:
            if buf:
                nodes.append(('text', buf))
                buf = ''
            nodes.append(('tag', m['emphasis']))
        elif m['tag'] == '<br>':
            buf += '\n'
        elif game and m['tag'] and STYLE.match(m['tag']):
            pass
        elif game and m['control']:
            token = m['control']
            if token == '==PLAYER_NAME==':
                buf += PROTAG_NAME
            elif token in presets.sex:
                if buf:
                    nodes.append(('text', buf))
                    buf = ''
                nodes.append(('sex', *presets.sex[token]))
            elif token == '==RT==':
                buf += '\n'
            elif CONTROL.fullmatch(token):
                pass
            else:
                buf += token
                logger.warning('未知标记 %s', token)
        elif game and m['nonlog']:
            pass
        else:
            buf += m[0]
    buf += text[pos:]
    if buf:
        nodes.append(('text', buf))
    if game:
        nodes = normalize_nodes(nodes, diagnostics)
    return nodes


def normalize_nodes(nodes, diagnostics):
    """Keep paired emphasis and merge adjacent text nodes."""
    stack, paired = [], set()
    for i, n in enumerate(nodes):
        if n[0] != 'tag':
            continue
        tag = n[1]
        if tag in ('<b>', '<i>'):
            stack.append((i, tag[1]))
        elif stack and stack[-1][1] == tag[2]:
            paired.add(stack.pop()[0])
            paired.add(i)
    if diagnostics is not None:
        diagnostics['paired'] += len(paired)
        diagnostics['orphan'] += sum(n[0] == 'tag' for n in nodes) - len(paired)
    out = []
    for i, n in enumerate(nodes):
        if n[0] == 'tag' and i not in paired:
            continue
        if n[0] == 'text':
            value = n[1]
            if out and out[-1][0] == 'text':
                value = out.pop()[1] + value
            out.append(('text', value))
        else:
            out.append(n)
    if out and out[0][0] == 'text':
        out[0] = ('text', out[0][1].lstrip())
    if out and out[-1][0] == 'text':
        out[-1] = ('text', out[-1][1].rstrip())
    return [n for n in out if n[0] != 'text' or n[1]]


def serialize_text(nodes, sex='female'):
    out = []
    for n in nodes:
        if n[0] in ('text', 'tag'):
            out.append(n[1])
        elif n[0] == 'sex':
            out.append(n[2] if sex == 'male' else n[1])
        elif n[0] == 'ruby':
            out.append('%s<r=%s></r>' % (n[1], n[2]))
        elif n[0] == 'ruby_body':
            out.append('<r=%s>%s</r>' % (n[2], n[1]))
    return ''.join(out)


def serialize_md(nodes, sex='female'):
    return serialize_text(nodes, sex).replace('\n', '<br>')


def serialize_html(nodes, sex='female'):
    out = []
    for n in nodes:
        if n[0] == 'text':
            out.append(escape(n[1]).replace('\n', '<br>'))
        elif n[0] == 'sex':
            out.append(escape(n[2] if sex == 'male' else n[1]))
        elif n[0] == 'tag':
            out.append(EMPH_HTML[n[1]])
        elif n[0] == 'ruby':
            out.append('<ruby class="ruby-point"><rt>%s</rt></ruby>' % escape(n[2]))
        else:
            out.append('<ruby>%s<rt>%s</rt></ruby>' % (escape(n[1]), escape(n[2])))
    return ''.join(out)


@dataclass
class Text:
    versions: dict

    def __bool__(self):
        return any(self.versions.values())

    def select(self, sex='female', voice='CN'):
        """Select a nonempty version using language and gender fallback."""
        keys = ['cn_f']
        male = sex == 'male'
        if male:
            keys.append('cn_m')
        if voice == 'JP':
            keys.append('jp_f')
            if male:
                keys.append('jp_m')
        return next((self.versions[k] for k in reversed(keys) if self.versions.get(k)), [])

    def render_versions(self, serialize):
        """Render source slots and gender substitutions as complete text variants."""
        rendered = {}
        for key in VERSION_KEYS:
            if self.versions.get(key):
                sex = 'male' if key.endswith('_m') else 'female'
                rendered[key] = serialize(self.versions[key], sex)
        for female, male in (('cn_f', 'cn_m'), ('jp_f', 'jp_m')):
            if female in rendered and male not in rendered:
                text = serialize(self.versions[female], 'male')
                if text != rendered[female]:
                    rendered[male] = text
        return {key: rendered[key] for key in VERSION_KEYS if key in rendered}

    def to_data(self):
        """Store a single Chinese text as a string, or variants as a flat map."""
        texts = self.render_versions(serialize_text)
        if not texts or list(texts) == ['cn_f']:
            return texts.get('cn_f', '')
        return texts


def decode_text(value):
    """Restore flat text-variant maps without loading game data."""
    if isinstance(value, dict):
        if any(key in value for key in VERSION_KEYS):
            return Text({key: parse_inline(value[key]) for key in VERSION_KEYS if key in value})
        return {k: decode_text(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decode_text(v) for v in value]
    return value


def encode_text(value):
    if isinstance(value, Text):
        return value.to_data()
    if isinstance(value, dict):
        return {k: encode_text(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [encode_text(v) for v in value]
    return value


def nodes_of(value, sex='female'):
    if isinstance(value, Text):
        return value.select(sex)
    return parse_inline(value)


def text(value, sex='female'):
    return serialize_text(nodes_of(value, sex), sex)


def markdown(value, sex='female'):
    return serialize_md(nodes_of(value, sex), sex)


def plain(value, sex='female'):
    return ''.join(n[2] if n[0] == 'sex' and sex == 'male' else n[1]
                   for n in nodes_of(value, sex) if n[0] != 'tag')


def html_versions(value):
    """Render nonempty source slots and gender differences within those slots."""
    if not isinstance(value, Text):
        return [('cn_f', serialize_html(parse_inline(value)))]
    return list(value.render_versions(serialize_html).items())


def html(value):
    """Render a native per-text selector for available source versions."""
    versions = html_versions(value)
    if len(versions) < 2:
        return versions[0][1] if versions else ''
    labels = VERSION_LABELS
    if all(key.startswith('cn_') for key, _ in versions):
        labels = {'cn_f': '女主', 'cn_m': '男主'}
    elif all(key.endswith('_f') for key, _ in versions):
        labels = {'cn_f': '中文', 'jp_f': '日语'}
    options = ''.join('<button type="button" data-version="%s" aria-pressed="%s">%s</button>' %
                      (key, 'false' if i else 'true', labels[key])
                      for i, (key, _) in enumerate(versions))
    contents = ''.join('<span data-text-version="%s"%s>%s</span>' %
                       (key, ' hidden' if i else '', text)
                       for i, (key, text) in enumerate(versions))
    return ('<span class="text-variants">'
            '<span class="text-variant-controls" role="group" aria-label="本句文案版本">%s</span>'
            '%s</span>') % (options, contents)


def alternatives(value):
    if isinstance(value, Text):
        return [(VERSION_LABELS[key], text)
                for key, text in value.render_versions(serialize_md).items() if key != 'cn_f']
    return []


class TextCompiler:
    """Own official word tables and compile all story text fields."""
    def __init__(self, sex, words=None):
        self.sex = sex
        self.words = words or {}
        self.diagnostics = {'paired': 0, 'orphan': 0}
        self._cache = {}

    @classmethod
    def load(cls, preset, binary, language):
        table = parse_lua(Path(preset, 'AvgUIText.lua').read_text(encoding='utf-8'))
        sex = {k: list(v) for k, v in table.get('SEX').pairs.items()}
        terms = json.loads(Path(binary, 'ContentWord.json').read_text(encoding='utf-8'))
        translated = json.loads(Path(language, 'ContentWord.json').read_text(encoding='utf-8'))
        return cls(sex, {key: translated[row['Word']] for key, row in terms.items()})

    def compile(self, cn_f='', cn_m='', jp_f='', jp_m=''):
        versions = {}
        for key, raw in zip(VERSION_KEYS, (cn_f, cn_m, jp_f, jp_m)):
            if raw:
                if raw not in self._cache:
                    self._cache[raw] = parse_inline(raw, game=True, presets=self,
                                                    diagnostics=self.diagnostics)
                versions[key] = self._cache[raw]
        return Text(versions)


def project(value, sex='female'):
    """Project structured text to Markdown strings for comparisons."""
    value = decode_text(value)
    if isinstance(value, Text):
        return markdown(value, sex)
    if isinstance(value, dict):
        return {k: project(v, sex) for k, v in value.items()}
    if isinstance(value, list):
        return [project(v, sex) for v in value]
    return value
