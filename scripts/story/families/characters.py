# -*- coding: utf-8 -*-
"""角色个人剧情族：Plot.json 挂载的 CG_<char>_<part> 好感剧情。

每个角色三段，分别卡好感 1 / 5 / 10。皮肤复刻会为同一份剧本另注册 Plot 行，
因此按剧本分组：有标题的行拥有页面，其余行在页面上列出。

NEEDS：BIN/LANG Plot；角色名经 ctx.character_name（SHARED_NEEDS 覆盖）。
"""
import os
import collections

from context import field_lang
from sink import safe_name, write
from pipeline.pagedoc import PageDoc
from pipeline.render_md import page_markdown

NEEDS = (('BIN', 'Plot'), ('LANG', 'Plot'))
MOUNTS = (('Plot', 'AvgId'),)


def build(ctx, sink):
    BIN_PLOT = ctx.table('BIN', 'Plot')
    LANG_PLOT = ctx.lang_table('LANG', 'Plot')
    stats = collections.Counter()
    by_stem = collections.OrderedDict()
    for r in ctx.rows(BIN_PLOT):
        by_stem.setdefault(r.get('AvgId'), []).append(r)
    for stem, group in by_stem.items():
        parsed = ctx.extract_script(stem)
        if not parsed:
            continue
        owner = next((r for r in group if field_lang(LANG_PLOT, r)), group[0])
        cname = ctx.character_name(owner.get('Char'))
        title = field_lang(LANG_PLOT, owner) or stem
        info = [
            "- **所属角色**：%s（角色编号 `%s`）" % (cname or '未知', owner.get('Char')),
            "- **解锁条件**：好感等级 %s" % owner.get('UnlockAffinityLevel'),
            "- **剧情档案 ID**：`%s`" % owner['Id'],
            "- **AVG 剧本**：`%s`" % stem,
        ]
        twins = [ctx.character_name(r.get('Char')) for r in group if r is not owner]
        if twins:
            info.append("- **复用此剧本的档案**：%s" % "、".join(x for x in twins if x))
        folder = os.path.join(ctx.out, 'characters',
                              safe_name('%s_%s' % (owner.get('Char'), cname or stem)))
        path = os.path.join(folder, 'sections', safe_name('%s_%s' % (owner['Id'], title)) + '.md')
        doc = PageDoc("# %s" % title, info, parsed['meta']['recap'], "逐句台词",
                      parsed['beats'], info_title="剧情档案信息", meta=parsed['meta'])
        write(path, page_markdown(doc))
        sink.record_page('characters', path, doc, owner['Id'], title,
                         group={'kind': 'character', 'id': owner.get('Char'), 'label': cname},
                         stems=[stem], page='characters/%s/%s.html' % (owner.get('Char'), owner['Id']),
                         affinity=owner.get('UnlockAffinityLevel'), twins=twins)
        stats['sections'] += 1
        stats['lines'] += sum(1 for b in parsed['beats'] if b['k'] in ('talk', 'bubble'))
    return stats
