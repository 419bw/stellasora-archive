# -*- coding: utf-8 -*-
"""
Validator for scripts/build_story.py against the legacy docs it must not regress.

Independent by construction: it re-extracts ground truth from the raw Lua with plain
line scanning and never imports build_story.py.

A  逐句对齐   : legacy dialogue == new dialogue, per 关卡 Id, same order.
B  气泡完整性 : every SetBubble text of the mapped BBm script appears, in order,
               under the right 战斗阶段 marker; and the mapping itself follows the
               stage's own StoryId battle token, never the display code.
C  增量归因   : new-only lines are only scene headings / chat lines / battle bubbles /
               generic choices / branch markers, and their totals match Lua counts.
D  变异测试   : planted errors must be caught.
K  挂载语义   : a mounted BBm script only speaks with characters of that stage's chapter
               (F checks content against the declared stem, so a wrong declaration is
               invisible to it; this contract ignores file names entirely)
"""
import sys, os, re, glob, json, collections

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OLD = os.path.join(ROOT, 'docs')
NEW = os.path.join(ROOT, 'story_docs')
CFG = os.path.join(ROOT, 'data', 'ss_lua', 'Lua', 'Game', 'UI', 'Avg', '_cn', 'Config')
BIN = os.path.join(ROOT, 'data', 'StellaSoraData', 'CN', 'bin')
LANG = os.path.join(ROOT, 'data', 'StellaSoraData', 'CN', 'language', 'zh_CN')

# ---- 分级退出码（管线重构 Phase 0 引入）----------------------------------------
# 绝对真值契约（B/C/D/E/F/K/M：产物 vs 剧本原文/表数据、全部变异测试）违例 → exit 1。
# 历史对照契约（A/A2 的 old-vs-new 比较）走白名单：docs/ 是 legacy 生成器产物，
# 下列 6 个关卡的 old-vs-new 差异是旧生成器缺陷 + 新生成器 _NOT_IN_LOG_ 帧折叠修复
# 的既定结果（人工核对过，非回归信号），仅当差异超出白名单才硬失败。
HARD = []


def hard(cond, label):
    if not cond:
        HARD.append(label)


A_WHITELIST = {
    # old=docs/ legacy 产物, new=story_docs/ 现产物；len 为可比台词行数 old vs new
    '1011':        '旧版把渐显帧逐帧计入（len 208 vs 166），新版按 _NOT_IN_LOG_ 折叠',
    '101110206':   '旧版多计一条渐显帧（len 98 vs 97）',
    '201010209':   '旧版把渐显帧逐帧计入（len 97 vs 83）',
    '605':         '旧版把 ==A-1==/==RT== 信号原样写进文本（len 121 vs 121）',
    '927':         '旧版把渐显帧逐帧计入（len 249 vs 193）',
    '928':         '旧版多计渐显帧（len 314 vs 307）',

    # ---- 上游 1.16.1（2026-10-06）第十章《遥远的塔》更新触发的差异 ----
    # docs/ 是旧世代生成器产物（渲染自更早的上游数据）。以下每一项都已回 Lua
    # 原文核对，且与 04d14b6（上游自动同步提交=旧解析器渲染同一份新数据）对拍：
    # 新旧解析器台词逐行一致，差异全部在旧产物侧，非新解析器回归。上游再次
    # 修订文本时本表需按同一流程补充登记。
    '1002':        '旧产物文本损坏（Lua 原文「好，很有精神」，legacy 误作「好，好有精神」）',
    '1003':        '旧产物剥离 <r=BOSS></r> 注音标记（新版自 Phase 4a 起保留）',
    '1006':        '旧产物分句词序错（Lua 原文「与…同时开战」，legacy 作「同时与…一同开战」）',
    '1012':        '旧产物句尾「？」误作「。」（Lua 原文为「？」）',
    '1017':        '旧产物「的多」（Lua 原文「得多」）',
    '1019':        '旧产物未渲染该篇（台词 0 行 vs 103）；新旧解析器对拍一致',
    '1021':        '旧产物未渲染该篇（台词 0 行 vs 113）；新旧解析器对拍一致',
    '1022':        '旧产物未渲染该篇（台词 0 行 vs 147）；新旧解析器对拍一致',
    '1024':        '旧产物未渲染该篇（台词 0 行 vs 128）；新旧解析器对拍一致',
    '1025':        '旧产物未渲染该篇（台词 0 行 vs 95）；新旧解析器对拍一致',
    '1026':        '旧产物未渲染该篇（台词 0 行 vs 411）；新旧解析器对拍一致',
}


TALK = re.compile(r'^\*\*(.+?)\*\*(?:（[^）]*）)?：「(.*)」$')
BUBBLE = re.compile(r'^\*\*(.+?)\*\*（战斗气泡）：「(.*)」$')
CHAT = re.compile(r'^\*\*(.+?)\*\*(?:（短信）)?：「(.*)」$|^\*\*(.+?)\*\*：〔发送表情')
SCENE = re.compile(r'^> \*\*【场景 · (.*)】\*\*$')
WAVE = re.compile(r'^> \*\*\[战斗阶段 (.+)\]\*\*$')
MARKER = re.compile(r'^> \*\*\[(若选|▲)')
CHOICE = re.compile(r'^> \*\*\[(重大抉择|玩家抉择|抉择|玩家回应|通讯回复抉择)')
BULLET = re.compile(r'^> - ')
SILENT = re.compile(r'^> \*（其中')


def norm(s):
    s = s.replace('<br>', ' ')            # a line break is a space in text, not nothing
    s = re.sub(r'<[^>]*>', '', s)
    s = s.replace('==PLAYER_NAME==', '魔王')
    s = re.sub(r'==SEX\d*==', '你', s)
    s = re.sub(r'==[A-Za-z0-9_.]*==', ' ', s)     # ==A0.5== / ==Off== carry no words either
    s = s.replace('_NOT_IN_LOG_', '')
    return re.sub(r'\s+', ' ', s).strip()


def lines_of(path):
    return [l.rstrip('\r') for l in open(path, encoding='utf-8').read().splitlines()]


def id_of(path):
    return os.path.basename(path).split('_')[0]


