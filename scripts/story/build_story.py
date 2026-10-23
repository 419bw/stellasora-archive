# -*- coding: utf-8 -*-
"""
Story-only extractor for Stella Sora narrative content.

Covers three modules and nothing else:
  * main story chapters        (Story.json / StoryChapter.json  -> STm*.lua)
  * event story chapters       (ActivityStory.json              -> STev*.lua)
  * in-battle bubble dialogue  (BBm*.lua, attached by chapter + Index code)

Unlike the legacy generator this reads the Lua command tables with a real parser
(nested tables, string group ids) instead of regexes, so `SetChoiceBegin`,
`SetPhoneMsg`, `SetBubble` and `SetSceneHeading` are no longer silently dropped.

Usage: python scripts/build_story.py
Output: story_docs/
"""

import sys, os, re, json, shutil, collections

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, SCRIPT_DIR)
import graph_layout
import chapter_path

sys.stdout.reconfigure(encoding='utf-8')
OUT = os.path.join(ROOT, 'story_docs')

# 主角域常量（PROTAG_ID/PROTAG_NAME）已随语义 pass 移入 pipeline/domain.py

# Stages whose own StoryId carries a `BTnn` battle token that disagrees with the display
# code the localization table publishes for them (upstream official labelling slip).
# Filled by build_main(), reported in _battle_reconciliation.md.
# （Phase B-0 起改记入 SidecarSink.code_mismatches；此处暂留模块级。）
CODE_MISMATCHES = []

# ============================================================== Lua table parser
# 解析器已拆分为 pipeline/lua_lexer.py（词法，token 流带 SourcePos）与
# pipeline/lua_parser.py（语法，递归下降 → T(list)）；剧本解析（command_ir 的
# build_commands）改由 context.DataContext.script_commands 提供（Phase A），
# 此处不再保留兼容壳（对 git 4496bd1 原实现做过 588 Config + AvgCharacter
# 预设全量对拍）。
from pipeline.text_rules import clean_text  # noqa: E402
from pipeline.pagedoc import PageDoc  # noqa: E402
from pipeline.render_md import page_markdown  # noqa: E402
import phone_chat  # noqa: E402
# 表懒加载 + 共享服务一次构造注入（import 无副作用；族取数经 ctx）。
from context import DataContext, lang_of, rows_of, field_lang  # noqa: E402


# ================================================================= data loading
# 约 40 张 BIN/LANG 表与全部共享服务（TextCompiler / SpeakerResolver /
# ConditionCatalog / 剧本解析缓存 / character_name）的加载移入
# context.DataContext：按 (scope, name) 懒加载 + 进程内缓存，编排器构造一次
# 经 ctx 注入，族模块不得自行构造。text rules 与 command processing 均已随
# pipeline 拆分移出（见原注释）；extract_script 即 ctx.extract_script。


# ==================================================================== rendering
# beat 渲染（render_beats→beat_lines）与页面骨架（section_doc→page_markdown）
# 已移入 pipeline/render_md.py（Markdown 后端，Phase 1d）；页面文档结构统一为
# pipeline/pagedoc.py 的 PageDoc IR，同时落盘 story_docs/_beats/ 侧车供
# Phase 2 的 HTML 后端直渲。


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text if text.endswith("\n") else text + "\n")


def safe_name(s):
    return re.sub(r'[\\/:*?"<>|]', '_', s).strip()


# Phase B 混合调度中间态：已搬迁族经 SidecarSink 记录，但累加器容器注入本文件的
# 模块级列表/集合（未搬迁族仍写同一批累加器），从而保持 sections.json /
# search.json/_coverage 的字节序与页面追加序不变。全部已搬迁族共用同一个 sink
# 实例（battle_map/skipped/code_mismatches 是跨族对账数据，main 写、aggregate 读）；
# 最后一族搬完后（Phase C）整体删除。
_SINK = None


