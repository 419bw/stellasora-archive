# -*- coding: utf-8 -*-
"""主线族：Story 表挂载的章节关卡（ST*）+ 战斗气泡（BB*）的挂载推断。

含三个对账记录（R1，全部经 sink.record_* 落 sink，编排器/聚合零特判）：
  * battle_map  —— 战斗关卡的气泡脚本挂载推断结果（attached / MISSING）；
  * skipped     —— 关卡表有行、包内无剧本的行；
  * code_mismatches —— 官方显示代号与 StoryId 交叉的上游笔误行。

bubble_stem_for / stem_code_mismatch 是本族私有推断逻辑（原 build_story 顶层
函数），随族搬迁；node_time 只在 record_node 用，归 sink。

NEEDS：BIN/LANG Story + BIN/LANG StoryChapter（章节元数据与 URL slug 来源
ctx.chapter_slugs，后者由 SHARED_NEEDS 审计）。
"""
import os
import re
import collections

from context import lang_of
from sink import safe_name, write, node_time
from pipeline.pagedoc import PageDoc
from pipeline.render_md import page_markdown
import chapter_path

NEEDS = (('BIN', 'Story'), ('LANG', 'Story'),
         ('BIN', 'StoryChapter'), ('LANG', 'StoryChapter'))
MOUNTS = (('Story', 'AvgLuaName'),)


def bubble_stem_for(ctx, story_id, code):
    """The client names a battle's bubble script after the battle token baked into the
    stage's own StoryId (BAm09_BT03 -> BBm09_BT03), not after Story.Chapter and not
    after the stage's display code. Two reasons the StoryId wins:
      * 特别篇 stages are `BAm06x5_*` while the table numbers that chapter 7 (already
        handled by taking the chapter token from the StoryId);
      * ch09 rows 1010/1013 carry a display code that is crossed against their own
        StoryId / ConditionId / FloorId (1010: StoryId BAm09_BT03, code BT02;
        1013: StoryId BAm09_BT02, code BT03). The pack proves the StoryId is right:
        BBm09_BT03 holds the 安琪/塔菲特 lines, BBm09_BT02 the 千都世 counter-ambush
        lines, matching ConditionId and FloorId, not the display codes.
    The display code is only a fallback for stages whose StoryId tail is not a battle
    token (ch01-ch05 sequential names such as BAm01_05, and 特别篇 BAm06x5_01)."""
    m = re.match(r'^BA([0-9a-zA-Z]+)_([^_]+)$', story_id or '')
    if not m:
        return None
    token = m.group(1)
    tail = re.sub(r'[^A-Za-z0-9]', '', m.group(2))
    if re.fullmatch(r'BT\d+', tail):
        return 'BB%s_%s' % (token, tail)
    # 顺序名关卡（ch01–ch05）与特别篇：StoryId 尾部不是战斗编号，只能退回显示代号。
    # 这是既定正常行为（docstring 与 _battle_reconciliation.md 有说明），但此前侧车里
    # 没有计数——按 speaker_inline_names 的惯例登记一个去重计数，上游若哪天开始给
    # 这些关卡补 BTnn 编号，diff 里立刻可见。
    ctx.diag.bump('bubble_stem_display_code_fallback',
                  key=(str(story_id or ''), str(code or '')))
    return 'BB%s_%s' % (token, re.sub(r'[^A-Za-z0-9]', '', code or ''))


def stem_code_mismatch(story_id, code):
    """True when a stage's own StoryId carries a `BTnn` battle token that disagrees
    with the display code the tables publish for it. That is an upstream (official)
    labelling slip, not ours: the script / ConditionId / FloorId all follow the
    StoryId, so the site must render the StoryId's script and merely print a note."""
    m = re.match(r'^BA[0-9a-zA-Z]+_([^_]+)$', story_id or '')
    if not m:
        return False
    tail = re.sub(r'[^A-Za-z0-9]', '', m.group(1))
    return bool(re.fullmatch(r'BT\d+', tail)) and tail != re.sub(r'[^A-Za-z0-9]', '', code or '')


