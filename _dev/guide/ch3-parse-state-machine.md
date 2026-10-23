> 《AI 技术交接手册》第 三 章正文分册；总索引与「按需索取」表见 [AI_HANDOVER_GUIDE.md](../AI_HANDOVER_GUIDE.md)。章节编号沿用原书，跨章引用（如「见 3.6」）按索引定位。

## 三、 剧情解析核心状态机（关键业务逻辑）

这是整个知识库最核心的技术点，任何接手的 AI 必须严格遵守以下规则：

### 3.1 主角正名逻辑（为什么是“魔王”，为何原始数据是“塞拉”）
- **背景**：在官方剧本 `AvgCharacter.lua` 中，主角女性外观 `avg3_100` 与男性外观 `avg3_101` 的 `name` 字段被填为了 `"塞拉"`。这是米哈游/悠星等二次元游戏开发期常用的内部原型代号（Sera）。
- **玩家实际感知**：在游戏主线与世界观中，主角自始至终被公认和正式称呼为**「魔王」**（魔王协议负责人）。
- **规范**：
  - 必须对以下说话人 ID 强制重写为 **“魔王”**：
    `avg3_100`, `avg3_101`, `avg3_1311`, `avg3_1312`, `1`
  - 严禁直接输出“塞拉”！

### 3.2 灰色对话框（内心独白）判定：TalkType 枚举
在官方源码 `ss_lua/Avg/_cn/Config/AvgCmdParamOptionDefine.lua`（`TalkType` 枚举表）中，`SetTalk` 传入的第一个参数代表 `TalkType`：
```lua
TalkType = {
  "角色说",   -- 0: NPC/其他角色说出口的话
  "主角说",   -- 1: 魔王对外正常说出口的话
  "主角想",   -- 2: 官方枚举"主角想" -> 灰色无箭头气泡，属于内心独白/思考！
  "底部字幕", -- 3: 旁白叙事
  ...
}
```
- **判定规则**：
  ```python
  if talk_type == "2":
      # 灰色思考对话框
      line = f"**{speaker}**（思考）：「{dialogue_text}」"
  else:
      # 正常说出的话
      line = f"**{speaker}**：「{dialogue_text}」"
  ```
- **特例**：当 `speaker_id == "0"` 且 `talk_type == "2"` 时（如 `CG_147_02.lua` 中“稍微心疼钱包一秒。”），这是没有立绘显示的主角心理活动，发言人必须归结为 **魔王（思考）**，而不是旁白。

### 3.3 玩家抉择项精准解析（严禁粗暴正则）
在 Lua 剧本中，选项绝不能用 `re.findall(r'"([^"]+)"', param)`。这样会抓到 UI 预制体名字（`AvgChoice_item_02_01`）、跳转分支 ID（`E201`）、布局代号（`c`）、字号（`020`）、表情（`avg_emoji_think`）。

必须实现 3 类独立提取逻辑：

#### ① 重大抉择 (`SetMajorChoice`)
- **Lua 原文结构**：
  ```lua
  cmd = "SetMajorChoice",
  param = {
    1, "AvgChoice_item_02_01", 0, "趁着夜色潜入", "没有计划的计划就是好计划", "", "E201", 0,
    "AvgChoice_item_02_02", 0, "让密涅瓦侦查", "有算胜无算，多算胜少算", "", "E202", 0,
    "AvgChoice_item_02_03", 0, "考虑其他办法", "藏在箱子里混进去", "", "E203", 1,
    "c", "020", "avg_emoji_think", "该选哪个呢？", ""
  }
  ```
- **提取逻辑**：
  1. 扫描末尾布局元组 `[对齐, 数字, 表情, 提示词, ""]`，提取 `该选哪个呢？` 作为 Prompt。
  2. 扫描每一个以 `AvgChoice_` 开头的项，紧接着的两个有效字符串即为 **【选项标题】** 与 **【选项副标题/说明】**。
  3. 过滤掉 `E201`、`E1001` 等分支跳转 ID。
- **目标输出格式**：
  ```markdown
  > **[重大抉择：该选哪个呢？]**
  > - **趁着夜色潜入**：没有计划的计划就是好计划
  > - **让密涅瓦侦查**：有算胜无算，多算胜少算
  > - **考虑其他办法**：藏在箱子里混进去
  ```

