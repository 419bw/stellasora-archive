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

sys.stdout.reconfigure(encoding='utf-8')
BIN = os.path.join(ROOT, 'data', 'StellaSoraData', 'CN', 'bin')
LANG = os.path.join(ROOT, 'data', 'StellaSoraData', 'CN', 'language', 'zh_CN')
CFG = os.path.join(ROOT, 'data', 'ss_lua', 'Lua', 'Game', 'UI', 'Avg', '_cn', 'Config')
PRESET = os.path.join(ROOT, 'data', 'ss_lua', 'Lua', 'Game', 'UI', 'Avg', '_cn', 'Preset')
OUT = os.path.join(ROOT, 'story_docs')

# 主角域常量（PROTAG_ID/PROTAG_NAME）已随语义 pass 移入 pipeline/domain.py

# Stages whose own StoryId carries a `BTnn` battle token that disagrees with the display
# code the localization table publishes for them (upstream official labelling slip).
# Filled by build_main(), reported in _battle_reconciliation.md.
CODE_MISMATCHES = []

# Phase 3 诊断侧车（story_docs/_diagnostics.json）收集点：上游数据异常的机器可读
# 登记，只记录、不改变任何行为。SPEAKER_FALLBACKS 由 pipeline/speakers.py 填充
# （预置表查不到、走前缀/裸 id 兜底的说话人），FRAME_ANOMALIES 由
# pipeline/passes.py 填充（抉择关闭指令的 group 找不到活跃帧，如 CG_126_03）。
SPEAKER_FALLBACKS = []
FRAME_ANOMALIES = []      # [(stem, {'idx','cmd','group','closer'})]

# ============================================================== Lua table parser
# 解析器已拆分为 pipeline/lua_lexer.py（词法，token 流带 SourcePos）与
# pipeline/lua_parser.py（语法，递归下降 → T(list)）。此处仅保留兼容壳：
# T / LuaError / parse_lua 三个符号与原 LuaReader 实现语义一致
# （对 git 4496bd1 原实现做过 588 Config + AvgCharacter 预设全量对拍）。
from pipeline.lua_parser import LuaError, T, parse_lua  # noqa: E402
from pipeline.command_ir import Command, build_commands  # noqa: E402,F401
from pipeline.text_rules import clean_text  # noqa: E402
from pipeline.speakers import SpeakerResolver  # noqa: E402
from pipeline.passes import extract_beats  # noqa: E402
from pipeline import markup  # noqa: E402
from pipeline.pagedoc import PageDoc  # noqa: E402
from pipeline.render_md import page_markdown  # noqa: E402


# ================================================================= data loading
def load_json(folder, name):
    p = os.path.join(folder, name)
    if not os.path.exists(p):
        return {}
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def load_speakers():
    """id -> (name, surfix) from the official AVG character preset."""
    recs = parse_lua(open(os.path.join(PRESET, 'AvgCharacter.lua'), encoding='utf-8').read())
    out = {}
    for r in recs:
        if isinstance(r, T):
            sid = r.get('id')
            if sid is not None:
                out[str(sid)] = (r.get('name') or "", r.get('surfix') or "")
    return out


