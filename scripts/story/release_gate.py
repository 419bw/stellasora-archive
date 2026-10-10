# -*- coding: utf-8 -*-
"""Release gate: story groups the official tables say are not open yet.

``StorySetChapterItemCtrl`` keeps an unreleased story set visible in the game's
list but locked: the name is masked with ``StorySet_Chapter_Empty``, the cover is
grey-locked and ``OpenTime`` is compared against the server clock.  This module
reproduces that judgement for the static site so a group whose official open
time is still in the future is published as a locked placeholder instead of its
transcript.

Three families carry an official open time and are therefore gated:

* ``storysets`` -- ``StorySetChapter.OpenTime``
* ``main``      -- ``StoryChapter.OpenTime``
* ``events``    -- ``ActivityGroup.StartTime`` (an activity story chapter's
  ``ChapterId`` *is* the ``ActivityGroup`` id)

No other family has an open-time field, so nothing else is gated.

Fails open: a missing / empty / unparsable time means "released", never the
other way round -- one dirty row must not silently drop real content.

Env:
* ``STELLA_RELEASE_NOW``  -- ISO-8601 instant used instead of wall clock
  (lets CI/tests prove the auto-unlock path).
* ``STELLA_RELEASE_GATE`` -- set to off/0/false/no to bypass the gate entirely
  (emergency rollback: the site renders exactly as it did before gating).
"""

import json
import os
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
BIN = os.path.join(ROOT, 'data', 'StellaSoraData', 'CN', 'bin')
LANG = os.path.join(ROOT, 'data', 'StellaSoraData', 'CN', 'language', 'zh_CN')

TZ = timezone(timedelta(hours=8))
ENV_NOW = 'STELLA_RELEASE_NOW'
ENV_OFF = 'STELLA_RELEASE_GATE'

# ``StorySetChapterItemCtrl.RefreshItem`` swaps a locked chapter's name for
# ``StorySet_Chapter_Empty``; the zh_CN text of that key is 敬请期待, which is
# what the game itself shows. tests/story/test_release_gate.py pins this
# constant against the upstream UIText row, so a re-translation cannot drift.
MASK = '敬请期待'


def _warn(msg):
    """失败开放告警。优先走管线统一出口（pipeline.diagnostics.warn），保持与
    _diagnostics.json 同一套日志格式；本模块被单独 import（path 上没有 scripts/story）
    时退回 print，不因此多一个硬依赖——门控是安全组件，依赖越少越稳。
    """
    try:
        from pipeline.diagnostics import warn
    except ImportError:
        print('[release_gate] %s' % msg)
    else:
        warn('[release_gate] %s' % msg)