#### ② 性格倾向抉择 (`SetPersonalityChoice`)
- 包含 3 个选项，通常对应魔王的三种态度。
- **目标输出格式**：
  ```markdown
  > **[玩家抉择：我该怎么回答她呢]**
  > - 你就是管理采购商店的布洛可吧？
  > - 我第一次来采购商店，你是谁？
  > - 光顾着领每日奖励了，没想到商店里居然有人。
  ```

#### ③ 终端短信回复 (`SetPhoneMsgChoiceBegin`)
- 手机聊天交互选项，过滤掉数字 `'1'` 与内部预设 `'avg3_100'`。
- **目标输出格式**：
  ```markdown
  > **[通讯回复抉择]**
  > - 听上去像是恐怖故事？
  > - 啊，我看过！
  ```

### 3.4 文本占位符与富文本标记清洗标准

> ⚠️ **本节 2026-10-10 重写**。旧版这里放的是一段"想象出来"的伪代码（把 `==SEX==` 换成"你"、
> 把 `<r=>` 注音剥掉、把所有 `==XXX==` 替换成空格），与真实实现 `scripts/story/pipeline/markup.py`
> 几乎条条不符。下面以代码为准。

内联标记的**唯一**实现在 `pipeline/markup.py`（`parse_inline` → `normalize_nodes` → `TextCompiler.compile`），
按以下顺序处理，**不是**一串正则替换：

| 标记 | 真实行为 | 说明 |
|---|---|---|
| `$nnnn` | 替换为官方词表文案 | 词表来自 `ContentWord.json`（`bin/` 取 key、`language/zh_CN` 取译文）。**查不到的 `$nnnn` 原样保留**并登记 `unknown_preset_words`——客户端会显示裸 token，本就是数据缺陷 |
| `==SEX1==` / `==SEX2==` | **性别变体**，不是"你" | 按说话人性别二选一（`AvgUIText.lua` 的 `SEX` 表，如 `她/他`）。产物因此可能是 `{cn_f, cn_m}` 两个变体，`Text.select(sex)` 取一个 |
| `==W==` | **直接删除**（不补空格） | 打字机停顿标记 |
| `==RT==` | 换行 | 场景头 5 槽之间用 |
| `==A0.15==` | 删除 | 动画等待时长 |
| `<r=注音></r>` / `<r=注音>正文</r>` | **保留**为 Markdown 内联注音 | 站点侧由 `render_html.py` 转成 `<ruby><rt>`；契约 M 逐句核对位置与文字 |
| `<b>` / `<i>` | **保留**（成对时） | 只丢孤儿标记不丢字，计数进 `emph_tags_preserved` / `orphan_emph_tags_stripped` |
| `<size=…>` `<color=…>` `<margin-left=…>` `<align=…>` `<alpha=…>` `<voffset=…>` 等排版标签 | 全部剥离 | 纯引擎排版，无语义 |
| `<br>` | 转为换行 | 场景头 5 槽之间用 |
| `==PLAYER_NAME==` | 替换为 `魔王` | 见 3.1 |
| 其余 `==XXX==` | **原样保留** + `logger.warning` + 登记 `unknown_control_markers` | PR #3 立的"容错不抛错"，见 3.6 |

**不要把这段逻辑改成正则批处理**：`<b><i></b></i>` 这类交叉标签要用栈配对（close 只配栈顶同种 open），
孤儿标记单独计数；`==SEX==` 的性别选择依赖 `Text.select(sex)`，替换成固定字符串会直接毁掉男女变体。
`text_rules.clean_dialogue()` / `default_compiler()` 是给外部用的薄封装。

### 3.5 抉择分支的台词归属与汇合标记

#### ① 三类玩家交互抉择（同一套帧栈机制）