TEXT_COMPILER = markup.TextCompiler.load(PRESET, BIN, LANG)
EMPH_STATS = TEXT_COMPILER.diagnostics
SPEAKERS = load_speakers()
SPEAKER_RESOLVER = SpeakerResolver(SPEAKERS, diag=SPEAKER_FALLBACKS)
LANG_STORY = load_json(LANG, 'Story.json')
LANG_STORY_CHAP = load_json(LANG, 'StoryChapter.json')
LANG_STORY_TS = load_json(LANG, 'StoryChapterTimeStamp.json')
LANG_PERSONALITY = load_json(LANG, 'StoryPersonality.json')
LANG_ROLE_PERSONALITY = load_json(LANG, 'StoryRolePersonality.json')
LANG_ACT = load_json(LANG, 'ActivityStory.json')
LANG_ACT_GROUP = load_json(LANG, 'ActivityGroup.json')
BIN_STORY = load_json(BIN, 'Story.json')
BIN_CHAPTER = load_json(BIN, 'StoryChapter.json')
BIN_ACTIVITY = load_json(BIN, 'ActivityStory.json')
BIN_ACTIVITY_CHAPTER = load_json(BIN, 'ActivityStoryChapter.json')
BIN_CHARACTER = load_json(BIN, 'Character.json')
BIN_PLOT = load_json(BIN, 'Plot.json')
BIN_NPC_PLOT = load_json(BIN, 'NPCAffinityPlot.json')
BIN_NPC = load_json(BIN, 'StarTowerNPC.json')
BIN_DISC = load_json(BIN, 'DiscIP.json')
BIN_SST_TAB = load_json(BIN, 'StorySetTab.json')
BIN_SST_CHAPTER = load_json(BIN, 'StorySetChapter.json')
BIN_SST_SECTION = load_json(BIN, 'StorySetSection.json')
BIN_STORY_TS = load_json(BIN, 'StoryChapterTimeStamp.json')
BIN_PERSONALITY = load_json(BIN, 'StoryPersonality.json')
BIN_ROLE_PERSONALITY = load_json(BIN, 'StoryRolePersonality.json')
LANG_CHARACTER = load_json(LANG, 'Character.json')
LANG_PLOT = load_json(LANG, 'Plot.json')
LANG_NPC_PLOT = load_json(LANG, 'NPCAffinityPlot.json')
LANG_NPC = load_json(LANG, 'StarTowerNPC.json')
LANG_DISC = load_json(LANG, 'DiscIP.json')
LANG_SST_TAB = load_json(LANG, 'StorySetTab.json')
LANG_SST_CHAPTER = load_json(LANG, 'StorySetChapter.json')
LANG_SST_SECTION = load_json(LANG, 'StorySetSection.json')
BIN_DISPATCH_PERF = load_json(BIN, 'AgentSpecialPerformance.json')

_TAG_CACHE = {}


def script_commands(stem):
    """Parse one AVG script into an ordered [Command] list (stable idx identity)."""
    if stem in _TAG_CACHE:
        return _TAG_CACHE[stem]
    path = os.path.join(CFG, stem + '.lua')
    if not os.path.exists(path):
        _TAG_CACHE[stem] = None
        return None
    recs = parse_lua(open(path, encoding='utf-8').read(), stem)
    cmds = build_commands(recs)
    _TAG_CACHE[stem] = cmds
    return cmds


# ==================================================================== text rules
# 文本清洗/签名规则（clean_text/clean_dialogue/is_resource_name/_sig/_related）已移入
# pipeline/text_rules.py；动画帧折叠 fold_animations（原 nonlog_repeats）、抉择方言
# fork_options、beat 提取与分支归属 extract_beats 已移入 pipeline/passes.py；
# 说话人解析已移入 pipeline/speakers.py（Phase 1c）。行为与原实现逐行等价。


# ============================================================ command processing
# FORK_DEFS/FORK_CLOSE/fork_options 已移入 pipeline/passes.py（Phase 1c）。


def extract_script(stem):
    """Turn one AVG script into an ordered beat list with branch attribution."""
    cmds = script_commands(stem)
    if cmds is None:
        return None
    diag = []
    res = extract_beats(cmds, SPEAKER_RESOLVER, TEXT_COMPILER, diag=diag)
    for d in diag:
        FRAME_ANOMALIES.append((stem, d))
    return res


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
    beats = doc.beats
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
        'preview': " ".join(markup.plain(b['text']) for b in beats if b['k'] == 'talk')[:180],
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
    search_text = [title, rec['recap'], rec['preview'],
                   markup.text(doc.meta['recap'], 'male'),
                   ' '.join(markup.plain(b['text'], 'male')
                            for b in beats if b['k'] == 'talk')[:180]]
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
_SLOTS = None


