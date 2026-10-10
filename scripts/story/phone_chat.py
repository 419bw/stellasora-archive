# -*- coding: utf-8 -*-
"""心链（手机聊天）全篇提取：Chat 表驱动的分段渲染 + 回复抉择分支归属。

「心链」是游戏内手机聊天功能的官方名（`OpenFunc.Phone.1` = 心链；
`UIText.Guide_43_1.1` = "「心链」可以和结识的旅人发送信息，是手机最重要的功能"）。
63 个 `PM_*` 剧本经 `Chat.json`（498 行）挂载：一行 = 一个聊天段，`AVGId` 指剧本、
`AVGGroupId` 指剧本里的 `SetGroupId` 段号。

与主管线的分工（`pipeline/passes.py` 一行不改）：
- 复用：`parse_lua`/`build_commands`（指令解析）、`TextCompiler`（文本编译）、
  `SpeakerResolver`（说话人）、`fold_animations`（动画帧折叠）、`markup`（渲染）、
  `fork_options`/`command_text_slots`（抉择块与文本槽）。
- 自研：段切分与 `SetPhoneMsgChoiceJumpTo` 的分支归属。passes.py 对 phone 方言
  "平铺不推帧"是既定设计（`STev_03_01` 等已渲染活动剧照此输出，改推帧会撞
  `docs/` 冻结基线的字节锁），所以心链只在自家渲染里补「若选…」分支标记。

产物由 `build_story.build_chat()` 写盘（本模块不碰文件系统、不读数据表）：
    story_docs/_chat/PM<编号>.md          一段一节（63 个，扁平摆放）
    story_docs/_chat/_index.md           总索引
    story_docs/_chat/_diagnostics.json   兜底登记
**必须扁平、不能再建子目录**：validate_site 的 G2 是按"直接所在目录名是否 `_` 前缀"放行
`.md` 的（`_data/`、`_beats/` 正因如此被跳过），`_chat/<子目录>/x.md` 会被当成站点页收编、
撞"sections.json 没登记"。63 个文件名按 PM 编号排序即按联系人分组，角色名在每篇 H1 与
`_index.md` 里。信息行同样不写 `AVG 剧本**：` 标签，validate_story 的 A/C/F 也不收编。

段内消息类型（`AllEnum.PhoneMsgType`，见 data/ss_lua 的 AllEnum.lua）：
    0 收到文字 / 1 发出文字 / 2 回复抉择 / 3 收到表情图 / 4 发出表情图 /
    5 系统提示（上线/下线）/ 6,7 正在输入（PM 剧本中未出现）
表情/图片按**消息类型**判（3/4），不按"渲染文本像不像资源名"：杏子（PM12301）有两条
type 0 的口头禅 "mumu"/"mumumu"，用资源名规则会被误判成表情（手册 7.6 的 822 条即此粗规则
的计数，真实值 820 = 437 + 383）。
"""
import collections
import re

from pipeline import markup
from pipeline.passes import command_text_slots, fold_animations, fork_options, slot
from pipeline.text_rules import clean_text, is_resource_name

GROUP_CMD = 'SetGroupId'
MSG_CMD = 'SetPhoneMsg'
CHOICE_BEGIN = 'SetPhoneMsgChoiceBegin'
CHOICE_JUMP = 'SetPhoneMsgChoiceJumpTo'
CHOICE_END = 'SetPhoneMsgChoiceEnd'

# AllEnum.PhoneMsgType
TYPE_SYSTEM = 5
STICKER_TYPES = (3, 4)          # 收到表情图 / 发出表情图（pic_* 图片消息也在这两槽）
EMOJI_PREFIX = 'emoji_'

# GameEnum.chatTriggerType（GAME_ENUM_DEFINE.lua）：None=0, Immediately=1, Time=2。
# 客户端 lua 不读 Chat.TriggerType，故此映射只是枚举名推断，输出里保留原值。
TRIGGER_TYPES = {1: '立即', 2: '定时'}

# 当前上游数据的已知怪象（白名单，其余类别必须为 0）：
#   segment_without_chat_row —— 39 个文件的脚本带 `08` 段而 Chat 表无对应行（上游缺行）。
#   unbalanced_choice        —— 2 个段有 Begin 无 End（PM11701 第 04 段、PM14101 第 05 段）。
#   empty_segment_skipped    —— PM13501 的 `08` 段在剧本中为空。
#   jump_index_out_of_range  —— PM14101 第 05 段：同一段内两个同组 Begin，前一个只声明
#                              1 个选项却带一个指向选项 2 的 JumpTo（客户端会把同组目标表
#                              合并覆盖，该 JumpTo 实为死数据），渲染为「分支2」标记。
KNOWN_GAPS = ('segment_without_chat_row', 'unbalanced_choice', 'empty_segment_skipped',
              'jump_index_out_of_range')


