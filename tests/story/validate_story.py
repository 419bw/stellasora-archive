# -*- coding: utf-8 -*-
"""
Validator for scripts/build_story.py against the legacy docs it must not regress.

Independent by construction: it re-extracts ground truth from the raw Lua with plain
line scanning and never imports build_story.py.

A  逐句对齐   : legacy dialogue == new dialogue, per 关卡 Id, same order.
B  气泡完整性 : every SetBubble text of the mapped BBm script appears, in order,
               under the right 战斗阶段 marker.
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
old_only = set(old_files) - set(new_files)


def bbm_candidate(r):
    """The client names a bubble script after the chapter token inside the stage's own
    StoryId (BAm06x5_01 -> 06x5), which is NOT Story.Chapter (the 特别篇 is numbered 7 in
    the table but filed as 06x5 between ch06 and ch07)."""
    m = re.match(r'^BA([0-9a-zA-Z]+)_[^_]+$', str(r.get('StoryId') or ''))
    if not m:
        return None
    return 'BB%s_%s' % (m.group(1), re.sub(r'[^A-Za-z0-9]', '', norm(lang.get(r.get('Index', ''), ''))))


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

print()
print("=" * 66)
print("B  战斗气泡完整性（naive 行扫描为准，逐阶段对齐）")
print("=" * 66)
bad_b = []
bubbles_checked = 0
for r in story.values():
    if not r.get('IsBattle'):
        continue
    idx = re.sub(r'[^A-Za-z0-9]', '', norm(lang.get(r.get('Index', ''), '')))
    stem = bbm_candidate(r)
    if not stem:
        continue
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
print('正对照（未改动文件）: %s' % ('PASS' if base == truth else 'FAIL'))
v1 = orig.replace(base[1][1], base[1][1] + 'X', 1)
first_wave_line = next(l for l in orig.splitlines() if WAVE.match(l.strip()))
v2 = orig.replace(first_wave_line, "> **[战斗阶段 99]**", 1)
first_bubble_line = next(l for l in orig.splitlines() if BUBBLE.match(l.strip()))
v3 = orig.replace(first_bubble_line + "\n", "", 1)
print('植入[改一个字]      : %s' % ('CAUGHT' if bubble_seq(v1) != truth else 'MISSED'))
print('植入[阶段号写错]    : %s' % ('CAUGHT' if bubble_seq(v2) != truth else 'MISSED'))
print('植入[删掉一条气泡]  : %s' % ('CAUGHT' if bubble_seq(v3) != truth else 'MISSED'))
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
    return None if rows is None else [norm(r) for _c, r in rows]


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

# 覆盖对账：产物声明已渲染的剧本数要和 _coverage.md 一致
cov = open(os.path.join(NEW, '_coverage.md'), encoding='utf-8').read()
decl = re.search(r'已渲染：(\d+)　未渲染：(\d+)', cov)
uniq = len({s for _p, s in pages})
print('去重后剧本数 %d，_coverage.md 声明 %s' % (uniq, decl.group(1) if decl else '?'))

# 变异测试：序章与存目战斗页各改一处
for label, pick in (('序章台词', lambda q: q[1].startswith('STm00')),
                    ('存目气泡阶段', lambda q: q[1].startswith('BBm00'))):
    tgt = next((q for q in pages if pick(q)), None)
    if not tgt:
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

print()
print('K2 变异测试')
sp = next(p for p, s in pages if s == 'BBm07_BT01')
print('正对照（第七章 BT01 挂 BBm07_BT01）: %s'
      % ('PASS' if not audit_mount(sp, 'BBm07_BT01') else 'FAIL'))
# 特别篇的战斗行现在没有页面，所以直接按关卡 Id 造一个路径来测规则本身
sp_row = next(str(r['Id']) for r in story.values()
              if r.get('IsBattle') and int(r['Chapter']) == 7)
fake = os.path.join(NEW, 'main', 'x', 'sections', '%s_BT01_x.md' % sp_row)
print('植入[把 BBm07_BT01 挂回特别篇]: %s'
      % ('CAUGHT' if audit_mount(fake, 'BBm07_BT01') else 'MISSED'))
print('植入[把 BBm08_BT01 挂到第七章]: %s'
      % ('CAUGHT' if audit_mount(sp, 'BBm08_BT01') else 'MISSED'))


# ============================================================ M  注音保真
print()
print("=" * 66)
print("M  台词里的 <r=注音></r> 逐句对齐剧本：位置（紧跟哪个字）+ 文字")
print("=" * 66)
RUBY = re.compile(r'<r=([^<>]*)></r>')


def ruby_marks(text):
    """[(紧跟在注音前面的那个字, 注音)] in reading order. The client's ruby has an empty
    body, so a note is identified by where it was inserted, not by what it covers."""
    out = []
    for m in RUBY.finditer(text):
        base = norm(text[:m.start()])
        out.append((base[-1] if base else '', m.group(1)))
    return out


def audit_ruby(path, stem):
    rows = lua_speech_rows(stem)
    if rows is None:
        return ['剧本查无文件']
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

print()
print('M2 变异测试')
rp = next(p for p, s in pages if '<r=mowang></r>' in open(p, encoding='utf-8').read())
rstem = next(s for p, s in pages if p == rp)
src = open(rp, encoding='utf-8').read()
tmp = rp + '.mut.md'
try:
    print('正对照（未篡改）: %s' % ('PASS' if not audit_ruby(rp, rstem) else 'FAIL'))
    for label, mut in [
            ('植入[删掉一处注音]', src.replace('<r=mowang></r>', '', 1)),
            ('植入[注音挪到字后]', src.replace('魔<r=mowang></r>王', '魔王<r=mowang></r>', 1)),
            ('植入[改注音文字]', src.replace('<r=mowang></r>', '<r=BOSS></r>', 1))]:
        if mut == src:
            print('%s : 样本里没有该形状，跳过' % label)
            continue
        open(tmp, 'w', encoding='utf-8', newline='\n').write(mut)
        print('%s : %s' % (label, 'CAUGHT' if audit_ruby(tmp, rstem) else 'MISSED'))
finally:
    if os.path.exists(tmp):
        os.remove(tmp)
print('还原后复检: %s' % ('PASS' if not audit_ruby(rp, rstem) else 'FAIL'))
