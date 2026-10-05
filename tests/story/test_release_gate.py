# -*- coding: utf-8 -*-
"""Unit tests for scripts/story/release_gate.py.

The gate decides which story groups are still closed in the game and must
therefore be published as a locked placeholder instead of a transcript. These
tests pin the three judgement rules (time comparison, fail-open on dirty data,
the two env overrides) without touching story_docs/ or site/.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'story'))

import release_gate as rg  # noqa: E402

BIN = os.path.join(rg.ROOT, 'data', 'StellaSoraData', 'CN', 'bin')


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Every test starts from a wall-clock judgement with no env overrides."""
    monkeypatch.delenv(rg.ENV_NOW, raising=False)
    monkeypatch.delenv(rg.ENV_OFF, raising=False)


AT = rg.parse_iso('2026-10-05T12:00:00+08:00')


# ------------------------------------------------------------------ time parsing
@pytest.mark.parametrize('raw', [
    '2026-10-13T12:00:00+08:00',
    '2026-10-13T12:00:00Z',
    '2026-10-13 12:00:00',
    '2026-10-13T12:00:00',
])
def test_parse_iso_accepts_official_shapes(raw):
    dt = rg.parse_iso(raw)
    assert dt is not None
    assert dt.tzinfo is not None


@pytest.mark.parametrize('raw', ['', None, 'not-a-time', '2026-13-45T99:00:00+08:00', 42])
def test_parse_iso_rejects_junk(raw):
    assert rg.parse_iso(raw) is None


# ------------------------------------------------------------------ is_locked
@pytest.mark.parametrize('open_time,locked', [
    ('2026-10-13T12:00:00+08:00', True),    # future -> locked
    ('2026-10-05T12:00:00+08:00', False),   # exactly now -> already open
    ('2026-09-29T12:00:00+08:00', False),   # past -> open
    ('', False),                            # missing -> fail open
    (None, False),
    ('garbage', False),                     # dirty -> fail open
])
def test_is_locked(open_time, locked):
    assert rg.is_locked(open_time, AT) is locked


def test_fmt_open():
    assert rg.fmt_open('2026-10-13T12:00:00+08:00') == '2026-10-13 12:00'
    assert rg.fmt_open('2026-10-13T12:00:00Z') == '2026-10-13 20:00'
    assert rg.fmt_open('') == ''
    assert rg.fmt_open(None) == ''


# ------------------------------------------------------------------ env overrides
def test_release_now_override(monkeypatch):
    monkeypatch.setenv(rg.ENV_NOW, '2026-10-14T12:00:00+08:00')
    assert rg.now() == rg.parse_iso('2026-10-14T12:00:00+08:00')
    assert not rg.is_locked('2026-10-13T12:00:00+08:00')


def test_release_now_ignores_junk(monkeypatch):
    monkeypatch.setenv(rg.ENV_NOW, 'nonsense')
    assert rg.now().tzinfo is not None


def test_gate_off_bypasses_everything(monkeypatch):
    monkeypatch.setenv(rg.ENV_OFF, 'off')
    assert rg.is_locked('2099-01-01T00:00:00+08:00') is False
    assert rg.gate_off() is True


def test_gate_on_means_default(monkeypatch):
    monkeypatch.setenv(rg.ENV_OFF, 'on')
    assert rg.gate_off() is False
    assert rg.is_locked('2099-01-01T00:00:00+08:00', AT) is True


# ------------------------------------------------------------------ real upstream data
def test_gate_finds_the_real_storyset_18():
    """The story set that is actually closed in the pack today."""
    gate = rg.load_gate(at=AT)
    items = gate.items('storysets')
    assert [i['id'] for i in items] == [1018]
    item = items[0]
    assert item['no'] == '#18'
    assert item['preview'] == '诺瓦异闻 #18'
    assert item['open_text'] == '2026-10-13 12:00'
    assert item['is_high_light'] is True
    assert item['pages'] == ['storysets/1018/101801.html',
                             'storysets/1018/101802.html',
                             'storysets/1018/101803.html']
    # the descriptor must not be able to spoil anything
    assert 'name' not in item
    for bad in ('眠于秋分之日', '第一话', '第二话', '第三话'):
        assert bad not in repr(item)