def time_slots(chapter):
    global _SLOTS
    if _SLOTS is None:
        _SLOTS = collections.defaultdict(dict)
        for k in BIN_STORY_TS:
            txt = lang_of(LANG_STORY_TS, 'StoryChapterTimeStamp.%s.1' % k)
            if txt:
                _SLOTS[int(k) // 100][int(k) % 100] = txt
    return _SLOTS.get(chapter, {})


def node_time(beats):
    head = next((b for b in beats or [] if b['k'] == 'scene'), None)
    if not head:
        return None
    return {'clock': head['time'], 'date': head['date']}


def bubble_stem_for(story_id, code):
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


def record_node(ch, row, page, bubble_stem, beats=None):
    """Every Story row is a graph node, even the ones with no script in the pack."""
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
def lang_of(table, key):
    return clean_text(table.get(key, ''))


def build_main():
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
            if st and script_commands(st):
                released_stems.add(st)
            bcand = bubble_stem_for(st, idx_cand)
            if bcand and script_commands(bcand):
                released_stems.add(st)

        for r in sorted(rows.get(ch, []), key=lambda x: x['Id']):
            idx = lang_of(LANG_STORY, r.get('Index', ''))
            title = lang_of(LANG_STORY, r.get('Title', ''))
            hint = lang_of(LANG_STORY, r.get('Desc', ''))
            aim = lang_of(LANG_STORY, r.get('Aim', ''))
            stem = r.get('StoryId')
            parsed = extract_script(stem) if stem else None
            bubbles = None
            bubble_stem = None
            if parsed is None and r.get('IsBattle'):
                cand = bubble_stem_for(stem, idx)
                if cand and script_commands(cand):
                    bubbles = extract_script(cand)
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
                    cno = cdef.get('Index') or 'sp'
                    page = 'main/ch%s/%s.html' % (cno, stem)
                    record_node(ch, r, page, None)
                    continue
                record_node(ch, r, None, None)
                skipped.append((ch, r['Id'], stem, title, '战斗关卡' if r.get('IsBattle') else '剧情关卡'))
                continue
            cno = cdef.get('Index') or 'sp'
            page = 'main/ch%s/%s.html' % (cno, stem)
            body_src = bubbles or parsed
            record_node(ch, r, page, bubble_stem, body_src['beats'])
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


def activity_name(cid, first_section_title):
    """The official activity title only exists inside the 「…」 of the activity notice."""
    notice = LANG_ACT_GROUP.get('ActivityGroup.%s.1' % cid, '')
    m = re.search(r'「(.+?)」', notice)
    return (m.group(1) if m else first_section_title)[:24]


def build_events():
    stats = collections.Counter()
    groups = collections.defaultdict(list)
    for r in BIN_ACTIVITY.values():
        groups[r['ChapterId']].append(r)
    for cid in sorted(groups):
        secs = sorted(groups[cid], key=lambda x: x['Id'])
        name = activity_name(cid, lang_of(LANG_ACT, secs[0].get('Title', '')))
        folder = os.path.join(OUT, 'events', 'activity_%s_%s' % (cid, safe_name(name)))
        for r in sorted(secs, key=lambda x: x['Id']):
            stem = r.get('AvgLuaName') or r.get('StoryId')
            parsed = extract_script(stem) if stem else None
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
def rows_of(table):
    return sorted(table.values(), key=lambda r: r.get('Id', 0))


def field_lang(lang_table, row, field='Name'):
    return lang_of(lang_table, row.get(field, ''))


def character_name(cid):
    row = BIN_CHARACTER.get(str(cid))
    return field_lang(LANG_CHARACTER, row) if row else ''


def build_character_plots():
    """Plot.json mounts each traveller's personal story (CG_<char>_<part>).

    Three parts per character, gated at affinity 1 / 5 / 10. Costume reissues register
    their own Plot rows against the same script, so rows are grouped by script and the
    titled row owns the page while the others are listed on it.
    """
    stats = collections.Counter()
    by_stem = collections.OrderedDict()
    for r in rows_of(BIN_PLOT):
        by_stem.setdefault(r.get('AvgId'), []).append(r)
    for stem, group in by_stem.items():
        parsed = extract_script(stem)
        if not parsed:
            continue
        owner = next((r for r in group if field_lang(LANG_PLOT, r)), group[0])
        cname = character_name(owner.get('Char'))
        title = field_lang(LANG_PLOT, owner) or stem
        info = [
            "- **所属角色**：%s（角色编号 `%s`）" % (cname or '未知', owner.get('Char')),
            "- **解锁条件**：好感等级 %s" % owner.get('UnlockAffinityLevel'),
            "- **剧情档案 ID**：`%s`" % owner['Id'],
            "- **AVG 剧本**：`%s`" % stem,
        ]
        twins = [character_name(r.get('Char')) for r in group if r is not owner]
        if twins:
            info.append("- **复用此剧本的档案**：%s" % "、".join(x for x in twins if x))
        folder = os.path.join(OUT, 'characters',
                              safe_name('%s_%s' % (owner.get('Char'), cname or stem)))
        path = os.path.join(folder, 'sections', safe_name('%s_%s' % (owner['Id'], title)) + '.md')
        doc = PageDoc("# %s" % title, info, parsed['meta']['recap'], "逐句台词",
                      parsed['beats'], info_title="剧情档案信息", meta=parsed['meta'])
        write(path, page_markdown(doc))
        record_page('characters', path, doc, owner['Id'], title,
                    group={'kind': 'character', 'id': owner.get('Char'), 'label': cname},
                    stems=[stem], page='characters/%s/%s.html' % (owner.get('Char'), owner['Id']),
                    affinity=owner.get('UnlockAffinityLevel'), twins=twins)
        stats['sections'] += 1
        stats['lines'] += sum(1 for b in parsed['beats'] if b['k'] in ('talk', 'bubble'))
    return stats


def build_npc_plots():
    """NPCAffinityPlot.json mounts the star-tower staff bond stories (CG_npc<id>_<part>)."""
    stats = collections.Counter()
    for r in rows_of(BIN_NPC_PLOT):
        parsed = extract_script(r.get('avgId'))
        if not parsed:
            continue
        npc = BIN_NPC.get(str(r.get('NPCId')))
        npc_name = field_lang(LANG_NPC, npc) if npc else ''
        idx = field_lang(LANG_NPC_PLOT, r)
        sub = field_lang(LANG_NPC_PLOT, r, 'Desc')
        info = [
            "- **所属 NPC**：%s（NPC 编号 `%s`）" % (npc_name or '未知', r.get('NPCId')),
            "- **解锁条件**：好感等级 %s" % r.get('AffinityLevel'),
            "- **剧情档案 ID**：`%s`" % r['Id'],
            "- **AVG 剧本**：`%s`" % r.get('avgId'),
        ]
        folder = os.path.join(OUT, 'npc_bonds',
                              safe_name('%s_%s' % (r.get('NPCId'), npc_name or r.get('avgId'))))
        path = os.path.join(folder, 'sections', safe_name('%s_%s' % (r['Id'], idx or sub)) + '.md')
        doc = PageDoc("# %s" % " ".join(x for x in (idx, sub) if x), info,
                      parsed['meta']['recap'], "逐句台词", parsed['beats'],
                      info_title="剧情档案信息", meta=parsed['meta'])
        write(path, page_markdown(doc))
        record_page('npc_bonds', path, doc, r['Id'],
                    " ".join(x for x in (idx, sub) if x), code=idx,
                    group={'kind': 'npc', 'id': r.get('NPCId'), 'label': npc_name},
                    stems=[r.get('avgId')],
                    page='npc/%s/%s.html' % (r.get('NPCId'), r['Id']),
                    affinity=r.get('AffinityLevel'), hint=sub)
        stats['sections'] += 1
        stats['lines'] += sum(1 for b in parsed['beats'] if b['k'] in ('talk', 'bubble'))
    return stats


def build_discs():
    """DiscIP rows carrying an AvgId play a CG_disc* vignette.

    The same row also stores a prose retelling in StoryDesc. It is table copy, not
    script dialogue -- none of its lines appear in the AVG -- so it is kept as a
    labelled appendix instead of being merged into the beat list.
    """
    stats = collections.Counter()
    for r in rows_of(BIN_DISC):
        stem = r.get('AvgId')
        parsed = extract_script(stem) if stem else None
        if not parsed:
            continue
        title = field_lang(LANG_DISC, r, 'StoryName')
        chars = [character_name(c) for c in (r.get('CharId') or [])]
        owners = "、".join(x for x in chars if x)
        info = [
            "- **唱片 ID**：`%s`" % r['Id'],
            "- **关联角色**：%s" % (owners or '无'),
            "- **AVG 剧本**：`%s`" % stem,
        ]
        prose = LANG_DISC.get(r.get('StoryDesc', ''), '').strip()
        doc = PageDoc("# %s" % title, info, parsed['meta']['recap'], "逐句台词",
                      parsed['beats'], info_title="唱片信息", meta=parsed['meta'],
                      appendix={'title': '唱片附文（DiscIP 表 StoryDesc 原文）',
                                'note': '与上面的 AVG 剧本是两份文本：这段是唱片自带的散文，剧本里没有对应的台词。',
                                'prose': prose} if prose else None)
        path = os.path.join(OUT, 'discs', safe_name('%s_%s' % (r['Id'], title or stem)) + '.md')
        write(path, page_markdown(doc))
        record_page('discs', path, doc, r['Id'], title,
                    group={'kind': 'disc', 'id': r['Id'], 'label': title,
                           'characters': [c for c in chars if c]},
                    stems=[stem], page='discs/%s.html' % r['Id'],
                    prose_lines=len(prose.split("\n")) if prose else 0)
        stats['sections'] += 1
        stats['lines'] += sum(1 for b in parsed['beats'] if b['k'] in ('talk', 'bubble'))
    return stats


def build_dispatch():
    """AgentSpecialPerformance: 委托（Agent）结算演出 DP_single*/DP_multi*。

    委托完成时，若该委托掉落[特殊报酬]，客户端会从 AgentSpecialPerformance 里按
    「上阵旅人组合 + 权重」随机抽一段 DP_* 演出播放（结算面板 DispatchResultCtrl）。
    一份 DP 脚本按 SetGroupId 切成多段，每段对应表里一行：CharId=上阵旅人，
    AVGGroupId=段号，Weight=随机权重（单人 50 / 双人 150 / 三人 300）。

    收录口径：一页 = 一段结算演出（即 AgentSpecialPerformance 的一行），按「该段
    出场的旅人 / 组合」归类——单人段归到对应旅人名下（每位 2 变体各一页），双人/三人段
    按组合成页。这是委托专场，md 放 dispatch/ 下、**不进各族的 sections/ 子目录**，
    也不写 `AVG 剧本**：` 挂载行（一页只含该段而非整份共用脚本）。因此由 validate_story
    的「委托分段保真(N)」契约按 (脚本, 段号) 独立切段对账；A/A2/B/C/D/E 与 F/M 对它不适用。
    """
    stats = collections.Counter()
    parsed = {}

    def segments(stem):
        if stem not in parsed:
            pr = extract_script(stem) or {'beats': []}
            groups, cur = {}, None
            for b in pr['beats']:
                if b['k'] == 'wave':
                    cur = b['no']
                    groups.setdefault(cur, [])
                elif cur is not None:
                    groups[cur].append(b)
            parsed[stem] = groups
        return parsed[stem]

    variant_no = {}
    for r in rows_of(BIN_DISPATCH_PERF):
        stem, gid = r.get('Avg'), str(r.get('AVGGroupId'))
        seg = segments(stem).get(gid) or []
        if not seg:
            print("!! 委托结算演出表行查无该段剧本，跳过: id=%s avg=%s 段=%s" % (r.get('Id'), stem, gid))
            continue
        cast = [int(c) for c in (r.get('CharId') or [])]
        n = len(cast)
        kind = {1: '单人', 2: '双人', 3: '三人'}.get(n, '%d 人' % n)
        names = [character_name(c) or ('旅人 %d' % c) for c in cast]
        if n == 1:
            variant_no[cast[0]] = variant_no.get(cast[0], 0) + 1
            ordinal = {1: '其一', 2: '其二', 3: '其三'}.get(variant_no[cast[0]], str(variant_no[cast[0]]))
            label = names[0]
            title = '%s · 委托结算演出（%s）' % (names[0], ordinal)
            group = {'kind': 'dispatch', 'id': 'c%d' % cast[0], 'label': label, 'characters': cast}
            sub = 'solo'
        else:
            label = ' ＋ '.join(names)
            title = '%s · %s人委托结算演出' % (label, kind)
            group = {'kind': 'dispatch', 'id': 'm%d' % r['Id'], 'label': label, 'characters': cast}
            sub = 'multi'
        info = [
            "- **结算演出**：`%s`（第 `%s` 段）" % (stem, gid),
            "- **上阵旅人**：%s（Id %s）" % (label, '、'.join(str(c) for c in cast)),
            "- **结算类型**：%s结算演出，出现权重 %s（单人 50 / 双人 150 / 三人 300，越大越易抽中）"
            % (kind, r.get('Weight')),
            "- **触发条件**：委托完成且含「特殊报酬」时，按上阵旅人与权重随机抽一段结算演出播放；"
            "同一份共用剧本按段切分，此处为第 %s 段" % gid,
        ]
        path = os.path.join(OUT, 'dispatch', sub, safe_name('%s_%s' % (title, r['Id'])) + '.md')
        doc = PageDoc("# " + title, info, '', '结算演出台词', seg,
                      info_title='委托结算演出信息',
                      meta={'recap': '', 'episode': '', 'title': ''})
        write(path, page_markdown(doc))
        record_page('dispatch', path, doc, r['Id'], title,
                    code='', group=group, stems=[stem],
                    page='dispatch/%s/%s.html' % (sub, r['Id']),
                    cast=cast, weight=r.get('Weight'))
        stats['sections'] += 1
        stats['lines'] += sum(1 for b in seg if b['k'] in ('talk', 'bubble'))
    return stats


def build_storysets():
    """StorySet* tables mount the side-story collections (STsp_<chapter>_<part>).

    Tab (栏目) -> Chapter (故事集) -> Section (小节); tab 1 is the site-wide "全部"
    filter, not a category, so chapters are filed under their real tab only.
    """
    stats = collections.Counter()
    tabs = {r['Id']: lang_of(LANG_SST_TAB, r.get('TabName', ''))
            for r in rows_of(BIN_SST_TAB) if not r.get('IsAll')}
    sections = collections.defaultdict(list)
    for s in rows_of(BIN_SST_SECTION):
        sections[s['ChapterId']].append(s)
    for chap in rows_of(BIN_SST_CHAPTER):
        secs = sections.get(chap['Id'])
        if not secs:
            continue
        cname = lang_of(LANG_SST_CHAPTER, chap.get('Name', ''))
        cno = lang_of(LANG_SST_CHAPTER, chap.get('Title', ''))
        tab = tabs.get(chap.get('TabId'), '未分类')
        folder = os.path.join(OUT, 'storysets', safe_name(tab),
                              safe_name('%s_%s' % (chap['Id'], cname)))
        for s in secs:
            parsed = extract_script(s.get('AVGId'))
            if not parsed:
                continue
            idx = lang_of(LANG_SST_SECTION, s.get('Title', ''))
            desc = lang_of(LANG_SST_SECTION, s.get('Desc', ''))
            info = [
                "- **所属故事集**：%s《%s》" % (cno, cname),
                "- **栏目**：%s" % tab,
                "- **小节 ID**：`%s`" % s['Id'],
                "- **AVG 剧本**：`%s`" % s.get('AVGId'),
            ]
            path = os.path.join(folder, 'sections',
                                safe_name('%s_%s' % (s['Id'], idx or desc)) + '.md')
            doc = PageDoc("# %s" % (desc or idx), info, parsed['meta']['recap'],
                          "逐句台词", parsed['beats'], info_title="故事集小节信息",
                          meta=parsed['meta'])
            write(path, page_markdown(doc))
            record_page('storysets', path, doc, s['Id'], desc or idx, code=idx,
                        group={'kind': 'storyset', 'id': chap['Id'], 'label': cname,
                               'no': cno, 'tab': tab},
                        stems=[s.get('AVGId')],
                        page='storysets/%s/%s.html' % (chap['Id'], s['Id']))
            stats['sections'] += 1
            stats['lines'] += sum(1 for b in parsed['beats'] if b['k'] in ('talk', 'bubble'))
    return stats


def build_prologue():
    """STm00_* is the opening 序章《最初的起点》played during registration.

    Story lists no chapter 0 row, so the stage table cannot mount it; the script's own
    SetIntro carries the official episode labels, and BBm00_* are the battle bubbles of
    that same desert mission (same trio, same 许愿箱).
    """
    stats = collections.Counter()
    stems = sorted(f[:-4] for f in os.listdir(CFG) if f.startswith('STm00_'))
    battle = sorted(f[:-4] for f in os.listdir(CFG) if f.startswith('BBm00_'))
    for stem in stems:
        parsed = extract_script(stem)
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
        path = os.path.join(OUT, 'prologue', 'sections',
                            safe_name('%s_%s' % (stem, parsed['meta']['title'] or stem)) + '.md')
        doc = PageDoc("# %s %s" % (parsed['meta']['episode'] or '序',
                                   parsed['meta']['title'] or ''),
                      info, parsed['meta']['recap'], "逐句台词", parsed['beats'],
                      info_title="序章信息", meta=parsed['meta'])
        write(path, page_markdown(doc))
        record_page('prologue', path, doc, stem, parsed['meta']['title'] or stem,
                    code=parsed['meta']['episode'] or '序',
                    group={'kind': 'prologue', 'id': 0, 'label': '序章'},
                    stems=[stem], page='prologue/%s.html' % stem)
        stats['sections'] += 1
        stats['lines'] += sum(1 for b in parsed['beats'] if b['k'] in ('talk', 'bubble'))
    return stats


def build_orphan_battles(used):
    """BBm* scripts no stage row points at.

    No CN/bin table ever names a BBm script -- the client derives the name from the
    chapter and stage index -- so these can only be filed by their own code. They are
    still official dialogue, so they get pages rather than a footnote.
    """
    stats = collections.Counter()
    orphans = sorted(f[:-4] for f in os.listdir(CFG)
                     if f.startswith('BBm') and f[:-4] not in used)
    for stem in orphans:
        parsed = extract_script(stem)
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


def write_data():
    """Site-facing structure: chapter graphs, the page index, search, personality axes."""
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
            'edge_source': 'ParentStoryId' if any(n['parents'] for n in nodes) else 'none',
            'time_slots': {str(i): v for i, v in sorted(time_slots(ch).items())},
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
                                             edge_field='ParentStoryId'),
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


