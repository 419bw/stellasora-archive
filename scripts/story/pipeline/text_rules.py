# -*- coding: utf-8 -*-
"""Shared text helpers for extraction and animation-frame comparison."""
import re
from functools import lru_cache
from pathlib import Path
from . import markup

NONLOG = '_NOT_IN_LOG_'
RESOURCE_NAME = re.compile(r'[a-z][a-z0-9_]*')


def clean_text(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip()


def is_resource_name(text):
    return bool(RESOURCE_NAME.fullmatch(text))


@lru_cache(maxsize=1)
def default_compiler():
    root = Path(__file__).resolve().parents[3]
    return markup.TextCompiler.load(root / 'data/ss_lua/Lua/Game/UI/Avg/_cn/Preset',
                                    root / 'data/StellaSoraData/CN/bin',
                                    root / 'data/StellaSoraData/CN/language/zh_CN')


def clean_dialogue(s):
    return markup.markdown(default_compiler().compile(s))


def _sig(text, sex='female'):
    if not isinstance(text, markup.Text):
        text = default_compiler().compile(text)
    nodes = [n for n in text.select(sex) if n[0] != 'tag']
    signature = markup.serialize_md(nodes, sex).replace('<br>', '')
    return re.sub(r'\s+', '', signature)


def _related(a, b):
    return a == b or a in b or b in a