class ChatDiagnostics:
    """心链自有兜底登记。

    刻意不进 `pipeline.diagnostics` 的共享 `DIAG`/`CATEGORIES`：共享侧车的 schema
    由 validate_story 的 P 契约同构校验，加类别会动它。文本/说话人兜底（未知
    markup、说话人前缀回落）仍走共享 DIAG，只落既有类别。
    """

    def __init__(self):
        self.data = collections.OrderedDict()

    def add(self, category, entry):
        self.data.setdefault(category, []).append(entry)

    def counts(self):
        return {k: len(v) for k, v in sorted(self.data.items())}

    def unexpected(self):
        return {k: len(v) for k, v in sorted(self.data.items()) if k not in KNOWN_GAPS}

    def as_dict(self):
        return {
            'note': ('心链提取兜底登记。segment_without_chat_row / unbalanced_choice / '
                     'empty_segment_skipped / jump_index_out_of_range 是当前上游数据的已知怪象'
                     '（白名单，实例见各条目），其余类别必须为 0。'
                     '文本与说话人兜底走共享 DIAG，落在 story_docs/_diagnostics.json 的既有类别里。'),
            'counts': self.counts(),
            'categories': {k: v for k, v in self.data.items()},
        }


# ============================================================ 剧本 → 段
def split_segments(commands):
    """按 SetGroupId 切段 → [(段号, [Command, ...])]。

    段号与 `Chat.AVGGroupId` 对应；脚本段是权威（537 段 > Chat 498 行，多出的
    是上游缺行的 `08` 段）。文件尾的 `{cmd = "End"}` 终止符不属于任何命令族，忽略。
    """
    segs, gid, cur = [], None, []
    for c in commands:
        if c.cmd == GROUP_CMD:
            if gid is not None:
                segs.append((gid, cur))
            gid = clean_text(c.param[0]) if len(c.param) else ''
            cur = []
        elif gid is not None:
            cur.append(c)
    if gid is not None:
        segs.append((gid, cur))
    return segs


def _msg_type(talk_type):
    try:
        return int(str(talk_type))
    except (TypeError, ValueError):
        return None


def _msg_kind(talk_type, rendered):
    """消息形态：system / sticker / text。类型是权威判据，资源名规则只作未知类型的回退。"""
    t = _msg_type(talk_type)
    if t == TYPE_SYSTEM:
        return 'system'
    if t in STICKER_TYPES:
        return 'sticker'
    if t is None and is_resource_name(rendered):
        return 'sticker'
    return 'text'


def _branch_label(branch, titles):
    """分支标记用的选项标题；JumpTo 下标越界时回落「分支N」（与 passes.py 惯例一致）。"""
    text = titles.get(branch)
    return markup.text(text) if text is not None else '分支%s' % branch


def _close_choice(items, opened, titles, diag, stem, gid, group, implicit):
    """收束一个抉择组：发汇合标记（仅当确有分支消息），隐式收束时登记上游怪象。"""
    if implicit:
        diag.add('unbalanced_choice', {'stem': stem, 'gid': gid, 'group': group})
    if not opened:
        return
    silent = [_branch_label(i, titles) for i in sorted(titles) if i not in opened]
    items.append({'k': 'merge', 'opened': len(opened), 'silent': silent})