def dialogue(path, drop_chat=False, raw=False):
    out = []
    for l in lines_of(path):
        if BUBBLE.match(l) or MARKER.match(l) or SCENE.match(l) or CHOICE.match(l) or BULLET.match(l) or SILENT.match(l):
            continue
        m = TALK.match(l)
        if not m:
            continue
        if drop_chat and '（短信）' in l:
            continue
        out.append(m.group(2) if raw else norm(m.group(2)))
    return out


# ---------------------------------------------------------------- lua ground truth
def unescape_lua(s):
    s = s.strip()
    # strip('"') would eat the closing quote of a line ending in \" and leave a dangling
    # backslash, so peel exactly the two delimiting quotes and unescape in one pass.
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1]
    esc = {'n': '\n', 't': ' ', '"': '"', '\\': '\\'}
    return re.sub(r'\\([nt"\\])', lambda m: esc[m.group(1)], s)


def lua_bubbles(stem):
    """[(wave_no, text)] by naive line scan."""
    p = os.path.join(CFG, stem + '.lua')
    if not os.path.exists(p):
        return None
    res, wave = [], '?'
    ls = lines_of(p)
    i = 0
    while i < len(ls):
        l = ls[i].strip()
        if l.startswith('cmd = "SetGroupId"'):
            j = i + 1
            while j < len(ls) and 'param' not in ls[j]:
                j += 1
            if j < len(ls):
                m = re.search(r'\{\s*"?([0-9A-Za-z_]+)"?', ls[j])
                if m:
                    wave = m.group(1)
        elif l.startswith('cmd = "SetBubble"'):
            j = i + 1
            vals = []
            while j < len(ls):
                st = ls[j].strip().rstrip(',')
                if st.startswith('}'):
                    break
                if not st.startswith('param'):
                    vals.append(st)
                j += 1
            if len(vals) >= 3:
                res.append((wave, norm(unescape_lua(vals[2]))))
        i += 1
    return res


def lua_counts(stems):
    c = collections.Counter()
    for stem in stems:
        p = os.path.join(CFG, stem + '.lua')
        if not os.path.exists(p):
            continue
        txt = open(p, encoding='utf-8').read()
        c['scene'] += len(re.findall(r'cmd = "SetSceneHeading"', txt))
        c['msg'] += len(re.findall(r'cmd = "SetPhoneMsg"', txt))
        c['choice'] += len(re.findall(r'cmd = "SetChoiceBegin"', txt))
        c['bubble'] += len(re.findall(r'cmd = "SetBubble"', txt))
    return c


# ============================================================= pair up old vs new
new_files = {}
for p in glob.glob(os.path.join(NEW, '**', 'sections', '*.md'), recursive=True):
    new_files.setdefault(id_of(p), p)
old_files = {}
for p in glob.glob(os.path.join(OLD, 'story', '**', 'sections', '*.md'), recursive=True):
    old_files.setdefault(id_of(p), p)

def strip_esc(s):
    BS = chr(92)
    return s.replace(BS + '"', '').replace(BS, '')


def recap_of(path):
    ls = lines_of(path)
    for i, l in enumerate(ls):
        if l.startswith('## 2.'):
            block = []
            for j in range(i + 1, len(ls)):
                s = ls[j].strip()
                if not s:
                    if block:
                        break
                    continue
                if s.startswith('## '):
                    break
                block.append(s.lstrip('> ').strip())
            return norm(' '.join(block))
    return ''


def lua_setintro_recap(stem):
    p = os.path.join(CFG, stem + '.lua')
    if not os.path.exists(p):
        return None
    txt = open(p, encoding='utf-8').read()
    i = txt.find('cmd = "SetIntro"')
    if i < 0:
        return ''
    j = txt.find('param', i)
    if j < 0:
        return None
    seg = txt[j:j + 900]
    strs = re.findall(r'"((?:[^"\\]|\\.)*)"', seg)
    if len(strs) < 4:
        return None
    return norm(unescape_lua(strs[3]).replace('==RT==', ' '))


story = json.load(open(os.path.join(BIN, 'Story.json'), encoding='utf-8'))
lang = json.load(open(os.path.join(LANG, 'Story.json'), encoding='utf-8'))
act = json.load(open(os.path.join(BIN, 'ActivityStory.json'), encoding='utf-8'))
both = sorted(set(old_files) & set(new_files))

print()
print("=" * 66)
print("A2  跳过概要：旧产物 == 新产物 == 剧本 SetIntro[3]")
print("=" * 66)
mism_old, mism_intro = [], []
escape_recap = 0
truncated = []
checked = 0
for i in both:
    np_ = new_files[i]
    new_recap = recap_of(np_)
    old_recap = recap_of(old_files[i])
    m = re.search(r'AVG 剧本\*\*：`([A-Za-z0-9_]+)`', open(np_, encoding='utf-8').read())
    stem = m.group(1) if m else None
    truth = lua_setintro_recap(stem) if stem else None
    if not new_recap and not old_recap and not truth:
        continue
    checked += 1
    if new_recap != old_recap:
        if new_recap == old_recap.replace('\\' + '"', '"'):
            escape_recap += 1
            continue          # 旧产物把 Lua 的 \" 漏进文本，新产物已正确还原
        if new_recap.startswith(strip_esc(old_recap).rstrip()):
            truncated.append((i, old_recap[-24:]))
            continue          # 旧产物用 "([^"]*)" 抠 SetIntro，遇到 \" 直接截断
        mism_old.append((i, old_recap[:38], new_recap[:38]))
    if truth is not None and truth and new_recap != truth:
        mism_intro.append((i, truth[:38], new_recap[:38]))
print('有概要的关卡：%d   新产物与 SetIntro 不一致：%d   旧产物转义泄漏：%d   旧产物被截断：%d   其它不一致：%d'
      % (checked, len(mism_intro), escape_recap, len(truncated), len(mism_old)))
for x in truncated[:6]:
    print('   ~  旧版截断于:', x)
for x in mism_old[:6]:
    print('   !! old vs new', x)
for x in mism_intro[:6]:
    print('   !! intro vs new', x)
hard(not mism_intro, 'A2 新产物概要与剧本 SetIntro[3] 不符：%d 处' % len(mism_intro))
hard(not [x for x in mism_old if x[0] not in A_WHITELIST],
     'A2 old-vs-new 超白名单：%s' % sorted({x[0] for x in mism_old} - set(A_WHITELIST)))

