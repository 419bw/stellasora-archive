# -*- coding: utf-8 -*-
"""模板分发注册表 + CSS 超级拼接（设计 4.1）。

Phase D3 上线模板分发注册表；Phase E1 起本模块兼任 CSS 超级拼接
（theme/tokens|base|graph_base + families/*/style.css，manifest 显式有序）。

分发键 ``(family, kind)``，kind taxonomy 保持极小：
``home / index / chapter_graph / activity_graph / battle_archive / reading``。
族模块通过两类钩子入表：
- ``INDEX_OVERRIDE``：覆盖默认二级索引（main 的时间线轮盘即此钩子）；
- 独有页型渲染函数（main 章图、events 活动图）在表中显式登记。

解析顺序：族专属条目 → 通配（``family=None``）默认条目。新增族页型只需在
本表加一行，编排器 main() 零特判。
"""

from theme.home import home_page
from theme.index import family_index
from theme.reading import script_page
from theme.battle import battle_archive_page
from families.main.templates import INDEX_OVERRIDE as MAIN_INDEX, chapter_graph_page
from families.events.templates import activity_graph_page


# (family, kind) -> 渲染函数；family=None 为通配默认。族专属条目覆盖通配条目。
DISPATCH = {
    (None, 'home'): home_page,
    (None, 'index'): family_index,          # 默认二级索引（main 被下行覆盖）
    (None, 'reading'): script_page,
    (None, 'battle_archive'): battle_archive_page,
    ('main', 'index'): MAIN_INDEX,          # INDEX_OVERRIDE 钩子消费点
    ('main', 'chapter_graph'): chapter_graph_page,
    ('events', 'activity_graph'): activity_graph_page,
}


def render(family, kind, *args, **kwargs):
    """按 (family, kind) 取渲染函数并调用：族专属优先，通配默认兜底。"""
    fn = DISPATCH.get((family, kind)) or DISPATCH.get((None, kind))
    if fn is None:
        raise KeyError('分发表缺渲染函数: family=%r kind=%r' % (family, kind))
    return fn(*args, **kwargs)
