# -*- coding: utf-8 -*-
"""管线 Stage 2: 命令 IR —— 带稳定索引的 AVG 命令序列。

原 build_story.script_commands 产出 [(cmd, T-param)] 裸元组，动画帧折叠
（nonlog_repeats）用 id(param) 做命令身份。id() 依赖对象存活期，缓存一旦
重建就是悬空身份。Command IR 给每条命令一个文档序稳定 idx，作为唯一身份：

    Command(idx, cmd, param)

- idx: 在剧本内的 0 起文档序编号（仅计带 cmd 字段的记录，与旧元组序一致）；
- cmd: 命令名字符串（SetTalk/SetChoiceBegin/...）；
- param: 参数表 T(list)；非表参数包装为单元素 T（与旧 script_commands 相同）。

后续 pass（fold_animations 等）以 idx 集合表达"跳过哪些命令"，不再触碰 id()。
"""
from __future__ import annotations

from collections import namedtuple

from .lua_parser import T

Command = namedtuple('Command', ('idx', 'cmd', 'param'))


def build_commands(recs) -> list:
    """解析出的根表（T 记录序列）→ [Command]。

    与旧 script_commands 内联循环逐行为等价：只收带非空 cmd 的记录，
    param 缺省/标量时包装为 T。
    """
    out: list = []
    for r in recs:
        if isinstance(r, T) and r.get('cmd'):
            p = r.get('param')
            out.append(Command(len(out), r.get('cmd'),
                               p if isinstance(p, T) else T([] if p is None else [p])))
    return out
