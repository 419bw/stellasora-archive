# -*- coding: utf-8 -*-
"""尖兵陷阵族（Soldier，自走棋模式）：开场剧本 + 终局档案。

开场剧本 `ST_sys_soldier_intro.lua` 由模式入口直接调用，包内无任何配置表引用；
终局取自 `SoldierEndingPlan` 表（标题 + 描述 + 解锁条件），表驱动、仿逸闻笔记的
anecdote beat 机制（每页 1 则）。

局内随机事件（`SoldierStoryType` / `SoldierOptionType` /
`SoldierStoryPersonalityOption` / `SoldierStoryResult` /
`SoldierEventPersonalityStory`）以 3 选 1、性格轴检定与奖励结算为主，结果文案
大量缺失（语言表 114 条去重后仅 7 条独立文本），按玩法内容不纳入本档案。

NEEDS：仅 SoldierEndingPlan 一对 BIN/LANG 表；开场剧本是流程直接调用
（目录内固定 stem），无表依赖。
"""
import os
import collections

from context import lang_of, rows_of
from sink import safe_name, write
from pipeline.pagedoc import PageDoc
from pipeline.render_md import page_markdown

NEEDS = (('BIN', 'SoldierEndingPlan'), ('LANG', 'SoldierEndingPlan'))
MOUNTS = ()


def build(ctx, sink):
    BIN_ENDING = ctx.table('BIN', 'SoldierEndingPlan')
    LANG_ENDING = ctx.lang_table('LANG', 'SoldierEndingPlan')
    stats = collections.Counter()
    stem = 'ST_sys_soldier_intro'
    parsed = ctx.extract_script(stem)
    if parsed:
        title = '尖兵陷阵 · 开场剧情'
        info = [
            "- **所属**：尖兵陷阵（自走棋模式）开场剧情",
            "- **AVG 剧本**：`%s`" % stem,
            "- **挂载状态**：模式入口直接调用，包内无任何配置表引用",
            "- **标题来源**：站点拟名（剧本无官方章节标题；「尖兵陷阵」为官方模式名）",
        ]
        path = os.path.join(ctx.out, 'soldier', 'sections',
                            safe_name('%s_%s' % (stem, title)) + '.md')
        doc = PageDoc("# %s" % title, info, parsed['meta']['recap'], "逐句台词",
                      parsed['beats'], info_title="尖兵陷阵信息", meta=parsed['meta'])
        write(path, page_markdown(doc))
        sink.record_page('soldier', path, doc, stem, title,
                         group={'kind': 'soldier_intro', 'id': '01_intro', 'label': '开场'},
                         stems=[stem], page='soldier/%s.html' % stem)
        stats['sections'] += 1
        stats['lines'] += sum(1 for b in parsed['beats'] if b['k'] in ('talk', 'bubble'))

    for r in rows_of(BIN_ENDING):
        rid = r.get('Id')
        etitle = lang_of(LANG_ENDING, r.get('EndingTitle', ''))
        raw_story = LANG_ENDING.get(r.get('Desc', ''), '').replace('\r\n', '\n')
        paras = [ln.strip() for ln in raw_story.split('\n') if ln.strip()]
        story = '\n'.join(paras)
        if not etitle or not story:
            print("!! 尖兵陷阵终局表行缺标题或正文，跳过: id=%s" % rid)
            continue
        cond = r.get('EndingCondition1')
        info = [
            "- **所属**：尖兵陷阵（自走棋模式）终局",
            "- **表 Id**：`%s`（`SoldierEndingPlan`）" % rid,
            "- **解锁条件**：`EndingCondition1 = %s`" % cond,
        ]
        beat = {'k': 'anecdote', 'id': int(rid), 'sort': 0,
                'title': etitle, 'source': '尖兵陷阵终局',
                'story': story}
        path = os.path.join(ctx.out, 'soldier', 'sections',
                            safe_name('%s_%s' % (rid, etitle)) + '.md')
        doc = PageDoc("# %s" % etitle, info, '', '终局文本', [beat],
                      info_title="终局信息", meta={'recap': '', 'episode': '', 'title': ''})
        write(path, page_markdown(doc))
        sink.record_page('soldier', path, doc, int(rid), etitle,
                         group={'kind': 'soldier_ending', 'id': '02_ending', 'label': '终局'},
                         table_refs=['SoldierEndingPlan#%s' % rid], stems=[],
                         page='soldier/endings/%s.html' % rid,
                         text_chars=len(story))
        stats['sections'] += 1
    return stats
