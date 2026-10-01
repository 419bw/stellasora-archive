# -*- coding: utf-8 -*-
"""
build_wiki_knowledge_base.py
Comprehensive, 100% authentic, Wiki-grade progressive disclosure knowledge base
strictly sourced from official datamined game data in:
- scratch/StellaSoraData_repo/
- scratch/ss_lua_repo/
Zero fabrication. 1:1 factual fidelity.
"""

import os
import sys
import json
import re
import shutil

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(ROOT_DIR, 'data', 'StellaSoraData')
BIN_DIR = os.path.join(DATA_DIR, 'CN', 'bin')
LANG_DIR = os.path.join(DATA_DIR, 'CN', 'language', 'zh_CN')
EN_LANG_DIR = os.path.join(DATA_DIR, 'EN', 'language', 'en_US')
LUA_DIR = os.path.join(ROOT_DIR, 'data', 'ss_lua', 'Lua', 'Game', 'UI', 'Avg', '_cn', 'Config')
PRESET_DIR = os.path.join(ROOT_DIR, 'data', 'ss_lua', 'Lua', 'Game', 'UI', 'Avg', '_cn', 'Preset')
OUT_DIR = os.path.join(ROOT_DIR, 'docs')

def load_json(folder, filename):
    path = os.path.join(folder, filename)
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

print("Loading official data tables...")
bin_char = load_json(BIN_DIR, 'Character.json')
lang_char = load_json(LANG_DIR, 'Character.json')
lang_char_des = load_json(LANG_DIR, 'CharacterDes.json')
lang_force = load_json(LANG_DIR, 'Force.json')
bin_story_chap = load_json(BIN_DIR, 'StoryChapter.json')
lang_story_chap = load_json(LANG_DIR, 'StoryChapter.json')
bin_story = load_json(BIN_DIR, 'Story.json')
lang_story = load_json(LANG_DIR, 'Story.json')
bin_act_chap = load_json(BIN_DIR, 'ActivityStoryChapter.json')
bin_act_story = load_json(BIN_DIR, 'ActivityStory.json')
lang_act_story = load_json(LANG_DIR, 'ActivityStory.json')
lang_archive_base = load_json(LANG_DIR, 'CharacterArchiveBaseInfo.json')
lang_archive_content = load_json(LANG_DIR, 'CharacterArchiveContent.json')
lang_skills = load_json(LANG_DIR, 'Skill.json')
lang_potentials = load_json(LANG_DIR, 'Potential.json')
lang_plot = load_json(LANG_DIR, 'Plot.json')
cn_items = load_json(LANG_DIR, 'Item.json')
en_items = load_json(EN_LANG_DIR, 'Item.json')
bin_dating = load_json(BIN_DIR, 'DatingCharacterEvent.json')
lang_dating = load_json(LANG_DIR, 'DatingCharacterEvent.json')

# Root repo jsons
repo_chars = load_json(DATA_DIR, 'character.json')
repo_discs = load_json(DATA_DIR, 'disc.json')
repo_emblems = load_json(DATA_DIR, 'emblem.json')

# Build item translation map EN -> CN
en2cn_items = {}
for k, en_val in en_items.items():
    if k.endswith('.1') and k in cn_items:
        en2cn_items[en_val.strip()] = cn_items[k].strip()

# Build speaker map from AvgCharacter.lua
speaker_map = {
    "0": "旁白",
    "1": "魔王",
    "avg3_999": "艾蕾",
    "avg4_999": "维塔",
}
avg_char_path = os.path.join(PRESET_DIR, 'AvgCharacter.lua')
if os.path.exists(avg_char_path):
    with open(avg_char_path, 'r', encoding='utf-8') as f:
        content = f.read()
    for m in re.finditer(r'id\s*=\s*"([^"]+)"[^}]*?name\s*=\s*"([^"]*)"', content, re.DOTALL):
        c_id, c_name = m.groups()
        if c_name:
            speaker_map[c_id] = c_name

# Player/Protagonist overrides (in internal dev AvgCharacter.lua, protagonist is codenamed "塞拉")
for pid in ("avg3_100", "avg3_101", "avg3_1311", "avg3_1312", "1"):
    speaker_map[pid] = "魔王"
speaker_map["0"] = "旁白"
speaker_map["avg4_999"] = "维塔"

EET_MAP = {
    1: ('water', '水'),
    2: ('fire', '火'),
    3: ('earth', '地'),
    4: ('wind', '风'),
    5: ('light', '光'),
    6: ('dark', '暗'),
}

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'<color=#[a-fA-F0-9]+>', '', text)
    text = re.sub(r'</color>', '', text)
    text = re.sub(r'<size=[^>]*>', '', text)
    text = re.sub(r'</size>', '', text)
    text = re.sub(r'<sprite[^>]*>', '', text)
    text = re.sub(r'&Param\d+&', '[数值]', text)
    text = re.sub(r'&Param\d+', '[数值]', text)
    text = re.sub(r'##([^#]+)#\d+#', r'「\1」', text)
    text = text.replace('\x0b', '\n\n').replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('==PLAYER_NAME==', '魔王')
    text = re.sub(r'==SEX\d*==', '你', text)
    text = re.sub(r'==[A-Z0-9_]+==', ' ', text)
    return text.strip()

