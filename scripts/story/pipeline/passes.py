# -*- coding: utf-8 -*-
"""管线 Stage 3c: 语义 pass —— 命令 IR → beat 列表。

自 build_story.py 原样迁出（Phase 1c），逐行为等价：
  * fold_animations（原 nonlog_repeats）：折叠 _NOT_IN_LOG_ 渐显动画帧，
    返回应跳过命令的 idx 集合（命令 IR 稳定身份，不再用 id(param)）；
  * fork_options：四种抉择方言（major/personality/generic/phone）的选项抽取；
  * extract_beats（原 extract_script 核心循环）：单遍状态机，产出 beat 列表
    与分支归属（branch_open/merge），即 PageDoc 的正文 IR。

beat 字典的键与取值是 md/HTML 双后端和 sections.json 的共同上游契约，
改动必须过黄金对拍与双 validator。
"""
import re

from .lua_parser import T
from .text_rules import NONLOG, _related, _sig, clean_dialogue, clean_text, is_resource_name


def fold_animations(commands):
    """SetTalk/SetPhoneMsg params whose only job was the fade-in animation.

    The client renders one long line by issuing the same SetTalk over and over with
    a rising <alpha=#22..#FF>, and those frames carry a _NOT_IN_LOG_ prefix because
    they never enter the in-game backlog. Emitting one archive line per frame makes
    the same sentence appear 6..57 times, so the frames must be folded back down.

    Rules, per run of consecutive _NOT_IN_LOG_ frames:
      1) if the animated visual ends on a logged frame carrying the same text, drop
         the whole run -- that logged frame is what the backlog shows;
      2) otherwise keep only the run's last non-empty frame (the animation's final
         state), so standalone visuals never vanish from the archive.

    The logged twin is searched along the animation chain around the run, because
    the script interleaves Clear / SetBGM / Wait between the fade frames and their
    final logged frame -- segmenting on Clear alone splits one visual in two.

    返回：应跳过的命令 idx 集合（Command IR 稳定身份）。
    """
    rows = []          # [(idx, in_log, signature)]
    for c in commands:
        if c.cmd in ('SetTalk', 'SetPhoneMsg') and len(c.param) >= 3:
            raw = c.param[2]
            if isinstance(raw, str):
                rows.append((c.idx, not raw.startswith(NONLOG),
                             _sig(raw.replace(NONLOG, ''))))

    n = len(rows)
    skip = set()
    i = 0
    while i < n:
        if rows[i][1]:                          # logged frame, always kept
            i += 1
            continue
        j = i
        while j < n and not rows[j][1]:
            j += 1
        run = range(i, j)                       # maximal _NOT_IN_LOG_ run
        nonempty = [k for k in run if rows[k][2]]
        if nonempty:
            last = nonempty[-1]
            sig = rows[last][2]
            twin = None
            for step in (-1, 1):                # walk the animation chain
                k = last + step
                while 0 <= k < n and rows[k][2] and _related(rows[k][2], sig):
                    if rows[k][1] and rows[k][2] == sig:
                        twin = k
                        break
                    k += step
                if twin is not None:
                    break
            if twin is not None:                # rule 1: the log already shows it
                skip.update(rows[k][0] for k in run)
            else:                               # rule 2: keep the final state
                skip.update(rows[k][0] for k in run)
                skip.discard(rows[last][0])
        i = j
    return skip


# ============================================================ command processing
FORK_DEFS = {
    "SetMajorChoice": "major",
    "SetPersonalityChoice": "personality",
    "SetChoiceBegin": "generic",
    "SetPhoneMsgChoiceBegin": "phone",
}
FORK_CLOSE = {"ChoiceJumpTo": "jump", "ChoiceRollover": "roll", "ChoiceEnd": "end"}


