# -*- coding: utf-8 -*-
"""Extract story beats, localized choices and animation-frame groups from commands."""
import re

from .text_rules import NONLOG, _related, _sig, clean_text, is_resource_name
from . import markup


def fold_animations(commands, compiler):
    """Keep the final text of fade-frame runs, comparing every language and gender."""
    rows = []          # [(idx, in_log, signature)]
    for c in commands:
        if c.cmd in ('SetTalk', 'SetPhoneMsg') and len(c.param) >= 3:
            raw = c.param[2]
            if isinstance(raw, str):
                rows.append((c.idx, not raw.startswith(NONLOG),
                             tuple(_sig(compiler.compile(v.replace(NONLOG, '')), sex)
                                   for v in command_text_slots(c) for sex in ('female', 'male'))))

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
        nonempty = [k for k in run if any(rows[k][2])]
        if nonempty:
            last = nonempty[-1]
            sig = rows[last][2]
            twin = None
            for step in (-1, 1):                # walk the animation chain
                k = last + step
                while 0 <= k < n and any(rows[k][2]) and all(_related(a, b) for a, b in zip(rows[k][2], sig)):
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


def fork_options(kind, param, compiler):
    """Extract (prompt, [(option title, option desc, jump EvId)]) per fork dialect."""
    compile_text = compiler.compile
    strings = [x for x in param if isinstance(x, str)]

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
            title = compile_text(seg[0])
            desc = compile_text(seg[1]) if len(seg) > 1 and not re.match(r'^[EC][A-Za-z0-9_]*$', seg[1]) else ""
            ev = next((s for s in seg[1:] if re.match(r'^E[A-Za-z0-9_]+$', s)), "")
            if title:
                opts.append((title, desc, ev))
        prompt = next((compile_text(s) for s in reversed(strings)
                       if not s.startswith(("AvgChoice_", "avg_emoji")) and re.search(r'[？?]', s)), "")
        return prompt, opts

    if kind == "phone":
        options = [compiler.compile(slot(param, i), slot(param, i + 3)) for i in range(1, 4)]
        return "", [(t, "", "") for t in options if t]

    if kind == "generic":
        columns = [slot(param, i, []) for i in (3, 10, 12, 13)]
        labels = [compiler.compile(*(slot(col, i) for col in columns))
                  for i in range(4)]
        return compiler.compile(slot(param, 9)), [(t, "", "") for t in labels if t]

    male_labels = [slot(param, i) for i in (10, 11, 12)]
    if not all(male_labels):
        male_labels = ['', '', '']
    labels = [compiler.compile(slot(param, i + 2), male_labels[i]) for i in range(3)]
    return compiler.compile(slot(param, 8), slot(param, 13)), [(t, "", "") for t in labels if t]


def slot(values, index, empty=''):
    return values[index] if index < len(values) and values[index] is not None else empty


def command_text_slots(command):
    indices = (2, 5, 8, 9) if command.cmd == 'SetBubble' else (2, 6, 7, 8)
    return tuple(slot(command.param, i) for i in indices)


def extract_beats(commands, resolver, compiler, diag=None, conditions=None, stem=''):
    """Extract ordered story beats and their choice-branch ownership.

    diag: 可选 Diagnostics 收集器。帧栈失配这类"指令被静默丢弃"的降级在此登记
    （choice_frame_anomalies）；不传则完全不登记，库用法不受影响。
    stem: 剧本代号，仅用于登记条目定位。
    """
    beats = []
    stack = []
    pending_close = []
    last_marker = None
    meta = {'recap': '', 'episode': '', 'title': ''}
    # Fade-in frames of the same line are not separate lines of dialogue.
    if conditions is not None:
        from .conditions import condition_markers
        markers = condition_markers(commands, conditions)
    else:
        markers = {}
    boundaries = sorted({0, len(commands), *markers})
    skip = set().union(*(fold_animations(commands[start:end], compiler)
                         for start, end in zip(boundaries, boundaries[1:])))

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
        beats.extend(markers.get(c.idx, []))
        cmd, param = c.cmd, c.param
        head = str(param[0]) if param else ""
        kind = FORK_DEFS.get(cmd)
        if kind:
            prompt, opts = fork_options(kind, param, compiler)
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
            elif diag is not None and 'PhoneMsg' not in cmd:
                # 关闭指令的 group 找不到活跃帧：上游 Begin/End 错配（如 CG_126_03
                # 用 a_4 的 SetChoiceEnd 关 a_10，见 _dev/AI_HANDOVER_GUIDE.md 3.5）
                # 之类数据异常，指令被静默丢弃（行为与历史一致），此处登记。
                # phone 方言从不入帧栈（上方 kind != 'phone' 才推帧），其
                # JumpTo/End 落空是设计使然，不登记。
                diag.add('choice_frame_anomalies',
                         key=(stem, c.idx, cmd, head, closer),
                         stem=stem, idx=c.idx, cmd=cmd, group=head, closer=closer)
            continue

        if cmd in ("SetTalk", "SetPhoneMsg"):
            if len(param) < 3:
                continue
            if c.idx in skip:
                continue
            talk_type, spk, raw = str(param[0]), param[1], param[2]
            text = compiler.compile(*command_text_slots(c))
            rendered = markup.markdown(text)
            if not text:
                continue
            # In SetTalk/SetBubble a bare asset key is a sprite placeholder, not a line.
            # In SetPhoneMsg it means the character sent that sticker -- real content.
            if cmd == "SetTalk" and (rendered.startswith(("ep_", "BG_")) or is_resource_name(rendered)):
                continue
            sticker = cmd == "SetPhoneMsg" and is_resource_name(rendered)
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
            text = compiler.compile(*command_text_slots(c))
            if not text:
                continue
            if is_resource_name(markup.markdown(text)):
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
                meta['recap'] = compiler.compile(s[3])
                meta['episode'] = markup.text(compiler.compile(s[1]))
                meta['title'] = markup.text(compiler.compile(s[2]))

    return {'meta': meta, 'beats': beats}