print()
print("=" * 66)
print("A  逐句对齐（旧产物台词序列 == 新产物台词序列）")
print("=" * 66)
diffs = []
escape_only = []
compared = 0
chat_added = 0
for i in both:
    a = dialogue(old_files[i])
    b = dialogue(new_files[i], drop_chat=True)
    chat_added += len([l for l in lines_of(new_files[i]) if '（短信）' in l or '〔发送表情' in l])
    if not a and not b:
        continue
    compared += 1
    if a != b:
        if [x.replace('\\' + '"', '"') for x in a] == b:
            escape_only.append(i)
            continue
        first = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), None)
        diffs.append((i, os.path.basename(old_files[i]), 'len %d vs %d' % (len(a), len(b)),
                      'old=%s' % (a[first][:34] if first is not None and first < len(a) else ''),
                      'new=%s' % (b[first][:34] if first is not None and first < len(b) else '')))
print('共同关卡：%d  有台词且可比：%d  真实不一致：%d  仅旧版转义泄漏：%d'
      % (len(both), compared, len(diffs), len(escape_only)))
print('   （转义泄漏 = 旧产物把 Lua 的 \\" 直接写进文本，共 %s 篇：%s）'
      % (len(escape_only), ", ".join(escape_only[:6])))
print('新产物补出的短信正文行数：%d（旧产物完全没渲染 SetPhoneMsg）' % chat_added)
for d in diffs[:12]:
    print('   !!', d)
hard(all(d[0] in A_WHITELIST for d in diffs),
     'A 历史对照超白名单：%s' % sorted({d[0] for d in diffs} - set(A_WHITELIST)))
old_only = set(old_files) - set(new_files)


def bbm_candidate(r):
    """The client names a bubble script after the battle token inside the stage's own
    StoryId (BAm06x5_01 -> 06x5, BAm09_BT03 -> BBm09_BT03), which is NOT Story.Chapter
    (the 特别篇 is numbered 7 in the table but filed as 06x5 between ch06 and ch07) and
    is NOT the localization display code either (ch09 rows 1010/1013 publish a display
    code crossed against their own StoryId/ConditionId/FloorId; the pack's script
    contents follow the StoryId). Kept as a local copy on purpose -- this validator is
    independent by construction; see scripts/story/build_story.py::bubble_stem_for for
    the generating side of the same rule."""
    m = re.match(r'^BA([0-9a-zA-Z]+)_([^_]+)$', str(r.get('StoryId') or ''))
    if not m:
        return None
    tail = re.sub(r'[^A-Za-z0-9]', '', m.group(2))
    if re.fullmatch(r'BT\d+', tail):
        return 'BB%s_%s' % (m.group(1), tail)
    return 'BB%s_%s' % (m.group(1), re.sub(r'[^A-Za-z0-9]', '', norm(lang.get(r.get('Index', ''), ''))))


def bbm_story_token(r):
    """The `BTnn` token baked into a stage's own StoryId, or None."""
    m = re.match(r'^BA[0-9a-zA-Z]+_([^_]+)$', str(r.get('StoryId') or ''))
    if not m:
        return None
    tail = re.sub(r'[^A-Za-z0-9]', '', m.group(1))
    return tail if re.fullmatch(r'BT\d+', tail) else None


exp_main = {str(r['Id']) for r in story.values()
            if not os.path.exists(os.path.join(CFG, str(r.get('StoryId')) + '.lua'))
            and not (r.get('IsBattle') and bbm_candidate(r)
                     and os.path.exists(os.path.join(CFG, bbm_candidate(r) + '.lua')))}
exp_act = {str(r['Id']) for r in act.values()
           if not os.path.exists(os.path.join(CFG, str(r.get('AvgLuaName') or '') + '.lua'))}
expected = exp_main | exp_act
print('旧有新无的关卡 Id：%d（预期：%d = 主线无剧本行 %d + 活动战斗行 %d）%s'
      % (len(old_only), len(expected), len(exp_main), len(exp_act),
         'OK' if old_only == expected else '!! 差集: %s' % str(sorted(old_only ^ expected))[:200]))
hard(old_only == expected,
     'A 旧有新无差集与表推导不符: %s' % str(sorted(old_only ^ expected))[:120])

print()
print("=" * 66)
print("B  战斗气泡完整性（naive 行扫描为准，逐阶段对齐）")
print("=" * 66)
bad_b = []
bubbles_checked = 0
bad_stem = []
for r in story.values():
    if not r.get('IsBattle'):
        continue
    idx = re.sub(r'[^A-Za-z0-9]', '', norm(lang.get(r.get('Index', ''), '')))
    stem = bbm_candidate(r)
    if not stem:
        continue
    # Contract: when a stage's own StoryId carries a BTnn token, the mounted script must
    # be the one that token names. A localisation display code may disagree with it (an
    # upstream slip); the StoryId side is what the script contents, ConditionId and
    # FloorId all follow, so trusting the display code silently swaps whole battles.
    token = bbm_story_token(r)
    if token and stem != 'BB%s_%s' % (re.match(r'^BA([0-9a-zA-Z]+)_', str(r.get('StoryId'))).group(1), token):
        bad_stem.append((str(r['Id']), str(r.get('StoryId')), token, idx, stem))
    truth = lua_bubbles(stem)
    if not truth:
        continue
    p = new_files.get(str(r['Id']))
    if not p:
        bad_b.append((str(r['Id']), stem, 'no section written'))
        continue
    waves, cur = [], None
    for l in lines_of(p):
        w = WAVE.match(l)
        if w:
            cur = w.group(1)
            continue
        m = BUBBLE.match(l)
        if m:
            waves.append((cur, norm(m.group(2))))
    bubbles_checked += len(truth)
    if waves != truth:
        bad_b.append((str(r['Id']), stem, 'expected %d got %d' % (len(truth), len(waves)),
                      next((t for t, g in zip(truth, waves) if t != g), ('', ''))))
print('挂接剧本的气泡条数（基准）：%d   不一致：%d' % (bubbles_checked, len(bad_b)))
for b in bad_b[:10]:
    print('   !!', b)
print('StoryId 编号与挂接剧本不同源：%d（应 0；若不为 0，说明又在用显示代号拼脚本名）' % len(bad_stem))
for b in bad_stem[:10]:
    print('   !!', b)
hard(not bad_b, 'B 气泡完整性不一致：%d 处' % len(bad_b))
hard(not bad_stem, 'B StoryId 编号与挂接剧本不同源：%d 处' % len(bad_stem))

