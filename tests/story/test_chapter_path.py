# -*- coding: utf-8 -*-
"""Unit tests for scripts/story/chapter_path.py.

The module is the single place that turns three upstream fields into the
judgements every consumer shares:

* ``StoryChapter.Type``        -> 特别篇 (``is_special``)
* ``StoryChapter.StoryLineId`` -> 时间线 (``chapter_line`` / ``story_lines``)
* ``StoryChapter.Index``/``Id`` -> 站点 URL 目录 (``resolve_chapter_slug``)

``tests/story/validate_site.py`` pins the *contract* (special ⇔ 无边 ⇔ 无编号)
against the real sidecar; these tests pin the *derivation* itself — the slug
rule, the Id/Index offset that keeps ``ch07`` and ``chsp7`` apart, the
uniqueness guard that turns a directory collision into a build error, and the
StoryLine table parsing. No story_docs/ or site/ is touched.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'story'))

import chapter_path as cp  # noqa: E402


def _chapter(cid, index=None, ctype=1, line=1):
    row = {'Id': cid, 'Type': ctype, 'StoryLineId': line}
    if index is not None:
        row['Index'] = index
    return row


# --------------------------------------------------------------- slug 规则
# (Index, Id, Type) -> slug。特别篇(Id=7/11) 无 Index，走 chsp{Id}；
# 普通章 Id 与 Index 错开一位（特别篇占 Id=7 但无显示编号），所以 Id=8 的章
# Index 是 '07' —— ch07 与 chsp7 因此并存且不冲突。
@pytest.mark.parametrize('cdef,expected', [
    (_chapter(1, '01'), 'ch01'),
    (_chapter(6, '06'), 'ch06'),
    (_chapter(7, None, ctype=2), 'chsp7'),
    (_chapter(8, '07'), 'ch07'),
    (_chapter(9, '08'), 'ch08'),
    (_chapter(10, '09'), 'ch09'),
    (_chapter(11, None, ctype=2, line=2), 'chsp11'),
])
def test_resolve_chapter_slug(cdef, expected):
    assert cp.resolve_chapter_slug(cdef) == expected


def test_resolve_chapter_slug_rejects_row_without_id():
    with pytest.raises(ValueError):
        cp.resolve_chapter_slug({'Index': None, 'Type': 2})


def test_build_slug_map_covers_every_chapter_and_is_unique():
    chapters = {
        '1': _chapter(1, '01'), '7': _chapter(7, None, ctype=2),
        '8': _chapter(8, '07'), '11': _chapter(11, None, ctype=2, line=2),
    }
    assert cp.build_slug_map(chapters) == {1: 'ch01', 7: 'chsp7', 8: 'ch07', 11: 'chsp11'}


def test_build_slug_map_raises_on_collision():
    # 两章拿到同一个目录时旧实现是"后写覆盖先写"的静默故障，这里必须炸掉。
    chapters = {'7': _chapter(7, None, ctype=2), '11': _chapter(11, None, ctype=2, line=2)}
    chapters['11']['Index'] = '07'
    chapters['8'] = _chapter(8, '07')
    with pytest.raises(ValueError):
        cp.build_slug_map(chapters)


# --------------------------------------------------------------- 特别篇判定
@pytest.mark.parametrize('ctype,expected', [(1, False), (2, True), (None, False)])
def test_is_special_reads_type_only(ctype, expected):
    assert cp.is_special(_chapter(9, '08', ctype=ctype)) is expected


# --------------------------------------------------------------- 时间线
@pytest.mark.parametrize('line,expected', [(1, 1), (2, 2), (None, None), ('3', 3)])
def test_chapter_line(line, expected):
    row = _chapter(11, None, ctype=2)
    if line is None:
        row.pop('StoryLineId')
    else:
        row['StoryLineId'] = line
    assert cp.chapter_line(row) == expected


def test_story_lines_parses_titles_and_sort_index(tmp_path):
    bin_dir = tmp_path / 'bin'
    lang_dir = tmp_path / 'lang'
    bin_dir.mkdir()
    lang_dir.mkdir()
    (bin_dir / 'StoryLine.json').write_text(
        '{"1": {"Id": 1, "TitleMain": "StoryLine.1.1", "TitleSub": "StoryLine.1.2",'
        ' "SortIndex": 2, "Icon": "Icon/ZZZOther/timeline_2_l"},'
        ' "2": {"Id": 2, "TitleMain": "StoryLine.2.1", "TitleSub": "StoryLine.2.2",'
        ' "SortIndex": 1}}',
        encoding='utf-8')
    (lang_dir / 'StoryLine.json').write_text(
        '{"StoryLine.1.1": "我思，故魔王在", "StoryLine.1.2": "星塔历996年",'
        ' "StoryLine.2.1": "魔王，吾向您祈愿", "StoryLine.2.2": "前星塔历4年"}',
        encoding='utf-8')
    lines = cp.story_lines(str(bin_dir), str(lang_dir))
    assert lines == {
        1: {'id': 1, 'title': '我思，故魔王在', 'subtitle': '星塔历996年',
            'sort_index': 2, 'icon': 'Icon/ZZZOther/timeline_2_l'},
        2: {'id': 2, 'title': '魔王，吾向您祈愿', 'subtitle': '前星塔历4年',
            'sort_index': 1, 'icon': None},
    }


def test_story_lines_missing_table_degrades_to_empty(tmp_path):
    # 老快照没有 StoryLine.json：时间线是上游新增维度，缺表不能让构建失败。
    assert cp.story_lines(str(tmp_path / 'nope'), str(tmp_path / 'nope')) == {}


def test_chapter_line_info_returns_line_or_none():
    lines = {2: {'id': 2, 'title': '魔王，吾向您祈愿', 'subtitle': '前星塔历4年',
                 'sort_index': 1, 'icon': None}}
    assert cp.chapter_line_info(_chapter(11, None, ctype=2, line=2), lines)['title'] == '魔王，吾向您祈愿'
    assert cp.chapter_line_info(_chapter(1, '01'), lines) is None
    assert cp.chapter_line_info(_chapter(11, None, ctype=2, line=9), lines) is None


# --------------------------------------------------------------- 页面路径
def test_node_and_chapter_page():
    assert cp.node_page('chsp11', 'STm10001_01') == 'main/chsp11/STm10001_01.html'
    assert cp.chapter_page('ch07') == 'main/ch07/index.html'
