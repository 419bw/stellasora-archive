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

import graph_layout

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, 'data', 'StellaSoraData', 'CN', 'bin')
LANG = os.path.join(ROOT, 'data', 'StellaSoraData', 'CN', 'language', 'zh_CN')
CFG = os.path.join(ROOT, 'data', 'ss_lua', 'Lua', 'Game', 'UI', 'Avg', '_cn', 'Config')
PRESET = os.path.join(ROOT, 'data', 'ss_lua', 'Lua', 'Game', 'UI', 'Avg', '_cn', 'Preset')
OUT = os.path.join(ROOT, 'story_docs')

PROTAG_ID = ("avg3_100", "avg3_101", "avg3_1311", "avg3_1312", "1")
PROTAG_NAME = "魔王"

# ============================================================== Lua table parser
class T(list):
    """A Lua table: positional items plus any key = value pairs."""
    def __init__(self, items=(), pairs=None):
        super().__init__(items)
        self.pairs = pairs or {}

    def get(self, key, default=None):
        return self.pairs.get(key, default)

    def text(self, i=0):
        return self[i] if i < len(self) and isinstance(self[i], str) else ""


class LuaError(Exception):
    pass


class LuaReader:
    IDENT = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
    NUM = re.compile(r'-?\d+(?:\.\d+)?')

    def __init__(self, text):
        self.s = text
        self.i = 0

    def ws(self):
        while self.i < len(self.s):
            c = self.s[self.i]
            if c in ' \t\r\n':
                self.i += 1
            elif c == '-' and self.s.startswith('--', self.i):
                nl = self.s.find('\n', self.i)
                self.i = len(self.s) if nl < 0 else nl + 1
            else:
                return

    def parse(self):
        self.ws()
        if self.i >= len(self.s):
            raise LuaError('unexpected end')
        if self.s[self.i] == '{':
            return self.table()
        m = self.IDENT.match(self.s, self.i)
        if m and m.group(0) == 'return':
            self.i = m.end()
            return self.parse()
        return self.value()

    def value(self):
        self.ws()
        c = self.s[self.i]
        if c == '{':
            return self.table()
        if c == '"':
            return self.string()
        m = self.NUM.match(self.s, self.i)
        if m:
            self.i = m.end()
            txt = m.group(0)
            return float(txt) if '.' in txt else int(txt)
        m = self.IDENT.match(self.s, self.i)
        if m:
            self.i = m.end()
            return {'true': True, 'false': False, 'nil': None}.get(m.group(0), m.group(0))
        raise LuaError('bad value at %d: %r' % (self.i, self.s[self.i:i + 20]))

    def string(self):
        self.i += 1
        out, esc = [], False
        while self.i < len(self.s):
            c = self.s[self.i]
            self.i += 1
            if esc:
                out.append({'n': '\n', 't': '\t', '"': '"', '\\': '\\', "'": "'"}.get(c, c))
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                return ''.join(out)
            else:
                out.append(c)
        raise LuaError('unterminated string')

    def table(self):
        self.i += 1  # consume {
        items, pairs = [], {}
        while True:
            self.ws()
            if self.i >= len(self.s):
                raise LuaError('unterminated table')
            if self.s[self.i] == '}':
                self.i += 1
                break
            key = None
            m = self.IDENT.match(self.s, self.i)
            if m:
                after = m.end()
                while after < len(self.s) and self.s[after] in ' \t':
                    after += 1
                if after < len(self.s) and self.s[after] == '=' and self.s[after + 1:after + 2] != '=':
                    key = m.group(0)
                    self.i = after + 1
            v = self.parse()
            if key is not None:
                pairs[key] = v
            else:
                items.append(v)
            self.ws()
            if self.i < len(self.s) and self.s[self.i] in ',;':
                self.i += 1
        return T(items, pairs)


def parse_lua(text):
    return LuaReader(text).parse()


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


SPEAKERS = load_speakers()
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

_TAG_CACHE = {}


