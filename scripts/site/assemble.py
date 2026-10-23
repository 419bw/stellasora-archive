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

import os

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


# ---------------------------------------------------------------------------
# CSS 超级拼接（Phase E1）
# ---------------------------------------------------------------------------

# 片段文件内以独占一行的 ``/* @@ */`` 分块；manifest 的块号指文件内第 n 块
# （从 1 计）。分隔注释只存在于源片段，拼接入产物时剔除。
BLOCK_SEP = '/* @@ */'

# (片段文件, 块号) 有序清单 = 原 site_css.py 样式块的发现序——族块天然夹杂
# （bento 浅色整批 → 深色整批、grp 浅色整批 → 深色整批、拓扑族块四散），
# 故 manifest 必须到块级才能既保发现序又一族一文件。E1 拼接待产物与拆分前
# 逐字节一致（不注入文件头注释）；E3 才归一为 tokens → base → graph_base →
# FAMILY_ORDER 并注入清单注释，走声明式预期 diff。
CSS_MANIFEST = [
    ('theme/base.css', 1),
    ('theme/tokens.css', 1),
    ('theme/base.css', 2),
    ('families/main/style.css', 1),
    ('families/characters/style.css', 1),
    ('families/events/style.css', 1),
    ('families/discs/style.css', 1),
    ('families/storysets/style.css', 1),
    ('families/npc_bonds/style.css', 1),
    ('families/prologue/style.css', 1),
    ('families/battles_unmounted/style.css', 1),
    ('families/dispatch/style.css', 1),
    ('families/anecdotes/style.css', 1),
    ('families/returnee/style.css', 1),
    ('families/soldier/style.css', 1),
    ('families/main/style.css', 2),
    ('families/characters/style.css', 2),
    ('families/events/style.css', 2),
    ('families/discs/style.css', 2),
    ('families/storysets/style.css', 2),
    ('families/npc_bonds/style.css', 2),
    ('families/prologue/style.css', 2),
    ('families/battles_unmounted/style.css', 2),
    ('families/dispatch/style.css', 2),
    ('families/anecdotes/style.css', 2),
    ('families/returnee/style.css', 2),
    ('families/soldier/style.css', 2),
    ('theme/base.css', 3),
    ('families/events/style.css', 3),
    ('families/characters/style.css', 3),
    ('families/storysets/style.css', 3),
    ('families/discs/style.css', 3),
    ('families/npc_bonds/style.css', 3),
    ('families/prologue/style.css', 3),
    ('families/battles_unmounted/style.css', 3),
    ('families/dispatch/style.css', 3),
    ('families/anecdotes/style.css', 3),
    ('families/returnee/style.css', 3),
    ('families/soldier/style.css', 3),
    ('families/events/style.css', 4),
    ('families/characters/style.css', 4),
    ('families/storysets/style.css', 4),
    ('families/discs/style.css', 4),
    ('families/npc_bonds/style.css', 4),
    ('families/prologue/style.css', 4),
    ('families/battles_unmounted/style.css', 4),
    ('families/dispatch/style.css', 4),
    ('families/anecdotes/style.css', 4),
    ('families/returnee/style.css', 4),
    ('families/soldier/style.css', 4),
    ('theme/base.css', 4),
    ('theme/graph_base.css', 1),
    ('families/main/style.css', 3),
    ('families/events/style.css', 5),
    ('theme/graph_base.css', 2),
    ('families/main/style.css', 4),
    ('families/events/style.css', 6),
    ('theme/graph_base.css', 3),
    ('families/main/style.css', 5),
    ('families/events/style.css', 7),
    ('theme/graph_base.css', 4),
    ('families/main/style.css', 6),
    ('families/events/style.css', 8),
    ('theme/graph_base.css', 5),
    ('theme/base.css', 5),
]

_HERE = os.path.dirname(os.path.abspath(__file__))


def _css_blocks(rel_path):
    path = os.path.join(_HERE, rel_path.replace('/', os.sep))
    with open(path, encoding='utf-8') as f:
        text = f.read()
    text = text.replace('\r\n', '\n')   # 输出恒 LF（拆分前 site_css.py 同契约）
    if text.endswith('\n'):
        text = text[:-1]                  # 文件尾换行不属于任何块
    return text.split('\n' + BLOCK_SEP + '\n')


def assemble_css():
    """按 CSS_MANIFEST（发现序）拼接全部片段，返回与拆分前逐字节一致的 CSS。"""
    out = []
    for rel_path, n in CSS_MANIFEST:
        blocks = _css_blocks(rel_path)
        if not 1 <= n <= len(blocks):
            raise IndexError('%s 缺块 %d（共 %d 块）' % (rel_path, n, len(blocks)))
        out.append(blocks[n - 1])
    return '\n' + '\n'.join(out) + '\n'
