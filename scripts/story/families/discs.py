# -*- coding: utf-8 -*-
"""唱片剧情族：DiscIP 行携带 AvgId 的 CG_disc* 小 vignette。

同一行还在 StoryDesc 存了一份散文复述。它是表内文案、不是剧本台词——AVG 里
没有对应台词——因此作为带标注的附录保留，不并入 beat 列表。

NEEDS：BIN/LANG DiscIP；角色名经 ctx.character_name（SHARED_NEEDS 覆盖）。
"""
import os
import collections

from context import field_lang
from sink import safe_name, write
from pipeline.pagedoc import PageDoc
from pipeline.render_md import page_markdown

NEEDS = (('BIN', 'DiscIP'), ('LANG', 'DiscIP'))
MOUNTS = (('DiscIP', 'AvgId'),)


def build(ctx, sink):
    BIN_DISC = ctx.table('BIN', 'DiscIP')
    LANG_DISC = ctx.lang_table('LANG', 'DiscIP')
    stats = collections.Counter()
    for r in ctx.rows(BIN_DISC):
        stem = r.get('AvgId')
        parsed = ctx.extract_script(stem) if stem else None
        if not parsed:
            continue
        title = field_lang(LANG_DISC, r, 'StoryName')
        chars = [ctx.character_name(c) for c in (r.get('CharId') or [])]
        owners = "、".join(x for x in chars if x)
        info = [
            "- **唱片 ID**：`%s`" % r['Id'],
            "- **关联角色**：%s" % (owners or '无'),
            "- **AVG 剧本**：`%s`" % stem,
        ]
        prose = LANG_DISC.get(r.get('StoryDesc', ''), '').strip()
        doc = PageDoc("# %s" % title, info, parsed['meta']['recap'], "逐句台词",
                      parsed['beats'], info_title="唱片信息", meta=parsed['meta'],
                      appendix={'title': '唱片附文（DiscIP 表 StoryDesc 原文）',
                                'note': '与上面的 AVG 剧本是两份文本：这段是唱片自带的散文，剧本里没有对应的台词。',
                                'prose': prose} if prose else None)
        path = os.path.join(ctx.out, 'discs', safe_name('%s_%s' % (r['Id'], title or stem)) + '.md')
        write(path, page_markdown(doc))
        sink.record_page('discs', path, doc, r['Id'], title,
                         group={'kind': 'disc', 'id': r['Id'], 'label': title,
                                'characters': [c for c in chars if c]},
                         stems=[stem], page='discs/%s.html' % r['Id'],
                         prose_lines=len(prose.split("\n")) if prose else 0)
        stats['sections'] += 1
        stats['lines'] += sum(1 for b in parsed['beats'] if b['k'] in ('talk', 'bubble'))
    return stats