def fork_options(kind, param):
    """Extract (prompt, [(option title, option desc, jump EvId)]) per fork dialect."""
    strings = [x for x in param if isinstance(x, str)]
    nested = [x for x in param if isinstance(x, T)]

    if kind == "major":
        # Every option block starts at an AvgChoice_ prefab and runs until the next
        # prefab: [title, desc(?), route marker(?), ..., jump EvId]. The EvId (E901,
        # Eev5_01, ...) is the first E-prefixed string after the title; it joins with
        # StoryCondition/ActivityStoryEvidence to tell which level the option leads to.
        prefabs = [i for i, s in enumerate(strings) if s.startswith("AvgChoice_")]
        opts = []
        for n, i in enumerate(prefabs):
            seg = strings[i + 1:prefabs[n + 1] if n + 1 < len(prefabs) else len(strings)]
            if not seg:
                continue
            title = clean_dialogue(seg[0])
            desc = clean_dialogue(seg[1]) if len(seg) > 1 and not re.match(r'^[EC][A-Za-z0-9_]*$', seg[1]) else ""
            ev = next((s for s in seg[1:] if re.match(r'^E[A-Za-z0-9_]+$', s)), "")
            if title:
                opts.append((title, desc, ev))
        prompt = next((clean_dialogue(s) for s in reversed(strings)
                       if not s.startswith(("AvgChoice_", "avg_emoji")) and re.search(r'[？?]', s)), "")
        return prompt, opts

    if kind == "phone":
        # param[0] is the group id the reply jumps are keyed by; the labels follow it
        return "", [(clean_dialogue(s), "", "") for s in list(param)[1:]
                    if isinstance(s, str) and clean_dialogue(s) and s != "avg3_100"]

    if kind == "generic":
        filled = [x for x in nested if any(isinstance(v, str) and v.strip() for v in x)]
        labels = [clean_dialogue(v) for v in filled[0] if isinstance(v, str) and clean_dialogue(v)] if filled else []
        prompt = ""
        if len(filled) > 1:
            prompt = next((clean_dialogue(v) for v in filled[-1] if isinstance(v, str) and clean_dialogue(v)), "")
        return prompt, [(l, "", "") for l in labels]

    # personality: flat label list, no AvgChoice_ prefabs
    skip = ("c", "l", "r", "e", "b", "a", "g", "none", "close")
    labels = [clean_dialogue(s) for s in strings
              if clean_dialogue(s) and s not in skip and not re.match(r'^\d{2,3}$', s)
              and not s.startswith(("avg_emoji", "AvgChoice_"))]
    prompt = next((l for l in reversed(labels) if re.search(r'[？?]', l)), "")
    return prompt, [(l, "", "") for l in labels if l != prompt]


def extract_beats(commands, resolver):
    """Turn one AVG script's command IR into an ordered beat list with branch
    attribution（原 extract_script 核心循环，行为逐行等价）。

    resolver: SpeakerResolver 实例（说话人 id → 显示名）。
    返回 {'meta': {recap/episode/title}, 'beats': [...]}。
    """
    beats = []
    stack = []
    pending_close = []
    last_marker = None
    meta = {'recap': '', 'episode': '', 'title': ''}
    # Fade-in frames of the same line are not separate lines of dialogue.
    skip = fold_animations(commands)

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

    for c in commands:
        cmd, param = c.cmd, c.param
        head = str(param[0]) if param else ""
        kind = FORK_DEFS.get(cmd)
        if kind:
            prompt, opts = fork_options(kind, param)
            opts = [(t, d, e) for t, d, e in opts if t]
            if opts:
                beats.append({'k': 'choice', 'kind': kind, 'prompt': prompt, 'options': opts})
                last_marker = None
                if kind != 'phone':
                    stack.append({'group': head, 'titles': [t for t, _, _ in opts], 'cur': None, 'opened': set()})
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
            if c.idx in skip:
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
            name = resolver.of(spk, talk_type)
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
            beats.append({'k': 'bubble', 'speaker': resolver.of(param[0], 0), 'text': text})

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
