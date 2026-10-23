# -*- coding: utf-8 -*-
"""aggregate：侧车汇总落盘与剧本覆盖对账（Phase C-2 上线）。

从编排器 build_story.py 拆出（编排器只负责建 ctx/sink、按 FAMILY_ORDER 调族、
打印收尾）：

  * write_data      —— chapters/sections/search/personality 四份站点侧车；
  * write_coverage  —— _coverage.md；挂载对从各族 MOUNTS 声明自动汇总，
                       消灭原先硬编码的 9 个 (表, 字段) 对（双份真相）；
  * write_diagnostics —— _diagnostics.json；
  * write_reconciliation —— 人读 _battle_reconciliation.md（对账输入全部
                       来自 sink：battle_map/skipped/code_mismatches）。
"""
import os
import re
import json
import collections

import graph_layout
import chapter_path

from context import lang_of, rows_of, field_lang
from sink import write, safe_name
from families import FAMILY_ORDER

# 挂载对的中文挂载源说明（_coverage.md 的「挂载来源」列；MOUNTS 声明提供
# (表, 字段) 机器可读对账，本表只提供给人看的文案）。
_MOUNT_SRC_LABEL = {
    'Story': 'Story.AvgLuaName', 'ActivityStory': 'ActivityStory.AvgLuaName',
    'Plot': 'Plot.AvgId', 'NPCAffinityPlot': 'NPCAffinityPlot.avgId',
    'DiscIP': 'DiscIP.AvgId', 'StorySetSection': 'StorySetSection.AVGId',
    'Chat': 'Chat.AVGId', 'AgentSpecialPerformance': 'AgentSpecialPerformance.Avg',
    'ActivityReturnee': 'ActivityReturnee.AVG',
}


def dump_json(out, name, obj):
    write(os.path.join(out, '_data', name),
          json.dumps(obj, ensure_ascii=False, indent=1) + "\n")


def write_data(ctx, sink):
    """Site-facing structure: chapter graphs, the page index, search, personality axes."""
    BIN_CHAPTER = ctx.table('BIN', 'StoryChapter')
    LANG_STORY_CHAP = ctx.lang_table('LANG', 'StoryChapter')
    BIN_PERSONALITY = ctx.table('BIN', 'StoryPersonality')
    LANG_PERSONALITY = ctx.lang_table('LANG', 'StoryPersonality')
    chapters = []
    for ch, nodes in sink.chapter_nodes.items():
        cdef = BIN_CHAPTER.get(str(ch), {})
        name = lang_of(LANG_STORY_CHAP, cdef.get('Name', ''))
        title = lang_of(LANG_STORY_CHAP, cdef.get('Desc', ''))
        edges = None
        if any(n['parents'] for n in nodes):
            # coordinates ship with the data so the layout is reviewable (and checkable)
            # before any HTML exists
            placed = graph_layout.layout([{'sid': n['sid'], 'story_id': n['story_id'],
                                           'parents': n['parents'], 'code': n['code']}
                                          for n in nodes])
            pos = {p['sid']: p for p in placed['nodes']}
            for n in nodes:
                n.update(col=pos[n['sid']]['col'], lane=pos[n['sid']]['lane'],
                         x=pos[n['sid']]['x'], y=pos[n['sid']]['y'])
            edges = placed['edges']
        chapters.append({
            'id': ch,                                   # table id, NOT the in-game number
            'no': cdef.get('Index'),                    # official chapter code, '' for 特别篇
            'name': name, 'title': title,
            'year': lang_of(LANG_STORY_CHAP, cdef.get('ChapterYear', '')),
            'prev_stories': [p for p in (cdef.get('PrevStories') or []) if isinstance(p, str)],
            'unlock_show_story_id': cdef.get('UnlockShowStoryId'),
            'open_time': cdef.get('OpenTime'),
            'folder': 'main/chapter_%02d_%s' % (ch, safe_name(title or name or 'chapter')),
            'special': chapter_path.is_special(cdef),   # StoryChapter.Type == 2
            'story_line': chapter_path.chapter_line_info(cdef, ctx.story_lines),
            'slug': ctx.chapter_slugs[ch],         # 站点 URL 目录，全局唯一
            'edge_source': 'ParentStoryId' if any(n['parents'] for n in nodes) else 'none',
            'time_slots': {str(i): v for i, v in sorted(ctx.time_slots(ch).items())},
            'geometry': None if edges is None else {
                'columns': placed['columns'], 'width': placed['width'],
                'height': placed['height'], 'roots': list(placed['roots']),
                'card': [graph_layout.CARD_W, graph_layout.CARD_H],
                'step_x': graph_layout.CARD_W + graph_layout.GUT_X,
                'step_y': graph_layout.CARD_H + graph_layout.ROW_H,
                'edges': [list(e) for e in edges]},
            'nodes': sorted(nodes, key=lambda n: n['sid']),
        })
    total = {'chapters': len(chapters), 'nodes': sum(len(c['nodes']) for c in chapters),
             'pages': len(sink.pages)}
    dump_json(ctx.out, 'chapters.json', {'meta': dict(total, source='Story.json',
                                                      edge_field='ParentStoryId',
                                                      story_lines=[ctx.story_lines[k]
                                                                   for k in sorted(ctx.story_lines)]),
                                         'chapters': chapters})
    dump_json(ctx.out, 'sections.json', {'meta': dict(total,
                                                      families=sorted({p['family']
                                                                        for p in sink.pages})),
                                         'pages': sink.pages})
    dump_json(ctx.out, 'search.json', {'meta': {'pages': len(sink.search_entries)},
                                       'entries': sink.search_entries})
    dump_json(ctx.out, 'personality.json', {
        'axes': [{'id': r['Id'], 'name': field_lang(LANG_PERSONALITY, r),
                  'color': r.get('Color'), 'icon': r.get('Icon')}
                 for r in rows_of(BIN_PERSONALITY)],
        'note': '表内只有三轴定义；玩家当前倾向值来自存档，解包数据里没有。'})
    return total