def test_gate_leaves_everything_else_alone():
    gate = rg.load_gate(at=AT)
    assert gate.items('main') == []          # all mainline chapters are open
    assert gate.items('events') == []        # so is every activity in the pack
    assert not gate.is_group('main', 10)
    assert not gate.is_group('events', 10112)
    assert not gate.is_page('storysets', 100101)   # a released story set stays reachable
    assert gate.is_page('storysets', 101801)
    assert gate.is_group('storysets', 1018)
    assert gate.is_group('storysets', '1018')
    assert not gate.is_group('storysets', 'nope')


def test_gate_auto_unlocks_after_open_time():
    gate = rg.load_gate(at=rg.parse_iso('2026-10-13T12:00:01+08:00'))
    assert gate.items('storysets') == []
    assert not gate.is_page('storysets', 101801)
    assert gate.page_urls() == []
    assert not gate


def test_gate_off_gate_has_nothing_locked(monkeypatch):
    monkeypatch.setenv(rg.ENV_OFF, 'off')
    gate = rg.load_gate(at=AT)
    assert gate.items('storysets') == []
    assert not gate.is_page('storysets', 101801)
    assert not gate


# ------------------------------------------------------------------ synthetic tables
def _rows(*items):
    return {str(r['Id']): r for r in items}


def patch_tables(monkeypatch, mapping):
    """Serve the given bin tables from memory, fall back to the real files."""
    real = rg._read

    def fake(path):
        return mapping.get(os.path.basename(path), real(path))

    monkeypatch.setattr(rg, '_read', fake)


def test_storysets_gate_only_future_chapters(monkeypatch):
    patch_tables(monkeypatch, {
        'StorySetChapter.json': _rows(
            {'Id': 1001, 'Title': 'StorySetChapter.1001.1', 'Name': 'x', 'OpenTime': ''},
            {'Id': 1018, 'Title': 'StorySetChapter.1018.1', 'Name': 'x',
             'OpenTime': '2026-10-13T12:00:00+08:00', 'IsHighLight': True},
            {'Id': 2000, 'Title': 'StorySetChapter.2000.1', 'Name': 'x',
             'OpenTime': '2099-01-01T00:00:00+08:00'},
        ),
        'StorySetSection.json': _rows(
            {'Id': 101801, 'ChapterId': 1018, 'Title': 'k'},
            {'Id': 200001, 'ChapterId': 2000, 'Title': 'k'},
        ),
    })
    out = {}
    rg._storysets(out, AT)
    assert sorted(out) == [1018, 2000]
    assert out[1018]['page_ids'] == [101801]
    assert out[2000]['is_high_light'] is False


def test_main_gate_only_future_chapters(monkeypatch):
    patch_tables(monkeypatch, {
        'StoryChapter.json': _rows(
            {'Id': 10, 'Index': '09', 'Name': 'StoryChapter.10.1',
             'OpenTime': '2026-09-29T12:00:00+08:00'},
            {'Id': 11, 'Index': '10', 'Name': 'StoryChapter.11.1',
             'OpenTime': '2026-11-01T12:00:00+08:00'},
        ),
        'Story.json': _rows(
            {'Id': 900, 'Chapter': 10, 'StoryId': 'STm09_01'},
            {'Id': 1100, 'Chapter': 11, 'StoryId': 'STm10_01'},
        ),
    })
    out = {}
    rg._main(out, AT)
    assert list(out) == [11]
    assert out[11]['pages'] == ['main/ch10/STm10_01.html']


def test_events_gate_only_future_groups(monkeypatch):
    patch_tables(monkeypatch, {
        'ActivityGroup.json': _rows(
            {'Id': 10112, 'StartTime': '2026-09-29T12:00:00+08:00'},
            {'Id': 10113, 'StartTime': '2026-10-27T12:00:00+08:00'},
        ),
        'ActivityStory.json': _rows(
            {'Id': 101130101, 'ChapterId': 10113, 'StoryId': 'STev_01_01'},
        ),
    })
    out = {}
    rg._events(out, AT)
    assert list(out) == [10113]
    assert out[10113]['pages'] == ['events/10113/101130101.html']


def test_no_pages_means_no_placeholder(monkeypatch):
    """A locked group with no rows in the pack protects nothing, so it is not listed."""
    patch_tables(monkeypatch, {
        'StorySetChapter.json': _rows(
            {'Id': 1018, 'Title': 'k', 'Name': 'x',
             'OpenTime': '2026-10-13T12:00:00+08:00'}),
        'StorySetSection.json': {},
    })
    out = {}
    rg._storysets(out, AT)
    assert out == {}