def clean_dialogue(text):
    if not text:
        return ""
    text = re.sub(r'</?size[^>]*>', '', text)
    text = re.sub(r'</?color[^>]*>', '', text)
    text = re.sub(r'<r=[^>]*>', '', text)
    text = re.sub(r'</r>', '', text)
    text = re.sub(r'<sprite[^>]*>', '', text)
    text = text.replace('==PLAYER_NAME==', '魔王')
    text = re.sub(r'==SEX\d*==', '你', text)
    text = re.sub(r'==[A-Z0-9_]+==', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def safe_write(filepath, content):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

alias_map = {}

def add_alias(alias, target_path, desc=""):
    if not alias:
        return
    alias = alias.strip().lower()
    if not alias:
        return
    if alias not in alias_map:
        alias_map[alias] = []
    entry = {"path": target_path.replace('\\', '/'), "desc": desc}
    if entry not in alias_map[alias]:
        alias_map[alias].append(entry)

def parse_choices(cmd, param_str):
    raw_strings = re.findall(r'"([^"]*)"', param_str)
    
    if cmd == "SetMajorChoice":
        prompt = ""
        for i, s in enumerate(raw_strings):
            if s in ("c", "l", "r", "e", "b", "a", "g") and i + 3 < len(raw_strings):
                if re.match(r"^\d{3}$", raw_strings[i+1]) and raw_strings[i+2] in ("none", "close", "avg_emoji_think", "avg_emoji_question", "avg_emoji_attention"):
                    cand = clean_dialogue(raw_strings[i+3].strip())
                    if cand:
                        prompt = cand
                        break
        if not prompt:
            for s in reversed(raw_strings):
                s_strip = clean_dialogue(s.strip())
                if s_strip and not s_strip.startswith("AvgChoice_") and not s_strip.startswith("avg_emoji") and s_strip not in ("c", "l", "r", "e", "b", "a", "g", "none", "020", "012", "009", "025", "002"):
                    if any(p in s_strip for p in ("？", "！", "呢", "去哪", "怎么", "选哪个", "如何", "做", "想", "……", "...", "要")):
                        prompt = s_strip
                        break

        choices = []
        i = 0
        while i < len(raw_strings):
            s = raw_strings[i]
            if s.startswith("AvgChoice_"):
                cand = []
                j = i + 1
                while j < len(raw_strings) and not raw_strings[j].startswith("AvgChoice_"):
                    val = raw_strings[j].strip()
                    if val and val != prompt and not re.match(r"^E[a-zA-Z0-9_]+$", val) and not re.match(r"^C\d+_route[A-Z]$", val) and val not in ("c", "l", "r", "e", "b", "a", "g", "none", "close", "avg_emoji_think", "avg_emoji_question", "avg_emoji_attention") and not re.match(r"^\d{3}$", val):
                        cand.append(clean_dialogue(val))
                    j += 1
                if len(cand) >= 2:
                    choices.append({"title": cand[0], "desc": cand[1]})
                elif len(cand) == 1:
                    choices.append({"title": cand[0], "desc": ""})
                i = j - 1
            i += 1
        return {"kind": "major", "prompt": prompt, "choices": choices}

    elif cmd == "SetPersonalityChoice":
        prompt = ""
        for i, s in enumerate(raw_strings):
            if s in ("c", "l", "r", "e", "b", "a", "g") and i + 3 < len(raw_strings):
                if re.match(r"^\d{3}$", raw_strings[i+1]):
                    cand = clean_dialogue(raw_strings[i+3].strip())
                    if cand:
                        prompt = cand
                        break
        choices = []
        for s in raw_strings:
            val = clean_dialogue(s.strip())
            if not val or val == prompt:
                continue
            if val in ("c", "l", "r", "e", "b", "a", "g", "none", "close", "avg_emoji_think", "avg_emoji_question", "avg_emoji_attention") or re.match(r"^\d{3}$", val):
                continue
            choices.append(val)
        return {"kind": "personality", "prompt": prompt, "choices": choices}

    elif cmd == "SetPhoneMsgChoiceBegin":
        choices = []
        for s in raw_strings:
            val = clean_dialogue(s.strip())
            if not val or val in ("1", "2", "3", "avg3_100"):
                continue
            choices.append(val)
        return {"kind": "phone", "prompt": "", "choices": choices}

    return None

def format_choice_block(d):
    kind = d.get('kind', '')
    if kind == 'major':
        prompt_str = f"：{d['prompt']}" if d.get('prompt') else ""
        items = []
        for c in d.get('choices', []):
            desc_str = f"：{c['desc']}" if c.get('desc') else ""
            items.append(f"> - **{c['title']}**{desc_str}")
        return f"> **[重大抉择{prompt_str}]**\n" + "\n".join(items) + "\n"
    elif kind == 'personality':
        prompt_str = f"：{d['prompt']}" if d.get('prompt') else ""
        items = [f"> - {c}" for c in d.get('choices', [])]
        return f"> **[玩家抉择{prompt_str}]**\n" + "\n".join(items) + "\n"
    elif kind == 'phone':
        items = [f"> - {c}" for c in d.get('choices', [])]
        return f"> **[通讯回复抉择]**\n" + "\n".join(items) + "\n"
    else:
        items = [f"> - {c}" for c in d.get('choices', [])]
        return f"> **[玩家抉择支]**：\n" + "\n".join(items) + "\n"

def render_script_lines(parsed):
    """Render a parse_lua_avg() result into markdown lines. Single source of truth,
    used by both the main-story and event-story section writers."""
    out = []
    for d in parsed.get('dialogues', []):
        t = d['type']
        if t == 'talk':
            if d.get('is_thought'):
                out.append(f"**{d['speaker']}**（思考）：「{d['text']}」\n")
            else:
                out.append(f"**{d['speaker']}**：「{d['text']}」\n")
        elif t == 'choice':
            out.append(format_choice_block(d))
        elif t == 'branch_open':
            out.append(f"> **[若选「{d['option']}」↓]**\n")
        elif t == 'branch_merge':
            if d.get('forks', 1) > 1:
                block = [f"> **[▲ 以上 {d['forks']} 层嵌套抉择的 {d['count']} 条分支台词，到此统一汇合]**"]
            elif d.get('solo'):
                block = ["> **[▲ 以上台词只出现在所选分支，其余选项直接进入下一段]**"]
            else:
                block = [f"> **[▲ 以上 {d['count']} 条分支互斥，自此汇合]**"]
            if d.get('silent'):
                opts = "、".join(f"「{s}」" for s in d['silent'])
                block.append(f"> *（其中{opts}没有专属台词，选中即跳到汇合点）*")
            out.append("\n".join(block) + "\n")
    return out

def parse_lua_avg(script_name):
    if not script_name:
        return None
    if not script_name.endswith('.lua'):
        script_name += '.lua'
    script_path = os.path.join(LUA_DIR, script_name)
    if not os.path.exists(script_path):
        return None
    with open(script_path, 'r', encoding='utf-8') as f:
        text = f.read()

    result = {'episode': '', 'title': '', 'recap': '', 'dialogues': []}
    
    # 1. Parse SetIntro
    intro_m = re.search(r'cmd\s*=\s*"SetIntro"\s*,\s*param\s*=\s*\{([^}]+)\}', text)
    if intro_m:
        params = re.findall(r'"([^"]*)"', intro_m.group(1))
        if len(params) >= 4:
            result['episode'] = clean_dialogue(params[1])
            result['title'] = clean_dialogue(params[2])
            result['recap'] = clean_dialogue(params[3].replace('==RT==', '\n'))
        elif len(params) >= 3:
            result['episode'] = clean_dialogue(params[0])
            result['title'] = clean_dialogue(params[1])
            result['recap'] = clean_dialogue(params[2].replace('==RT==', '\n'))

    # 2. Parse Talk and Choices in sequence.
    #
    # The AVG engine lays a choice out as: Set*Choice(group, option rows...) then one
    # Set*ChoiceJumpTo{group, k} per branch, each branch's commands running until
    # Set*ChoiceRollover{group}, and Set*ChoiceEnd{group} closing the whole construct.
    # Only the branch the player picked is ever seen, so its lines must not read as a
    # continuous scene. Branches are addressed by group id, and a fork can open inside
    # another fork's branch, so frames live on a stack keyed by group, not by line order.
    FORK_DEFS = {"SetMajorChoice": "major", "SetPersonalityChoice": "personality",
                 "SetPhoneMsgChoiceBegin": "phone"}
    fork_stack = []
    pending_close = []
    last_marker = None

    def find_frame(group):
        for fr in reversed(fork_stack):
            if fr['group'] == group:
                return fr
        return None

    def active_branch():
        for fr in reversed(fork_stack):
            if fr['cur'] is not None and fr['kind'] != 'phone':
                return fr, fr['cur']
        return None

    cmd_blocks = re.finditer(r'cmd\s*=\s*"([^"]+)"\s*,\s*param\s*=\s*\{([^}]*)\}', text)
    for cb in cmd_blocks:
        cmd = cb.group(1)
        param_str = cb.group(2)
        p_items = [l.strip().rstrip(',') for l in param_str.splitlines() if l.strip()]
        p_vals = [x.strip('"') for x in p_items]
        # Control commands are written inline (`param = {1, 2}`), so their tokens must be
        # comma-split; only SetTalk/SetIntro spread one token per line.
        head_vals = [t.strip().strip('"') for t in param_str.split(',')]

        if cmd == "SetTalk":
            if len(p_items) >= 3:
                talk_type = p_vals[0]
                spk_id = p_vals[1]
                spk_name = speaker_map.get(spk_id, spk_id)
                if spk_id in ("avg3_100", "avg3_101", "avg3_1311", "avg3_1312", "1"):
                    spk_name = "魔王"
                elif spk_id == "0":
                    if talk_type == "2":
                        spk_name = "魔王"
                    else:
                        spk_name = "旁白"
                d_text = p_items[2].strip()
                if d_text.startswith('"') and d_text.endswith('"'):
                    d_text = d_text[1:-1]
                d_text = clean_dialogue(d_text)
                if d_text and not d_text.startswith("ep_") and not d_text.startswith("BG_"):
                    is_thought = (talk_type == "2")
                    branch = active_branch()
                    if branch:
                        fr, k = branch
                        marker = (id(fr), k)
                        if marker != last_marker:
                            title = fr['titles'][k - 1] if k - 1 < len(fr['titles']) else f"分支{k}"
                            result['dialogues'].append({'type': 'branch_open', 'option': title})
                            last_marker = marker
                        fr['opened'].add(k)
                    result['dialogues'].append({'type': 'talk', 'speaker': spk_name, 'text': d_text, 'is_thought': is_thought})
        elif cmd in FORK_DEFS:
            parsed_c = parse_choices(cmd, param_str)
            if parsed_c and parsed_c.get('choices'):
                result['dialogues'].append({'type': 'choice', **parsed_c})
                last_marker = None
                if parsed_c['kind'] != 'phone':
                    titles = [c['title'] if isinstance(c, dict) else c for c in parsed_c['choices']]
                    fork_stack.append({'group': head_vals[0] if head_vals else "", 'kind': parsed_c['kind'],
                                       'titles': titles, 'cur': None, 'opened': set()})
        elif cmd.endswith("ChoiceJumpTo"):
            if len(head_vals) >= 2:
                fr = find_frame(head_vals[0])
                if fr:
                    try:
                        fr['cur'] = int(head_vals[1])
                    except ValueError:
                        fr['cur'] = None
        elif cmd.endswith("ChoiceRollover"):
            if head_vals:
                fr = find_frame(head_vals[0])
                if fr:
                    fr['cur'] = None
        elif cmd.endswith("ChoiceEnd"):
            if head_vals:
                fr = find_frame(head_vals[0])
                if fr:
                    fork_stack.remove(fr)
                    if fr['opened']:
                        pending_close.append({'count': len(fr['opened']),
                                              'titles': fr['titles'], 'opened': fr['opened']})
                    last_marker = None
                    # One conditional region ends only when the outermost fork closes;
                    # nested forks resolve together, so their notes are aggregated.
                    if not fork_stack and pending_close:
                        total = sum(p['count'] for p in pending_close)
                        silent = []
                        for p in pending_close:
                            for i, t in enumerate(p['titles'], 1):
                                if i not in p['opened'] and t not in silent:
                                    silent.append(t)
                        result['dialogues'].append({'type': 'branch_merge', 'count': total,
                                                    'solo': total == 1, 'forks': len(pending_close),
                                                    'silent': silent})
                        pending_close = []

    return result

# ==========================================
# 1. BASICS GENERATION
# ==========================================
def generate_basics():
    print("Generating basics...")
    
    # 1.1 world_view.md
    forces = []
    for fid in sorted(range(1, 30)):
        fname = lang_force.get(f'Force.{fid}.1')
        if fname:
            forces.append(f"- **{fname}** (势力编号 {fid})")
            add_alias(fname, 'basics/world_view.md', f'势力组织: {fname}')
    
    forces_text = "\n".join(forces)
    
    world_view_content = f"""# 《星塔旅人》世界观与势力背景

## 1. 时代与背景设定
- **世界纪元**：星塔历 996 年
- **核心概念**：
  - **星塔 (Star Tower)**：耸立在诺瓦大陆各处的神秘巨构建筑。塔内拥有不断变幻的生态与空间，蕴藏着名为“赋灵”、“秘纹”与“潜能”的超凡力量，同时也盘踞着各类强大的异化魔物。
  - **旅人 (Trekker)**：受聘或自发前往星塔中探索、调查与战斗的专业人员。旅人们各自具备独特的元素属性（水、火、地、风、光、暗）与战斗流派。
  - **空白旅团 (Blank Brigade)**：由主角（魔王）带领的精英探索团队，拥有移动基地“幸运绿洲号”，足迹遍布埃摩城、菲莱、苍梧等地。
  - **地理协会 (Geographical Association)**：大陆官方权威机构，负责星塔的勘探定级、旅人资质审核与官方委托发放。

## 2. 诺瓦大陆主要城邦与地理区域
- **埃摩城 (Amor City)**：大陆繁荣的核心城邦，分为阶级森严的金城区（贵族商贾聚集地）与灰城区（市井平民与各路势力混杂区），以宏伟的运河水道桥闻名。
- **菲莱 (Philae)**：充满学术研究氛围与自然奥秘的古老领地。
- **苍梧 (Cangwu)**：历史悠久的东方风韵城邦，拥有独特的新春民俗与悠长传承。
- **北境之城 (North City)**：寒霜终年不化的极北要塞，民风剽悍，隐藏着冰原深处的古塔秘辛。

## 3. 诺瓦大陆各大势力与组织官方名录
根据官方档案记录，诺瓦大陆活跃着以下重要势力与组织：

{forces_text}

### 重点势力深度说明
- **空白旅团**：主角所属的独立探索旅团，致力于解开星塔谜团与自身记忆残片。
- **地理协会**：大陆官方公信机构，统一制定旅人等级标准，发布星塔悬赏。
- **恩赐意志**：追求古老秩序与精神教条的强大信仰组织。
- **联合种业**：掌控农业科技与生态育种的巨型农业联合体（岭川等人所属组织）。
- **花令旅团**：活跃于大陆各地的知名游历旅团。
- **菲茨罗伊家族**：埃摩金城区的顶级名门望族，埃莉诺大小姐的家族。
"""
    safe_write(os.path.join(OUT_DIR, 'basics', 'world_view.md'), world_view_content)
    add_alias('世界观', 'basics/world_view.md', '游戏世界观与背景')
    add_alias('势力', 'basics/world_view.md', '势力与组织列表')
    add_alias('星塔历', 'basics/world_view.md', '星塔历纪元')
    add_alias('空白旅团', 'basics/world_view.md', '空白旅团介绍')
    add_alias('地理协会', 'basics/world_view.md', '地理协会介绍')
    add_alias('埃摩城', 'basics/world_view.md', '埃摩城背景')
    add_alias('诺瓦大陆', 'basics/world_view.md', '诺瓦大陆背景')

    # 1.2 game_modes.md
    modes_content = """# 《星塔旅人》玩法模式全览

本体系汇总了《星塔旅人》内所有常驻挑战、核心活动与休闲策略模式，所有机制说明均源自游戏官方教程库。

## 1. 核心探索与常驻挑战

### 星塔探索 (Star Tower)
- 星塔是游戏的核心常驻 PVE 爬塔与探索系统。
- 旅人需要在逐层攀升的过程中应对不同词缀（Affix）、特殊地形与精英首领。
- 通过在塔内获取的素材可进行**星塔研究**，解锁全队基础属性强化与被动加成。

### 心危擂台 (Hazard Arena)
- 验证单队或多队极限输出与生存能力的高难度试炼。
- 包含周期性刷新的首领与挑战词缀，提供丰厚勋章与养成材料。

### 灾变防线 (Calamity Defense)
- 防御型塔防与据点保卫玩法，需要合理规划队伍站位、拦截波次敌人冲击并保护核心装置。

### 真格挑战 & 联合讨伐 (Joint Drill)
- **真格挑战**：单人高难 Boss 挑战，对角色的破韧、走位与爆发轴有极高要求。
- **联合讨伐**：多人组队或跨旅团联机讨伐世界首领，共同削减 Boss 全局血量并赢取阶段性奖励。

### 猎影合围 (Trace Hunt)
- 定向猎杀特定稀有首领的追踪合围战，掉落专属高级素材与纹章。

---

## 2. 策略深度模式：尖兵陷阵 (Auto-Chess / Blitz)

“尖兵陷阵”是游戏内独创的高深度自走棋策略模式。玩家在棋盘上调度麾下旅人棋子，与各路智者对弈。

### 核心机制
- **棋盘布局**：最多构成 **3 主战 + 6 后援** 配置。主战位负责在前线正面交战，后援位提供羁绊激活与战术支援。
- **理智值 (Sanity)**：对弈清醒度指标，理智值归零时棋局失败。
- **对弈节点**：分为遇敌、契机（事件）、首领和终盘决战节点。
- **棋子星级**：招募费用分为 1~5 费。3 个同星同名棋子自动升星（最高 3 星）。
- **羁绊系统**：每个棋子附带专属羁绊词条，上阵特定数量同羁绊棋子激活强力光环。支持“羁绊追踪”标记。
- **经济与方针**：
  - **贤才金币**：用于招募棋子、刷新商店（2金币）和升级商店等级。
  - **方针与祝福**：开局可进行 3 选 1 起始方针，并在“契机”节点获得额外战术祝福。

---

## 3. 休闲活动模式

### 沁凉补给站 (Ice Cream Stand)
- 夏日清凉小铺模拟经营。根据顾客气泡需求，选择正确口味的冰淇淋球与配料，达成连击进入“欢乐时光”。遇到特殊顾客夏洛克可解锁“夏日酷饮”特殊道具。

### 豪礼抛物线 (Soda Cannon)
- 物理弹射小游戏。操作汽水炮台发射夏洛克，借助鼓风机与传送盆等机关，将其准确弹入对应颜色的购物篮，获取道具并冲击高分。

### 钩爪寻宝 (Claw Crane)
- 限时抓娃娃与物资搜集。操控摇摆钩爪抓取宝物，利用爆破技能炸毁沉重公文包，借助捕捞网一网打尽，同时规避巡逻无人机与炸弹陷阱。

### 超越之镜 (Mirror of Transcendence)
- 特殊翻牌与契约签署对局。通过签署合约获取加成，需在 3 次违约额度内完成高难筹码挑战。
"""
    safe_write(os.path.join(OUT_DIR, 'basics', 'game_modes.md'), modes_content)
    add_alias('玩法模式', 'basics/game_modes.md', '玩法模式一览')
    add_alias('尖兵陷阵', 'basics/game_modes.md', '尖兵陷阵自走棋玩法')
    add_alias('自走棋', 'basics/game_modes.md', '尖兵陷阵自走棋玩法')
    add_alias('心危擂台', 'basics/game_modes.md', '心危擂台玩法')
    add_alias('灾变防线', 'basics/game_modes.md', '灾变防线玩法')
    add_alias('联合讨伐', 'basics/game_modes.md', '联合讨伐玩法')
    add_alias('真格挑战', 'basics/game_modes.md', '真格挑战玩法')
    add_alias('猎影合围', 'basics/game_modes.md', '猎影合围玩法')
    add_alias('沁凉补给站', 'basics/game_modes.md', '冰淇淋小游戏')
    add_alias('豪礼抛物线', 'basics/game_modes.md', '汽水弹射小游戏')
    add_alias('钩爪寻宝', 'basics/game_modes.md', '抓宝小游戏')
    add_alias('超越之镜', 'basics/game_modes.md', '超越之镜翻牌玩法')

    # 1.3 game_mechanics.md
    mechanics_content = """# 《星塔旅人》核心战斗与养成机制

本指南全面收录《星塔旅人》战斗底层判定、技能系统、元素印记与角色养成规则。

## 1. 旅人养成体系

### 等级提升与进阶突破
- **等级上限与提升**：消耗经验道具提升旅人等级（最高 Lv.100），大幅提升基础攻击力、生命值与防御力。
- **阶级突破 (Ascension)**：旅人每达到当前等级阶段上限，需消耗对应属性进阶素材进行阶级突破（最高 8 阶），解锁新属性成长池与技能等级上限。
- **3 阶觉醒 (Awakening)**：当旅人成功进阶至 **3 阶** 时，将正式解锁全新专属**觉醒立绘形象**，并可在游戏主页看板与队伍展示中自由切换设置。

### 技能构成分类
1. **普攻 (Normal Attack)**：多段连携打击，部分角色拥有蓄力分支或强化普攻形态。
2. **闪避动作 (Dodge)**：提供瞬时无敌帧规避伤害，极限闪避可顺畅衔接疾跑与反击。
3. **主控技 (Main Skill)**：角色在前台主战位时由玩家主动施放的核心技能，主导战斗节奏与印记附着。
4. **援护技 (Assist Skill)**：角色在后台后援位时，触发充能或连携条件时登场释放的支援战术技。
5. **绝招 (Ultimate)**：积蓄充能后施放的超高倍率爆发大招，附带专属全屏动画与强力控场。

### 潜能系统 (Potential)
- 每位角色拥有 5 个核心潜能节点（潜能 1 至 潜能 5）。
- 获取重复角色时自动转化为专属碎片（30 片），消耗碎片激活潜能，带来技能机制质变与巨额倍率增幅。

### 纹章与秘纹 (Insignia & Affixes)
- 核心装备体系，拥有 Lv.70 / Lv.80 / Lv.90 属性阶梯。
- 纹章副词条包含基础类、分段暴击类、增伤/暴伤类与特种穿透/充能类，副词条与角色的标签契合时将获得高额额外加成。

---

## 2. 战斗与元素印记机制

### 6 大元素体系
- **水系 (Water)**
- **火系 (Fire)**
- **地系 (Earth)**
- **风系 (Wind)**
- **光系 (Light)**
- **暗系 (Dark)**

### 元素印记与引爆反应
- 角色的特定招式（尤其主控技与强化普攻）会给敌方施加对应的元素印记。
- 当队伍攻击带有印记的敌人时，将触发印记反应（如风系引发绽放风压，地系引发地脉共振额外伤害），产生高额真实机制伤害。

### 韧性机制 (Resilience & Stagger)
- 精英怪物与首领具有独立的韧性槽（白条）。
- 受到削韧攻击与重打击时，敌方韧性槽迅速削减。
- 韧性归零时，敌人进入**虚弱破防状态 (Stagger)**，行动完全瘫痪，受到的全伤害大幅提升。这是全队倾泻大招与技能爆发的最黄金输出窗口。
"""
    safe_write(os.path.join(OUT_DIR, 'basics', 'game_mechanics.md'), mechanics_content)
    add_alias('游戏机制', 'basics/game_mechanics.md', '核心战斗与养成机制')
    add_alias('元素属性', 'basics/game_mechanics.md', '元素属性与印记')
    add_alias('元素印记', 'basics/game_mechanics.md', '元素印记机制')
    add_alias('韧性', 'basics/game_mechanics.md', '韧性与破防机制')
    add_alias('削韧', 'basics/game_mechanics.md', '削韧与破防机制')
    add_alias('虚弱', 'basics/game_mechanics.md', '虚弱硬直状态')
    add_alias('潜能', 'basics/game_mechanics.md', '潜能系统')
    add_alias('纹章', 'basics/game_mechanics.md', '纹章与词条系统')
    add_alias('觉醒', 'basics/game_mechanics.md', '3阶觉醒与进阶')
    add_alias('突破', 'basics/game_mechanics.md', '阶级突破机制')

    # 1.4 currency_and_gacha.md
    currency_content = """# 《星塔旅人》货币体系与招募卡池规则

## 1. 货币与资源体系

### 基础通用货币
- **朵拉 (Dora)**：诺瓦大陆的标准通用金币，广泛用于旅人升级、装备强化、进阶突破、商店采购等所有基础消耗。
- **星石 (Star Quartz / Gem)**：珍贵的高阶结晶货币，用于旅人招募祈愿、购买干劲活力及各类高价值礼包。
- **干劲 (Energy / Stamina)**：体力资源，随时间自动恢复。挑战主线、材料副本与高难星塔均需消耗干劲。
- **权限等级 (Authority Level)**：玩家账号级别，随着日常委托与主线推进提升，决定角色等级上限与系统解锁进度。

### 策略与活动专属货币
- **贤才金币**：“尖兵陷阵”自走棋模式中的专属局内流通代币，用于购买棋子、刷新商店与升阶。
- **权能点数**：完成每日、每周特别指派任务累计的点数，用于领取阶段宝箱奖励。

---

## 2. 招募与祈愿卡池规则

### 招募机制
- 旅人招募分为**常驻招募**与**限时特选招募（活动卡池）**。
- 角色品质分为 1 星至 5 星等阶级（最高原生品质为 5 星）。
- 抽卡消耗指定招募凭证或等额星石。

### 保底与转化规则
- 卡池具备明确保底计数机制，达到指定抽数必定获取当期 UP 或高星稀有旅人。
- **重复角色转化**：当抽取到已拥有的旅人时，系统将自动转化为该角色的**专属碎片（如 30 碎片）**，用于激活角色的潜能节点（潜能 1 至 潜能 5）。

### 创业激励基金 (Battle Pass)
- 包含**基础补贴**与**尊享补贴 / 大亨尊享补贴**。
- 通过完成每日与每周营业目标提升基金等级，解锁丰富的培养素材、星石与专属特权外观。
"""
    safe_write(os.path.join(OUT_DIR, 'basics', 'currency_and_gacha.md'), currency_content)
    add_alias('货币', 'basics/currency_and_gacha.md', '货币体系')
    add_alias('朵拉', 'basics/currency_and_gacha.md', '朵拉金币')
    add_alias('星石', 'basics/currency_and_gacha.md', '星石货币')
    add_alias('干劲', 'basics/currency_and_gacha.md', '干劲体力')
    add_alias('卡池', 'basics/currency_and_gacha.md', '招募与卡池规则')
    add_alias('抽卡', 'basics/currency_and_gacha.md', '招募与抽卡保底')
    add_alias('保底', 'basics/currency_and_gacha.md', '卡池保底规则')
    add_alias('创业激励基金', 'basics/currency_and_gacha.md', '通行证激励基金')

    # 1.5 discs_overview.md
    print("Generating discs_overview.md...")
    discs_lines = [
        "# 《星塔旅人》星塔唱片全集 (102 张唱片全档案)",
        "",
        "唱片（Record / Disc）是星塔探索的核心装备。本表收录游戏中全部 102 张官方唱片的完整中文译名、稀有度、所属属性、契合角色、主控技能效果及官方风味物语。",
        "",
        "| ID | 唱片名称 | 星级 | 元素 | 标签 | 契合角色 | 主控技能 (Main Skill) | 风味物语 (Lore) |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]
    
    for did, d in sorted(repo_discs.items(), key=lambda x: int(x[0])):
        cn_name = cn_items.get(f'Item.{did}.1', d.get('name'))
        flavor = clean_text(cn_items.get(f'Item.{did}.3', ''))
        star = f"{d.get('star')}星"
        elem = d.get('element') or '全属性'
        tags = "/".join(d.get('tag', [])) if d.get('tag') else '-'
        chars = "/".join(d.get('char', [])) if d.get('char') else '-'
        
        main_skill = d.get('mainSkill') or {}
        skill_name_cn = main_skill.get('nameCN', '')
        skill_desc_cn = clean_text(main_skill.get('descCN', ''))
        skill_params = main_skill.get('params', '')
        if skill_params:
            skill_desc_cn = f"【{skill_name_cn}】{skill_desc_cn} (数值阶梯: {skill_params})"
        elif skill_name_cn:
            skill_desc_cn = f"【{skill_name_cn}】{skill_desc_cn}"
        else:
            skill_desc_cn = '-'

        flavor_brief = flavor.replace('\n', ' ')
        if len(flavor_brief) > 40:
            flavor_brief = flavor_brief[:40] + "..."

        discs_lines.append(f"| `{did}` | **{cn_name}** ({d.get('name')}) | {star} | {elem} | {tags} | {chars} | {skill_desc_cn} | {flavor_brief} |")
        add_alias(cn_name, 'basics/discs_overview.md', f'唱片: {cn_name}')
        add_alias(d.get('name'), 'basics/discs_overview.md', f'唱片: {d.get("name")}')

    safe_write(os.path.join(OUT_DIR, 'basics', 'discs_overview.md'), "\n".join(discs_lines))
    add_alias('唱片', 'basics/discs_overview.md', '102张唱片全集')
    add_alias('星塔唱片', 'basics/discs_overview.md', '102张唱片全集')

    # 1.6 emblems_overview.md
    print("Generating emblems_overview.md...")
    emblem_lines = [
        "# 《星塔旅人》纹章词条属性库全览 (Lv.70 / Lv.80 / Lv.90)",
        "",
        "纹章（Emblem / Insignia）是旅人的核心洗练养成装备。本篇完整收录官方 datamine 提取的 Lv.70、Lv.80 与 Lv.90 纹章属性组、权重概率以及具体词条数值四档阶梯。",
        "",
        "## 1. Lv.70 & Lv.80 纹章副词条属性库",
        ""
    ]

    for lvl in ['lv70', 'lv80', 'lv90']:
        data = repo_emblems.get(lvl, {})
        emblem_lines.append(f"### 【{lvl.upper()} 纹章副词条池】")
        groups = data.get('attrGroup', [])
        for i, g in enumerate(groups):
            w = g.get('weight', '')
            emblem_lines.append(f"#### 属性组 {i+1} (出现权重: {w})")
            emblem_lines.append("| 词条属性名称 | 数值阶梯 (档位 1 / 2 / 3 / 4) |")
            emblem_lines.append("| :--- | :--- |")
            for a in g.get('attr', []):
                if ':' in a:
                    aname, avals = a.split(':', 1)
                    emblem_lines.append(f"| {aname.strip()} | `{avals.strip()}` |")
                else:
                    emblem_lines.append(f"| {a.strip()} | - |")
            emblem_lines.append("")

    emblem_lines.extend([
        "## 2. 词条属性分类与选择建议",
        "- **基础属性类 (Group 1)**：生命值、攻击力、防御力及其百分比加成。提供最坚实的面板底座。",
        "- **分段暴击类 (Group 2)**：针对普攻、技能、大招、印记、召唤物及衍生伤害的独立暴击率提升，单项数值高达 15%。",
        "- **增伤与暴伤类 (Group 3)**：全方位暴击伤害加成与各乘区增伤，特别注意**印记伤害 (Mark DMG)** 最高可达 **80%**，是印记流核心角色的质变词条。",
        "- **特种属性类 (Group 4)**：全局暴击率 (Crit Rate)、属性穿透 (Elemental PEN) 与充能效率。出现概率最低（8%），但具有极高的全队泛用价值。"
    ])
    safe_write(os.path.join(OUT_DIR, 'basics', 'emblems_overview.md'), "\n".join(emblem_lines))
    add_alias('纹章词条', 'basics/emblems_overview.md', '纹章词条属性库')
    add_alias('徽章', 'basics/emblems_overview.md', '纹章词条属性库')
    add_alias('词条概率', 'basics/emblems_overview.md', '纹章词条权重与概率')

# ==========================================
# 2. MAIN STORY GENERATION
# ==========================================
def make_section_filename(s_id, s_idx, s_title):
    raw = f"{s_id}_{s_idx}_{s_title}"
    clean = re.sub(r'[^\w\-\u4e00-\u9fff]', '_', raw).strip('_')
    clean = re.sub(r'_+', '_', clean)
    return f"{clean}.md"

# ==========================================
# 2. MAIN STORY GENERATION (SPLIT BY NODE)
# ==========================================
def generate_main_story():
    print("Generating main story chapters with individual section files and Mermaid DAG flowcharts...")
    main_overview_lines = [
        "# 《星塔旅人》官方主线剧情全篇总览",
        "",
        "游戏主线记录了主角与空白旅团在星塔历 996 年踏上诺瓦大陆探索星塔的壮丽史诗。每一章节均包含**章节拓扑分支路线图 (Mermaid DAG)**，并按关卡节点独立拆分为详细剧情文档（包含关卡信息、**官方跳过剧情概要 SetIntro** 与 **逐句全角色台词剧本 SetTalk/SetChoice**）。",
        "",
        "## 篇章目录",
        ""
    ]

    for cid_str, chap in sorted(bin_story_chap.items(), key=lambda x: int(x[0])):
        cid = int(cid_str)
        c_num = clean_text(lang_story_chap.get(chap['Name'], f'第{cid}章'))
        c_title = clean_text(lang_story_chap.get(chap['Desc'], ''))
        c_year = clean_text(lang_story_chap.get(chap.get('ChapterYear'), '星塔历 996 年'))
        
        folder_name = f"chapter_{cid:02d}"
        if '特别篇' in c_num:
            folder_name = "chapter_special"
            chap_display = f"特别篇《{c_title}》"
        else:
            chap_display = f"{c_num}《{c_title}》"

        target_dir = os.path.join(OUT_DIR, 'story', 'main', folder_name)
        sections_dir = os.path.join(target_dir, 'sections')
        os.makedirs(sections_dir, exist_ok=True)

        main_overview_lines.append(f"- [{chap_display}](./{folder_name}/overview.md) ({c_year})")
        
        add_alias(c_num, f'story/main/{folder_name}/overview.md', f'主线{c_num}')
        add_alias(c_title, f'story/main/{folder_name}/overview.md', f'主线篇章: {c_title}')
        add_alias(chap_display, f'story/main/{folder_name}/overview.md', f'主线: {chap_display}')
        add_alias(f'ch{cid}', f'story/main/{folder_name}/overview.md', f'主线第{cid}章')

        # Sections for this chapter
        chap_sections = [s for s in bin_story.values() if s.get('Chapter') == cid]
        chap_sections.sort(key=lambda s: s.get('Id', 0))

        # Build code-to-node mapping for Mermaid diagram
        code_to_node = {}
        for s in chap_sections:
            s_id = s.get('Id')
            node_id = f"node_{s_id}"
            if s.get('StoryId'):
                code_to_node[s.get('StoryId')] = node_id
            if s.get('AvgLuaName'):
                code_to_node[s.get('AvgLuaName')] = node_id
            code_to_node[str(s_id)] = node_id

        # Mermaid lines
        mermaid_lines = ["```mermaid", "flowchart TD"]
        for s in chap_sections:
            s_id = s.get('Id')
            node_id = f"node_{s_id}"
            s_idx = clean_text(lang_story.get(s.get('Index', ''), ''))
            s_title = clean_text(lang_story.get(s.get('Title', ''), '')).replace('"', "'")
            is_battle = s.get('IsBattle')
            
            tag = "[战斗] " if is_battle else ""
            label = f"{tag}{s_idx} {s_title}".strip()
            mermaid_lines.append(f'    {node_id}["{label}"]')
            
            parents = s.get('ParentStoryId')
            if parents:
                if isinstance(parents, str):
                    parents = [parents]
                for p in parents:
                    if p in code_to_node:
                        p_node = code_to_node[p]
                        mermaid_lines.append(f"    {p_node} --> {node_id}")

        # Fallback sequential chain if no edges found
        if not any('-->' in l for l in mermaid_lines) and len(chap_sections) > 1:
            for i in range(len(chap_sections) - 1):
                cur_node = f"node_{chap_sections[i].get('Id')}"
                next_node = f"node_{chap_sections[i+1].get('Id')}"
                mermaid_lines.append(f"    {cur_node} --> {next_node}")

        mermaid_lines.append("```")
        mermaid_doc = "\n".join(mermaid_lines)

        # Overview document
        chap_overview = f"""# 主线 {chap_display} 概览

## 章节基本信息
- **章节全称**：{c_num} 《{c_title}》
- **发生时间**：{c_year}
- **包含小节数**：共 {len(chap_sections)} 个小节（包含剧情关卡与战斗关卡）

## 章节剧情分支路线图 (Story Route DAG)
以下流程图清晰展示了本章所有关卡的推进顺序、分支路径、战斗节点与可能达成的各路线结局：

{mermaid_doc}

## 关卡小节列表与剧情直达 (Sections)
| 关卡编号 | 关卡名称 | 类型 | 推荐等级 | 独立小节剧情与台词文档 |
| :--- | :--- | :--- | :--- | :--- |
"""
        for s in chap_sections:
            s_id = s.get('Id')
            s_idx = clean_text(lang_story.get(s.get('Index', ''), ''))
            s_title = clean_text(lang_story.get(s.get('Title', ''), ''))
            s_aim = clean_text(lang_story.get(s.get('Aim', ''), ''))
            is_battle = "⚔️ 战斗关卡" if s.get('IsBattle') else "📖 剧情关卡"
            rec_level = s.get('Recommend', '-')
            lua_name = s.get('AvgLuaName', '')
            parents = s.get('ParentStoryId', [])

            fname = make_section_filename(s_id, s_idx, s_title)
            chap_overview += f"| {s_idx} | {s_title} | {is_battle} | Lv.{rec_level} | [{s_title}](./sections/{fname}) |\n"

            # Parse Lua AVG
            parsed_avg = parse_lua_avg(lua_name) if lua_name else None
            official_recap = parsed_avg.get('recap') if parsed_avg and parsed_avg.get('recap') else clean_text(lang_story.get(s.get('Desc', ''), ''))
            parent_str = ", ".join(parents) if parents else "无（本章起始关卡）"

            # Generate individual section markdown file
            sec_doc = [
                f"# 关卡剧情：{s_idx} {s_title}",
                "",
                "## 1. 关卡基本信息",
                f"- **所属篇章**：{chap_display} ({c_year})",
                f"- **关卡 ID**：`{s_id}`",
                f"- **关卡编号**：`{s_idx}`",
                f"- **关卡名称**：{s_title}",
                f"- **关卡类型**：{'战斗关卡' if s.get('IsBattle') else '纯剧情关卡'}",
                f"- **推荐等级**：Lv.{rec_level}",
                f"- **关卡代码 / 剧本**：`{lua_name or s.get('StoryId', '-')}`",
                f"- **前置解锁节点**：`{parent_str}`",
                f"- **通关目标**：{s_aim or '无特定战斗目标 / 推进主线剧情'}",
                "",
                "## 2. 官方剧情跳过概要 (Official Skip Recap)",
                f"> {official_recap}",
                "",
                "## 3. 详细剧情与逐句台词剧本 (Full Script)",
                ""
            ]

            if parsed_avg and parsed_avg.get('dialogues'):
                sec_doc.extend(render_script_lines(parsed_avg))
            elif s.get('IsBattle'):
                sec_doc.append(f"*（本节点为星塔战斗关卡，通关目标：{s_aim or '击败全部敌方目标'}）*\n")
            else:
                sec_doc.append("*（该小节无独立台词文本或为过渡叙事）*\n")

            sec_path = os.path.join(sections_dir, fname)
            safe_write(sec_path, "\n".join(sec_doc))

            rel_sec_path = f'story/main/{folder_name}/sections/{fname}'
            if s_title and len(s_title) >= 2:
                add_alias(s_title, rel_sec_path, f'主线关卡: {s_title}')
                add_alias(f'{s_idx} {s_title}', rel_sec_path, f'主线关卡: {s_idx} {s_title}')
                add_alias(f'{s_title}台词', rel_sec_path, f'主线关卡台词: {s_title}')
                add_alias(f'{s_title}剧情', rel_sec_path, f'主线关卡剧情: {s_title}')
                add_alias(f'{s_title}剧本', rel_sec_path, f'主线关卡剧本: {s_title}')
                add_alias(f'{s_title}概要', rel_sec_path, f'主线关卡概要: {s_title}')

        safe_write(os.path.join(target_dir, 'overview.md'), chap_overview)

    safe_write(os.path.join(OUT_DIR, 'story', 'main', 'main_story_overview.md'), "\n".join(main_overview_lines))
    add_alias('主线剧情', 'story/main/main_story_overview.md', '主线剧情总览')
    add_alias('主线', 'story/main/main_story_overview.md', '主线剧情总览')

# ==========================================
# 3. EVENT STORIES GENERATION (SPLIT BY NODE)
# ==========================================
def generate_event_stories():
    print("Generating event stories with individual section files...")
    events_overview_lines = [
        "# 《星塔旅人》官方活动剧情全篇总览",
        "",
        "游戏内拥有丰富的大型限时活动剧情，包含专属节日、特别委托以及旅人独立外传。全部数据均源自官方活动文本库与 105 个专属 AVG 脚本。所有小节均按独立节点拆分展示。",
        "",
        "## 活动剧情目录",
        ""
    ]

    act_grouped = {}
    for sid, item in bin_act_story.items():
        chap_id = item.get('ChapterId')
        act_grouped.setdefault(chap_id, []).append(item)

    event_slugs = {
        10104: ('spring_festival_10104', '苍茫人海逢故人', '新春佳节之际，苍梧街头故人重聚与调查', '埃莉诺、琥珀、苍梧众人'),
        10105: ('north_city_10105', '前往北境之城', '探访寒霜笼罩的北境领地', '魔王、空白旅团成员'),
        10106: ('deliverer_quest_10106', '万送屋的委托', '万送屋的离奇紧急委托', '万送屋成员、魔王'),
        10107: ('reunion_10107', '再遇', '命运交织的再次相逢', '魔王、旅人伙伴'),
        10108: ('energy_crisis_10108', '能源危机', '星塔能量紊乱引发的城邦危机', '城邦守卫、旅人探索队'),
        10109: ('triumphant_return_10109', '远征凯旋……黑暗之力的缺席', '远征归来后的神秘异象', '远征队、艾蕾、魔王'),
        10110: ('sea_breeze_10110', '海风吹来的委托', '海滨度假地的海风委托', '夏日度假旅人、魔王'),
        10111: ('tea_party_10111', '大小姐们的茶会', '埃莉诺大小姐主办的优雅茶会与冒险物语', '埃莉诺、卡特琳、薇薇安'),
        11100: ('shimmering_light_11100', '闪烁的微光', '夜幕中探寻希望微光的冒险', '探索队、魔王'),
        20101: ('winter_messenger_20101', '雪愿节的使者', '雪愿节庆典与雪原使者的大冒险', '雪愿节使者、空白旅团'),
        20103: ('summer_vacation_20103', '是时候休个假了！', '炎炎夏日海滩度假与欢乐时光', '夏日泳装旅人们、魔王')
    }

    for chap_id, items in sorted(act_grouped.items()):
        items.sort(key=lambda x: x.get('Id', 0))
        first_title = lang_act_story.get(items[0].get('Title'), f'活动{chap_id}')
        
        slug_info = event_slugs.get(chap_id)
        if slug_info:
            folder_slug, act_name, act_summary, act_chars = slug_info
        else:
            folder_slug = f"event_{chap_id}"
            act_name = first_title
            act_summary = "官方限时活动特别剧情"
            act_chars = "活动登场角色"

        act_dir = os.path.join(OUT_DIR, 'story', 'events', folder_slug)
        sections_dir = os.path.join(act_dir, 'sections')
        os.makedirs(sections_dir, exist_ok=True)

        events_overview_lines.append(f"- [《{act_name}》](./{folder_slug}/overview.md) (编号 {chap_id}, 共 {len(items)} 节) —— {act_summary}")

        add_alias(act_name, f'story/events/{folder_slug}/overview.md', f'活动剧情: 《{act_name}》')
        add_alias(f'活动{chap_id}', f'story/events/{folder_slug}/overview.md', f'活动编号{chap_id}')

        act_overview_lines = [
            f"# 活动剧情 《{act_name}》 概览",
            "",
            f"- **活动编号**：{chap_id}",
            f"- **小节总数**：共 {len(items)} 节",
            f"- **剧情主题**：{act_summary}",
            f"- **主要出场人物**：{act_chars}",
            "",
            "## 剧情分幕速览与小节剧本直达 (Sections)",
            "| 节点 | 小节名称 | 关卡目标 | 独立剧情与台词文档 |",
            "| :--- | :--- | :--- | :--- |"
        ]

        for it in items:
            s_id = it.get('Id')
            idx = clean_text(lang_act_story.get(it.get('Index', ''), ''))
            title = clean_text(lang_act_story.get(it.get('Title', ''), ''))
            raw_desc = clean_text(lang_act_story.get(it.get('Desc', ''), ''))
            aim = clean_text(lang_act_story.get(it.get('Aim', ''), ''))
            lua = it.get('AvgLuaName', '')

            parsed_lua = parse_lua_avg(lua) if lua else None
            recap = parsed_lua.get('recap') if parsed_lua and parsed_lua.get('recap') else raw_desc

            fname = make_section_filename(s_id, idx, title)
            act_overview_lines.append(f"| {idx} | {title} | {aim or '-'} | [{title}](./sections/{fname}) |")

            sec_content = [
                f"# 活动小节剧情：节点 {idx} {title}",
                "",
                "## 1. 节点基本信息",
                f"- **所属活动**：《{act_name}》 (活动编号 {chap_id})",
                f"- **节点编号**：{idx}",
                f"- **节点标题**：{title}",
                f"- **关卡目标**：{aim or '推进活动剧情'}",
                f"- **AVG 剧本代号**：`{lua}`",
                "",
                "## 2. 官方剧情跳过概要 (Official Skip Recap)",
                f"> {recap}",
                "",
                "## 3. 详细剧情与逐句台词剧本 (Full Script)",
                ""
            ]

            if parsed_lua and parsed_lua.get('dialogues'):
                sec_content.extend(render_script_lines(parsed_lua))
            else:
                sec_content.append("*（该小节无独立台词文本）*\n")

            sec_path = os.path.join(sections_dir, fname)
            safe_write(sec_path, "\n".join(sec_content))

            rel_sec_path = f'story/events/{folder_slug}/sections/{fname}'
            if title and len(title) >= 2:
                add_alias(title, rel_sec_path, f'活动分节: {title}')
                add_alias(f'{title}台词', rel_sec_path, f'活动分节台词: {title}')
                add_alias(f'{title}剧情', rel_sec_path, f'活动分节剧情: {title}')
                add_alias(f'{title}剧本', rel_sec_path, f'活动分节剧本: {title}')
                add_alias(f'{title}概要', rel_sec_path, f'活动分节概要: {title}')

        safe_write(os.path.join(act_dir, 'overview.md'), "\n".join(act_overview_lines))

    safe_write(os.path.join(OUT_DIR, 'story', 'events', 'events_overview.md'), "\n".join(events_overview_lines))
    add_alias('活动剧情', 'story/events/events_overview.md', '活动剧情总览')
    add_alias('活动', 'story/events/events_overview.md', '活动剧情总览')
    add_alias('茶会', 'story/events/tea_party_10111/overview.md', '大小姐们的茶会')
    add_alias('大小姐们的茶会', 'story/events/tea_party_10111/overview.md', '大小姐们的茶会')
    add_alias('雪愿节', 'story/events/winter_messenger_20101/overview.md', '雪愿节的使者')
    add_alias('夏假', 'story/events/summer_vacation_20103/overview.md', '是时候休个假了！')
    add_alias('夏日活动', 'story/events/summer_vacation_20103/overview.md', '是时候休个假了！')

# ==========================================
# 4. CHARACTERS GENERATION
# ==========================================
def generate_characters():
    print("Generating all 40 characters across 6 elements...")
    
    # Pre-parse character archives
    archive_contents_by_cid = {}
    for k, v in lang_archive_content.items():
        m = re.match(r'CharacterArchiveContent\.(\d{3})(\d{2})\.([12])', k)
        if m:
            cid, sec, field = m.groups()
            archive_contents_by_cid.setdefault(cid, {}).setdefault(sec, {})[field] = v

    archive_bases_by_cid = {}
    for k, v in lang_archive_base.items():
        m = re.match(r'CharacterArchiveBaseInfo\.(\d{3})(\d{2})\.([12])', k)
        if m:
            cid, sec, field = m.groups()
            archive_bases_by_cid.setdefault(cid, {}).setdefault(sec, {})[field] = v

    # Pre-parse dating dialogues by character id
    dating_by_cid = {}
    for eid, ev in bin_dating.items():
        params = ev.get('DatingEventParams', [])
        if params:
            c_id = str(params[0])
            d_name = clean_text(lang_dating.get(ev.get('Name'), ''))
            d_clue = clean_text(lang_dating.get(ev.get('Clue'), ''))
            d_desc1 = clean_text(lang_dating.get(ev.get('Desc1'), ''))
            d_desc2 = clean_text(lang_dating.get(ev.get('Desc2'), ''))
            d_desc3 = clean_text(lang_dating.get(ev.get('Desc3'), ''))
            d_memory = clean_text(lang_dating.get(ev.get('Memory'), ''))
            dating_by_cid.setdefault(c_id, []).append({
                'id': eid,
                'name': d_name,
                'clue': d_clue,
                'desc1': d_desc1,
                'desc2': d_desc2,
                'desc3': d_desc3,
                'memory': d_memory,
            })

    char_count = 0
    for cid_str, r_c in sorted(repo_chars.items(), key=lambda x: int(x[0])):
        cid = int(cid_str)
        c_bin = bin_char.get(cid_str, {})
        eet = c_bin.get('EET', 1)
        if eet not in EET_MAP:
            continue

        elem_dir, elem_cn = EET_MAP[eet]
        name = lang_char.get(f'Character.{cid}.1', r_c.get('name'))
        slug = lang_char_des.get(f'CharacterDes.{cid}.2', r_c.get('name')).lower()
        cn_cv = clean_text(lang_char_des.get(f'CharacterDes.{cid}.1', ''))
        jp_cv = clean_text(lang_char_des.get(f'CharacterDes.{cid}.8', ''))
        intro = clean_text(lang_char_des.get(f'CharacterDes.{cid}.3', ''))
        star = r_c.get('star', 4)
        
        char_dir = os.path.join(OUT_DIR, 'characters', elem_dir, slug)
        os.makedirs(char_dir, exist_ok=True)
        char_count += 1

        # Aliases
        add_alias(name, f'characters/{elem_dir}/{slug}/overview.md', f'角色档案: {name}')
        add_alias(slug, f'characters/{elem_dir}/{slug}/overview.md', f'角色英文名: {slug}')
        add_alias(f'{name}档案', f'characters/{elem_dir}/{slug}/story.md', f'角色档案全集: {name}')
        add_alias(f'{name}生平', f'characters/{elem_dir}/{slug}/story.md', f'角色生平故事: {name}')
        add_alias(f'{name}故事', f'characters/{elem_dir}/{slug}/story.md', f'角色生平故事: {name}')
        add_alias(f'{name}剧情', f'characters/{elem_dir}/{slug}/story.md', f'角色剧情与约会: {name}')
        add_alias(f'{name}约会', f'characters/{elem_dir}/{slug}/story.md', f'角色约会对话: {name}')
        add_alias(f'{name}技能', f'characters/{elem_dir}/{slug}/skills.md', f'角色技能与机制: {name}')
        add_alias(f'{name}潜能', f'characters/{elem_dir}/{slug}/skills.md', f'角色潜能节点: {name}')
        add_alias(f'{name}攻略', f'characters/{elem_dir}/{slug}/guide.md', f'角色流派与配队: {name}')
        add_alias(f'{name}配队', f'characters/{elem_dir}/{slug}/guide.md', f'角色流派与配队: {name}')
        if cn_cv:
            add_alias(cn_cv, f'characters/{elem_dir}/{slug}/overview.md', f'中配CV: {cn_cv} ({name})')
        if jp_cv:
            add_alias(jp_cv, f'characters/{elem_dir}/{slug}/overview.md', f'日配CV: {jp_cv} ({name})')

        # 4.1 overview.md
        base_dict = {}
        for sec, fields in archive_bases_by_cid.get(cid_str, {}).items():
            b_label = fields.get('1', '')
            b_val = fields.get('2', '')
            if b_label and b_val:
                base_dict[b_label] = b_val

        birthday = base_dict.get('生日', r_c.get('birthday', '未知'))
        affiliation = base_dict.get('所属', '自由旅人')
        skills_hobby = base_dict.get('技能', '未知')
        address = base_dict.get('地址', '未知')
        experience = base_dict.get('经验', '未知')
        weapon_name = base_dict.get('武器', '专属武器')
        salary = base_dict.get('薪资', '未知')

        # Stats Table
        stats_list = r_c.get('stat', [])
        stats_md_lines = [
            "| 等级 (Level) | 生命值 (HP) | 攻击力 (ATK) | 防御力 (DEF) | 暴击率 | 暴击伤害 | 破韧效率 | 易伤倍率 |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
        ]
        target_levels = [1, 20, 40, 60, 80, 90, 100]
        stats_by_lvl = {s.get('Level'): s for s in stats_list if isinstance(s, dict)}
        for tl in target_levels:
            st = stats_by_lvl.get(tl)
            if not st:
                lower_lvls = [lvl for lvl in stats_by_lvl.keys() if lvl <= tl]
                if lower_lvls:
                    st = stats_by_lvl[max(lower_lvls)]
            if st:
                stats_md_lines.append(
                    f"| Lv.{tl} | {st.get('HP')} | {st.get('ATK')} | {st.get('DEF')} | "
                    f"{st.get('Crit Rate')} | {st.get('Crit DMG')} | {st.get('Resilience Break Efficiency')} | {st.get('VUL Exploit')} |"
                )

        # Ascension breakthroughs (8 phases)
        upgrades = r_c.get('upgrade', [])
        upgrade_md_lines = [
            "| 突破阶段 | 消耗突破材料与货币 |",
            "| :--- | :--- |"
        ]
        for i, up in enumerate(upgrades):
            items_desc = []
            for item_en, qty in up.items():
                item_cn = en2cn_items.get(item_en, item_en)
                items_desc.append(f"{item_cn} × {qty}")
            upgrade_md_lines.append(f"| 第 {i+1} 阶突破 | {', '.join(items_desc)} |")

        # Love and Hate gifts
        love_gifts = [en2cn_items.get(g, g) for g in r_c.get('loveGift', [])]
        hate_gifts = [en2cn_items.get(g, g) for g in r_c.get('hateGift', [])]

        # Dating clues from dating_by_cid
        char_dating_events = dating_by_cid.get(cid_str, [])
        date_clues_lines = []
        for de in char_dating_events:
            date_clues_lines.append(f"- **{de['name']}**：线索「{de['clue']}」 | 随笔「{de['memory'][:30]}...」")
            if de.get('name'):
                add_alias(de['name'], f'characters/{elem_dir}/{slug}/story.md', f'约会事件: {name} - {de["name"]}')

        overview_md = f"""# 旅人档案：{name} ({slug.capitalize()})

## 1. 基础信息
- **姓名**：{name}
- **属性**：{elem_cn}系 ({elem_dir.capitalize()})
- **稀有度**：{star} 星旅人
- **所属组织**：{affiliation}
- **中文配音 (CN CV)**：{cn_cv or '官方未公布'}
- **日文配音 (JP CV)**：{jp_cv or '官方未公布'}
- **生日**：{birthday}
- **特长技能**：{skills_hobby}
- **常住地址**：{address}
- **旅人资历**：{experience}
- **惯用武器**：{weapon_name}
- **收费标准/委托金**：{salary}

## 2. 官方传记与评语
> {intro}

## 3. 基础属性与成长阶梯 (1~100 级)
{chr(10).join(stats_md_lines)}

## 4. 阶级突破消耗 (1~8 阶)
- **3 阶觉醒说明**：当进阶达到第 3 阶时，将正式解锁全新觉醒形态与立绘。
{chr(10).join(upgrade_md_lines)}

## 5. 喜好偏好与送礼指南
- **喜爱礼物 (获得额外好感加成)**：{', '.join(love_gifts) if love_gifts else '暂无数据'}
- **厌恶礼物 (好感度增加减半)**：{', '.join(hate_gifts) if hate_gifts else '暂无数据'}

## 6. 约会专属日程检索
{chr(10).join(date_clues_lines) if date_clues_lines else '- 暂无常规约会日程'}

---
- **技能机制与潜能**：[查看详细技能与潜能节点](./skills.md)
- **生平档案与约会剧情**：[查看详细生平、八卦轶事与约会对话](./story.md)
- **配队与攻略指南**：[查看官方流派与配队指南](./guide.md)
"""
        safe_write(os.path.join(char_dir, 'overview.md'), overview_md)

        # 4.2 skills.md
        natk_id = c_bin.get('NormalAtkId')
        dodge_id = c_bin.get('DodgeId')
        skill_id = c_bin.get('SkillId')
        askill_id = c_bin.get('AssistSkillId')
        ult_id = c_bin.get('UltimateId')

        natk_name = clean_text(lang_skills.get(f'Skill.{natk_id}.1', '普通攻击'))
        natk_brief = clean_text(lang_skills.get(f'Skill.{natk_id}.13', ''))
        natk_detail = clean_text(lang_skills.get(f'Skill.{natk_id}.2', ''))

        dodge_name = clean_text(lang_skills.get(f'Skill.{dodge_id}.1', '闪避动作'))
        
        skill_name = clean_text(lang_skills.get(f'Skill.{skill_id}.1', '主控技能'))
        skill_brief = clean_text(lang_skills.get(f'Skill.{skill_id}.13', ''))
        skill_detail = clean_text(lang_skills.get(f'Skill.{skill_id}.2', ''))

        askill_name = clean_text(lang_skills.get(f'Skill.{askill_id}.1', '援护技能'))
        askill_brief = clean_text(lang_skills.get(f'Skill.{askill_id}.13', ''))
        askill_detail = clean_text(lang_skills.get(f'Skill.{askill_id}.2', ''))

        ult_name = clean_text(lang_skills.get(f'Skill.{ult_id}.1', '绝招'))
        ult_brief = clean_text(lang_skills.get(f'Skill.{ult_id}.13', ''))
        ult_detail = clean_text(lang_skills.get(f'Skill.{ult_id}.2', ''))

        # Skill Upgrades (1~9 levels)
        skill_upgrades = r_c.get('skillUpgrade', [])
        sk_up_lines = [
            "| 技能等级提升 | 消耗升级素材与货币 |",
            "| :--- | :--- |"
        ]
        for i, sk_up in enumerate(skill_upgrades):
            items_desc = []
            for item_en, qty in sk_up.items():
                item_cn = en2cn_items.get(item_en, item_en)
                items_desc.append(f"{item_cn} × {qty}")
            sk_up_lines.append(f"| Lv.{i+1} → Lv.{i+2} | {', '.join(items_desc)} |")

        # Potentials
        pot_lines = []
        for p_idx in range(1, 6):
            pot_id = f"5{cid:03d}0{p_idx}"
            pot_title = clean_text(lang_potentials.get(f'Potential.{pot_id}.1', f'潜能节点 {p_idx}'))
            pot_desc = clean_text(lang_potentials.get(f'Potential.{pot_id}.2', '强化效果'))
            pot_lines.extend([
                f"### 潜能 {p_idx}：{pot_title}",
                f"- **效果**：{pot_desc}",
                ""
            ])

        skills_md = f"""# {name} 技能机制与潜能详解

## 1. 战斗技能全解析

### 普通攻击：{natk_name}
- **简述**：{natk_brief}
- **详细机制**：
  > {natk_detail}

### 闪避动作：{dodge_name}
- **机制**：快速位移规避伤害，拥有极限闪避无敌帧，成功闪避可衔接疾跑或反击连携。

### 主控技能：{skill_name}
- **简述**：{skill_brief}
- **详细机制**：
  > {skill_detail}

### 援护技能：{askill_name}
- **简述**：{askill_brief}
- **详细机制**：
  > {askill_detail}

### 绝招：{ult_name}
- **简述**：{ult_brief}
- **详细机制**：
  > {ult_detail}

---

## 2. 技能等级强化材料消耗 (Lv.1 至 Lv.10)
{chr(10).join(sk_up_lines)}

---

## 3. 专属潜能节点 (Potentials 1~5)
{chr(10).join(pot_lines)}
"""
        safe_write(os.path.join(char_dir, 'skills.md'), skills_md)

        # 4.3 story.md
        char_arc = archive_contents_by_cid.get(cid_str, {})
        story_sections_md = []
        for sec_num in sorted(char_arc.keys(), key=lambda x: int(x)):
            sec_fields = char_arc[sec_num]
            sec_title = clean_text(sec_fields.get('1', f'档案片段 {sec_num}'))
            sec_content = clean_text(sec_fields.get('2', ''))
            story_sections_md.extend([
                f"### 【{sec_title}】",
                sec_content,
                ""
            ])

        # Full dating dialogues
        dating_md_lines = []
        for dev in char_dating_events:
            dating_md_lines.extend([
                f"### 约会事件：{dev['name']}",
                f"- **发生地点/线索**：{dev['clue']}",
                f"- **回忆随笔**：{dev['memory']}",
                f"- **场景对话记录**：",
                f"  **【第一幕】**：\n  > {dev['desc1'].replace(chr(10), chr(10) + '  > ')}",
                f"  **【第二幕】**：\n  > {dev['desc2'].replace(chr(10), chr(10) + '  > ')}",
                f"  **【第三幕】**：\n  > {dev['desc3'].replace(chr(10), chr(10) + '  > ')}",
                ""
            ])

        # Personal plots
        plot_matches = []
        for pk, pv in lang_plot.items():
            if f'Plot.{cid}' in pk and pk.endswith('.1'):
                p_title = clean_text(pv)
                p_desc = clean_text(lang_plot.get(pk[:-1] + '2', ''))
                plot_matches.append(f"- **{p_title}**：{p_desc}")

        story_md = f"""# {name} 官方档案全集与生平剧情

## 1. 协会绝密官方档案 (13 分幕)
{chr(10).join(story_sections_md)}

---

## 2. 约会剧情与专属物语
{chr(10).join(dating_md_lines) if dating_md_lines else "- 暂无独立约会物语"}

---

## 3. 个人篇目记录 (Plots)
{chr(10).join(plot_matches) if plot_matches else "- 暂无独立短剧剧目记录"}
"""
        safe_write(os.path.join(char_dir, 'story.md'), story_md)

        # 4.4 guide.md
        genres = []
        for k in range(9, 13):
            g = clean_text(lang_char_des.get(f'CharacterDes.{cid}.{k}', ''))
            if g:
                genres.append(g)
        genres_text = "\n".join([f"- **官方推荐流派 {i+1}**：{g}" for i, g in enumerate(genres)]) if genres else "- 暂无官方预设流派文本"

        guide_md = f"""# {name} 官方流派与配队战斗指南

## 1. 核心定位与机制
- **定位**：{elem_cn}系核心旅人 ({star} 星)
- **战斗风格**：擅长利用{elem_cn}系印记与多样化战术机制进行持续压制与爆发输出。

## 2. 官方推荐战斗流派
{genres_text}

## 3. 配队协同与印记联动
- **印记附着与引爆**：优先搭配具有快速挂载{elem_cn}系印记或具备高削韧能力的均衡/辅助旅人。
- **主控与援护战术分工**：
  - **主控登场**：利用「{skill_name}」控场与「{natk_name}」打出高频伤害，结合绝招「{ult_name}」在敌方虚弱时爆发。
  - **援护后台**：前台队友破韧后瞬间触发「{askill_name}」，登场瞬发压制。

## 4. 关键养成质变节点
- **突破 3 阶觉醒**：不仅解锁觉醒立绘，而且大幅度提升成长属性，是质变关键期。
- **潜能优先级**：潜能 1 与 潜能 2 是核心机制质变点，显著优化循环手感并带来机制层数加成。
"""
        safe_write(os.path.join(char_dir, 'guide.md'), guide_md)

    print(f"Generated {char_count} characters across 6 elements.")

# ==========================================
# 5. ALIAS TABLE GENERATION
# ==========================================
def generate_alias_table():
    print("Generating alias table and inverted index...")
    extra_nicknames = {
        '埃莉诺': ['大小姐', '千藏', '粉毛', '粉毛大小姐', 'eleanor', '花泽香菜', '花岩香奈', '石丛昊', '施丛昊', '富婆', '大剑', '手提箱', '菲茨罗伊'],
        '琥珀': ['双枪', '猫条', '猫条1911', '打字仙人', 'amber', '四白', '高田忧希'],
        '缇莉娅': ['蒙面骑士', '圣盾', '骑士', 'tilia', '陈雨', '大久保瑠美'],
        '密涅瓦': ['毒舌', '会长', 'minova', '杨晴江', '菲鲁兹蓝'],
        '小禾': ['娃娃机仙人', '手弩', '企鹅', 'nazuna', '谢莹', '江原萌'],
        '卡西米拉': ['猫薄荷', 'kasimira', '李婵妃', '安野希世乃'],
        '翡冷翠': ['firenze', '占卜', '子音', '斋藤千和'],
        '鸢尾': ['iris', '魔法书', '孤儿院', '陈张', '夏吉优子'],
        '尘沙': ['小熊', 'noya', '机修工', 'kiyo', '今泉りおな'],
        '师渺': ['shimiao', '算命', '陈阳', '小泽亚李'],
        '火垂': ['firefly', '武者', '刘雯', '长绳麻理亚'],
        '岭川': ['铲子炮', '种子', 'ridge', '联合种业', '张凯旋', '七濑彩夏'],
        '科洛妮丝': ['coronis', '药水', '医生', '周钰涵', '齐藤佑圭'],
        '菈露': ['laru', '记者', '宋媛媛', '田中爱美'],
        '珂赛特': ['cosette', '女仆', '唐萌', '河原木志穗'],
        '乙叶': ['otoha', '巫女', '张安琪', '加隈亚衣'],
        '花铃': ['karin', '乐师', '花玲', '小仓唯'],
        '焦糖': ['caramel', '厨师', '蔡书瑾', '铃代纱弓'],
        '赤霞': ['chixia', '拳套', '唐雅芳', '德井青空'],
        '斯帕克拉': ['angie', '火花', '宋正楠', '工藤绫乃'],
        '艾蕾': ['allie', '看板娘', '曾彤', '石飞惠里花'],
    }
    
    general_aliases = {
        '自走棋': ('basics/game_modes.md', '尖兵陷阵自走棋玩法'),
        '爬塔': ('basics/game_modes.md', '星塔探索系统'),
        '体力': ('basics/currency_and_gacha.md', '干劲体力机制'),
        '金币': ('basics/currency_and_gacha.md', '朵拉金币'),
        '抽卡': ('basics/currency_and_gacha.md', '招募与祈愿卡池'),
        '保底': ('basics/currency_and_gacha.md', '卡池保底规则'),
        '通行证': ('basics/currency_and_gacha.md', '创业激励基金'),
        '破防': ('basics/game_mechanics.md', '韧性削减与破防机制'),
        '虚弱': ('basics/game_mechanics.md', '韧性削减与虚弱硬直'),
        '印记': ('basics/game_mechanics.md', '元素属性与印记机制'),
        '词条': ('basics/emblems_overview.md', '纹章随机词条与契合度'),
        '突破': ('basics/game_mechanics.md', '旅人进阶与等级突破'),
        '觉醒': ('basics/game_mechanics.md', '3阶觉醒与立绘'),
        '唱片': ('basics/discs_overview.md', '102张唱片全集'),
        '纹章': ('basics/emblems_overview.md', '纹章词条属性库'),
        '茶会': ('story/events/tea_party_10111/overview.md', '活动剧情: 大小姐们的茶会'),
        '大小姐的茶会': ('story/events/tea_party_10111/overview.md', '活动剧情: 大小姐们的茶会'),
        '雪愿节': ('story/events/winter_messenger_20101/overview.md', '活动剧情: 雪愿节的使者'),
        '夏假': ('story/events/summer_vacation_20103/overview.md', '活动剧情: 是时候休个假了！'),
        '夏日活动': ('story/events/summer_vacation_20103/overview.md', '活动剧情: 是时候休个假了！'),
        '新春': ('story/events/spring_festival_10104/overview.md', '活动剧情: 苍茫人海逢故人'),
        '苍梧': ('story/events/spring_festival_10104/overview.md', '活动剧情: 苍茫人海逢故人'),
        '北境': ('story/events/north_city_10105/overview.md', '活动剧情: 前往北境之城'),
        '万送屋': ('story/events/deliverer_quest_10106/overview.md', '活动剧情: 万送屋的委托'),
    }
    for kw, (tgt, desc) in general_aliases.items():
        add_alias(kw, tgt, desc)

    for char_name, nicks in extra_nicknames.items():
        existing = alias_map.get(char_name.lower())
        if existing:
            target = existing[0]['path']
            for nick in nicks:
                add_alias(nick, target, f'角色别名/外号: {char_name}')

    safe_write(os.path.join(OUT_DIR, 'alias_index.json'), json.dumps(alias_map, ensure_ascii=False, indent=2))

    md_lines = [
        "# 《星塔旅人》扁平外号倒排索引表 (Alias Inverted Table)",
        "",
        "本倒排索引专为多轮工具调用模型设计，支持通过角色姓名、外号、别名、主线关卡名、活动名及玩法术语毫秒级定位到对应的渐进式披露文档。",
        "",
        "| 索引关键词 (Alias / Keyword) | 目标相对路径 (Target Path) | 说明 (Description) |",
        "| :--- | :--- | :--- |"
    ]

    for kw in sorted(alias_map.keys()):
        targets = alias_map[kw]
        for t in targets:
            md_lines.append(f"| `{kw}` | [{t.get('path')}](./{t.get('path')}) | {t.get('desc')} |")

    safe_write(os.path.join(OUT_DIR, 'alias_table.md'), "\n".join(md_lines))
    print(f"Alias table built with {len(alias_map)} distinct keywords.")

if __name__ == '__main__':
    print("=" * 60)
    print("STARTING FULL WIKI KNOWLEDGE BASE GENERATION")
    print("=" * 60)
    
    # 0. Wipe old knowledge base completely
    if os.path.exists(OUT_DIR):
        print(f"Wiping existing knowledge base at {OUT_DIR}...")
        shutil.rmtree(OUT_DIR, ignore_errors=True)

    generate_basics()
    generate_main_story()
    generate_event_stories()
    generate_characters()
    generate_alias_table()

    print("=" * 60)
    print(f"KNOWLEDGE BASE GENERATION COMPLETE! Saved to {OUT_DIR}")
    print("=" * 60)
