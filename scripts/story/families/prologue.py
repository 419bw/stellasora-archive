# -*- coding: utf-8 -*-
"""序章族（STm00_*《最初的起点》）。

STm00_* is the opening 序章《最初的起点》played during registration.
Story lists no chapter 0 row, so the stage table cannot mount it; the script's own
SetIntro carries the official episode labels, and BBm00_* are the battle bubbles of
that same desert mission (same trio, same 许愿箱).

NEEDS：目录扫描型（os.listdir(ctx.cfg) 匹配 STm00_* 前缀），无表依赖。
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
    stems = sorted(f[:-4] for f in os.listdir(ctx.cfg) if f.startswith('STm00_'))
    battle = sorted(f[:-4] for f in os.listdir(ctx.cfg) if f.startswith('BBm00_'))
    for stem in stems:
        parsed = ctx.extract_script(stem)
        if not parsed:
            continue
        info = [
            "- **所属**：序章《%s》" % (parsed['meta']['title'] or '最初的起点'),
            "- **话数**：%s" % (parsed['meta']['episode'] or '序'),
            "- **AVG 剧本**：`%s`" % stem,
            "- **挂载状态**：Story 表从第 1 章起列关卡，序章由注册流程直接调用，故表内无行",
        ]
        if stem.startswith('STm00_01') and battle:
            info.append("- **同场战斗气泡**：%s（见 `battles_unmounted/`）" % "、".join(battle))
        path = os.path.join(ctx.out, 'prologue', 'sections',
                            safe_name('%s_%s' % (stem, parsed['meta']['title'] or stem)) + '.md')
        doc = PageDoc("# %s %s" % (parsed['meta']['episode'] or '序',
                                   parsed['meta']['title'] or ''),
                      info, parsed['meta']['recap'], "逐句台词", parsed['beats'],
                      info_title="序章信息", meta=parsed['meta'])
        write(path, page_markdown(doc))
        sink.record_page('prologue', path, doc, stem, parsed['meta']['title'] or stem,
                         code=parsed['meta']['episode'] or '序',
                         group={'kind': 'prologue', 'id': 0, 'label': '序章'},
                         stems=[stem], page='prologue/%s.html' % stem)
        stats['sections'] += 1
        stats['lines'] += sum(1 for b in parsed['beats'] if b['k'] in ('talk', 'bubble'))
    return stats