def extract_segment(stem, gid, commands, skip, resolver, compiler, diag):
    """段内逐命令走状态机 → 有序 items（msg/choice/branch_open/merge）与计数。

    分支归属规则（与客户端 PlayerPhoneData.lua 的跳转语义一致）：
    `ChoiceJumpTo{组, 下标}` 之后、直到同组下一个 JumpTo/End 之前的消息，
    只会在玩家选该选项时出现——这就是该分支的专属台词。
    """
    items = []
    branch = None            # 当前归属的选项下标；None = 共通台词
    opened = set()           # 已发出分支起点标记的下标
    titles = {}              # 下标 -> 选项 Text
    group = None             # 当前抉择组 id
    n_cmd = n_folded = n_msg = n_empty = n_begin = 0
    for c in commands:
        if c.cmd == CHOICE_BEGIN:
            n_begin += 1
            _prompt, opts = fork_options('phone', c.param, compiler)
            opts = [(t, d, e) for t, d, e in opts if t]
            if not opts:
                diag.add('choice_begin_without_options',
                         {'stem': stem, 'gid': gid, 'group': clean_text(c.param[0])})
                continue
            if group is not None:      # 上一个抉择组没有 ChoiceEnd
                _close_choice(items, opened, titles, diag, stem, gid, group, True)
            group = clean_text(c.param[0]) if len(c.param) else ''
            titles = {i + 1: t for i, (t, _d, _e) in enumerate(opts)}
            items.append({'k': 'choice', 'options': [t for t, _d, _e in opts]})
            branch, opened = None, set()
            continue

        if c.cmd == CHOICE_JUMP:
            g = clean_text(c.param[0]) if len(c.param) else ''
            raw = slot(c.param, 1)
            if group is not None and g != group:
                diag.add('choice_group_mismatch',
                         {'stem': stem, 'gid': gid, 'cmd': 'jump',
                          'open_group': group, 'cmd_group': g})
            try:
                branch = int(str(raw))
            except (TypeError, ValueError):
                branch = None
            if branch not in titles:
                diag.add('jump_index_out_of_range',
                         {'stem': stem, 'gid': gid, 'group': g, 'index': str(raw)})
            continue

        if c.cmd == CHOICE_END:
            g = clean_text(c.param[0]) if len(c.param) else ''
            if group is None:
                continue              # 没有对应 Begin 的 End：忽略（与 passes.py 容错一致）
            if g != group:
                diag.add('choice_group_mismatch',
                         {'stem': stem, 'gid': gid, 'cmd': 'end',
                          'open_group': group, 'cmd_group': g})
            _close_choice(items, opened, titles, diag, stem, gid, group, False)
            group, branch, opened, titles = None, None, set(), {}
            continue

        if c.cmd == MSG_CMD:
            n_cmd += 1
            if c.idx in skip:
                n_folded += 1
                continue
            if len(c.param) < 3:
                continue
            talk_type = str(c.param[0])
            text = compiler.compile(*command_text_slots(c))
            if not text:
                n_empty += 1
                diag.add('empty_text_skipped',
                         {'stem': stem, 'gid': gid, 'idx': c.idx, 'speaker': str(c.param[1])})
                continue
            kind = _msg_kind(talk_type, markup.markdown(text))
            if branch is not None and branch not in opened:
                opened.add(branch)
                items.append({'k': 'branch_open', 'option': _branch_label(branch, titles)})
            items.append({'k': 'msg', 'kind': kind,
                          'speaker': resolver.of(c.param[1], talk_type), 'text': text})
            n_msg += 1

    if group is not None:              # 段末仍未收束（上游 Begin 无 End）
        _close_choice(items, opened, titles, diag, stem, gid, group, True)
    if n_folded:
        diag.add('folded_frames_skipped', {'stem': stem, 'gid': gid, 'count': n_folded})
    if n_msg != n_cmd - n_folded - n_empty:
        diag.add('message_count_mismatch',
                 {'stem': stem, 'gid': gid, 'rendered': n_msg, 'commands': n_cmd,
                  'folded': n_folded, 'empty': n_empty})
    return {'gid': gid, 'items': items, 'n_cmd': n_cmd, 'n_msg': n_msg,
            'n_begin': sum(1 for it in items if it['k'] == 'choice'),
            'n_folded': n_folded, 'n_empty': n_empty}


def extract_script(stem, commands, resolver, compiler, diag):
    """一个 PM 剧本 → [段 dict]（按段号升序；零填充段号字符串序即正确序）。"""
    skip = fold_animations(commands, compiler)
    return [extract_segment(stem, gid, cmds, skip, resolver, compiler, diag)
            for gid, cmds in split_segments(commands)]


# ============================================================ Chat 表 → 人话
def _cond_params(row):
    return re.findall(r'-?\d+', str(row.get('TriggerCondParam') or ''))


