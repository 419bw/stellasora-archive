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

import sys, os, re, json, collections

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
LANG_ACT = load_json(LANG, 'ActivityStory.json')
LANG_ACT_GROUP = load_json(LANG, 'ActivityGroup.json')
BIN_STORY = load_json(BIN, 'Story.json')
BIN_CHAPTER = load_json(BIN, 'StoryChapter.json')
BIN_ACTIVITY = load_json(BIN, 'ActivityStory.json')
BIN_ACTIVITY_CHAPTER = load_json(BIN, 'ActivityStoryChapter.json')

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


def clean_dialogue(s):
    if not s:
        return ""
    s = re.sub(r'</?size[^>]*>', '', s)
    s = re.sub(r'</?color[^>]*>', '', s)
    s = re.sub(r'<r=[^>]*>', '', s)
    s = re.sub(r'</r>', '', s)
    s = re.sub(r'<sprite[^>]*>', '', s)
    s = s.replace('==PLAYER_NAME==', PROTAG_NAME)
    s = re.sub(r'==SEX\d*==', '你', s)
    s = re.sub(r'==[A-Z0-9_]+==', ' ', s)
    s = re.sub(r'[ \t]+', ' ', s)
    return s.strip()


def speaker_of(spk_id, talk_type):
    """Resolve an AVG speaker id to a display name, honouring the protagonist rules."""
    sid = str(spk_id)
    if sid in PROTAG_ID:
        return PROTAG_NAME
    if sid == "0":
        return PROTAG_NAME if str(talk_type) == "2" else "旁白"
    name, surfix = SPEAKERS.get(sid, ("", ""))
    return clean_text(name or surfix or sid)


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
        return "", [(clean_dialogue(s), "") for s in strings if clean_dialogue(s) and s not in ("avg3_100",)]

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
    meta = {'recap': ''}

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



def section_doc(heading, info, recap, body_title, beats):
    """Shared page skeleton for both main and event sections.

    The skip recap is authored inside the script (SetIntro[3], with ==RT== as the line
    break); the stage table's Desc is a one-line flavour hint and is not the recap.
    """
    lines = [heading, "", "## 1. 关卡信息", *info, ""]
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
                cand = 'BBm%02d_%s' % (ch, re.sub(r'[^A-Za-z0-9]', '', idx))
                if script_commands(cand):
                    bubbles = extract_script(cand)
                    bubble_stem = cand
                    battle_map.append((stem, cand, 'attached'))
                else:
                    battle_map.append((stem, cand, 'MISSING'))
            if parsed is None and not bubbles:
                skipped.append((ch, r['Id'], stem, title, '战斗关卡' if r.get('IsBattle') else '剧情关卡'))
                continue
            info = [
                "- **所属篇章**：%s《%s》（%s）" % (clabel or '第 %d 章' % ch, ctitle, cyear),
                "- **关卡 ID**：`%s`　**编号**：`%s`" % (r['Id'], idx or '-'),
                "- **关卡名称**：%s" % title,
                "- **关卡类型**：%s" % ("战斗关卡" if r.get('IsBattle') else "剧情关卡"),
                "- **AVG 剧本**：`%s`" % (stem if parsed else (bubble_stem or '无（解包中不存在该剧本）')),
                "- **关卡描述**：%s" % hint,
                "- **通关目标**：%s" % (aim or '推进主线剧情'),
            ]
            body_src = bubbles or parsed
            doc = section_doc("# %s %s" % (idx, title), info,
                              body_src['meta']['recap'] or hint,
                              "战斗内气泡对白（SetBubble，随战斗阶段推进）" if bubbles else "逐句台词",
                              body_src['beats'])
            write(os.path.join(sdir, safe_name('%s_%s_%s' % (r['Id'], idx, title)) + '.md'), doc)
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
            write(os.path.join(folder, 'sections', safe_name('%s_%s_%s' % (r['Id'], idx, title)) + '.md'), doc)
            stats['sections'] += 1
            stats['lines'] += sum(1 for b in parsed['beats'] if b['k'] == 'talk')
    return stats


def main():
    print("Parsing official AVG scripts (main story)...")
    mstats, battle_map, skipped = build_main()
    mstats['empty'] = len(skipped)
    print("  sections=%(sections)s 战斗气泡关卡=%(bubbles)s 台词行=%(lines)s 无剧本关卡行=%(empty)s" % mstats)
    print("Parsing event story scripts...")
    estat = build_events()
    print("  sections=%(sections)s lines=%(lines)s" % estat)

    attached = [b for b in battle_map if b[2] == 'attached']
    missing = [b for b in battle_map if b[2] == 'MISSING']
    used = {b[1] for b in attached}
    unattached = sorted(f for f in os.listdir(CFG) if f.startswith('BBm') and f[:-4] not in used)
    lines = ["# 战斗气泡剧本对账", "",
             "- 战斗关卡行：%d，挂到气泡剧本：%d，包内暂无剧本：%d" % (len(battle_map), len(attached), len(missing)),
             "- 有剧本但关卡表未引用（教学关或未上线）：%d 个" % len(unattached), "",
             "> 包内暂无剧本的关卡行全部集中在第十章《遥远的塔》。该章剧情目前只开放了部分线路，"
             "关卡表先行、后续线路的剧本随版本补进客户端，因此这些行不是解包遗漏。", ""]
    if missing:
        lines += ["## 无气泡剧本的战斗关卡", ""]
        lines += ["- `%s`（按命名规则期望：%s）" % (b[0], b[1]) for b in missing] + [""]
    if unattached:
        lines += ["## 未被任何关卡引用的 BBm 剧本", ""]
        for f in unattached:
            s = extract_script(f[:-4])
            n = sum(1 for b in s['beats'] if b['k'] == 'bubble') if s else 0
            lines.append("- `%s` —— %d 条气泡" % (f[:-4], n))
        lines.append("")
    if skipped:
        lines += ["## 关卡表已列出、包内无剧本的关卡行（未开放线路）", ""]
        lines += ["- 第 %s 章 `%s` %s（%s，剧本代号 `%s`）" % (c, sid, t, kind, stem) for c, sid, stem, t, kind in skipped]
    write(os.path.join(OUT, '_battle_reconciliation.md'), "\n".join(lines))
    print("Wrote %s" % OUT)


if __name__ == '__main__':
    main()
