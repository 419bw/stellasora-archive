# -*- coding: utf-8 -*-
"""无关卡引用的战斗气泡族：BBm* 脚本（R1 的 used 从 sink.battle_map 取）。

No CN/bin table ever names a BBm script -- the client derives the name from the
chapter and stage index -- so these can only be filed by their own code. They are
still official dialogue, so they get pages rather than a footnote.

NEEDS：目录扫描型（os.listdir(ctx.cfg) 匹配 BBm 前缀），无表依赖；
used 集合族内自算（sink.battle_map 的 attached 项），编排器零特判。
"""
import os
import collections

from sink import safe_name, write
from pipeline.pagedoc import PageDoc
from pipeline.render_md import page_markdown

NEEDS = ()
MOUNTS = ()


def build(ctx, sink):
    stats = collections.Counter()
    used = {b[1] for b in sink.battle_map if b[2] == 'attached'}
    orphans = sorted(f[:-4] for f in os.listdir(ctx.cfg)
                     if f.startswith('BBm') and f[:-4] not in used)
    for stem in orphans:
        parsed = ctx.extract_script(stem)
        if not parsed:
            continue
        n = sum(1 for b in parsed['beats'] if b['k'] == 'bubble')
        who = "、".join(collections.Counter(b['speaker'] for b in parsed['beats']
                                            if b['k'] == 'bubble'))
        note = ("属序章《最初的起点》沙漠星塔一战，Story 表不列序章所以无行引用"
                if stem.startswith('BBm00_') else
                "包内没有任何关卡表引用此剧本，只按剧本代号存目")
        doc = PageDoc("# 战斗气泡 `%s`" % stem,
                      ["- **AVG 剧本**：`%s`" % stem,
                       "- **气泡条数**：%d" % n,
                       "- **出场说话人**：%s" % who,
                       "- **挂载状态**：%s" % note],
                      "", "战斗气泡对白（SetBubble，随战斗阶段推进）", parsed['beats'],
                      info_title="剧本信息", meta=parsed['meta'])
        path = os.path.join(ctx.out, 'battles_unmounted', safe_name(stem) + '.md')
        write(path, page_markdown(doc))
        sink.record_page('battles_unmounted', path, doc, stem, stem,
                         group={'kind': 'unmounted', 'id': None, 'label': '无关卡引用的战斗气泡'},
                         stems=[stem], page='battles/%s.html' % stem, mount_note=note)
        stats['sections'] += 1
        stats['lines'] += n
    sink.record_unattached(orphans)
    return stats