def unlock_label(row, contact_name):
    """TriggerCondParam → 人话：`[103]` 结识该旅人、`[103,5]` 好感等级 5。"""
    raw = str(row.get('TriggerCondParam') or '')
    nums = _cond_params(row)
    if len(nums) >= 2:
        return '好感等级 %s（TriggerCondParam `%s`）' % (nums[1], raw)
    if len(nums) == 1:
        if nums[0] == str(row.get('AddressBookId')):
            return '结识%s（TriggerCondParam `%s`）' % (contact_name, raw)
        return 'TriggerCondParam `%s`（单参数形态，语义未决）' % raw
    return '无（TriggerCondParam 为空）'


def trigger_type_label(row):
    t = row.get('TriggerType')
    name = TRIGGER_TYPES.get(t)
    if name:
        return '%s（TriggerType `%s`，枚举推断）' % (name, t)
    return 'TriggerType `%s`（未识别）' % t


def reward_label(row, item_names):
    rid, qty = row.get('Reward1'), row.get('RewardQty1')
    if rid is None:
        return ''
    name = item_names.get(str(rid)) or ''
    if name:
        return '**奖励**：%s ×`%s`（Item `%s`）' % (name, qty, rid)
    return '**奖励**：Item `%s` ×`%s`' % (rid, qty)


# ============================================================ 渲染
def _variant_lines(text):
    return ['- %s：「%s」' % (label, value) for label, value in markup.alternatives(text)]


def _msg_blocks(item):
    """一条消息 → 1~2 个块（正句 + 可选的性别/语言变体块）。"""
    text = item['text']
    rendered = markup.markdown(text)
    if item['kind'] == 'system':
        head = ['> *（系统）%s*' % rendered]
    elif item['kind'] == 'sticker':
        what = '表情' if rendered.startswith(EMOJI_PREFIX) else '图片'
        head = ['**%s**：〔发送%s `%s`〕' % (item['speaker'], what, rendered)]
    else:
        head = ['**%s**：「%s」' % (item['speaker'], rendered)]
    variants = _variant_lines(text)
    return [head] + ([variants] if variants else [])


def _items_blocks(items):
    """段内 items → markdown 块列表（块间空一行）。标记文案与 render_md.py 对齐。"""
    blocks = []
    for it in items:
        k = it['k']
        if k == 'msg':
            blocks += _msg_blocks(it)
        elif k == 'choice':
            blocks.append(['> **[通讯回复抉择]**'] +
                          ['> - **%s**' % markup.markdown(t) for t in it['options']])
        elif k == 'branch_open':
            blocks.append(['> **[若选「%s」↓]**' % it['option']])
        elif k == 'merge':
            if it['opened'] == 1:
                mark = '> **[▲ 以上台词只出现在所选分支，其余选项直接进入下一段]**'
            else:
                mark = '> **[▲ 以上 %d 条分支互斥，自此汇合]**' % it['opened']
            block = [mark]
            if it['silent']:
                block.append('> *（其中%s没有专属台词，选中即跳到汇合点）*'
                             % '、'.join('「%s」' % s for s in it['silent']))
            blocks.append(block)
    return blocks


def _segment_info(gid, row, contact_name, item_names):
    if row is None:
        return ['- **Chat ID**：无（Chat 表未挂载此段，上游缺行）　**段号**：`%s`' % gid]
    lines = [
        '- **Chat ID**：`%s`　**段号**：`%s`' % (row.get('Id'), gid),
        '- **解锁条件**：%s' % unlock_label(row, contact_name),
        '- **前置聊天**：%s' % ('无（起始段）' if not row.get('PreChatId')
                              else '`%s`' % row.get('PreChatId')),
        '- **触发类型**：%s' % trigger_type_label(row),
    ]
    tail = ['**优先级**：`%s`' % row.get('Priority'), reward_label(row, item_names)]
    lines.append('- %s' % '　'.join(x for x in tail if x))
    return lines