print()
print("=" * 66)
print("C  新增行的来源核对")
print("=" * 66)
stems = []
for p in glob.glob(os.path.join(NEW, '**', 'sections', '*.md'), recursive=True):
    m = re.search(r'AVG \u5267\u672c\*\*\uff1a`([A-Za-z0-9_]+)`', open(p, encoding='utf-8').read())
    if m:
        stems.append(m.group(1))
truth = lua_counts(stems)
n_scene = sum(1 for p in new_files.values() for l in lines_of(p) if SCENE.match(l))
n_bub = sum(1 for p in new_files.values() for l in lines_of(p) if BUBBLE.match(l))
n_chat = sum(1 for p in new_files.values() for l in lines_of(p) if '（短信）' in l or '〔发送表情' in l)
n_choice_generic = sum(1 for p in new_files.values() for l in lines_of(p)
                       if l.startswith('> **[抉择') or l.startswith('> **[玩家回应'))
print('场景卡 md=%d  Lua SetSceneHeading=%d' % (n_scene, truth['scene']))
print('气泡   md=%d  Lua SetBubble(含未挂接文件)=%d' % (n_bub, truth['bubble']))
print('短信   md=%d  Lua SetPhoneMsg=%d' % (n_chat, truth['msg']))
print('通用抉择块 md=%d  Lua SetChoiceBegin=%d' % (n_choice_generic, truth['choice']))
# 前三项的既有基线是相等，作硬断言；通用抉择块只作信息行——Lua 的 SetChoiceBegin
# 含重大抉择帧，md 的「抉择/玩家回应」通用块天然不含（基线 474 vs 485），不可断言相等。
hard(n_scene == truth['scene'], 'C 场景卡计数不符: md=%d Lua=%d' % (n_scene, truth['scene']))
hard(n_bub == truth['bubble'], 'C 气泡计数不符: md=%d Lua=%d' % (n_bub, truth['bubble']))
hard(n_chat == truth['msg'], 'C 短信行数不符: md=%d Lua=%d' % (n_chat, truth['msg']))

print()
print("=" * 66)
print("D  变异测试")
print("=" * 66)
# pick a battle section with bubbles
bt = None
for i, p in new_files.items():
    if any(BUBBLE.match(l) for l in lines_of(p)):
        bt = p
        break
orig = open(bt, encoding='utf-8').read()
rows = {str(r['Id']): r for r in story.values()}
r = rows[id_of(bt)]
stem = bbm_candidate(r)
truth = lua_bubbles(stem)


def bubble_seq(text):
    waves, cur = [], None
    for l in text.splitlines():
        w = WAVE.match(l.strip())
        if w:
            cur = w.group(1)
            continue
        m = BUBBLE.match(l.strip())
        if m:
            waves.append((cur, norm(m.group(2))))
    return waves


base = bubble_seq(orig)
_d_pos = base == truth
hard(_d_pos, 'D 正对照 FAIL（未改动文件应与 Lua 一致）')
print('正对照（未改动文件）: %s' % ('PASS' if _d_pos else 'FAIL'))
v1 = orig.replace(base[1][1], base[1][1] + 'X', 1)
first_wave_line = next(l for l in orig.splitlines() if WAVE.match(l.strip()))
v2 = orig.replace(first_wave_line, "> **[战斗阶段 99]**", 1)
first_bubble_line = next(l for l in orig.splitlines() if BUBBLE.match(l.strip()))
v3 = orig.replace(first_bubble_line + "\n", "", 1)
_d1 = bubble_seq(v1) != truth
_d2 = bubble_seq(v2) != truth
_d3 = bubble_seq(v3) != truth
hard(_d1, 'D 植入[改一个字] MISSED')
hard(_d2, 'D 植入[阶段号写错] MISSED')
hard(_d3, 'D 植入[删掉一条气泡] MISSED')
print('植入[改一个字]      : %s' % ('CAUGHT' if _d1 else 'MISSED'))
print('植入[阶段号写错]    : %s' % ('CAUGHT' if _d2 else 'MISSED'))
print('植入[删掉一条气泡]  : %s' % ('CAUGHT' if _d3 else 'MISSED'))
print('样本文件: %s / %s 气泡 %d 条' % (os.path.basename(bt), stem, len(truth)))


# ============================== E  新增四族（角色/NPC/唱片/故事集）挂载与逐句保真
def tbl(name, folder=BIN):
    o = json.load(open(os.path.join(folder, name + '.json'), encoding='utf-8'))
    return list(o.values()) if isinstance(o, dict) else o


def lg(name):
    return json.load(open(os.path.join(LANG, name + '.json'), encoding='utf-8'))


ASSET = re.compile(r'[a-z][a-z0-9_]*')


def lua_speech_rows(stem):
    """Naive line scan of one script: [(cmd, raw text)] for every SetTalk / SetPhoneMsg that
    carries words, in the raw official order.

    Only the documented content rules are mirrored here (empty lines and sprite asset keys
    inside SetTalk carry no words; an asset key inside SetPhoneMsg is a sticker send).
    The text is unescaped but deliberately NOT cleaned, so inline markup is still in it.
    """
    p = os.path.join(CFG, stem + '.lua')
    if not os.path.exists(p):
        return None
    ls = lines_of(p)
    out, i = [], 0
    while i < len(ls):
        s = ls[i].strip()
        m = re.match(r'cmd = "(SetTalk|SetPhoneMsg)"', s)
        if not m:
            i += 1
            continue
        j = i + 1
        vals = []
        while j < len(ls):
            st = ls[j].strip()
            if st.startswith('param'):
                head = st.split('{', 1)[1] if '{' in st else ''
                head = head.rstrip('}').rstrip(',').strip()
                if head:
                    vals.append(head)
                if st.rstrip().endswith('}'):
                    break
                j += 1
                continue
            st = st.rstrip(',')
            if st.startswith('}'):
                break
            vals.append(st)
            j += 1
        if len(vals) >= 3:
            raw = unescape_lua(vals[2])
            seen = norm(raw)
            if seen and not ASSET.fullmatch(seen) and not (
                    m.group(1) == 'SetTalk'
                    and (seen.startswith(('ep_', 'BG_')) or ASSET.fullmatch(seen))):
                out.append((m.group(1), raw))
        i = j
    return out


