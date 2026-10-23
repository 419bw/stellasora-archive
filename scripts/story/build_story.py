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
from pipeline.conditions import reading_beats  # noqa: E402
from pipeline import markup  # noqa: E402
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
# search.json/_coverage 的字节序与页面追加序不变。每搬迁一族调用一次；
# 最后一族搬完后（Phase C）整体删除。
def _migrated_sink(ctx):
    import sink as _sink_mod
    return _sink_mod.SidecarSink(ctx.out, ctx.lang_table('LANG', 'Story'), containers={
        'pages': _PAGES, 'search_entries': _SEARCH_ENTRIES,
        'chapter_nodes': _CHAPTER_NODES, 'rendered': _RENDERED,
        'battle_map': [], 'skipped': [], 'code_mismatches': CODE_MISMATCHES,
    })


# ============================================================ structured sidecars
# The site is built from these records, never from the Markdown, so both artefacts come
# out of the same parse pass and cannot drift apart.
_PAGES = []
_SEARCH_ENTRIES = []
_CHAPTER_NODES = collections.OrderedDict()
_RENDERED = set()


def write_beats(page, doc):
    """PageDoc 侧车落盘：story_docs/_beats/<page 的 .html 换 .json>。

    Phase 2 起 HTML 后端（scripts/site/render_html.py）直接消费这些侧车，
    不再从 Markdown 反编译。侧车随 git 提交（门控手册 8.5 认可的位置）。
    """
    if not page:
        return
    rel = page[:-len('.html')] + '.json' if page.endswith('.html') else page + '.json'
    write(os.path.join(OUT, '_beats', rel),
          json.dumps(doc.to_dict(), ensure_ascii=False, indent=1) + "\n")


def record_page(family, path, doc, ident, title, code='', group=None,
                stems=(), page=None, **extra):
    beats = reading_beats(doc.beats)
    speakers = []
    for b in beats:
        if b['k'] in ('talk', 'bubble') and b['speaker'] not in speakers:
            speakers.append(b['speaker'])
    stems = [s for s in stems if s]
    counts = collections.Counter(b['k'] for b in beats)
    counts['sticker'] = sum(1 for b in beats if b['k'] == 'talk' and b.get('sticker'))
    rec = {
        'id': ident, 'family': family, 'code': code, 'title': title,
        'group': group or {},
        'page_md': os.path.relpath(path, OUT).replace(os.sep, '/'),
        'page': page,
        'stems': stems,
        'recap': markup.text(doc.meta['recap']),
        'speakers': speakers,
        'counts': dict(counts),
        'preview': " ".join(
            [markup.plain(b['text']) for b in beats if b['k'] == 'talk']
            or [markup.plain(b['story']).replace('\n', ' ') for b in beats if b['k'] == 'anecdote']
        )[:180],
    }
    # Document-ordered 重大抉择 blocks with per-option jump EvId; the site joins
    # these against StoryCondition/ActivityStoryEvidence to label branch targets.
    major_choices = [
        [{'title': markup.text(t), 'ev': ev} for (t, _d, ev) in b['options']]
        for b in beats if b['k'] == 'choice' and b['kind'] == 'major' and b['options']
    ]
    if major_choices:
        rec['major_choices'] = major_choices
    rec.update(extra)
    _PAGES.append(rec)
    # 全量台词进检索 hay，中段文本才可被精确检索（issue #7）；男主变体仅在与默认
    # 文本不同时才收录，否则索引体积约翻倍
    lines, male_only = [], []
    for b in beats:
        if b['k'] in ('talk', 'bubble'):
            text_f = markup.plain(b['text'])
            text_m = markup.plain(b['text'], 'male')
            if text_f:
                lines.append(text_f)
            if text_m and text_m != text_f:
                male_only.append(text_m)
        elif b['k'] == 'choice':
            # options 首元素是 Text（versions 结构的编译产物），必须过 markup.plain 解码
            lines += [t for t in (markup.plain(o)
                                  for (o, _d, _ev) in b['options']) if t]
        elif b['k'] == 'anecdote':
            for fld in ('title', 'source'):
                v = markup.plain(b.get(fld, ''))
                if v:
                    lines.append(v)
            for para in markup.plain(b.get('story', '')).split('\n'):
                if para.strip():
                    lines.append(para.strip())
    recap_m = markup.text(doc.meta['recap'], 'male')
    search_text = [title, rec['recap']] + lines + male_only
    if recap_m and recap_m != rec['recap']:
        search_text.append(recap_m)
    _SEARCH_ENTRIES.append({
        **{key: rec[key] for key in ('id', 'family', 'code', 'title', 'page', 'speakers')},
        'group': rec['group'].get('label', ''),
        'hay': ' '.join(dict.fromkeys(text for text in search_text if text)),
    })
    _RENDERED.update(stems)
    write_beats(page, doc)
    return rec