def _migrated_sink(ctx):
    global _SINK
    if _SINK is None:
        import sink as _sink_mod
        _SINK = _sink_mod.SidecarSink(ctx.out, ctx.lang_table('LANG', 'Story'), containers={
            'pages': _PAGES, 'search_entries': _SEARCH_ENTRIES,
            'chapter_nodes': _CHAPTER_NODES, 'rendered': _RENDERED,
            'battle_map': [], 'skipped': [], 'code_mismatches': CODE_MISMATCHES,
        })
    return _SINK


# ============================================================ structured sidecars
# The site is built from these records, never from the Markdown, so both artefacts come
# out of the same parse pass and cannot drift apart.
_PAGES = []
_SEARCH_ENTRIES = []
_CHAPTER_NODES = collections.OrderedDict()
_RENDERED = set()
# ---------------------------------------------------------- other story families
# rows_of / field_lang 已移入 context.py（ctx.rows / ctx.field_lang 同语义）。
# activity_name / build_events 已迁至 families/events.py（Phase B-11）。


def dump_json(name, obj):
    write(os.path.join(OUT, '_data', name),
          json.dumps(obj, ensure_ascii=False, indent=1) + "\n")


def write_data(ctx):
    """Site-facing structure: chapter graphs, the page index, search, personality axes."""
    BIN_CHAPTER = ctx.table('BIN', 'StoryChapter')
    LANG_STORY_CHAP = ctx.lang_table('LANG', 'StoryChapter')
    BIN_PERSONALITY = ctx.table('BIN', 'StoryPersonality')
    LANG_PERSONALITY = ctx.lang_table('LANG', 'StoryPersonality')
    chapters = []
    for ch, nodes in _CHAPTER_NODES.items():
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
             'pages': len(_PAGES)}
    dump_json('chapters.json', {'meta': dict(total, source='Story.json',
                                             edge_field='ParentStoryId',
                                             story_lines=[ctx.story_lines[k] for k in sorted(ctx.story_lines)]),
                                'chapters': chapters})
    dump_json('sections.json', {'meta': dict(total, families=sorted({p['family'] for p in _PAGES})),
                                'pages': _PAGES})
    dump_json('search.json', {'meta': {'pages': len(_SEARCH_ENTRIES)},
                              'entries': _SEARCH_ENTRIES})
    dump_json('personality.json', {
        'axes': [{'id': r['Id'], 'name': field_lang(LANG_PERSONALITY, r),
                  'color': r.get('Color'), 'icon': r.get('Icon')}
                 for r in rows_of(BIN_PERSONALITY)],
        'note': '表内只有三轴定义；玩家当前倾向值来自存档，解包数据里没有。'})
    return total


def write_coverage(ctx):
    """Every script in the pack is either rendered or named here with its mount source."""
    rendered = set(_RENDERED)
    alls = sorted(f[:-4] for f in os.listdir(ctx.cfg) if f.endswith('.lua'))
    mounts = collections.defaultdict(set)
    for tbl, fld in (('Story', 'AvgLuaName'), ('ActivityStory', 'AvgLuaName'),
                     ('Plot', 'AvgId'), ('NPCAffinityPlot', 'avgId'), ('DiscIP', 'AvgId'),
                     ('StorySetSection', 'AVGId'), ('Chat', 'AVGId'),
                     ('AgentSpecialPerformance', 'Avg'), ('ActivityReturnee', 'AVG')):
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
    write(os.path.join(OUT, '_coverage.md'), "\n".join(lines) + "\n")
    return len(alls), len(alls) - len(todo), len(todo)