def render_script_md(contact, file, item_names):
    """一个心链剧本 → 整篇 md。file 需带 stem/script/segments/prepared/skipped_gids。"""
    lines = ['# %s 的心链聊天（%s）' % (contact['name'], file['stem']), '',
             '## 1. 聊天信息', '',
             '- **联系人**：%s（AddressBookId `%s`）' % (contact['name'], contact['id']),
             '- **心链剧本**：`%s`（%s）' % (file['stem'], file['script'])]
    siblings = [f for f in contact['files'] if f['stem'] != file['stem']]
    if siblings:
        lines.append('- **同联系人其他心链**：%s'
                     % '、'.join('[`%s`](%s.md)' % (f['stem'], f['stem']) for f in siblings))
    lines.append('- **段落数**：脚本 `%d` 段，其中 Chat 表挂载 `%d` 段'
                 % (len(file['segments']), sum(1 for s in file['segments']
                                               if s['gid'] in file['rows'])))
    if file['skipped_gids']:
        lines.append('- **跳过**：%s' % '、'.join(
            '第 `%s` 段（剧本中为空，无任何消息）' % g for g in file['skipped_gids']))
    lines.append('')
    for no, (seg, row) in enumerate(file['prepared'], 2):
        lines += ['## %d. 第 %s 段' % (no, seg['gid']), ''] + _segment_info(
            seg['gid'], row, contact['name'], item_names) + ['']
        for block in _items_blocks(seg['items']):
            lines += block + ['']
    return '\n'.join(lines).rstrip() + '\n'


def file_stats(prepared):
    st = collections.Counter()
    for seg, _row in prepared:
        st['segments'] += 1
        st['choices'] += seg['n_begin']
        for it in seg['items']:
            if it['k'] == 'msg':
                st['messages'] += 1
                st[it['kind']] += 1
    return st


def render_index_md(contacts):
    """总索引：一行一个心链剧本 + 合计 + 口径说明。"""
    lines = [
        '# 心链聊天总索引', '',
        '> 游戏内「心链」（手机聊天）功能的全篇文本存档，由 `scripts/story/build_story.py` 的',
        '> `build_chat()` 随主构建自动生成。**不进静态站点**——`_` 前缀目录在本仓库的约定是',
        '> "生成物但非站点页"（与 `_coverage.md` / `_battle_reconciliation.md` 同义），',
        '> validate_site 的 G2 与 validate_story 的 A/C/F 都不收编它。', '',
        '再生命令：`python scripts/story/build_story.py`', '',
        '| 联系人 | 心链剧本 | 段数 | 短信 | 表情/图片 | 系统提示 | 抉择 |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]
    total = collections.Counter()
    for contact in contacts:
        for f in contact['files']:
            st = file_stats(f['prepared'])
            total.update(st)
            total['files'] += 1
            lines.append('| %s | [%s](%s.md) | %d | %d | %d | %d | %d |'
                         % (contact['name'], f['stem'], f['stem'],
                            st['segments'], st['messages'], st['sticker'],
                            st['system'], st['choices']))
    lines += [
        '| **合计** | **%d 个剧本** | **%d** | **%d** | **%d** | **%d** | **%d** |'
        % (total['files'], total['segments'], total['messages'], total['sticker'],
           total['system'], total['choices']),
        '', '## 说明', '',
        '- **数据来源**：剧本 `data/ss_lua/Lua/Game/UI/Avg/_cn/Config/PM*.lua`（63 个），'
        '挂载表 `data/StellaSoraData/CN/bin/Chat.json`（498 行）。',
        '- **段号 `08`**：39 个文件的剧本带有 `08` 段而 Chat 表无对应行（上游缺行，含 783 条'
        '真实消息），照常渲染并在段头标注；`PM13501` 的 `08` 段在剧本中为空，已跳过。',
        '- **分支标记**：`> **[若选「…」↓]**` 之后的消息只会在玩家选该选项时出现；'
        '`> **[▲ 分支汇合]**` 表示抉择分支到此结束。',
        '- **`TriggerCond` 语义未决**：`Chat.TriggerCond`（10/13/14/114）在客户端代码中无消费点，'
        '疑似服务端门控，故只原样登记；`TriggerCondParam` 的 `[角色]` / `[角色, 好感等级]` 已翻译成人话。',
        '- **`TriggerType` 为枚举推断**：按 `GAME_ENUM_DEFINE.lua` 的 '
        '`chatTriggerType {Immediately=1, Time=2}` 标注"立即/定时"，原值一并保留。',
        '- **表情/图片计数口径**：按消息类型 3（角色发送）与 4（玩家发送）计，`emoji_*` 是表情、'
        '`pic_*` 是图片，合计 820 条。`_dev/AI_HANDOVER_GUIDE.md` 7.6 记的 822 是早先按'
        '"渲染文本是否为资源名"的粗规则数出来的，把杏子（PM12301）两句 type 0 的口头禅 '
        '"mumu"/"mumumu" 误计成了表情，真实值是 820。',
        '- 兜底登记见 [`_diagnostics.json`](_diagnostics.json)。',
        '',
    ]
    return '\n'.join(lines)
