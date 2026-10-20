# -*- coding: utf-8 -*-
"""章节目录与时间线的唯一解析处。

上游三张表各管一件事，本模块把它们读成下游统一使用的判据：

* ``StoryChapter.Type``        -> 是不是特别篇（``is_special``）
* ``StoryChapter.StoryLineId`` -> 属于哪条时间线（``chapter_line`` / ``story_lines``）
* ``StoryChapter.Index`` / ``Id`` -> 站点 URL 目录（``resolve_chapter_slug``）

``tests/story/validate_site.py`` 的 G 组把 ``special``、无边（``edge_source``）、
无编号（``Index is None``）锁成双向充要，所以下游只需要读 ``special`` 一个判据；
本模块自己不重复那三条断言，只负责把表字段读成判据。

三个"编号"不要混（详见 ``resolve_chapter_slug`` 的 docstring）：

* ``Id``    -- 表主键，1..N，恒存在且唯一，用于 ``chsp{Id}``
* ``Index`` -- 游戏内显示编号 ``'01'``..``'09'``，特别篇没有，用于 ``ch{Index}``
* ``Story.StoryId`` -- 关卡 Id，与章编号无关

本模块是叶子模块：不 import pipeline、不 import 任何项目内模块，四个消费端
（``build_story`` / ``build_site`` / ``release_gate`` / ``validate_site``）都能直接
import，避免为了拿一个 slug 把整条管线的依赖拖进来。
"""

import json
import os

__all__ = [
    'story_lines', 'chapter_line', 'chapter_line_info', 'is_special',
    'resolve_chapter_slug', 'build_slug_map', 'node_page', 'chapter_page',
]


def _read(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _as_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip('-').isdigit():
        return int(value.strip())
    return None


def story_lines(bin_dir, lang_dir):
    """``StoryLine.json`` -> ``{line_id: {id, title, subtitle, sort_index, icon}}``.

    表缺失时返回空 dict：时间线是本次上游新增的维度，老快照没有这张表，
    消费端按"只有一条未命名时间线"降级即可，不该因此构建失败。
    """
    rows = _read(os.path.join(bin_dir, 'StoryLine.json'))
    lang = _read(os.path.join(lang_dir, 'StoryLine.json'))
    out = {}
    for key, row in rows.items():
        lid = _as_int(key)
        if lid is None or not isinstance(row, dict):
            continue
        out[lid] = {
            'id': lid,
            'title': str(lang.get(row.get('TitleMain') or '', '') or ''),
            'subtitle': str(lang.get(row.get('TitleSub') or '', '') or ''),
            'sort_index': row.get('SortIndex'),
            'icon': row.get('Icon'),
        }
    return out


def chapter_line(cdef):
    """``StoryChapter.StoryLineId`` -> int，缺字段返回 None。"""
    return _as_int((cdef or {}).get('StoryLineId'))


def chapter_line_info(cdef, lines):
    """该章所属时间线的展示信息；表里没有这一行时返回 None。"""
    lid = chapter_line(cdef)
    if lid is None:
        return None
    info = (lines or {}).get(lid)
    return dict(info) if info else None


def is_special(cdef):
    """特别篇判定：``StoryChapter.Type == 2``（官方显式字段，唯一判据）。"""
    return (cdef or {}).get('Type') == 2


def resolve_chapter_slug(cdef):
    """单章 URL 目录，纯函数。

    * ``Index`` 存在 -> ``ch{Index}``（第 1-10 章，与历史 URL 一致）
    * 否则          -> ``chsp{Id}``（特别篇；``Id`` 是表主键，不是显示编号）

    ``Id`` 与 ``Index`` 错开一位：特别篇占 Id=7 这一行但没有显示编号，所以
    Id=8 的章 ``Index='07'``、Id=9 -> ``'08'``、Id=10 -> ``'09'``。因此
    ``ch07``（第八章）与 ``chsp7``（特别篇）并存且不冲突。
    """
    cdef = cdef or {}
    index = cdef.get('Index')
    if index:
        return 'ch%s' % index
    cid = _as_int(cdef.get('Id'))
    if cid is None:
        raise ValueError('StoryChapter 行缺少 Id，无法生成章节目录: %r' % (cdef,))
    return 'chsp%d' % cid


def build_slug_map(all_cdefs):
    """``{表Id: slug}``，一次性算全量并断言全局唯一。

    冲突直接 ``raise``：目录撞车在旧实现里表现为"后写的章覆盖先写的章"这类
    静默故障（本次 CI 失败的病根），这里把它变成构建期硬错误。
    """
    out = {}
    owner = {}
    for key, cdef in (all_cdefs or {}).items():
        cid = _as_int(key)
        if cid is None:
            continue
        slug = resolve_chapter_slug(cdef)
        if slug in owner:
            raise ValueError(
                '章节目录撞车：%s 同时属于第 %d 章和第 %d 章'
                % (slug, owner[slug], cid))
        owner[slug] = cid
        out[cid] = slug
    return out


def node_page(slug, stem):
    """``main/{slug}/{stem}.html``"""
    return 'main/%s/%s.html' % (slug, stem)


def chapter_page(slug):
    """``main/{slug}/index.html``"""
    return 'main/%s/index.html' % slug