def family_mounts():
    """汇总全部族的 MOUNTS 声明 -> [(表, 字段)]（保序去重）。

    MOUNTS 是族模块文件头的声明面；新增族只改族自己一处，coverage 自动收编
    （设计 4.4/5.4：挂载来源不得双份真相）。
    """
    import importlib
    seen, out = set(), []
    for fam_id in FAMILY_ORDER:
        mod = importlib.import_module('families.%s' % fam_id)
        for pair in getattr(mod, 'MOUNTS', ()):
            key = (pair[0], pair[1])
            if key not in seen:
                seen.add(key)
                out.append(key)
    return out


def write_coverage(ctx, sink):
    """Every script in the pack is either rendered or named here with its mount source."""
    rendered = set(sink.rendered)
    alls = sorted(f[:-4] for f in os.listdir(ctx.cfg) if f.endswith('.lua'))
    mounts = collections.defaultdict(set)
    for tbl, fld in family_mounts():
        for r in ctx.table('BIN', tbl).values():
            v = r.get(fld)
            if isinstance(v, str):
                mounts[v].add(tbl)
    fam = lambda s: re.match(r'[A-Za-z]+', s).group(0)
    gap = collections.defaultdict(collections.Counter)
    for s in alls:
        gap[fam(s)]['all'] += 1
        gap[fam(s)]['done' if s in rendered else 'todo'] += 1
    src = {'STm': 'Story.AvgLuaName', 'STev': 'ActivityStory.AvgLuaName',
           'CG': 'Plot / NPCAffinityPlot / DiscIP', 'STsp': 'StorySetSection.AVGId',
           'BBm': '无表引用，客户端按「关卡代号里的章号+关卡编号」拼名',
           'PM': 'Chat.AVGId', 'DP': 'AgentSpecialPerformance.Avg', 'GD': '无表引用',
           'ST': 'ActivityReturnee.AVG（ST_sys_reengagement）；ST_sys_soldier_intro 无表引用'}
    note = {'PM': '心链聊天全篇，已提取至 `_chat/` 人读存档（不进站点，故不计入已渲染）',
            'DP': '委托结算演出，已入 dispatch/（按结算演出段收录，见 _dev 手册 7.4）',
            'GD': '抽卡演出小段（4 句），表不引用，待决',
            'BBm': '战斗气泡，含 7 个无表引用者（序章一战 + 第七章追加战）',
            'STm': '含序章 STm00_*，已渲染进 prologue/',
            'ST': 'ST_sys_* 系统流程剧本：回归活动《归星漫途》入 returnee/，尖兵陷阵开场入 soldier/'}
    todo = [s for s in alls if s not in rendered]
    lines = ["# 剧本覆盖对账", "",
             "- 包内 AVG 剧本：%d　已渲染：%d　未渲染：%d" % (len(alls), len(alls) - len(todo), len(todo)),
             "",
             "| 剧本前缀 | 文件数 | 已渲染 | 未渲染 | 挂载来源 | 备注 |",
             "| --- | --- | --- | --- | --- | --- |"]
    for f in sorted(gap, key=lambda x: -gap[x]['all']):
        lines.append("| `%s_*` | %d | %d | %d | %s | %s |"
                     % (f, gap[f]['all'], gap[f]['done'], gap[f]['todo'],
                        src.get(f, '-'), note.get(f, '')))
    lines += ["", "## 未渲染剧本清单", ""]
    lines += ["- `%s`（挂载表：%s）" % (s, "、".join(sorted(mounts.get(s, []))) or "无")
              for s in todo]
    write(os.path.join(ctx.out, '_coverage.md'), "\n".join(lines) + "\n")
    return len(alls), len(alls) - len(todo), len(todo)