def lua_dialogue_seq(stem):
    rows = lua_speech_rows(stem)
    return None if rows is None else [norm(r) for _c, r in fold_nonlog(rows)]


NONLOG = '_NOT_IN_LOG_'


def _vsig(text):
    """Signature of one frame's rendered text (mirrors build_story.clean_dialogue)."""
    return re.sub(r'\s+', '', norm(text))


def _vrelated(a, b):
    return a == b or a in b or b in a


def fold_nonlog(rows):
    """[(cmd, raw)] with the client's _NOT_IN_LOG_ fade-in frames folded away.

    The client renders one long line as several SetTalk with a rising
    <alpha=#22..#FF>; those frames never enter the in-game backlog, so the generator
    emits one archive line per rendered line, not one per frame. This mirrors
    scripts/story/build_story.py:nonlog_repeats so the truth sequence compared
    against the pages has the same shape as what was generated.
    """
    tagged = [(cmd, not raw.startswith(NONLOG), _vsig(raw)) for cmd, raw in rows]
    n = len(tagged)
    drop = set()
    i = 0
    while i < n:
        if tagged[i][1]:
            i += 1
            continue
        j = i
        while j < n and not tagged[j][1]:
            j += 1
        run = range(i, j)
        nonempty = [k for k in run if tagged[k][2]]
        if nonempty:
            last = nonempty[-1]
            sig = tagged[last][2]
            twin = None
            for step in (-1, 1):
                k = last + step
                while 0 <= k < n and tagged[k][2] and _vrelated(tagged[k][2], sig):
                    if tagged[k][1] and tagged[k][2] == sig:
                        twin = k
                        break
                    k += step
                if twin is not None:
                    break
            if twin is None:                # rule 2: keep the animation's final state
                drop.update(run)
                drop.discard(last)
            else:                           # rule 1: the log already shows it
                drop.update(run)
        i = j
    return [rows[k] for k in range(n) if k not in drop]


LANG_P, LANG_N, LANG_D = lg('Plot'), lg('NPCAffinityPlot'), lg('DiscIP')
LANG_S, LANG_SC, LANG_C = lg('StorySetSection'), lg('StorySetChapter'), lg('Character')

expect = {}          # (family, item id) -> (stem, title, page path)
for r in tbl('Plot'):
    if not LANG_P.get(r.get('Name', '')):
        continue     # costume re-issue rows share the titled row's page
    expect[('characters', r['Id'])] = (r['AvgId'], LANG_P[r['Name']])
for r in tbl('NPCAffinityPlot'):
    nm = LANG_N.get(r.get('Name', ''))
    sub = LANG_N.get(r.get('Desc', ''))
    expect[('npc_bonds', r['Id'])] = (r['avgId'], (nm + ' ' + sub).strip())
for r in tbl('DiscIP'):
    if r.get('AvgId') and LANG_D.get(r.get('StoryName', '')):
        expect[('discs', r['Id'])] = (r['AvgId'], LANG_D[r['StoryName']])
for r in tbl('StorySetSection'):
    expect[('storysets', r['Id'])] = (r['AVGId'], LANG_S.get(r.get('Desc', ''), ''))

actual = {}
for fam in ('characters', 'npc_bonds', 'discs', 'storysets'):
    for p in glob.glob(os.path.join(NEW, fam, '**', '*.md'), recursive=True):
        txt = open(p, encoding='utf-8').read()
        sid = re.search(r'\*\*(?:剧情档案|小节|唱片) ID\*\*：`(\d+)`', txt)
        stem = re.search(r'AVG 剧本\*\*：`([A-Za-z0-9_]+)`', txt)
        h1 = re.search(r'^# (.+)$', txt, re.M)
        if sid and stem:
            actual[(fam, int(sid.group(1)))] = (stem.group(1), h1.group(1) if h1 else '', p)

print()
print("=" * 66)
print("E  新增四族：表 -> 页面 的挂载、标题、逐句、概要是否 1:1")
print("=" * 66)
missing = sorted(set(expect) - set(actual), key=str)
extra = sorted(set(actual) - set(expect), key=str)
bad_stem = [k for k in set(expect) & set(actual) if expect[k][0] != actual[k][0]]
bad_title = [(k, expect[k][1], actual[k][1]) for k in sorted(set(expect) & set(actual))
             if norm(expect[k][1]) != norm(actual[k][1])]
print('表应出页面：%d   实际：%d   缺失：%d   多余：%d   剧本代号不符：%d   标题与官方文案不符：%d'
      % (len(expect), len(actual), len(missing), len(extra), len(bad_stem), len(bad_title)))
print('分族实际数：%s' % dict(collections.Counter(k[0] for k in actual)))
for x in missing[:5]:
    print('   缺:', x)
for x in extra[:5]:
    print('   多:', x)
for x in bad_title[:5]:
    print('   标题:', x)
hard(not missing, 'E 表声明的页面缺失：%d' % len(missing))
hard(not extra, 'E 产物多出未声明页面：%d' % len(extra))
hard(not bad_stem, 'E 剧本代号不符：%d' % len(bad_stem))
hard(not bad_title, 'E 标题与官方文案不符：%d' % len(bad_title))

seq_bad, recap_bad, nodir = [], [], []
for k in sorted(set(expect) & set(actual), key=str):
    stem, _title = expect[k]
    _s, _h, path = actual[k]
    truth = lua_dialogue_seq(stem)
    got = dialogue(path)
    if truth is None:
        nodir.append((k, stem))
    elif truth != got:
        d = next((i for i, (a, b) in enumerate(zip(truth, got)) if a != b),
                 min(len(truth), len(got)))
        seq_bad.append((k, stem, len(truth), len(got), d,
                        truth[d][:26] if d < len(truth) else '-',
                        got[d][:26] if d < len(got) else '-'))
    tr = lua_setintro_recap(stem)
    if tr and recap_of(path) != tr:
        recap_bad.append((k, stem, tr[:30], recap_of(path)[:30]))
print('\n逐句序列不一致：%d   跳过概要与 SetIntro[3] 不符：%d   包内查无剧本：%d'
      % (len(seq_bad), len(recap_bad), len(nodir)))
for x in seq_bad[:6]:
    print('   ~ %s %s 表内%d句/产物%d句，第%d句起分叉: %r != %r' % x)