- **引擎结构**：`Set*Choice(group, 选项行…)` 声明一次抉择；此后每个选项的专属剧本以 `Set*ChoiceJumpTo{group, k}` 开始，到 `Set*ChoiceRollover{group}` 结束；`Set*ChoiceEnd{group}` 关闭整个构造。各段剧本在 Lua 文件里**顺序平铺**，玩家一局只看到自己选中的那一段，所以直接平铺进 Markdown 会让互斥台词读成连续剧情。
- **group 才是主键**：`group` 就是 `Set*Choice` 的 param 第 0 项。分支必须按 `JumpTo{group, k}` 定位，**不能按行序配对**——存在一个抉择嵌在另一个抉择分支里的级联（`STm01_07.lua` 4 层，group 99/3/1/4，且 `Set*ChoiceEnd` 不满足 LIFO），因此解析用按 group 查的帧栈。
- **输出规则**：分支首条台词前插入 `> **[若选「选项标题」↓]**`；当帧栈清空（含嵌套的全部抉择一起关闭）时插入**一条**汇合标记 `> **[▲ …]**`，嵌套多于单层时写明层数与分支总数，并列出去往空分支的选项名。
- **空分支不打标记**：`JumpTo` 之后紧跟 `Rollover` 的选项没有专属台词，不产生 `若选` 标记，只在汇合处以「其中「X」没有专属台词，选中即跳到汇合点」说明（按选项名去重，官方数据存在重名项）。
- **短信抉择不打标记**：`SetPhoneMsgChoiceBegin` 的正文由 `SetPhoneMsg` 指令承载，而该指令当前未被提取，文档中没有可归属的台词，因此不标注分支。
- **上游数据 bug 备案：`CG_126_03.lua` 的 End group 错配（不为它改生成器）**：角色 126 紫槿「蝶说 下」第 10 个抉择块 `SetChoiceBegin` 的 group 是 `a_10`，但其 `SetChoiceEnd` 误写成了更早、已关闭的 `a_4`——全库实测仅此一处 End 与 Begin 的 group 不配对。帧栈按 group 严格配对（见上条），`a_10` 因此永不退栈；又因每遇到新抉择标记会重置，其后 5 个**单选项**抉择的台词被反复标注。游戏内不可见（单选项 + 线性内容，无分支 UI）。**处理决定**：不为上游错误给生成器加特例；兜底放在渲染层语义（单选项父抉择不画分支框），此处仅备案，修上游后可删。
- **渲染层兜底实现（妥协点，修上游后可删）**：`scripts/site/render_html.py` 会给每个 `若选` 计算 `single_parent`（归属到的父抉择只有 1 个选项）；渲染时该标记整体不输出，也不产生「返回抉择 / 跳到汇合」导航条。契约 **M3**（`tests/story/validate_site.py`）独立从 md 重算单选项抉择，断言 HTML 不出现对应分支框，并带变异测试。

#### ② 历史条件分支（第四类，PR #4 新增）

与"玩家当场做选择"不同，还有一类分支由**玩家此前的存档状态**决定，剧本里是另一组指令：

| 指令族 | 判据 | 标签长相 |
|---|---|---|
| `IfUnlock` / `IfUnlockElse` / `IfUnlockEnd` | `StoryCondition` 表：读过哪些剧情、取得哪些 `StoryEvidence`、完成哪些成就、世界等级 | `若已阅读《终局 指尖的沙》、《终局 身旁的她》…` / `否则，若…` / `否则` |
| `IfTrue` / `EndIf` | `SetMajorChoice`/`SetPersonalityChoice` 当时选了哪项 | `若已选择《07 不同的许愿》中的「放弃思考」` |
| `CheckBE` / `CheckBECase` / `CheckBEEnd` | `CheckBE` 给出的终局已阅读比例区间（4 个档位） | `若第一章至第八章的终局已阅读比例为 0%` |

- **实现位置**：`pipeline/conditions.py`（`ConditionCatalog` 负责把 ID 翻成中文人话，`condition_markers` 负责把指令位置映射成 beat 标记，`reading_beats` 负责合并相邻等体分支）。
- **输出形态**：`> **[历史条件分支]**` + 若干条 `> - 若…`；多个分支正文完全相同时**只留一份正文、标签合并列出**；分支结束处 `> **[▲ 历史条件分支到此汇合]**`。站点侧额外渲染"跳到汇合"导航与 `condition-merge-N` 锚点。
- **为什么要合并**：第十章等"多周目"剧情里四个分支往往只差结尾一两句，不去重会让档案看起来是断裂的重复段落。
- **单测**：`tests/story/test_conditions.py` 断言 4 类真实剧本（`STm08_11` / `STm09_00_b` / `STm09_05_a` / `STm07_06_ba`）的标签文案、合并条数、md/HTML 锚点完整性；`test_diagnostics.py` 用假表逐个降级点断言"产出可读 + 恰好登记一条 + 不抛异常"。

