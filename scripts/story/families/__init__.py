# -*- coding: utf-8 -*-
"""族注册表：FAMILY_ORDER 是剧情族执行顺序的唯一声明处（Phase B-1）。

顺序同时决定 sections.json 的 pages 追加序，因此与改造前 build_story.main()
的调用顺序逐字对齐：

    main → events → characters → npc_bonds → discs → storysets → prologue
    → dispatch → anecdotes → returnee → soldier → chat → orphan_battles
族模块统一契约（设计 4.2 / R1）：``build(ctx, sink) -> collections.Counter``，
文件头声明 NEEDS（运行时门控的白名单，ScopedDataContext 强制执行）与 MOUNTS
（(表, 字段) 挂载对，供 aggregate.write_coverage 自动汇总，消灭双份真相）。
编排器循环对任何族无特判分支；跨族顺序依赖数据全部经 sink 显式 record。
"""
import collections

FAMILY_ORDER = (
    'main', 'events', 'characters', 'npc_bonds', 'discs', 'storysets',
    'prologue', 'dispatch', 'anecdotes', 'returnee', 'soldier', 'chat',
    'orphan_battles',
)

# 族的展示名与控制台标签（原 build_story.main() 的 (label, fn) 元组）。
FAMILY_LABELS = {
    'main': '主线剧情', 'events': '活动剧情', 'characters': '角色个人剧情',
    'npc_bonds': '星塔 NPC 好感剧情', 'discs': '唱片剧情', 'storysets': '故事集支线',
    'prologue': '序章', 'dispatch': '委托结算演出', 'anecdotes': '逸闻笔记',
    'returnee': '归星漫途', 'soldier': '尖兵陷阵', 'chat': '心链',
    'orphan_battles': '无关卡引用的战斗气泡',
}

__all__ = ['FAMILY_ORDER', 'FAMILY_LABELS', 'collections']