for x in recap_bad[:6]:
    print('   ~ %s %s SetIntro=%r 产物=%r' % x)
hard(not seq_bad, 'E 逐句序列不一致：%d 页' % len(seq_bad))
hard(not recap_bad, 'E 跳过概要与 SetIntro[3] 不符：%d 页' % len(recap_bad))
hard(not nodir, 'E 表声明剧本在包内查无文件：%d' % len(nodir))

# 变异测试：新族页面只要被动过就该被 E 抓到
probe_key = next(k for k in sorted(set(expect) & set(actual), key=str)
                 if k[0] == 'storysets' and len(lua_dialogue_seq(expect[k][0]) or []) > 8)
pstem, _ = expect[probe_key]
ppath = actual[probe_key][2]
base_seq = lua_dialogue_seq(pstem)
md = open(ppath, encoding='utf-8').read()
first = next(l for l in md.splitlines() if TALK.match(l))
mut = md.replace(first, first.replace('」', 'X」'), 1)
tmp = ppath + '.mut.md'
open(tmp, 'w', encoding='utf-8', newline='\n').write(mut)
caught_line = dialogue(tmp) != base_seq
recap_line = next(l for l in md.splitlines() if l.startswith('> ') and recap_of(ppath).split(' ')[0][:6] in l) if recap_of(ppath) else ''
mut2 = md.replace(recap_line, '> 被改写过的概要', 1) if recap_line else md.replace('# ', '# X', 1)
open(tmp, 'w', encoding='utf-8', newline='\n').write(mut2)
caught_recap = recap_of(tmp) != lua_setintro_recap(pstem)
os.remove(tmp)
hard(caught_line, 'E 变异[改一句台词] MISSED')
hard(caught_recap, 'E 变异[改概要] MISSED')
print('\n变异测试（%s / %s，%d 句）: 改一句台词->%s   改概要->%s'
      % (probe_key, pstem, len(base_seq),
         'CAUGHT' if caught_line else 'MISSED', 'CAUGHT' if caught_recap else 'MISSED'))


# ================================================= F  全树逐页保真（每一页 vs 它自己的剧本）
def md_bubbles(path):
    out, cur = [], '?'
    for l in lines_of(path):
        w = WAVE.match(l.strip())
        if w:
            cur = w.group(1)
            continue
        m = BUBBLE.match(l.strip())
        if m:
            out.append((cur, norm(m.group(2))))
    return out


print()
print("=" * 66)
print("F  全树逐页：台词序列 / 气泡+阶段 / 跳过概要，三项各自对齐剧本原文")
print("=" * 66)
pages, f_seq, f_bub, f_recap = [], [], [], []
for p in glob.glob(os.path.join(NEW, '**', '*.md'), recursive=True):
    txt = open(p, encoding='utf-8').read()
    m = re.search(r'AVG 剧本\*\*：`([A-Za-z0-9_]+)`', txt)
    if not m:
        continue
    stem = m.group(1)
    pages.append((p, stem))
    if lua_dialogue_seq(stem) != dialogue(p):
        f_seq.append((os.path.relpath(p, NEW), stem))
    lb = lua_bubbles(stem) or []
    if lb and lb != md_bubbles(p):
        f_bub.append((os.path.relpath(p, NEW), stem, len(lb), len(md_bubbles(p))))
    tr = lua_setintro_recap(stem)
    if tr and tr != recap_of(p):
        f_recap.append((os.path.relpath(p, NEW), stem))
print('逐页检查：%d 页   台词序列不符：%d   气泡/阶段不符：%d   概要不符：%d'
      % (len(pages), len(f_seq), len(f_bub), len(f_recap)))
for x in f_seq[:6]:
    print('   ~ 台词', x)
for x in f_bub[:6]:
    print('   ~ 气泡', x)
for x in f_recap[:6]:
    print('   ~ 概要', x)
hard(not f_seq, 'F 台词序列不符：%d 页' % len(f_seq))
hard(not f_bub, 'F 气泡/阶段不符：%d 页' % len(f_bub))
hard(not f_recap, 'F 概要不符：%d 页' % len(f_recap))

# ---------------------------------------------- N  委托结算分段保真（dispatch 专场）
print()
print("=" * 66)
print("N  委托结算演出：一页 == 该段（脚本 + SetGroupId 段号）的台词序列")
print("=" * 66)


def lua_segment_rows(stem, group):
    """SetTalk/SetPhoneMsg 台词行，限定在 SetGroupId==group 的那一段内。

    抽取规则镜像 lua_speech_rows，但按段边界裁开：一份 DP_* 脚本按 SetGroupId 被
    几十段共用，一个 dispatch 页只对应其中一段。
    """
    p = os.path.join(CFG, stem + '.lua')
    if not os.path.exists(p):
        return None
    ls, out, i, cur = lines_of(p), [], 0, None
    while i < len(ls):
        s = ls[i].strip()
        if re.match(r'cmd = "SetGroupId"', s):
            j = i + 1
            cur = None
            while j < len(ls) and ls[j].strip().startswith('param'):
                raw = ls[j].strip().split('{', 1)[1] if '{' in ls[j].strip() else ''
                cur = unescape_lua(raw.split('}')[0])
                break
            i += 1
            continue
        m = re.match(r'cmd = "(SetTalk|SetPhoneMsg)"', s)
        if m and cur == group:
            j, vals = i + 1, []
            while j < len(ls):
                st = ls[j].strip()
                if st.startswith('param'):
                    head = st.split('{', 1)[1] if '{' in st else ''
                    head = head.rstrip('}').rstrip(',').strip()
                    if head:
                        vals.append(head)
                    if st.rstrip().endswith('}'):
                        break
                    j += 1
                    continue
                st = st.rstrip(',')
                if st.startswith('}'):
                    break
                vals.append(st)
                j += 1
            if len(vals) >= 3:
                raw = unescape_lua(vals[2])
                seen = norm(raw)
                if seen and not ASSET.fullmatch(seen) and not (
                        m.group(1) == 'SetTalk'
                        and (seen.startswith(('ep_', 'BG_')) or ASSET.fullmatch(seen))):
                    out.append((m.group(1), raw))
            i = j
            continue
        i += 1
    return out


def lua_segment_seq(stem, group):
    rows = lua_segment_rows(stem, group)
    return None if rows is None else [norm(r) for _c, r in fold_nonlog(rows)]