def write_coverage():
    """Every script in the pack is either rendered or named here with its mount source."""
    rendered = set(_RENDERED)
    alls = sorted(f[:-4] for f in os.listdir(CFG) if f.endswith('.lua'))
    mounts = collections.defaultdict(set)
    for tbl, fld in (('Story', 'AvgLuaName'), ('ActivityStory', 'AvgLuaName'),
                     ('Plot', 'AvgId'), ('NPCAffinityPlot', 'avgId'), ('DiscIP', 'AvgId'),
                     ('StorySetSection', 'AVGId'), ('Chat', 'AVGId'),
                     ('AgentSpecialPerformance', 'Avg')):
        for r in load_json(BIN, tbl + '.json').values():
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
           'PM': 'Chat.AVGId', 'DP': 'AgentSpecialPerformance.Avg', 'GD': '无表引用'}
    note = {'PM': '心链聊天全篇（`UIText.MainView_Phone` / `OpenFunc.Phone`），外部已有收录，不做',
            'DP': '委托结算演出，已入 dispatch/（按结算演出段收录，见 _dev 手册 7.4）',
            'GD': '抽卡演出小段（4 句），表不引用，待决',
            'BBm': '战斗气泡，含 7 个无表引用者（序章一战 + 第七章追加战）',
            'STm': '含序章 STm00_*，已渲染进 prologue/'}
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