def build(ctx, sink):
    BIN_CHAPTER = ctx.table('BIN', 'StoryChapter')
    BIN_STORY = ctx.table('BIN', 'Story')
    LANG_STORY = ctx.lang_table('LANG', 'Story')
    LANG_STORY_CHAP = ctx.lang_table('LANG', 'StoryChapter')
    chapters = {int(k): v for k, v in BIN_CHAPTER.items()}
    rows = collections.defaultdict(list)
    for r in BIN_STORY.values():
        rows[int(r['Chapter'])].append(r)
    stats = collections.Counter()
    for ch in sorted(chapters):
        cdef = chapters[ch]
        clabel = lang_of(LANG_STORY_CHAP, cdef.get('Name', ''))
        ctitle = lang_of(LANG_STORY_CHAP, cdef.get('Desc', ''))
        cyear = lang_of(LANG_STORY_CHAP, cdef.get('ChapterYear', ''))
        folder = os.path.join(ctx.out, 'main', 'chapter_%02d_%s' % (ch, safe_name(ctitle or clabel or 'chapter')))
        sdir = os.path.join(folder, 'sections')
        # Collect released story/bubble stems in this chapter
        released_stems = set()
        for r_cand in rows.get(ch, []):
            st = r_cand.get('StoryId')
            idx_cand = lang_of(LANG_STORY, r_cand.get('Index', ''))
            if st and ctx.script_commands(st):
                released_stems.add(st)
            bcand = bubble_stem_for(ctx, st, idx_cand)
            if bcand and ctx.script_commands(bcand):
                released_stems.add(st)

        for r in sorted(rows.get(ch, []), key=lambda x: x['Id']):
            idx = lang_of(LANG_STORY, r.get('Index', ''))
            title = lang_of(LANG_STORY, r.get('Title', ''))
            hint = lang_of(LANG_STORY, r.get('Desc', ''))
            aim = lang_of(LANG_STORY, r.get('Aim', ''))
            stem = r.get('StoryId')
            parsed = ctx.extract_script(stem) if stem else None
            bubbles = None
            bubble_stem = None
            if parsed is None and r.get('IsBattle'):
                cand = bubble_stem_for(ctx, stem, idx)
                if cand and ctx.script_commands(cand):
                    bubbles = ctx.extract_script(cand)
                    bubble_stem = cand
                    sink.record_battle_map((stem, cand, 'attached', ch))
                else:
                    sink.record_battle_map((stem, cand, 'MISSING', ch))
                if stem_code_mismatch(stem, idx):
                    tail = re.sub(r'[^A-Za-z0-9]', '', re.match(r'^BA[0-9a-zA-Z]+_([^_]+)$', stem).group(1))
                    print('!! 官方显示代号与 StoryId 编号不一致（气泡脚本按 StoryId 取）: '
                          'sid=%s story=%s suffix=%s display=%s stem=%s'
                          % (r['Id'], stem, tail, idx, cand))
                    sink.record_code_mismatch((r['Id'], stem, tail, idx, cand,
                                               r.get('ConditionId'), ch))
            if parsed is None and not bubbles:
                # Dynamic pure battle stage detection:
                # A battle stage in an open chapter whose parents are released (or empty at chapter start)
                # is an official pure battle stage that receives an independent archive page.
                parents = [p for p in (r.get('ParentStoryId') or []) if isinstance(p, str)]
                is_valid_battle = (bool(r.get('IsBattle')) and len(released_stems) > 0
                                   and (not parents or all(p in released_stems for p in parents)))
                if is_valid_battle:
                    page = chapter_path.node_page(ctx.chapter_slugs[ch], stem)
                    sink.record_node(ch, r, page, None)
                    continue
                sink.record_node(ch, r, None, None)
                sink.record_skipped((ch, r['Id'], stem, title, '战斗关卡' if r.get('IsBattle') else '剧情关卡'))
                continue
            page = chapter_path.node_page(ctx.chapter_slugs[ch], stem)
            body_src = bubbles or parsed
            sink.record_node(ch, r, page, bubble_stem, body_src['beats'])
            info = [
                "- **所属篇章**：%s《%s》（%s）" % (clabel or '第 %d 章' % ch, ctitle, cyear),
                "- **关卡 ID**：`%s`　**编号**：`%s`" % (r['Id'], idx or '-'),
                "- **关卡名称**：%s" % title,
                "- **关卡类型**：%s" % ("战斗关卡" if r.get('IsBattle') else "剧情关卡"),
                "- **AVG 剧本**：`%s`" % (stem if parsed else (bubble_stem or '无（解包中不存在该剧本）')),
                "- **关卡描述**：%s" % hint,
                "- **通关目标**：%s" % (aim or '推进主线剧情'),
            ]
            doc = PageDoc("# %s %s" % (idx, title), info,
                          body_src['meta']['recap'] or hint,
                          "战斗内气泡对白（SetBubble，随战斗阶段推进）" if bubbles else "逐句台词",
                          body_src['beats'], meta=body_src['meta'])
            path = os.path.join(sdir, safe_name('%s_%s_%s' % (r['Id'], idx, title)) + '.md')
            write(path, page_markdown(doc))
            sink.record_page('main', path, doc, r['Id'], title, code=idx,
                             group={'kind': 'chapter', 'id': ch, 'label': clabel,
                                    'title': ctitle, 'year': cyear},
                             stems=[stem if parsed else None, bubble_stem], page=page,
                             story_id=stem, kind='battle' if r.get('IsBattle') else 'story',
                             parents=[p for p in (r.get('ParentStoryId') or []) if isinstance(p, str)],
                             hint=hint, aim=aim or '推进主线剧情')
            stats['sections'] += 1
            stats['bubbles'] += 1 if bubbles else 0
            stats['lines'] += sum(1 for b in body_src['beats'] if b['k'] in ('talk', 'bubble'))
    return stats
