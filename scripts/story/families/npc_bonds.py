# -*- coding: utf-8 -*-
"""星塔 NPC 好感剧情族：NPCAffinityPlot.json 挂载的 CG_npc<id>_<part>。

NEEDS：BIN/LANG NPCAffinityPlot（剧情行）+ BIN/LANG StarTowerNPC（NPC 命名）。
"""
import os
import collections

from context import field_lang
from sink import safe_name, write
from pipeline.pagedoc import PageDoc
from pipeline.render_md import page_markdown

NEEDS = (('BIN', 'NPCAffinityPlot'), ('LANG', 'NPCAffinityPlot'),
         ('BIN', 'StarTowerNPC'), ('LANG', 'StarTowerNPC'))
MOUNTS = (('NPCAffinityPlot', 'avgId'),)


def build(ctx, sink):
    BIN_NPC_PLOT = ctx.table('BIN', 'NPCAffinityPlot')
    BIN_NPC = ctx.table('BIN', 'StarTowerNPC')
    LANG_NPC = ctx.lang_table('LANG', 'StarTowerNPC')
    LANG_NPC_PLOT = ctx.lang_table('LANG', 'NPCAffinityPlot')
    stats = collections.Counter()
    for r in ctx.rows(BIN_NPC_PLOT):
        parsed = ctx.extract_script(r.get('avgId'))
        if not parsed:
            continue
        npc = BIN_NPC.get(str(r.get('NPCId')))
        npc_name = field_lang(LANG_NPC, npc) if npc else ''
        idx = field_lang(LANG_NPC_PLOT, r)
        sub = field_lang(LANG_NPC_PLOT, r, 'Desc')
        info = [
            "- **所属 NPC**：%s（NPC 编号 `%s`）" % (npc_name or '未知', r.get('NPCId')),
            "- **解锁条件**：好感等级 %s" % r.get('AffinityLevel'),
            "- **剧情档案 ID**：`%s`" % r['Id'],
            "- **AVG 剧本**：`%s`" % r.get('avgId'),
        ]
        folder = os.path.join(ctx.out, 'npc_bonds',
                              safe_name('%s_%s' % (r.get('NPCId'), npc_name or r.get('avgId'))))
        path = os.path.join(folder, 'sections', safe_name('%s_%s' % (r['Id'], idx or sub)) + '.md')
        doc = PageDoc("# %s" % " ".join(x for x in (idx, sub) if x), info,
                      parsed['meta']['recap'], "逐句台词", parsed['beats'],
                      info_title="剧情档案信息", meta=parsed['meta'])
        write(path, page_markdown(doc))
        sink.record_page('npc_bonds', path, doc, r['Id'],
                         " ".join(x for x in (idx, sub) if x), code=idx,
                         group={'kind': 'npc', 'id': r.get('NPCId'), 'label': npc_name},
                         stems=[r.get('avgId')],
                         page='npc/%s/%s.html' % (r.get('NPCId'), r['Id']),
                         affinity=r.get('AffinityLevel'), hint=sub)
        stats['sections'] += 1
        stats['lines'] += sum(1 for b in parsed['beats'] if b['k'] in ('talk', 'bubble'))
    return stats