def script_commands(stem):
    """Parse one AVG script into an ordered [(cmd, T-param)] list."""
    if stem in _TAG_CACHE:
        return _TAG_CACHE[stem]
    path = os.path.join(CFG, stem + '.lua')
    if not os.path.exists(path):
        _TAG_CACHE[stem] = None
        return None
    recs = parse_lua(open(path, encoding='utf-8').read())
    cmds = []
    for r in recs:
        if isinstance(r, T) and r.get('cmd'):
            p = r.get('param')
            cmds.append((r.get('cmd'), p if isinstance(p, T) else T([] if p is None else [p])))
    _TAG_CACHE[stem] = cmds
    return cmds


# ==================================================================== text rules
def clean_text(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip()


RESOURCE_NAME = re.compile(r'[a-z][a-z0-9_]*')


def is_resource_name(text):
    """Sprite/emoji asset keys are authored straight into the text field of some lines.
    In STm/STev/BBm they carry no words; in PM chat they mean a sticker send."""
    return bool(RESOURCE_NAME.fullmatch(text))


RUBY = re.compile(r'<r=([^<>]*)></r>')
# The client's own inline signals, from Avg_4_TalkCtrl.lua:292-296: ==P== paragraph,
# ==B== break, ==W== wait, ==RT== newline, ==A<delay>== auto-paragraph, ==Off== drop the
# centred background. None of them carry words, and _NOT_IN_LOG_ only keeps a line out of
# the in-game log panel.
TEXT_SIGNAL = re.compile(r'==[A-Za-z0-9_.]*==')


def clean_dialogue(s):
    if not s:
        return ""
    # ruby survives: <r=注音></r> is the small reading drawn above a word, i.e. content.
    # Park it behind a sentinel so the blanket tag strip below cannot eat it.
    s = RUBY.sub(lambda m: '\x00%s\x00' % m.group(1), s)
    s = s.replace('<br>', ' ')
    s = re.sub(r'<[^>]*>', '', s)
    s = s.replace('==PLAYER_NAME==', PROTAG_NAME)
    s = re.sub(r'==SEX\d*==', '你', s)
    s = TEXT_SIGNAL.sub(' ', s)
    s = s.replace('_NOT_IN_LOG_', '')
    s = re.sub(r'\x00([^\x00]*)\x00', lambda m: '<r=%s></r>' % m.group(1), s)
    s = re.sub(r'[ \t]+', ' ', s)
    return s.strip()


def speaker_of(spk_id, talk_type):
    """Resolve an AVG speaker id to a display name, honouring the protagonist rules."""
    sid = str(spk_id)
    if sid in PROTAG_ID:
        return PROTAG_NAME
    if sid == "0":
        return PROTAG_NAME if str(talk_type) == "2" else "旁白"
    name, surfix = SPEAKERS.get(sid) or speaker_prefix_of(sid) or ("", "")
    return clean_text(name or surfix or sid)


def speaker_prefix_of(sid):
    """Variant speaker keys carry a suffix the preset table does not list (avg1_144_BB_002
    is 千都世), so fall back to the longest dotted prefix that is registered."""
    parts = sid.split('_')
    for cut in range(len(parts) - 1, 1, -1):
        hit = SPEAKERS.get('_'.join(parts[:cut]))
        if hit:
            return hit
    return None


# ============================================================ command processing
FORK_DEFS = {
    "SetMajorChoice": "major",
    "SetPersonalityChoice": "personality",
    "SetChoiceBegin": "generic",
    "SetPhoneMsgChoiceBegin": "phone",
}
FORK_CLOSE = {"ChoiceJumpTo": "jump", "ChoiceRollover": "roll", "ChoiceEnd": "end"}


def fork_options(kind, param):
    """Extract (prompt, [option labels]) per fork dialect."""
    strings = [x for x in param if isinstance(x, str)]
    nested = [x for x in param if isinstance(x, T)]

    if kind == "major":
        opts = []
        for i, s in enumerate(strings):
            if s.startswith("AvgChoice_") and i + 2 < len(strings):
                title = clean_dialogue(strings[i + 1])
                desc = clean_dialogue(strings[i + 2]) if not re.match(r'^[EC]\d+$', strings[i + 2]) else ""
                if title:
                    opts.append((title, desc))
        prompt = next((clean_dialogue(s) for s in reversed(strings)
                       if not s.startswith(("AvgChoice_", "avg_emoji")) and re.search(r'[？?]', s)), "")
        return prompt, opts

    if kind == "phone":
        # param[0] is the group id the reply jumps are keyed by; the labels follow it
        return "", [(clean_dialogue(s), "") for s in list(param)[1:]
                    if isinstance(s, str) and clean_dialogue(s) and s != "avg3_100"]

    if kind == "generic":
        filled = [x for x in nested if any(isinstance(v, str) and v.strip() for v in x)]
        labels = [clean_dialogue(v) for v in filled[0] if isinstance(v, str) and clean_dialogue(v)] if filled else []
        prompt = ""
        if len(filled) > 1:
            prompt = next((clean_dialogue(v) for v in filled[-1] if isinstance(v, str) and clean_dialogue(v)), "")
        return prompt, [(l, "") for l in labels]

    # personality: flat label list, no AvgChoice_ prefabs
    skip = ("c", "l", "r", "e", "b", "a", "g", "none", "close")
    labels = [clean_dialogue(s) for s in strings
              if clean_dialogue(s) and s not in skip and not re.match(r'^\d{2,3}$', s)
              and not s.startswith(("avg_emoji", "AvgChoice_"))]
    prompt = next((l for l in reversed(labels) if re.search(r'[？?]', l)), "")
    return prompt, [(l, "") for l in labels if l != prompt]


def extract_script(stem):
    """Turn one AVG script into an ordered beat list with branch attribution."""
    cmds = script_commands(stem)
    if cmds is None:
        return None
    beats = []
    stack = []
    pending_close = []
    last_marker = None
    meta = {'recap': '', 'episode': '', 'title': ''}

    def frame_for(group):
        for fr in reversed(stack):
            if fr['group'] == group:
                return fr
        return None

    def active():
        for fr in reversed(stack):
            if fr['cur'] is not None:
                return fr, fr['cur']
        return None

    for cmd, param in cmds:
        head = str(param[0]) if param else ""
        kind = FORK_DEFS.get(cmd)
        if kind:
            prompt, opts = fork_options(kind, param)
            opts = [(t, d) for t, d in opts if t]
            if opts:
                beats.append({'k': 'choice', 'kind': kind, 'prompt': prompt, 'options': opts})
                last_marker = None
                if kind != 'phone':
                    stack.append({'group': head, 'titles': [t for t, _ in opts], 'cur': None, 'opened': set()})
            continue

        closer = next((v for suffix, v in FORK_CLOSE.items() if cmd.endswith(suffix)), None)
        if closer:
            fr = frame_for(head)
            if fr:
                if closer == 'jump':
                    try:
                        fr['cur'] = int(param[1])
                    except (ValueError, TypeError, IndexError):
                        fr['cur'] = None
                elif closer == 'roll':
                    fr['cur'] = None
                else:
                    stack.remove(fr)
                    if fr['opened']:
                        pending_close.append({'titles': fr['titles'], 'opened': fr['opened']})
                    last_marker = None
                    if not stack and pending_close:
                        total = sum(len(p['opened']) for p in pending_close)
                        silent = []
                        for p in pending_close:
                            for i, t in enumerate(p['titles'], 1):
                                if i not in p['opened'] and t not in silent:
                                    silent.append(t)
                        beats.append({'k': 'merge', 'count': total, 'forks': len(pending_close), 'silent': silent})
                        pending_close = []
            continue

        if cmd in ("SetTalk", "SetPhoneMsg"):
            if len(param) < 3:
                continue
            talk_type, spk, raw = str(param[0]), param[1], param[2]
            text = clean_dialogue(raw if isinstance(raw, str) else "")
            if not text:
                continue
            # In SetTalk/SetBubble a bare asset key is a sprite placeholder, not a line.
            # In SetPhoneMsg it means the character sent that sticker -- real content.
            if cmd == "SetTalk" and (text.startswith(("ep_", "BG_")) or is_resource_name(text)):
                continue
            sticker = cmd == "SetPhoneMsg" and is_resource_name(text)
            fr = active()
            if fr:
                f, kk = fr
                marker = (id(f), kk)
                if marker != last_marker:
                    title = f['titles'][kk - 1] if kk - 1 < len(f['titles']) else "分支%d" % kk
                    beats.append({'k': 'branch_open', 'option': title})
                    last_marker = marker
                f['opened'].add(kk)
            name = speaker_of(spk, talk_type)
            beats.append({'k': 'talk', 'speaker': name, 'text': text,
                          # type 2 only means "inner thought" for spoken lines; inside a
                          # phone conversation it is just the message the player sends.
                          'thought': talk_type == "2" and cmd == "SetTalk",
                          'sticker': sticker,
                          'channel': 'msg' if cmd == "SetPhoneMsg" else 'talk'})

        elif cmd == "SetBubble":
            if len(param) < 3:
                continue
            text = clean_dialogue(param[2] if isinstance(param[2], str) else "")
            if not text:
                continue
            if not text or is_resource_name(text):
                continue
            beats.append({'k': 'bubble', 'speaker': speaker_of(param[0], 0), 'text': text})

        elif cmd == "SetGroupId":
            beats.append({'k': 'wave', 'no': clean_text(param[0]) if param else ""})

        elif cmd == "SetSceneHeading":
            # Official layout is a fixed 5 slots: 时刻 / 月 / 日 / 区域 / 地点
            time_, month, day, region, place = (list(param) + ['', '', '', '', ''])[:5]
            beats.append({'k': 'scene',
                          'time': clean_text(time_),
                          'date': " ".join(x for x in (clean_text(month), clean_text(day)) if x),
                          'place': " ".join(x for x in (clean_text(region), clean_text(place)) if x)})

        elif cmd == "SetIntro":
            s = [x if isinstance(x, str) else "" for x in param]
            if len(s) >= 4:
                # [0] 代号 [1] 话数 [2] 标题 [3] 跳过概要（==RT== 是引擎的换行标记）
                parts = [clean_dialogue(p) for p in s[3].split('==RT==')]
                meta['recap'] = "\n".join(p for p in parts if p)
                meta['episode'] = clean_dialogue(s[1])
                meta['title'] = clean_dialogue(s[2])

    return {'meta': meta, 'beats': beats}


# ==================================================================== rendering
def render_beats(beats):
    """One beat list -> markdown lines. Used by both the main and event writers."""
    lines = []
    for b in beats:
        k = b['k']
        if k == 'talk':
            if b.get('sticker'):
                lines.append("**%s**：〔发送表情 `%s`〕" % (b['speaker'], b['text']))
            else:
                tag = "（思考）" if b['thought'] else ("（短信）" if b['channel'] == 'msg' else "")
                lines.append("**%s**%s：「%s」" % (b['speaker'], tag, b['text']))
        elif k == 'bubble':
            lines.append("**%s**（战斗气泡）：「%s」" % (b['speaker'], b['text']))
        elif k == 'wave':
            lines += ["", "> **[战斗阶段 %s]**" % b['no']]
        elif k == 'scene':
            bits = [x for x in (b['place'], b['date'], b['time']) if x]
            lines += ["", "> **【场景 · %s】**" % " · ".join(bits)]
        elif k == 'branch_open':
            lines += ["", "> **[若选「%s」↓]**" % b['option']]
        elif k == 'merge':
            if b['forks'] > 1:
                mk = "> **[▲ 以上 %d 层嵌套抉择的 %d 条分支台词，到此统一汇合]**" % (b['forks'], b['count'])
            elif b['count'] == 1:
                mk = "> **[▲ 以上台词只出现在所选分支，其余选项直接进入下一段]**"
            else:
                mk = "> **[▲ 以上 %d 条分支互斥，自此汇合]**" % b['count']
            lines += ["", mk]
            if b['silent']:
                lines.append("> *（其中%s没有专属台词，选中即跳到汇合点）*" %
                             "、".join("「%s」" % s for s in b['silent']))
        elif k == 'choice':
            label = {'major': '重大抉择', 'personality': '玩家抉择',
                     'generic': '玩家回应' if len(b['options']) == 1 else '抉择',
                     'phone': '通讯回复抉择'}[b['kind']]
            prompt = "：%s" % b['prompt'] if b['prompt'] else ""
            lines += ["", "> **[%s%s]**" % (label, prompt)]
            lines += ["> - **%s**%s" % (t, "：%s" % d if d else "") for t, d in b['options']]
        lines.append("")
    return lines



def section_doc(heading, info, recap, body_title, beats, info_title="关卡信息"):
    """Shared page skeleton for every story family.

    The skip recap is authored inside the script (SetIntro[3], with ==RT== as the line
    break); the stage table's Desc is a one-line flavour hint and is not the recap.
    """
    lines = [heading, "", "## 1. %s" % info_title, *info, ""]
    if recap:
        lines += ["## 2. 官方跳过概要", "",
                  "> " + recap.replace("\n", "\n> "), ""]
    lines += ["## 3. " + body_title, ""]
    lines += render_beats(beats)
    return "\n".join(lines).rstrip() + "\n"


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
_CHAPTER_NODES = collections.OrderedDict()
_RENDERED = set()


def record_page(family, path, parsed, ident, title, code='', group=None,
                stems=(), page=None, **extra):
    beats = parsed['beats']
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
        'recap': parsed['meta']['recap'],
        'speakers': speakers,
        'counts': dict(counts),
        'preview': " ".join(b['text'] for b in beats if b['k'] == 'talk')[:180],
    }
    rec.update(extra)
    _PAGES.append(rec)
    _RENDERED.update(stems)
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
    """The client names a battle's bubble script after the chapter token baked into the
    stage's own StoryId, not after Story.Chapter: 特别篇 stages are `BAm06x5_*` while the
    table numbers that chapter 7, and the bubble files follow `BBm07_*` for 第七章 stages
    (`BAm07_*`). Verified against every stage: a script's speakers always appear in the
    chapter its StoryId token points to, and never in the one Story.Chapter points to."""
    m = re.match(r'^BA([0-9a-zA-Z]+)_[^_]+$', story_id or '')
    if not m:
        return None
    return 'BB%s_%s' % (m.group(1), re.sub(r'[^A-Za-z0-9]', '', code or ''))


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
            doc = section_doc("# %s %s" % (idx, title), info,
                              body_src['meta']['recap'] or hint,
                              "战斗内气泡对白（SetBubble，随战斗阶段推进）" if bubbles else "逐句台词",
                              body_src['beats'])
            path = os.path.join(sdir, safe_name('%s_%s_%s' % (r['Id'], idx, title)) + '.md')
            write(path, doc)
            record_page('main', path, body_src, r['Id'], title, code=idx,
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
            doc = section_doc("# %s %s" % (idx, title),
                              ["- **所属活动**：%s（活动编号 %s）" % (name, cid),
                               "- **关卡 ID**：`%s`" % r['Id'],
                               "- **AVG 剧本**：`%s`" % stem,
                               "- **关卡描述**：%s" % hint],
                              parsed['meta']['recap'] or hint,
                              "逐句台词", parsed['beats'])
            path = os.path.join(folder, 'sections', safe_name('%s_%s_%s' % (r['Id'], idx, title)) + '.md')
            write(path, doc)
            record_page('events', path, parsed, r['Id'], title, code=idx,
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
        write(path, section_doc("# %s" % title, info, parsed['meta']['recap'], "逐句台词",
                                parsed['beats'], info_title="剧情档案信息"))
        record_page('characters', path, parsed, owner['Id'], title,
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
        write(path, section_doc("# %s" % " ".join(x for x in (idx, sub) if x), info,
                                parsed['meta']['recap'], "逐句台词", parsed['beats'],
                                info_title="剧情档案信息"))
        record_page('npc_bonds', path, parsed, r['Id'],
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
        doc = section_doc("# %s" % title, info, parsed['meta']['recap'], "逐句台词",
                          parsed['beats'], info_title="唱片信息")
        prose = LANG_DISC.get(r.get('StoryDesc', ''), '').strip()
        if prose:
            doc += ("\n\n## 4. 唱片附文（DiscIP 表 StoryDesc 原文）\n\n"
                    "> 与上面的 AVG 剧本是两份文本：这段是唱片自带的散文，剧本里没有对应的台词。\n\n"
                    + "\n".join("> " + ln for ln in prose.split("\n")) + "\n")
        path = os.path.join(OUT, 'discs', safe_name('%s_%s' % (r['Id'], title or stem)) + '.md')
        write(path, doc)
        record_page('discs', path, parsed, r['Id'], title,
                    group={'kind': 'disc', 'id': r['Id'], 'label': title,
                           'characters': [c for c in chars if c]},
                    stems=[stem], page='discs/%s.html' % r['Id'],
                    prose_lines=len(prose.split("\n")) if prose else 0)
        stats['sections'] += 1
        stats['lines'] += sum(1 for b in parsed['beats'] if b['k'] in ('talk', 'bubble'))
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
            write(path, section_doc("# %s" % (desc or idx), info, parsed['meta']['recap'],
                                    "逐句台词", parsed['beats'], info_title="故事集小节信息"))
            record_page('storysets', path, parsed, s['Id'], desc or idx, code=idx,
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
        write(path, section_doc("# %s %s" % (parsed['meta']['episode'] or '序',
                                             parsed['meta']['title'] or ''),
                                info, parsed['meta']['recap'], "逐句台词", parsed['beats'],
                                info_title="序章信息"))
        record_page('prologue', path, parsed, stem, parsed['meta']['title'] or stem,
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
        doc = section_doc("# 战斗气泡 `%s`" % stem,
                          ["- **AVG 剧本**：`%s`" % stem,
                           "- **气泡条数**：%d" % n,
                           "- **出场说话人**：%s" % who,
                           "- **挂载状态**：%s" % note],
                          "", "战斗气泡对白（SetBubble，随战斗阶段推进）", parsed['beats'],
                          info_title="剧本信息")
        path = os.path.join(OUT, 'battles_unmounted', safe_name(stem) + '.md')
        write(path, doc)
        record_page('battles_unmounted', path, parsed, stem, stem,
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
    dump_json('search.json', {'meta': {'pages': len(_PAGES)},
                              'entries': [{'id': p['id'], 'family': p['family'],
                                           'code': p['code'], 'title': p['title'],
                                           'group': p['group'].get('label', ''),
                                           'page': p['page'], 'speakers': p['speakers'],
                                           'hay': " ".join(x for x in
                                                            (p['title'], p['recap'],
                                                             p['preview']) if x)}
                                          for p in _PAGES]})
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
            'DP': '委托玩法结算短演出，待决',
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
                      ("序章", build_prologue)):
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
             "> BBm 剧本从不出现在任何配置表里，客户端按「关卡代号里的章号 + 关卡编号」拼出文件名："
             "`BAm07_01` → `BBm07_BT01`，`BAm06x5_01` → `BBm06x5_BT01`。"
             "注意这里跟的是关卡代号，**不是 `Story.Chapter`**：特别篇的关卡记作 `06x5`，"
             "而表把它的 `Chapter` 记成 7，用表号拼名会把第七章的气泡挂到特别篇上。"
             "判据是可核对的：每个 BBm 剧本的说话人集合都出现在其 StoryId 章号所指那一章的正篇演员表里，"
             "而特别篇正篇没有夏花/小禾/千都世，所以 `BBm07_*` 不属于它；"
             "特别篇的两场战斗（`BAm06x5_01`/`BAm06x5_02`）在包里确实没有气泡剧本。", "",
             "> `BBm00_01`–`BBm00_06` 的说话人只有鸢尾/琥珀/尘沙，内容与序章剧本 `STm00_01`《最初的起点》"
             "同为一场沙漠星塔许愿箱之战，即注册流程里打的那一关；关卡表里没有对应行。", ""]
    if missing:
        lines += ["## 无气泡剧本的战斗关卡", ""]
        lines += ["- `%s`（%s，按命名规则期望：%s）" % (b[0], chlab.get(b[3], b[3]), b[1])
                  for b in missing] + [""]
    if unattached:
        lines += ["## 未被任何关卡引用的 BBm 剧本", ""]
        lines += ["- [`%s`](battles_unmounted/%s.md)" % (s, safe_name(s)) for s in unattached]
        lines.append("")
    if skipped:
        lines += ["## 关卡表已列出、包内无剧本的关卡行（未开放线路）", ""]
        lines += ["- 第 %s 章 `%s` %s（%s，剧本代号 `%s`）" % (c, sid, t, kind, stem) for c, sid, stem, t, kind in skipped]
    write(os.path.join(OUT, '_battle_reconciliation.md'), "\n".join(lines))
    print("Wrote %s" % OUT)


if __name__ == '__main__':
    main()