def write_diagnostics(ctx, battle_map, skipped, unattached):
    """story_docs/_diagnostics.json —— 上游数据异常与编译器兜底的机器可读登记。

    与人读的 _battle_reconciliation.md 互补。所有分类都在解析/构建过程中实时登记进
    进程级 DIAG（pipeline/diagnostics.py），本函数只做两件事：把四个构建期分类补登
    进去，再整份序列化。分类口径、键序、note 文案全部由 CATEGORIES 注册表生成，
    不在这里手抄——所以"加了兜底忘记写说明"会直接 KeyError，而不是静默进侧车。
    同一输入重建字节稳定（list 按去重键排序，count 为累计值）。
    """
    for sid, story, suffix, disp, stem, cond, c in CODE_MISMATCHES:
        ctx.diag.add('code_mismatches', key=(sid, story, suffix, disp, stem, cond, c),
                 sid=sid, story_id=story, storyid_suffix=suffix, display_code=disp,
                 bubble_stem=stem, condition_id=cond, chapter=c)
    for b in battle_map:
        if b[2] == 'MISSING':
            ctx.diag.add('battle_bubble_missing', key=(b[0], b[1], b[3]),
                     sid=b[0], expected_stem=b[1], chapter=b[3])
    ctx.diag.extend('unattached_bbm_scripts', unattached)
    for c, sid, stem, t, kind in skipped:
        ctx.diag.add('rows_without_script', key=(c, sid, stem, t, kind),
                 chapter=c, sid=sid, stem=stem, title=t, kind=kind)
    obj = {'note': ctx.diag.note()}
    obj.update(ctx.diag.as_dict())
    write(os.path.join(OUT, '_diagnostics.json'),
          json.dumps(obj, ensure_ascii=False, indent=1) + "\n")
    return obj