# The official chip is authored per *column* (`StoryChapterTimeStamp.<chapter*100+column>`)
# and reads 「猎月 六角鲸日 10:36」; the column assignment itself lives in the UI prefab, which
# this dump does not carry, and a month's day-names cannot be matched to the numbered days
# the scripts use (「猎月 13日」 is 吠啸枭日, not the 刻木鸟日 that an equal clock would suggest).
# So a node carries its own script's opening scene time, and the chapter keeps the raw slot
# list as reference data instead of pretending the two are joined.
def node_time(beats):
    head = next((b for b in beats or [] if b['k'] == 'scene'), None)
    if not head:
        return None
    return {'clock': head['time'], 'date': head['date']}


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


def record_node(ctx, ch, row, page, bubble_stem, beats=None):
    """Every Story row is a graph node, even the ones with no script in the pack."""
    LANG_STORY = ctx.lang_table('LANG', 'Story')
    nodes = _CHAPTER_NODES.setdefault(ch, [])
    parents = [p for p in (row.get('ParentStoryId') or []) if isinstance(p, str)]
    nodes.append({
        'sid': row['Id'],
        'story_id': row.get('StoryId'),
        'code': lang_of(LANG_STORY, row.get('Index', '')),
        'title': lang_of(LANG_STORY, row.get('Title', '')),
        'desc': lang_of(LANG_STORY, row.get('Desc', '')),
        'aim': lang_of(LANG_STORY, row.get('Aim', '')),
        'kind': 'battle' if row.get('IsBattle') else 'story',
        'is_branch': bool(row.get('IsBranch')),
        'is_last': bool(row.get('IsLast')),
        'memory': row.get('MemoryType'),
        'has_evidence': bool(row.get('HasEvidence')),
        'condition': row.get('ConditionId'),
        'parents': parents,
        'stems': {'story': None if row.get('IsBattle') else row.get('StoryId'),
                  'bubble': bubble_stem},
        'state': 'released' if page else 'unreleased',
        'time': node_time(beats),
        'page': page,
    })
    return parents


# ==================================================================== generation
# lang_of / rows_of / field_lang / character_name 已移入 context.py
# （character_name 即 ctx.character_name，backed by BIN/LANG Character 表）；
# extract_script / script_commands 即 ctx.extract_script / ctx.script_commands。