def write_diagnostics(battle_map, skipped, unattached):
    """story_docs/_diagnostics.json —— 上游数据异常与编译器兜底的机器可读登记。

    与人读的 _battle_reconciliation.md 互补：这里是脚本/测试可直接消费的结构化
    条目（手册 8.5 认可的根级侧车）。纯增量文件：不在黄金清单覆盖面（其只收
    *.md、_data/*.json、site/**），也不被任何现有契约消费。列表按构造序或
    显式排序，同一输入重建字节稳定。
    """
    anomalies = {}
    for stem, d in FRAME_ANOMALIES:
        anomalies[(stem, d['idx'], d['cmd'], d['group'])] = {
            'stem': stem, 'idx': d['idx'], 'cmd': d['cmd'],
            'group': d['group'], 'closer': d['closer']}
    fallbacks = {}
    for f in SPEAKER_FALLBACKS:
        fallbacks.setdefault(f['sid'], f)
    obj = {
        'note': '上游数据异常与编译器兜底的机器可读登记（build_story 生成）。'
                '人读版见 _battle_reconciliation.md 与 _dev/AI_HANDOVER_GUIDE.md 3.5。'
                'speaker_prefix_fallbacks=预置表未收录、按最长点分前缀归位的变体键；'
                'speaker_inline_names=剧本把显示名直接写在 speaker 字段的条数'
                '（正常行为，按字面解析，不逐条列出）；'
                'choice_frame_anomalies=抉择关闭指令的 group 无活跃帧'
                '（phone 方言不入帧栈，其落空属设计使然，不登记）；'
                'emph_tags_preserved/orphan_emph_tags_stripped=成对保留与'
                '孤儿剥离的 <b>/<i> 强调标记计数（TextCompiler '
                '栈配对；孤儿如 STm06_01 悬空 </b>，只丢标记不丢字）。'
                '口径为本次构建中不同原始文本的标签数量，包含被折叠帧；'
                '相同原始文本复用缓存，不重复计数。',
        'code_mismatches': [
            {'sid': sid, 'story_id': story, 'storyid_suffix': suffix,
             'display_code': disp, 'bubble_stem': stem, 'condition_id': cond,
             'chapter': c}
            for sid, story, suffix, disp, stem, cond, c in CODE_MISMATCHES],
        'battle_bubble_missing': [
            {'sid': b[0], 'expected_stem': b[1], 'chapter': b[3]}
            for b in battle_map if b[2] == 'MISSING'],
        'unattached_bbm_scripts': sorted(unattached),
        'rows_without_script': [
            {'chapter': c, 'sid': sid, 'stem': stem, 'title': t, 'kind': kind}
            for c, sid, stem, t, kind in skipped],
        'speaker_prefix_fallbacks': [
            fallbacks[k] for k in sorted(fallbacks) if fallbacks[k]['via'] == 'prefix'],
        'speaker_inline_names': sum(1 for k in fallbacks if fallbacks[k]['via'] == 'sid'),
        'choice_frame_anomalies': [anomalies[k] for k in sorted(anomalies)],
        'emph_tags_preserved': EMPH_STATS['paired'],
        'orphan_emph_tags_stripped': EMPH_STATS['orphan'],
    }
    write(os.path.join(OUT, '_diagnostics.json'),
          json.dumps(obj, ensure_ascii=False, indent=1) + "\n")
    return obj