def main():
    # story_docs/ is fully generated: a mount change removes pages, and leaving the old
    # files behind would let the validators read a tree this script never wrote
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    # 上游数据与共享服务：构造一次，族经 ctx 取数（Phase A；ScopedDataContext
    # NEEDS 门控在 Phase C 的 FAMILY_ORDER 循环上线）
    ctx = DataContext(ROOT, out=OUT)
    # Phase B 混合调度中间态：已搬迁族走 families/<id>.build(ctx, sink)（sink 侧车），
    # 未搬迁族仍走本文件内的旧函数（record_page 等模块级累加器）。每搬完一族，
    # 此处与旧函数定义各删一处；Phase C 起全部收进 aggregate 前的 FAMILY_ORDER 循环。
    print("Parsing official AVG scripts (main story)...")
    import families.main as _fam_main
    _sink = _migrated_sink(ctx)
    mstats = _fam_main.build(ctx, _sink)
    battle_map = _sink.battle_map
    skipped = _sink.skipped
    mstats['empty'] = len(skipped)
    print("  sections=%(sections)s 战斗气泡关卡=%(bubbles)s 台词行=%(lines)s 无剧本关卡行=%(empty)s" % mstats)
    print("Parsing event story scripts...")
    import families.events as _fam_events
    _fam_events.build(ctx, _migrated_sink(ctx))
    print("Parsing 角色个人剧情 (characters) scripts...")
    import families.characters as _fam_characters
    _fam_characters.build(ctx, _migrated_sink(ctx))
    print("Parsing 星塔 NPC 好感剧情 (npc_bonds) scripts...")
    import families.npc_bonds as _fam_npc_bonds
    _fam_npc_bonds.build(ctx, _migrated_sink(ctx))
    # 已搬迁族（顺序须与 FAMILY_ORDER 一致：discs → storysets → prologue → dispatch
    # → anecdotes → returnee → soldier → chat）
    print("Parsing 唱片剧情 (discs) scripts...")
    import families.discs as _fam_discs
    _fam_discs.build(ctx, _migrated_sink(ctx))
    print("Parsing 故事集支线 (storysets) scripts...")
    import families.storysets as _fam_storysets
    _fam_storysets.build(ctx, _migrated_sink(ctx))
    # 已搬迁族（顺序须与 FAMILY_ORDER 一致：prologue → dispatch → anecdotes
    # → returnee → soldier → chat）
    print("Parsing 序章 (prologue) scripts...")
    import families.prologue as _fam_prologue
    _fam_prologue.build(ctx, _migrated_sink(ctx))
    print("Parsing 委托结算演出 (dispatch) scripts...")
    import families.dispatch as _fam_dispatch
    _fam_dispatch.build(ctx, _migrated_sink(ctx))
    print("Parsing 逸闻笔记 (anecdotes) scripts...")
    import families.anecdotes as _fam_anecdotes
    _fam_anecdotes.build(ctx, _migrated_sink(ctx))
    print("Parsing 归星漫途 (returnee) scripts...")
    import families.returnee as _fam_returnee
    _fam_returnee.build(ctx, _migrated_sink(ctx))
    print("Parsing 尖兵陷阵 (soldier) scripts...")
    import families.soldier as _fam_soldier
    _fam_soldier.build(ctx, _migrated_sink(ctx))
    print("Parsing 心链 (phone chat) scripts...")
    import families.chat as _fam_chat
    _fam_chat.build(ctx, _migrated_sink(ctx))
    attached = [b for b in battle_map if b[2] == 'attached']
    missing = [b for b in battle_map if b[2] == 'MISSING']
    used = {b[1] for b in attached}
    import families.orphan_battles as _fam_orphan
    ostats, unattached = _fam_orphan.build(ctx, _migrated_sink(ctx), used)
    chlab = {int(c['Id']): (clean_text(lang_of(ctx.lang_table('LANG', 'StoryChapter'), c.get('Name', '')))
                            or '表 Id %s' % c['Id']) for c in ctx.table('BIN', 'StoryChapter').values()}
    miss_ch = sorted({chlab.get(b[3], b[3]) for b in missing})
    print("  无关卡引用的战斗气泡剧本：脚本=%d 气泡=%d" % (ostats['sections'], ostats['lines']))
    dstats = write_data(ctx)
    print("结构化侧车：章=%d 节点=%d 页=%d" % (dstats['chapters'], dstats['nodes'], dstats['pages']))
    total, done, todo = write_coverage(ctx)
    print("剧本覆盖对账：包内 %d 个，已渲染 %d 个，未渲染 %d 个" % (total, done, todo))

    lines = ["# 战斗气泡剧本对账", "",
             "- 战斗关卡行：%d，挂到气泡剧本：%d，包内暂无剧本：%d" % (len(battle_map), len(attached), len(missing)),
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
    if CODE_MISMATCHES:
        lines += ["## 官方显示代号与 StoryId 编号不一致的关卡行（上游数据笔误）", "",
                  "这些行的本地化显示代号和它自己的 `StoryId` / `ConditionId` / `FloorId` 编号是交叉的。"
                  "本站按 `StoryId` 一侧取剧本（脚本内容、条件、楼层号三者互相印证），"
                  "**展示代号仍照抄官方原文**，仅在此登记，不去改动官方文字。", ""]
        lines += ["- 第 %s 章 `%s`：StoryId `%s`（%s）↔ 显示代号 `%s`；"
                  "ConditionId `%s`，实际挂接 `%s`"
                  % (c, sid, story, suffix, disp, cond, stem)
                  for sid, story, suffix, disp, stem, cond, c in CODE_MISMATCHES] + [""]
    if unattached:
        lines += ["## 未被任何关卡引用的 BBm 剧本", ""]
        lines += ["- [`%s`](battles_unmounted/%s.md)" % (s, safe_name(s)) for s in unattached]
        lines.append("")
    if skipped:
        lines += ["## 关卡表已列出、包内无剧本的关卡行（未开放线路）", ""]
        lines += ["- 第 %s 章 `%s` %s（%s，剧本代号 `%s`）" % (c, sid, t, kind, stem) for c, sid, stem, t, kind in skipped]
    write(os.path.join(OUT, '_battle_reconciliation.md'), "\n".join(lines))
    djson = write_diagnostics(ctx, battle_map, skipped, unattached)
    print("诊断侧车 _diagnostics.json：%s"
          % (' '.join('%s=%s' % kv for kv in sorted(ctx.diag.nonzero().items()))
             or '本次构建无任何兜底触发'))
    print("Wrote %s" % OUT)


if __name__ == '__main__':
    # --out 仅供校验用（tests/story/validate_story.py 的 P3 组重建到临时目录后逐字节
    # 比对 _diagnostics.json）。默认仍是 story_docs/，行为与加参数前完全一致。
    import argparse
    ap = argparse.ArgumentParser(description='解析上游数据源并生成 story_docs/')
    ap.add_argument('--out', default=OUT,
                    help='输出目录（默认 %s；仅校验用临时重建时才覆盖）' % OUT)
    args = ap.parse_args()
    OUT = args.out
    main()
