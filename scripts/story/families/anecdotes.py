# -*- coding: utf-8 -*-
"""逸闻笔记族：StarTowerBookEventReward 星塔图鉴短篇故事。

按人物合并成页，每页收录该人物的（一）（二）（三）共 3 则逸闻笔记、获取条件与
正文。md 置于 `anecdotes/` 下（char/ 旅人、npc/ 星塔 NPC 两个子目录）。

NEEDS：BIN/LANG StarTowerBookEventReward（笔记正文）+ BIN/LANG StarTowerNPC
（NPC 归属判定与命名）+ BIN/LANG Character（ctx.character_name 经 SHARED_NEEDS
覆盖，不在此重复声明）。
"""
import os
import re
import collections

from context import lang_of, field_lang
from sink import safe_name, write
from pipeline.pagedoc import PageDoc
from pipeline.render_md import page_markdown

NEEDS = (('BIN', 'StarTowerBookEventReward'), ('LANG', 'StarTowerBookEventReward'),
         ('BIN', 'StarTowerNPC'), ('LANG', 'StarTowerNPC'))
MOUNTS = ()


def build(ctx, sink):
    BIN_EVENT_BOOK = ctx.table('BIN', 'StarTowerBookEventReward')
    LANG_EVENT_BOOK = ctx.lang_table('LANG', 'StarTowerBookEventReward')
    BIN_NPC = ctx.table('BIN', 'StarTowerNPC')
    LANG_NPC = ctx.lang_table('LANG', 'StarTowerNPC')
    stats = collections.Counter()
    rows_sorted = sorted(
        (r for r in BIN_EVENT_BOOK.values() if not r.get('IsBanned')),
        key=lambda x: (int(x.get('Sort', 0)), int(x['Id'])),
    )
    by_person = collections.OrderedDict()
    for r in rows_sorted:
        key = (int(r.get('Type', 0)), int(r.get('NPCId', 0)))
        by_person.setdefault(key, []).append(r)

    for seq, ((r_type, npc_id), rows) in enumerate(by_person.items(), 1):
        if r_type == 2:
            npc = BIN_NPC.get(str(npc_id))
            who = field_lang(LANG_NPC, npc) if npc else ('NPC %s' % npc_id)
            role_label = '星塔 NPC'
            sub = 'npc'
        else:
            who = ctx.character_name(npc_id) or ('旅人 %s' % npc_id)
            role_label = '旅人'
            sub = 'char'
        group_label = who

        beats = []
        notes = []
        for r in rows:
            ntitle = lang_of(LANG_EVENT_BOOK, r.get('Name', ''))
            nsource = lang_of(LANG_EVENT_BOOK, r.get('Source', ''))
            raw_story = LANG_EVENT_BOOK.get(r.get('Story', ''), '').replace('\r\n', '\n')
            paras = [ln.strip() for ln in raw_story.split('\n') if ln.strip()]
            nstory = '\n'.join(paras)
            beats.append({
                'k': 'anecdote',
                'id': int(r['Id']),
                'sort': int(r.get('Sort', 0)),
                'title': ntitle,
                'source': nsource,
                'story': nstory,
            })
            notes.append({
                'id': int(r['Id']),
                'title': ntitle,
                'source': nsource,
            })

        base_titles = list(dict.fromkeys(
            re.sub(r'（[一二三四五六七八九十\d]+）$', '', b['title']).strip() or b['title']
            for b in beats
        ))
        series_title = ' / '.join(base_titles)
        page_title = '%s · %s' % (who, series_title)
        info = [
            "- **所属人物**：%s（编号 `%s`）" % (who, npc_id),
            "- **收录笔记**：%d 篇（%s）" % (len(beats), '、'.join('`%s`' % b['id'] for b in beats)),
        ]
        path = os.path.join(
            ctx.out, 'anecdotes', sub,
            safe_name('%s_%s_%s' % (npc_id, who, series_title)) + '.md',
        )
        doc = PageDoc(
            "# " + page_title, info, '', '逸闻笔记全文', beats,
            info_title='逸闻笔记信息',
            meta={'recap': '', 'episode': '', 'title': ''},
        )
        write(path, page_markdown(doc))
        sink.record_page(
            'anecdotes', path, doc, int(npc_id), page_title,
            code='',
            group={
                'kind': sub,
                'id': '%03d_%s' % (seq, npc_id),
                'label': group_label,
                'npc_id': int(npc_id),
                'type': r_type,
            },
            stems=[],
            page='anecdotes/%s/%s.html' % (sub, npc_id),
            notes=notes,
        )
        stats['sections'] += 1
        stats['lines'] += len(beats)
    return stats