#### ③ 校验

`.tmp_verify/validate_v2.py` 是与生成器实现相互独立的校验器（它用"最小包含行窗口"给台词归属，生成器用状态机），逐条验证：台词零增删、每条分支内容与 Lua 窗口一致，标记序列合法，并以植入错误反证校验器本身有效。

### 3.6 兜底与诊断策略（`pipeline/diagnostics.py`）

**为什么必须有这一节**：上游数据是社区解包镜像，随时会变；而 `scripts/automation/auto_sync.py` 以 `check=True` 跑 `build_story.py`，**生成器一抛异常，整条定时同步流水线就停**。所以管线的既定方针是"降级不崩"——但只崩改成不崩还不够：如果降级是静默的，上游加了新标记、改了表结构，只有等某个周目剧情在线上变成裸 id 才被发现。

**三条纪律**（改管线前必读，新增兜底时必守）：

1. **降级不崩**：解析/渲染路径遇到上游脏数据时产出**可读**结果，绝不向上抛异常。
2. **必登记**：每一次降级都要经过 `Diagnostics.add()/bump()/extend()` 登记进 `story_docs/_diagnostics.json`。只打 `logger`/`print` 的告警**不算**登记——log 给跑构建的人看，侧车给审 diff 的人看，两边都要有。
3. **分类必须进注册表**：`CATEGORIES`（`scripts/story/pipeline/diagnostics.py`）是唯一真源，键名/顺序/口径说明都在那里，`_diagnostics.json` 的 `note` 文案由它生成。**未注册的分类名会直接 `KeyError`**——这是故意的：把"加了兜底忘记写说明"变成开发期的显性失败，而不是运行期的静默通道。

**机制**：`build_story.py` 在 import 期建一个进程级 `DIAG = Diagnostics()`，所有降级通道都注入它——`markup`（强调配对计数、未知 `==XXX==` 标记、未知 `$nnnn` 词条）、`speakers`（预置表查不到的前缀/裸 id 兜底）、`passes`（抉择关闭指令的 group 无活跃帧）、`conditions`（历史条件的全部查表降级）、`build_story`（显示代号拼气泡剧本名的回退、四个构建期分类）。`write_diagnostics()` 只是把它序列化，不再手工拼盘。`add()` 按去重键去重（同一 key 只留一条，反复解析同一剧本不会让侧车膨胀），`bump()` 不给 key 时累加、给 key 时按 key 去重（如 `speaker_inline_names` 数的是去重 sid）。同一输入重建**字节稳定**。

**结构型缺参不登记**：`passes.slot()`/`fork_options()` 对缺参返回 `''`、`conditions.choice()` 对形状不符的指令参数直接退化，这类"上游指令形状变了"与"查表查不到"不是一回事，逐条登记只会把侧车噪声化。判据是**语义查找失败才登记**（ID 查得到不到、序号越界、档位越界、行缺主键）。

**站点侧只告警不登记**：`scripts/site/` 是纯消费方，不写 `story_docs/`。`render_html.py` 对条件组弹栈/锚点缺失做防御（交叉嵌套时按 group 退栈而非无条件 `pop()`，缺锚点时补兜底锚点），`build_site.py` 的分支角标未解析、`release_gate.py` 的失败开放，统一走 `pipeline.diagnostics.warn()` 记日志，不建站点侧侧车（避免新增要过 `release_gate.strip_locked_from_data()` 审查的发布物）。

**验收闸门**：`tests/story/validate_story.py` 里新增一组诊断侧车检查，断言提交的 `_diagnostics.json` 与 `CATEGORIES` 同构（键集合/形状/排序/去重）、`note` 与注册表重新生成的文案一致、并用子进程把 `build_story.py --out <tmp>` 重建后**逐字节**比对；带 6 个变异测试（多加/删分类、改坏 note、加重复条目、打乱排序、计数改负都必须被抓到）。`tests/story/test_diagnostics.py` 用假表逐个降级点断言"产出可读 + 恰好登记一条 + 不抛异常"；`tests/story/test_conditions.py` 有一个全量用例：`CFG` 目录下全部剧本跑完后 `condition_*` 必须一条都没触发。`STELLA_DIAG_REBUILD=0` 可跳过那次子进程重建（默认开）。