def build_main(ctx):
    BIN_CHAPTER = ctx.table('BIN', 'StoryChapter')
    BIN_STORY = ctx.table('BIN', 'Story')
    LANG_STORY = ctx.lang_table('LANG', 'Story')
    LANG_STORY_CHAP = ctx.lang_table('LANG', 'StoryChapter')
    chapters = {int(k): v for k, v in BIN_CHAPTER.items()}
    rows = collections.defaultdict(list)
    for r in BIN_STORY.values():
        rows[int(r['Chapter'])].append(r)
    stats = collections.Counter()
    battle_map = []
    skipped = []
    for ch in sorted(chapters):
        cdef = chapters[ch]
        clabel = lang_of(LANG_STORY_CHAP, cdef.get('Name', ''))
        ctitle = lang_of(LANG_STORY_CHAP, cdef.get('Desc', ''))
        cyear = lang_of(LANG_STORY_CHAP, cdef.get('ChapterYear', ''))
        folder = os.path.join(OUT, 'main', 'chapter_%02d_%s' % (ch, safe_name(ctitle or clabel or 'chapter')))
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
                    battle_map.append((stem, cand, 'attached', ch))
                else:
                    battle_map.append((stem, cand, 'MISSING', ch))
                if stem_code_mismatch(stem, idx):
                    tail = re.sub(r'[^A-Za-z0-9]', '', re.match(r'^BA[0-9a-zA-Z]+_([^_]+)$', stem).group(1))
                    print('!! 官方显示代号与 StoryId 编号不一致（气泡脚本按 StoryId 取）: '
                          'sid=%s story=%s suffix=%s display=%s stem=%s'
                          % (r['Id'], stem, tail, idx, cand))
                    CODE_MISMATCHES.append((r['Id'], stem, tail, idx, cand,
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
                    record_node(ctx, ch, r, page, None)
                    continue
                record_node(ctx, ch, r, None, None)
                skipped.append((ch, r['Id'], stem, title, '战斗关卡' if r.get('IsBattle') else '剧情关卡'))
                continue
            page = chapter_path.node_page(ctx.chapter_slugs[ch], stem)
            body_src = bubbles or parsed
            record_node(ctx, ch, r, page, bubble_stem, body_src['beats'])
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
            record_page('main', path, doc, r['Id'], title, code=idx,
                        group={'kind': 'chapter', 'id': ch, 'label': clabel,
                               'title': ctitle, 'year': cyear},
                        stems=[stem if parsed else None, bubble_stem], page=page,
                        story_id=stem, kind='battle' if r.get('IsBattle') else 'story',
                        parents=[p for p in (r.get('ParentStoryId') or []) if isinstance(p, str)],
                        hint=hint, aim=aim or '推进主线剧情')
            stats['sections'] += 1
            stats['bubbles'] += 1 if bubbles else 0
            stats['lines'] += sum(1 for b in body_src['beats'] if b['k'] in ('talk', 'bubble'))
    return stats, battle_map, skipped


def activity_name(ctx, cid, first_section_title):
    """The official activity title only exists inside the 「…」 of the activity notice."""
    LANG_ACT_GROUP = ctx.lang_table('LANG', 'ActivityGroup')
    notice = LANG_ACT_GROUP.get('ActivityGroup.%s.1' % cid, '')
    m = re.search(r'「(.+?)」', notice)
    return (m.group(1) if m else first_section_title)[:24]


def build_events(ctx):
    BIN_ACTIVITY = ctx.table('BIN', 'ActivityStory')
    LANG_ACT = ctx.lang_table('LANG', 'ActivityStory')
    stats = collections.Counter()
    groups = collections.defaultdict(list)
    for r in BIN_ACTIVITY.values():
        groups[r['ChapterId']].append(r)
    for cid in sorted(groups):
        secs = sorted(groups[cid], key=lambda x: x['Id'])
        name = activity_name(ctx, cid, lang_of(LANG_ACT, secs[0].get('Title', '')))
        folder = os.path.join(OUT, 'events', 'activity_%s_%s' % (cid, safe_name(name)))
        for r in sorted(secs, key=lambda x: x['Id']):
            stem = r.get('AvgLuaName') or r.get('StoryId')
            parsed = ctx.extract_script(stem) if stem else None
            if not parsed:
                continue
            idx = lang_of(LANG_ACT, r.get('Index', ''))
            title = lang_of(LANG_ACT, r.get('Title', ''))
            hint = lang_of(LANG_ACT, r.get('Desc', ''))
            doc = PageDoc("# %s %s" % (idx, title),
                          ["- **所属活动**：%s（活动编号 %s）" % (name, cid),
                           "- **关卡 ID**：`%s`" % r['Id'],
                           "- **AVG 剧本**：`%s`" % stem,
                           "- **关卡描述**：%s" % hint],
                          parsed['meta']['recap'] or hint,
                          "逐句台词", parsed['beats'], meta=parsed['meta'])
            path = os.path.join(folder, 'sections', safe_name('%s_%s_%s' % (r['Id'], idx, title)) + '.md')
            write(path, page_markdown(doc))
            record_page('events', path, doc, r['Id'], title, code=idx,
                        group={'kind': 'activity', 'id': cid, 'label': name},
                        stems=[stem], page='events/%s/%s.html' % (cid, r['Id']), hint=hint)
            stats['sections'] += 1
            stats['lines'] += sum(1 for b in parsed['beats'] if b['k'] == 'talk')
    return stats


# ---------------------------------------------------------- other story families
# rows_of / field_lang 已移入 context.py（ctx.rows / ctx.field_lang 同语义）。


def build_chat(ctx):
    """心链（手机聊天）全篇：Chat.json 挂载的 PM_* 剧本 → story_docs/_chat/ 人读 md。

    收录口径与 dispatch 同款自外于站点：一页 = 一个 PM 剧本（按 SetGroupId 切段，
    一段一节），**扁平**摆在 `_chat/` 下（63 个文件名按 PM 编号排序即按联系人分组，
    角色名在每篇 H1 与 `_index.md` 里）。**不调 record_page**、不进 sections.json /
    search.json / _beats 侧车，因此不生成任何 HTML、不进导航与离线检索；`_chat/` 目录名
    本身带 `_` 前缀，validate_site 的 G2 与 validate_story 的 A/C/F 都不会收编（见
    _dev/AI_HANDOVER_GUIDE.md 7.6/7.7）。信息行刻意写 `心链剧本**：` 而不写
    `AVG 剧本**：`，避免被 F 的「整本页」对账收编。

    注意：**不要在 `_chat/` 下再建子目录**。G2 的 `_` 放行是按"直接所在目录名"判的，
    `_chat/103_琥珀/PM10301.md` 会被当成站点页收编、撞"sections.json 没登记"。

    脚本段是权威：537 个 SetGroupId 段 vs Chat 表 498 行，多出的 39 个 `08` 段是
    上游缺行，照常渲染并标注；空段跳过。两者都在 _chat/_diagnostics.json 登记。
    """
    BIN_CHAT = ctx.table('BIN', 'Chat')
    BIN_ITEM = ctx.table('BIN', 'Item')
    LANG_ITEM = ctx.lang_table('LANG', 'Item')
    stats = collections.Counter()
    diag = phone_chat.ChatDiagnostics()
    item_names = {str(r['Id']): lang_of(LANG_ITEM, r.get('Title') or '')
                  for r in BIN_ITEM.values() if r.get('Title')}

    by_file = collections.defaultdict(dict)    # (cid, stem) -> {段号: Chat 行}
    stems_of = collections.defaultdict(list)   # cid -> [stem]（表内出现序）
    for r in BIN_CHAT.values():
        cid, stem = r.get('AddressBookId'), r.get('AVGId')
        if cid is None or not stem:
            continue
        by_file[(cid, stem)][str(r.get('AVGGroupId'))] = r
        if stem not in stems_of[cid]:
            stems_of[cid].append(stem)
    mounted = {stem for _cid, stem in by_file}
    for stem in sorted(f[:-4] for f in os.listdir(ctx.cfg)
                       if f.startswith('PM') and f.endswith('.lua')):
        if stem not in mounted:
            diag.add('script_without_chat_rows', {'stem': stem})

    contacts = []
    for cid in sorted(stems_of):
        cname = ctx.character_name(cid) or ('旅人 %s' % cid)
        files = []
        for stem in sorted(stems_of[cid]):
            path = os.path.join(ctx.cfg, stem + '.lua')
            if not os.path.exists(path):
                for gid, r in sorted(by_file[(cid, stem)].items()):
                    diag.add('chat_row_without_segment',
                             {'stem': stem, 'gid': gid, 'chat_id': r.get('Id')})
                continue
            segments = phone_chat.extract_script(stem, ctx.script_commands(stem),
                                                 ctx.speaker_resolver, ctx.text_compiler, diag)
            rows = by_file[(cid, stem)]
            prepared, skipped = [], []
            for seg in segments:
                if seg['gid'] not in rows:
                    diag.add('segment_without_chat_row', {'stem': stem, 'gid': seg['gid']})
                if seg['n_msg'] == 0 and seg['n_begin'] == 0:
                    diag.add('empty_segment_skipped', {'stem': stem, 'gid': seg['gid']})
                    skipped.append(seg['gid'])
                    continue
                prepared.append((seg, rows.get(seg['gid'])))
                stats['segments'] += 1
                stats['messages'] += seg['n_msg']
                stats['choices'] += seg['n_begin']
            if not prepared:
                continue
            files.append({'stem': stem,
                          'script': os.path.relpath(path, ROOT).replace(os.sep, '/'),
                          'segments': segments, 'rows': rows,
                          'prepared': prepared, 'skipped_gids': skipped})
            stats['scripts'] += 1
        if files:
            contacts.append({'id': cid, 'name': cname, 'files': files})
            stats['contacts'] += 1

    out = os.path.join(OUT, '_chat')
    for contact in contacts:
        for f in contact['files']:
            write(os.path.join(out, f['stem'] + '.md'),
                  phone_chat.render_script_md(contact, f, item_names))
    write(os.path.join(out, '_index.md'), phone_chat.render_index_md(contacts))
    write(os.path.join(out, '_diagnostics.json'),
          json.dumps(diag.as_dict(), ensure_ascii=False, indent=1) + "\n")
    for cat, n in sorted(diag.unexpected().items()):
        print("!! 心链诊断 %s：%d 处（详见 story_docs/_chat/_diagnostics.json）" % (cat, n))
    print("  心链聊天：联系人=%d 剧本=%d 段=%d 短信=%d 抉择=%d"
          % (stats['contacts'], stats['scripts'], stats['segments'],
             stats['messages'], stats['choices']))
    return stats


def build_orphan_battles(ctx, used):
    """BBm* scripts no stage row points at.

    No CN/bin table ever names a BBm script -- the client derives the name from the
    chapter and stage index -- so these can only be filed by their own code. They are
    still official dialogue, so they get pages rather than a footnote.
    """
    stats = collections.Counter()
    orphans = sorted(f[:-4] for f in os.listdir(ctx.cfg)
                     if f.startswith('BBm') and f[:-4] not in used)
    for stem in orphans:
        parsed = ctx.extract_script(stem)
        if not parsed:
            continue
        n = sum(1 for b in parsed['beats'] if b['k'] == 'bubble')
        who = "、".join(collections.Counter(b['speaker'] for b in parsed['beats']
                                            if b['k'] == 'bubble'))
        note = ("属序章《最初的起点》沙漠星塔一战，Story 表不列序章所以无行引用"
                if stem.startswith('BBm00_') else
                "包内没有任何关卡表引用此剧本，只按剧本代号存目")
        doc = PageDoc("# 战斗气泡 `%s`" % stem,
                      ["- **AVG 剧本**：`%s`" % stem,
                       "- **气泡条数**：%d" % n,
                       "- **出场说话人**：%s" % who,
                       "- **挂载状态**：%s" % note],
                      "", "战斗气泡对白（SetBubble，随战斗阶段推进）", parsed['beats'],
                      info_title="剧本信息", meta=parsed['meta'])
        path = os.path.join(OUT, 'battles_unmounted', safe_name(stem) + '.md')
        write(path, page_markdown(doc))
        record_page('battles_unmounted', path, doc, stem, stem,
                    group={'kind': 'unmounted', 'id': None, 'label': '无关卡引用的战斗气泡'},
                    stems=[stem], page='battles/%s.html' % stem, mount_note=note)
        stats['sections'] += 1
        stats['lines'] += n
    return stats, orphans


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
    mstats, battle_map, skipped = build_main(ctx)
    mstats['empty'] = len(skipped)
    print("  sections=%(sections)s 战斗气泡关卡=%(bubbles)s 台词行=%(lines)s 无剧本关卡行=%(empty)s" % mstats)
    print("Parsing event story scripts...")
    estat = build_events(ctx)
    print("  sections=%(sections)s lines=%(lines)s" % estat)
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
    build_chat(ctx)
    attached = [b for b in battle_map if b[2] == 'attached']
    missing = [b for b in battle_map if b[2] == 'MISSING']
    used = {b[1] for b in attached}
    ostats, unattached = build_orphan_battles(ctx, used)
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
