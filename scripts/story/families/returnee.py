# -*- coding: utf-8 -*-
"""回归活动重逢剧情族（ST_sys_reengagement*）。

ActivityReturnee.AVG → ST_sys_reengagement*.lua。回归活动（Reengagement）是面向
流失回归玩家的系统活动：其开场剧情由 `ActivityReturnee.json` 的 `AVG` 字段直接
点名剧本，不走关卡表（Story / ActivityStory 均无行），与序章 STm00_* 同为
「流程直接调用」的挂载方式。标题取官方 `UIText.MainView_Reengagement`
（归星漫途），取不到时回退「回归剧情」。

NEEDS：本族是目录扫描型（os.listdir(ctx.cfg)），唯一读取的表是 LANG UIText
（标题来源）。ActivityReturnee 表只被 aggregate 的 coverage 挂载审计扫阅
（MOUNTS），无 BIN 消费点，故不进 NEEDS。
"""
import os
import collections

from context import lang_of
from sink import safe_name, write
from pipeline.pagedoc import PageDoc
from pipeline.render_md import page_markdown

NEEDS = (('LANG', 'UIText'),)
MOUNTS = (('ActivityReturnee', 'AVG'),)


def build(ctx, sink):
    LANG_UITEXT = ctx.lang_table('LANG', 'UIText')
    stats = collections.Counter()
    official_title = lang_of(LANG_UITEXT, 'UIText.MainView_Reengagement.1')
    stems = sorted(f[:-4] for f in os.listdir(ctx.cfg) if f.startswith('ST_sys_reengagement'))
    for stem in stems:
        parsed = ctx.extract_script(stem)
        if not parsed:
            continue
        title = official_title or '回归剧情'
        info = [
            "- **所属**：回归活动《%s》" % title,
            "- **AVG 剧本**：`%s`" % stem,
            "- **挂载来源**：`ActivityReturnee.json` 的 `AVG` 字段（Id 101004，"
            "回归玩家专属活动流程直接调用，关卡表内无行）",
            ("- **标题来源**：官方 `UIText.MainView_Reengagement`" if official_title
             else "- **标题来源**：站点拟名（官方文案表无对应条目）"),
        ]
        path = os.path.join(ctx.out, 'returnee', 'sections',
                            safe_name('%s_%s' % (stem, title)) + '.md')
        doc = PageDoc("# %s" % title, info, parsed['meta']['recap'], "逐句台词",
                      parsed['beats'], info_title="回归剧情信息", meta=parsed['meta'])
        write(path, page_markdown(doc))
        sink.record_page('returnee', path, doc, stem, title,
                         group={'kind': 'returnee', 'id': 101004, 'label': title},
                         stems=[stem], page='returnee/%s.html' % stem)
        stats['sections'] += 1
        stats['lines'] += sum(1 for b in parsed['beats'] if b['k'] in ('talk', 'bubble'))
    return stats