DISPATCH = [p for p in glob.glob(os.path.join(NEW, 'dispatch', '**', '*.md'), recursive=True)
            if not os.path.basename(p).startswith('_')]
PERF_MARK = re.compile(r'结算演出\*\*：`([A-Za-z0-9_]+)`（第 `([A-Za-z0-9_]+)` 段）')
disp_bad, disp_stems = [], set()
for p in DISPATCH:
    txt = open(p, encoding='utf-8').read()
    m = PERF_MARK.search(txt)
    if not m:
        disp_bad.append((os.path.relpath(p, NEW), '缺分段挂载行'))
        continue
    stem, grp = m.group(1), m.group(2)
    disp_stems.add(stem)
    truth, got = lua_segment_seq(stem, grp), dialogue(p)
    if truth is None or truth != got:
        d = next((i for i, (a, b) in enumerate(zip(truth or [], got)) if a != b),
                 min(len(truth or []), len(got)))
        disp_bad.append((os.path.relpath(p, NEW), stem, grp, len(truth or []), len(got), d,
                         (truth[d][:26] if truth and d < len(truth) else '-'),
                         (got[d][:26] if d < len(got) else '-')))
print('委托结算分段页：%d   涉及剧本 %d   台词序列不符：%d' % (len(DISPATCH), len(disp_stems), len(disp_bad)))
for x in disp_bad[:8]:
    print('   ~', x)
hard(not disp_bad, 'N 委托分段保真不符：%d 页' % len(disp_bad))

if DISPATCH:
    _mp = DISPATCH[0]
    _mtxt = open(_mp, encoding='utf-8').read()
    _mm = PERF_MARK.search(_mtxt)
    _tstem, _tgrp = _mm.group(1), _mm.group(2)
    _tline = next(l for l in _mtxt.splitlines() if TALK.match(l))
    _tmp = _mp + '.mut.md'
    open(_tmp, 'w', encoding='utf-8', newline='\n').write(_mtxt.replace(_tline, _tline + '变', 1))
    _n_ok = lua_segment_seq(_tstem, _tgrp) != dialogue(_tmp)
    os.remove(_tmp)
    hard(_n_ok, 'N 变异[改一句结算台词] MISSED')
    print('变异测试（%s / %s 第 %s 段）: 改一句台词 -> %s'
          % (os.path.basename(_mp), _tstem, _tgrp, 'CAUGHT' if _n_ok else 'MISSED'))

# 覆盖对账：产物声明已渲染的剧本数要和 _coverage.md 一致
cov = open(os.path.join(NEW, '_coverage.md'), encoding='utf-8').read()
decl = re.search(r'已渲染：(\d+)　未渲染：(\d+)', cov)
uniq = len({s for _p, s in pages} | disp_stems)
print('去重后剧本数 %d（整本 %d + 委托分段涉及 %d），_coverage.md 声明 %s'
      % (uniq, len({s for _p, s in pages}), len(disp_stems), decl.group(1) if decl else '?'))
hard(decl is not None and int(decl.group(1)) == uniq,
     'F 覆盖对账不符: _coverage.md 声明 %s，实际去重 %d' % (decl.group(1) if decl else '?', uniq))

# 变异测试：序章与存目战斗页各改一处
for label, pick in (('序章台词', lambda q: q[1].startswith('STm00')),
                    ('存目气泡阶段', lambda q: q[1].startswith('BBm00'))):
    tgt = next((q for q in pages if pick(q)), None)
    if not tgt:
        hard(False, 'F %s：找不到变异样本' % label)
        print('%s：找不到样本' % label)
        continue
    p, stem = tgt
    md = open(p, encoding='utf-8').read()
    tmp = p + '.mut.md'
    if label == '序章台词':
        first = next(l for l in md.splitlines() if TALK.match(l))
        mut = md.replace(first, first.replace('」', 'X」'), 1)
        open(tmp, 'w', encoding='utf-8', newline='\n').write(mut)
        ok = dialogue(tmp) != lua_dialogue_seq(stem)
    else:
        wl = next(l for l in md.splitlines() if WAVE.match(l.strip()))
        mut = md.replace(wl, '> **[战斗阶段 99]**', 1)
        open(tmp, 'w', encoding='utf-8', newline='\n').write(mut)
        ok = md_bubbles(tmp) != (lua_bubbles(stem) or [])
    os.remove(tmp)
    hard(ok, 'F %s 变异 MISSED' % label)
    print('%s 变异（%s）-> %s' % (label, stem, 'CAUGHT' if ok else 'MISSED'))


# ============================================================ K  挂载语义
print()
print("=" * 66)
print("K  气泡剧本挂得对不对：说话人必须出自该关卡所在章的演员表")
print("=" * 66)
print("   F 只保证「页面内容 == 声明的那份剧本」，声明错了它看不见。")
print("   这里不看文件名规则，只看人：挂错章的剧本，说话人必然在那章的正篇里没出现过。")
SPK = re.compile(r'"(avg\d+_\d+)')


def cast_of(stem):
    p = os.path.join(CFG, str(stem) + '.lua')
    if not os.path.isfile(p):
        return set()
    return set(SPK.findall(open(p, encoding='utf-8', errors='replace').read()))


ROWS = {str(r['Id']): r for r in story.values()}
CHAP_CAST, ALL_CAST = collections.defaultdict(set), set()
for r in story.values():
    if r.get('IsBattle') or not r.get('StoryId'):
        continue
    s = cast_of(r['StoryId'])
    CHAP_CAST[int(r['Chapter'])] |= s
    ALL_CAST |= s


def audit_mount(path, stem):
    """Violations for one (page, declared script) pair. Empty list means consistent."""
    row = ROWS.get(id_of(path))
    if not row:
        return ['关卡行不存在']
    who, ch = cast_of(stem), int(row['Chapter'])
    if not who:
        return ['剧本查无文件']
    return ['%s 出自第 %s 章而非第 %d 章' % (s, sorted(
        c for c, u in CHAP_CAST.items() if s in u), ch)
        for s in sorted(who) if s in ALL_CAST and s not in CHAP_CAST[ch]]


bad_k, odd_k, checked_k = [], [], 0
for p, stem in pages:
    if not stem.startswith('BB') or not os.path.relpath(p, NEW).startswith('main'):
        continue
    checked_k += 1
    for v in audit_mount(p, stem):
        bad_k.append((os.path.relpath(p, NEW), stem, v))
    odd_k += [(os.path.relpath(p, NEW), s) for s in sorted(cast_of(stem)) if s not in ALL_CAST]
