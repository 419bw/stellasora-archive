# -*- coding: utf-8 -*-
"""族注册表与站点侧常量（Phase D1 从 site_templates.py 拆出）。

FAMILIES 的顺序即首页 bento 与导航的展示序；slug_of 是族 id → 站点 URL slug
的唯一来源（orphan_battles → battles_unmounted、npc_bonds → npc 是历史 slug，
站点链接与 CSS data-family 属性值都用它，故 SLUG_ALIAS 与 slug_of 同源）。
"""


FAMILIES = [
    ('main', '主线剧情', '全线剧情拓扑、分支抉择与终局推演。'),
    ('events', '活动剧情', '各期主题活动的关卡剧情全文与阶段收录。'),
    ('characters', '角色个人剧情', '旅人专属故事，好感等级逐级解锁。'),
    ('npc_bonds', '星塔 NPC 好感', '星塔驻留人员与常驻 NPC 羁绊剧情。'),
    ('discs', '秘闻', '收录秘闻剧本，附官方原版散文。'),
    ('storysets', '故事集支线', '主题故事集与日常侧写，收录支线剧情与回忆。'),
    ('prologue', '序章', '旅程开启的序幕篇章《最初的起点》。'),
    ('battles_unmounted', '存目战斗气泡', '战场独立战斗气泡与实时对白。'),
    ('dispatch', '委托对话', '委托（Agent）结算演出台词：完成含特殊报酬的委托时，按上阵旅人与权重随机播放；单人是每位旅人的代表作，双人/三人是随行短对话。'),
    ('anecdotes', '逸闻笔记', '攀登的旅途，总是伴随着意外'),
    ('returnee', '回归剧情', '回归玩家重逢活动《归星漫途》的开场剧情全文。'),
    ('soldier', '尖兵陷阵', '自走棋模式「尖兵陷阵」的开场剧情与终局档案。'),
]


FAMILY_META = {
    'main': {
        'code': '01',
        'span': 'span-2',
        'desc': '全线剧情拓扑、分支抉择与终局推演，涵盖主线各章节及特别篇完整图景。',
    },
    'characters': {
        'code': '02',
        'span': 'span-2',
        'desc': '旅人专属故事，好感等级逐级解锁，深入角色内心世界与往事。',
    },
    'events': {
        'code': '03',
        'span': 'span-1',
        'desc': '各期主题活动的关卡剧情全文与阶段收录。',
    },
    'discs': {
        'code': '04',
        'span': 'span-1',
        'desc': '收录秘闻剧本，附官方原版散文。',
    },
    'storysets': {
        'code': '05',
        'span': 'span-1',
        'desc': '主题故事集与日常侧写，收录支线剧情与多重视角回忆。',
    },
    'npc_bonds': {
        'code': '06',
        'span': 'span-1',
        'desc': '星塔驻留人员与常驻 NPC 的日常羁绊交流剧情。',
    },
    'prologue': {
        'code': '07',
        'span': 'span-1',
        'desc': '旅程开启的序幕篇章《最初的起点》，旅人初次相遇的故事。',
    },
    'battles_unmounted': {
        'code': '08',
        'span': 'span-1',
        'desc': '战场独立战斗气泡与角色实时对白。',
    },
    'dispatch': {
        'code': '09',
        'span': 'span-1',
        'desc': '委托结算演出台词，按结算演出类型收录。',
    },
    'anecdotes': {
        'code': '10',
        'span': 'span-1',
        'desc': '攀登的旅途，总是伴随着意外',
    },
    'returnee': {
        'code': '11',
        'span': 'span-1',
        'desc': '回归玩家重逢活动《归星漫途》的开场剧情全文。',
    },
    'soldier': {
        'code': '12',
        'span': 'span-1',
        'desc': '自走棋模式「尖兵陷阵」的开场剧情与终局档案。',
    },
}


FAMILY_NAME = {k: n for k, n, _ in FAMILIES}


# 族 id → 站点 slug 的差异映射（与 slug_of 内部字典同源；CSS 作用域 lint 与
# 注册表契约用）。
SLUG_ALIAS = {'orphan_battles': 'battles_unmounted', 'npc_bonds': 'npc'}


def slug_of(family):
    return {'main': 'main', 'events': 'events', 'characters': 'characters',
            'npc_bonds': 'npc', 'discs': 'discs', 'storysets': 'storysets',
            'prologue': 'prologue', 'battles_unmounted': 'battles',
            'dispatch': 'dispatch', 'anecdotes': 'anecdotes',
            'returnee': 'returnee', 'soldier': 'soldier'}[family]


STATE_LABEL = {'battle': '战斗', 'story': '剧情'}
