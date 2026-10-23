# -*- coding: utf-8 -*-
"""活动剧情族：ActivityStory 挂载的 STev*（按 ChapterId 分活动）。

官方活动标题只存在于活动公告的「…」里，取不到时回退首节标题。

NEEDS：BIN/LANG ActivityStory（关卡行）+ BIN/LANG ActivityGroup（活动名，
activity_name 取官方标题来源）。
"""
import os
import re
import collections

from context import lang_of
from sink import safe_name, write
from pipeline.pagedoc import PageDoc
from pipeline.render_md import page_markdown

NEEDS = (('BIN', 'ActivityStory'), ('LANG', 'ActivityStory'),
         ('LANG', 'ActivityGroup'))
MOUNTS = (('ActivityStory', 'AvgLuaName'),)


def activity_name(ctx, cid, first_section_title):
    """The official activity title only exists inside the 「…」 of the activity notice."""
    LANG_ACT_GROUP = ctx.lang_table('LANG', 'ActivityGroup')
    notice = LANG_ACT_GROUP.get('ActivityGroup.%s.1' % cid, '')
    m = re.search(r'「(.+?)」', notice)
    return (m.group(1) if m else first_section_title)[:24]


def build(ctx, sink):
    BIN_ACTIVITY = ctx.table('BIN', 'ActivityStory')
    LANG_ACT = ctx.lang_table('LANG', 'ActivityStory')
    stats = collections.Counter()
    groups = collections.defaultdict(list)
    for r in BIN_ACTIVITY.values():
        groups[r['ChapterId']].append(r)
    for cid in sorted(groups):
        secs = sorted(groups[cid], key=lambda x: x['Id'])
        name = activity_name(ctx, cid, lang_of(LANG_ACT, secs[0].get('Title', '')))
        folder = os.path.join(ctx.out, 'events', 'activity_%s_%s' % (cid, safe_name(name)))
        for r in sorted(secs, key=lambda x: x['Id']):
            stem = r.get('AvgLuaName') or r.get('StoryId')
            parsed = ctx.extract_script(stem) if stem else None
            if not parsed:
                continue
            idx = lang_of(LANG_ACT, r.get('Index', ''))
            title = lang_of(LANG_ACT, r.get('Title', ''))
            hint = lang_of(LANG_ACT, r.get('Desc', ''))
            doc = PageDoc("# %s %s" % (idx, title),
                          ["- **所属活动**：%s（活动编号 %s）" % (name, cid),
                           "- **关卡 ID**：`%s`" % r['Id'],
                           "- **AVG 剧本**：`%s`" % stem,
                           "- **关卡描述**：%s" % hint],
                          parsed['meta']['recap'] or hint,
                          "逐句台词", parsed['beats'], meta=parsed['meta'])
            path = os.path.join(folder, 'sections', safe_name('%s_%s_%s' % (r['Id'], idx, title)) + '.md')
            write(path, page_markdown(doc))
            sink.record_page('events', path, doc, r['Id'], title, code=idx,
                             group={'kind': 'activity', 'id': cid, 'label': name},
                             stems=[stem], page='events/%s/%s.html' % (cid, r['Id']), hint=hint)
            stats['sections'] += 1
            stats['lines'] += sum(1 for b in parsed['beats'] if b['k'] == 'talk')
    return stats