print('挂载气泡剧本的主线条目：%d   说话人越章：%d   正篇里没露过面的说话人（不计违例）：%d'
      % (checked_k, len(bad_k), len(set(x[1] for x in odd_k))))
for x in bad_k[:8]:
    print('   ~', x)
for x in sorted(set(odd_k))[:5]:
    print('   ?', x)
hard(not bad_k, 'K 说话人越章违例：%d 处' % len(bad_k))

print()
print('K2 变异测试')
sp = next(p for p, s in pages if s == 'BBm07_BT01')
_k2_pos = not audit_mount(sp, 'BBm07_BT01')
hard(_k2_pos, 'K2 正对照 FAIL')
print('正对照（第七章 BT01 挂 BBm07_BT01）: %s'
      % ('PASS' if _k2_pos else 'FAIL'))
# 特别篇的战斗行现在没有页面，所以直接按关卡 Id 造一个路径来测规则本身
sp_row = next(str(r['Id']) for r in story.values()
              if r.get('IsBattle') and int(r['Chapter']) == 7)
fake = os.path.join(NEW, 'main', 'x', 'sections', '%s_BT01_x.md' % sp_row)
_k2a = bool(audit_mount(fake, 'BBm07_BT01'))
_k2b = bool(audit_mount(sp, 'BBm08_BT01'))
hard(_k2a, 'K2 植入[把 BBm07_BT01 挂回特别篇] MISSED')
hard(_k2b, 'K2 植入[把 BBm08_BT01 挂到第七章] MISSED')
print('植入[把 BBm07_BT01 挂回特别篇]: %s'
      % ('CAUGHT' if _k2a else 'MISSED'))
print('植入[把 BBm08_BT01 挂到第七章]: %s'
      % ('CAUGHT' if _k2b else 'MISSED'))


# ============================================================ M  注音保真
print()
print("=" * 66)
print("M  台词里的 <r=注音></r> / <r=注音>正文</r> 逐句对齐剧本：位置（紧跟哪个字）+ 文字")
print("=" * 66)
# 空体 ruby 锚定标签前一个字符；带体 ruby 的 base 在标签体内（可多字，取末字）。
RUBY = re.compile(r'<r=([^<>]*)>([^<>]+)</r>|<r=([^<>]*)></r>')


def ruby_marks(text):
    """[(注音落点字, 注音)] in reading order. The client's empty-body ruby is
    identified by where it was inserted; the bodied form carries its own base."""
    out = []
    for m in RUBY.finditer(text):
        if m.group(2) is not None:                       # 带体 <r=note>base</r>
            base = norm(m.group(2))
            out.append((base[-1] if base else '', m.group(1)))
        else:                                            # 空体 <r=note></r>
            base = norm(text[:m.start()])
            out.append((base[-1] if base else '', m.group(3)))
    return out


def audit_ruby(path, stem):
    rows = lua_speech_rows(stem)
    if rows is None:
        return ['剧本查无文件']
    rows = fold_nonlog(rows)
    texts = dialogue(path, raw=True)
    if len(texts) != len(rows):
        return ['句数不等 md=%d lua=%d' % (len(texts), len(rows))]
    errs = []
    for n, (mt, (_cmd, raw)) in enumerate(zip(texts, rows)):
        a, b = ruby_marks(mt), ruby_marks(raw)
        if a != b:
            errs.append('第 %d 句 md=%s 剧本=%s' % (n + 1, a, b))
    return errs


bad_m, marks_m, pages_m = [], 0, 0
for p, stem in pages:
    n = sum(len(ruby_marks(t)) for t in dialogue(p, raw=True))
    marks_m += n
    pages_m += 1 if n else 0
    for e in audit_ruby(p, stem):
        bad_m.append((os.path.relpath(p, NEW), stem, e))
print('全树注音标记：%d 处   有注音的页：%d   不符：%d' % (marks_m, pages_m, len(bad_m)))
for x in bad_m[:6]:
    print('   ~', x)
hard(not bad_m, 'M 注音保真不符：%d 处' % len(bad_m))

print()
print('M2 变异测试')
rp = next(p for p, s in pages if '<r=mowang></r>' in open(p, encoding='utf-8').read())
rstem = next(s for p, s in pages if p == rp)
src = open(rp, encoding='utf-8').read()
tmp = rp + '.mut.md'
try:
    _m_pos = not audit_ruby(rp, rstem)
    hard(_m_pos, 'M2 正对照 FAIL')
    print('正对照（未篡改）: %s' % ('PASS' if _m_pos else 'FAIL'))
    for label, mut in [
            ('植入[删掉一处注音]', src.replace('<r=mowang></r>', '', 1)),
            ('植入[注音挪到字后]', src.replace('魔<r=mowang></r>王', '魔王<r=mowang></r>', 1)),
            ('植入[改注音文字]', src.replace('<r=mowang></r>', '<r=BOSS></r>', 1))]:
        if mut == src:
            print('%s : 样本里没有该形状，跳过' % label)
            continue
        open(tmp, 'w', encoding='utf-8', newline='\n').write(mut)
        _m_ok = bool(audit_ruby(tmp, rstem))
        hard(_m_ok, 'M2 %s MISSED' % label)
        print('%s : %s' % (label, 'CAUGHT' if _m_ok else 'MISSED'))
finally:
    if os.path.exists(tmp):
        os.remove(tmp)
_m_re = not audit_ruby(rp, rstem)
hard(_m_re, 'M2 还原后复检 FAIL')
print('还原后复检: %s' % ('PASS' if _m_re else 'FAIL'))

# ---- 汇总与退出码 -------------------------------------------------------------
print()
print('=' * 66)
if HARD:
    print('RESULT: FAIL —— %d 处绝对真值契约违例：' % len(HARD))
    for x in HARD:
        print('   ✗', x)
    sys.exit(1)
print('RESULT: PASS —— 绝对真值契约（B/C/D/E/F/K/M + 全部变异测试）全绿；')
print('              历史对照（A/A2）在白名单内（%d 关卡：%s）'
      % (len(A_WHITELIST), ', '.join(sorted(A_WHITELIST))))
sys.exit(0)