def write_diagnostics(ctx, sink):
    """story_docs/_diagnostics.json —— 上游数据异常与编译器兜底的机器可读登记。

    与人读的 _battle_reconciliation.md 互补。所有分类都在解析/构建过程中实时登记进
    进程级 DIAG（pipeline/diagnostics.py），本函数只做两件事：把四个构建期分类补登
    进去，再整份序列化。分类口径、键序、note 文案全部由 CATEGORIES 注册表生成，
    不在这里手抄——所以"加了兜底忘记写说明"会直接 KeyError，而不是静默进侧车。
    同一输入重建字节稳定（list 按去重键排序，count 为累计值）。
    """
    for sid, story, suffix, disp, stem, cond, c in sink.code_mismatches:
        ctx.diag.add('code_mismatches', key=(sid, story, suffix, disp, stem, cond, c),
                     sid=sid, story_id=story, storyid_suffix=suffix, display_code=disp,
                     bubble_stem=stem, condition_id=cond, chapter=c)
    for b in sink.battle_map:
        if b[2] == 'MISSING':
            ctx.diag.add('battle_bubble_missing', key=(b[0], b[1], b[3]),
                         sid=b[0], expected_stem=b[1], chapter=b[3])
    ctx.diag.extend('unattached_bbm_scripts', sink.unattached)
    for c, sid, stem, t, kind in sink.skipped:
        ctx.diag.add('rows_without_script', key=(c, sid, stem, t, kind),
                     chapter=c, sid=sid, stem=stem, title=t, kind=kind)
    obj = {'note': ctx.diag.note()}
    obj.update(ctx.diag.as_dict())
    write(os.path.join(ctx.out, '_diagnostics.json'),
          json.dumps(obj, ensure_ascii=False, indent=1) + "\n")
    return obj