def main():
    # story_docs/ is fully generated: a mount change removes pages, and leaving the old
    # files behind would let the validators read a tree this script never wrote
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    print("Parsing official AVG scripts (main story)...")
    mstats, battle_map, skipped = build_main()
    mstats['empty'] = len(skipped)
    print("  sections=%(sections)s 战斗气泡关卡=%(bubbles)s 台词行=%(lines)s 无剧本关卡行=%(empty)s" % mstats)
    print("Parsing event story scripts...")
    estat = build_events()
    print("  sections=%(sections)s lines=%(lines)s" % estat)
    for label, fn in (("角色个人剧情", build_character_plots),
                      ("星塔 NPC 好感剧情", build_npc_plots),
                      ("唱片剧情", build_discs),
                      ("故事集支线", build_storysets),
                      ("序章", build_prologue),
                      ("委托结算演出", build_dispatch)):
        st = fn()
        print("  %s：小节=%d 台词行=%d" % (label, st['sections'], st['lines']))

    attached = [b for b in battle_map if b[2] == 'attached']
    missing = [b for b in battle_map if b[2] == 'MISSING']
    used = {b[1] for b in attached}
    ostats, unattached = build_orphan_battles(used)
    chlab = {int(c['Id']): (clean_text(lang_of(LANG_STORY_CHAP, c.get('Name', '')))
                            or '表 Id %s' % c['Id']) for c in BIN_CHAPTER.values()}
    miss_ch = sorted({chlab.get(b[3], b[3]) for b in missing})
    print("  无关卡引用的战斗气泡剧本：剧本=%d 气泡=%d" % (ostats['sections'], ostats['lines']))
    dstats = write_data()
    print("结构化侧车：章=%d 节点=%d 页=%d" % (dstats['chapters'], dstats['nodes'], dstats['pages']))
    total, done, todo = write_coverage()
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
    djson = write_diagnostics(battle_map, skipped, unattached)
    print("诊断侧车 _diagnostics.json：代号错配=%d 气泡缺失=%d 未引用BBm=%d "
          "无剧本行=%d 前缀兜底=%d 内联名=%d 帧异常=%d 强调保留=%d 强调孤儿=%d"
          % (len(djson['code_mismatches']), len(djson['battle_bubble_missing']),
             len(djson['unattached_bbm_scripts']), len(djson['rows_without_script']),
             len(djson['speaker_prefix_fallbacks']), djson['speaker_inline_names'],
             len(djson['choice_frame_anomalies']),
             djson['emph_tags_preserved'], djson['orphan_emph_tags_stripped']))
    print("Wrote %s" % OUT)


if __name__ == '__main__':
    main()