def _read(path):
    """Read an upstream table into a dict keyed by Id (already a dict upstream)."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        out = {}
        for row in data:
            if isinstance(row, dict) and row.get('Id') is not None:
                out[str(row['Id'])] = row
        return out
    return {}


def _rows(table):
    return sorted(table.values(), key=lambda r: r.get('Id', 0) or 0)


def _lang(lang_table, key):
    if not key or not isinstance(lang_table, dict):
        return ''
    value = lang_table.get(key)
    return str(value).strip() if value is not None else ''


def parse_iso(value):
    """``"2026-10-13T12:00:00+08:00"`` -> aware datetime; anything odd -> None."""
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=TZ)
    return parsed


def gate_off():
    return os.environ.get(ENV_OFF, '').strip().lower() in ('off', '0', 'false', 'no')


def now(override=None):
    """Judgement instant: explicit override > STELLA_RELEASE_NOW > wall clock."""
    raw = override or os.environ.get(ENV_NOW) or ''
    if raw:
        parsed = parse_iso(raw)
        if parsed is None:
            _warn('ignoring unparsable %s=%r, using wall clock' % (ENV_NOW, raw))
        else:
            return parsed
    return datetime.now(TZ)


def is_locked(open_time, at=None):
    """True only when the official open time is known and still in the future."""
    if gate_off():
        return False
    at = at or now()
    parsed = parse_iso(open_time)
    if parsed is None:
        if open_time:
            _warn('ignoring unparsable open time %r (treating as released)' % (open_time,))
        return False
    return parsed > at


def fmt_open(open_time):
    """``2026-10-13 12:00`` for display, ``''`` when unknown."""
    parsed = parse_iso(open_time)
    return parsed.astimezone(TZ).strftime('%Y-%m-%d %H:%M') if parsed else ''


def _preview(kind):
    """``{story_id: banner title}`` from StoryPreview (1 = mainline, 2 = storyset).

    A preview banner is what the game shows *before* the chapter opens, so it is
    the only textual label about a locked group that is safe to display. The
    earliest announcement wins when several exist for one story.
    """
    lang = _read(os.path.join(LANG, 'StoryPreview.json'))
    out = {}
    for row in _rows(_read(os.path.join(BIN, 'StoryPreview.json'))):
        if row.get('Type') != kind:
            continue
        sid = row.get('StoryId')
        if sid is None or sid in out:
            continue  # keep the earliest announcement for each story
        out[int(sid)] = _lang(lang, 'StoryPreview.%s.1' % row.get('Id'))
    return out


def _item(family, gid, open_time, no, preview, pages, page_ids, highlight=False):
    """Descriptor for one locked group.

    Deliberately carries **no** chapter name, no section titles, no section count
    and no transcript: it is the only thing the site renders for a locked group,
    so it must not be able to leak "what is inside".
    """
    return {
        'family': family,
        'id': int(gid),
        'no': no or '',
        'preview': preview or '',
        'open_time': open_time or '',
        'open_text': fmt_open(open_time),
        'is_high_light': bool(highlight),
        'page_ids': [int(i) for i in page_ids],
        'pages': list(pages),
    }


def _storysets(out, at):
    chapters = _read(os.path.join(BIN, 'StorySetChapter.json'))
    lang = _read(os.path.join(LANG, 'StorySetChapter.json'))
    preview = _preview(2)
    by_chap = {}
    for row in _rows(_read(os.path.join(BIN, 'StorySetSection.json'))):
        if row.get('Id') is None:
            continue
        by_chap.setdefault(row.get('ChapterId'), []).append(row)
    for row in _rows(chapters):
        open_time = row.get('OpenTime')
        if not is_locked(open_time, at):
            continue
        cid = int(row['Id'])
        secs = by_chap.get(cid) or by_chap.get(str(cid)) or []
        if not secs:
            continue  # nothing in the pack to hide -> nothing to placeholder
        out[cid] = _item('storysets', cid, open_time,
                         _lang(lang, row.get('Title')),
                         preview.get(cid, ''),
                         ['storysets/%d/%d.html' % (cid, s['Id']) for s in secs],
                         [s['Id'] for s in secs],
                         row.get('IsHighLight'))


def _main(out, at):
    chapters = _read(os.path.join(BIN, 'StoryChapter.json'))
    preview = _preview(1)
    rows_by_chap = {}
    for row in _rows(_read(os.path.join(BIN, 'Story.json'))):
        if row.get('StoryId'):
            rows_by_chap.setdefault(row.get('Chapter'), []).append(row)
    for row in _rows(chapters):
        open_time = row.get('OpenTime')
        if not is_locked(open_time, at):
            continue
        cid = int(row['Id'])
        rows = rows_by_chap.get(cid) or rows_by_chap.get(str(cid)) or []
        if not rows:
            continue
        cno = row.get('Index') or 'sp'
        # the chapter index page is a real URL in the released site, so a locked
        # chapter gets a notice page there too instead of a 404
        out[cid] = _item('main', cid, open_time,
                         str(row.get('Index') or ''),
                         preview.get(cid, ''),
                         ['main/ch%s/index.html' % cno]
                         + ['main/ch%s/%s.html' % (cno, r['StoryId']) for r in rows],
                         [r['Id'] for r in rows if r.get('Id') is not None])


def _events(out, at):
    groups = _read(os.path.join(BIN, 'ActivityGroup.json'))
    rows_by_chap = {}
    for row in _rows(_read(os.path.join(BIN, 'ActivityStory.json'))):
        if row.get('Id') is None:
            continue
        rows_by_chap.setdefault(row.get('ChapterId'), []).append(row)
    for row in _rows(groups):
        open_time = row.get('StartTime')
        if not is_locked(open_time, at):
            continue
        gid = int(row['Id'])
        rows = rows_by_chap.get(gid) or rows_by_chap.get(str(gid)) or []
        if not rows:
            continue
        out[gid] = _item('events', gid, open_time, '', '',
                         ['events/%d/index.html' % gid]
                         + ['events/%d/%d.html' % (gid, r['Id']) for r in rows],
                         [r['Id'] for r in rows])


class Gate(object):
    """Locked groups plus the (family, page id) pairs they protect."""

    def __init__(self, groups):
        self.groups = groups
        self._pages = set()
        for items in groups.values():
            for item in items.values():
                for pid in item.get('page_ids') or ():
                    self._pages.add((item['family'], int(pid)))

    def items(self, family):
        return list(self.groups.get(family, {}).values())

    def is_group(self, family, gid):
        try:
            gid = int(gid)
        except (TypeError, ValueError):
            return False
        return gid in self.groups.get(family, {})

    def is_page(self, family, page_id):
        try:
            page_id = int(page_id)
        except (TypeError, ValueError):
            return False
        return (family, page_id) in self._pages

    def page_urls(self):
        urls = []
        for items in self.groups.values():
            for item in items.values():
                urls.extend(item['pages'])
        return urls

    def __bool__(self):
        return bool(self.groups.get('storysets') or self.groups.get('main')
                    or self.groups.get('events'))


def load_gate(at=None):
    """Read the upstream tables and decide which groups are still locked."""
    at = at or now()
    groups = {'storysets': {}, 'main': {}, 'events': {}}
    if not gate_off():
        _storysets(groups['storysets'], at)
        _main(groups['main'], at)
        _events(groups['events'], at)
    return Gate(groups)