def write_reconciliation(ctx, sink):
    """人读 _battle_reconciliation.md：战斗气泡挂载对账（输入全部来自 sink）。"""
    from pipeline.text_rules import clean_text
    battle_map, skipped = sink.battle_map, sink.skipped
    unattached = sink.unattached
    attached = [b for b in battle_map if b[2] == 'attached']
    missing = [b for b in battle_map if b[2] == 'MISSING']
    chlab = {int(c['Id']): (clean_text(lang_of(ctx.lang_table('LANG', 'StoryChapter'),
                                                c.get('Name', '')))
                            or '表 Id %s' % c['Id'])
             for c in ctx.table('BIN', 'StoryChapter').values()}
    miss_ch = sorted({chlab.get(b[3], b[3]) for b in missing})
    lines = ["# 战斗气泡剧本对账", "",
             "- 战斗关卡行：%d，挂到气泡剧本：%d，包内暂无剧本：%d"
             % (len(battle_map), len(attached), len(missing)),
             "- 有剧本但无关卡引用（全文见 `battles_unmounted/`）：%d 个" % len(unattached), "",
             "> 包内暂无剧本的战斗关卡行分布在：%s。"
             "其中最新一章的关卡表先行、后续线路的剧本随版本补进客户端，因此不是解包遗漏。"
             % '、'.join('《%s》' % x if not str(x).startswith('表') else str(x) for x in miss_ch), "",
             "> BBm 剧本从不出现在任何配置表里，客户端按「关卡代号（StoryId）里的章号 + 编号」拼出文件名："
             "`BAm07_01` → `BBm07_BT01`，`BAm06x5_01` → `BBm06x5_BT01`，`BAm09_BT03` → `BBm09_BT03`。"
             "两段都跟关卡自己的代号（StoryId），**都不是 `Story.Chapter`，也不是本地化表里的显示代号**："
             "特别篇的关卡记作 `06x5`，而表把它的 `Chapter` 记成 7，用表号拼名会把第七章的气泡挂到特别篇上；"
             "第九章 `1010`/`1013` 两行的显示代号与自身 StoryId 编号交叉（见下节），用显示代号拼名会把两场战斗的"
             "气泡对白整袋取反。判据是可核对的：每个 BBm 剧本的说话人集合都出现在其 StoryId 章号所指那一章的正篇演员表里，"
             "而特别篇正篇没有夏花/小禾/千都世，所以 `BBm07_*` 不属于它；"
             "特别篇的两场战斗（`BAm06x5_01`/`BAm06x5_02`）在包里确实没有气泡剧本。"
             "仅当 StoryId 后缀不是战斗编号（第一至第五章的顺序名如 `BAm01_05`）时才回退到显示代号。", "",
             "> `BBm00_01`–`BBm00_06` 的说话人只有鸢尾/琥珀/尘沙，内容与序章剧本 `STm00_01`《最初的起点》"
             "同为一场沙漠星塔许愿箱之战，即注册流程里打的那一关；关卡表里没有对应行。", ""]
    if missing:
        lines += ["## 无气泡剧本的战斗关卡", ""]
        lines += ["- `%s`（%s，按命名规则期望：%s）" % (b[0], chlab.get(b[3], b[3]), b[1])
                  for b in missing] + [""]
    if sink.code_mismatches:
        lines += ["## 官方显示代号与 StoryId 编号不一致的关卡行（上游数据笔误）", "",
                  "这些行的本地化显示代号和它自己的 `StoryId` / `ConditionId` / `FloorId` 编号是交叉的。"
                  "本站按 `StoryId` 一侧取剧本（脚本内容、条件、楼层号三者互相印证），"
                  "**展示代号仍照抄官方原文**，仅在此登记，不去改动官方文字。", ""]
        lines += ["- 第 %s 章 `%s`：StoryId `%s`（%s）↔ 显示代号 `%s`；"
                  "ConditionId `%s`，实际挂接 `%s`"
                  % (c, sid, story, suffix, disp, cond, stem)
                  for sid, story, suffix, disp, stem, cond, c in sink.code_mismatches] + [""]
    if unattached:
        lines += ["## 未被任何关卡引用的 BBm 剧本", ""]
        lines += ["- [`%s`](battles_unmounted/%s.md)" % (s, safe_name(s)) for s in unattached]
        lines.append("")
    if skipped:
        lines += ["## 关卡表已列出、包内无剧本的关卡行（未开放线路）", ""]
        lines += ["- 第 %s 章 `%s` %s（%s，剧本代号 `%s`）"
                  % (c, sid, t, kind, stem) for c, sid, stem, t, kind in skipped]
    write(os.path.join(ctx.out, '_battle_reconciliation.md'), "\n".join(lines))
