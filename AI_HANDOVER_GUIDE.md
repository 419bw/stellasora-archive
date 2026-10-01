# 《星塔旅人》剧情文本逆向提取与知识库构建全流程技术交接手册
> **适用对象**：后续接手此项目的 AI 助手（如 Claude, GPT, Gemini）或开发人员  
> **文档定位**：全链路工程落地手册——从客户端底层数据解密、表格与 Lua AVG 剧本关联，到清洗规则、状态机判定与 Markdown 自动化生成。  
> **核心原则**：**100% 官方数据源高保真，0 幻觉、0 脑补、0 遗漏。**

---

## 目录
1. [数据源层：开源数据规范与镜像结构](#一数据源层开源数据规范与镜像结构)
   - [1.1 开源数据源仓库架构](#11-开源数据源仓库架构)
2. [数据结构与映射关系规范](#二数据结构与映射关系规范)
   - [2.1 主线关卡：Story.json 与 StoryChapter.json](#21-主线关卡storyjson-与-storychapterjson)
   - [2.2 剧本载体：Avg/_cn/Config/*.lua](#22-剧本载体avg_cnconfiglua)
   - [2.3 文本国际化表：zh_CN/Story.json](#23-文本国际化表zh_cnstoryjson)
3. [剧情解析核心状态机（关键业务逻辑）](#三剧情解析核心状态机关键业务逻辑)
   - [3.1 主角正名逻辑（为什么是“魔王”，为何原始数据是“塞拉”）](#31-主角正名逻辑为什么是魔王为何原始数据是塞拉)
   - [3.2 灰色对话框（内心独白）判定：TalkType 枚举](#32-灰色对话框内心独白判定talktype-枚举)
   - [3.3 玩家抉择项精准解析（严禁粗暴正则）](#33-玩家抉择项精准解析严禁粗暴正则)
   - [3.4 文本占位符与富文本标记清洗标准](#34-文本占位符与富文本标记清洗标准)
   - [3.5 抉择分支的台词归属与汇合标记](#35-抉择分支的台词归属与汇合标记)
4. [拓扑图构建算法（Mermaid DAG）](#四拓扑图构建算法mermaid-dag)
5. [完整提取与生成参考脚本（Python 独立实现）](#五完整提取与生成参考脚本python-独立实现)
6. [常见踩坑记录与 FAQ（交接备忘）](#六常见踩坑记录与-faq交接备忘)
7. [剧情管道 v2：build_story.py（主线/活动/战斗气泡）](#七-剧情管道-v2scriptsbuild_storypy当前唯一在推进的模块)
   - [7.2 带文本的指令清单](#72-带文本的指令清单全库-588-个_cnconfig-剧本实测)
   - [7.4 已确认的遗漏](#74-已确认的遗漏下一步的活别再重新发现一遍)
8. [修订记录](#八-修订记录2026-10-02)

---

## 一、 数据源层：开源数据规范与镜像结构

本项目为保证代码合规性与长效免维护，**不包含任何客户端二进制逆向破解或客户端解密代码与密钥**。数据源完全依托开源社区维护的标准化结构镜像仓库，直接从结构化数据中消费提取：

### 1.1 开源数据源仓库架构
本项目的提取管道消费以下两个公开仓库的数据结构：
1. **结构化数据表库**（如 `StellaSoraData`）：
   - `CN/bin/Story.json`：关卡列表
   - `CN/bin/StoryChapter.json`：章节列表
   - `CN/bin/ActivityStory.json`：活动剧情关卡
   - `CN/bin/DatingCharacterEvent.json`：旅人约会剧情
   - `CN/language/zh_CN/*.json`：全量官方中文字符串查找表
2. **反编译 Lua 剧本库**（如 `ss_lua`）：
   - `Lua/Game/UI/Avg/_cn/Config/*.lua`：所有剧本源码（如 `STm01_01.lua`, `STm02_01.lua`）
   - `Lua/Game/UI/Avg/_cn/Preset/AvgCharacter.lua`：说话人 ID 与姓名对应表
   - `Lua/Game/UI/Avg/AvgCmdParamOptionDefine.lua`：AVG 引擎参数枚举定义（包含 `TalkType`）

---

## 二、 数据结构与映射关系规范

在生成任何剧情文档前，必须理清这三张核心表之间的关系：

```text
StoryChapter.json (章节定义)
   └── Id (如 1, 2, 3...)
        └── Story.json (关卡节点定义)
             ├── Id (关卡主键, 如 204)
             ├── Index (国际化Key, 如 "Story.204.4" -> "01")
             ├── Title (国际化Key, 如 "Story.204.1" -> "公司与绿洲")
             ├── Desc (官方跳过概要Key, 如 "Story.204.2")
             ├── Aim (通关目标Key, 如 "Story.204.3")
             ├── IsBattle (是否战斗关: true / false)
             ├── ParentStoryId (前置依赖关卡数组, 如 ["STm02_01"])
             └── AvgLuaName (对应的剧本文件名, 如 "STm02_01")
                  └── Avg/_cn/Config/STm02_01.lua (具体的逐句台词执行流)
```

> **注意**：文本绝不能直接硬编码，除 `AvgLuaName` 里的台词在 Lua 中外，关卡标题、通关目标、默认描述都在 `CN/language/zh_CN/Story.json` 里通过 Key 索引。

---

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
在官方源码 [AvgCmdParamOptionDefine.lua](file:///j:/学习/项目/星塔机器人/scratch/ss_lua_repo/Lua/Game/UI/Avg/AvgCmdParamOptionDefine.lua#L138-L151) 中，`SetTalk` 传入的第一个参数代表 `TalkType`：
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
必须按以下顺序对台词字符串执行过滤：
```python
def clean_dialogue(text):
    if not text:
        return ""
    # 1. 清除富文本与颜色标签
    text = re.sub(r'</?size[^>]*>', '', text)
    text = re.sub(r'</?color[^>]*>', '', text)
    text = re.sub(r'<r=[^>]*>', '', text)
    text = re.sub(r'</r>', '', text)
    text = re.sub(r'<sprite[^>]*>', '', text)
    # 2. 玩家名称变量重写
    text = text.replace('==PLAYER_NAME==', '魔王')
    text = re.sub(r'==SEX\d*==', '你', text)
    # 3. 消除引擎排版控制字符 (==W== 为打字机停顿, ==RT== 为换行)
    text = re.sub(r'==[A-Z0-9_]+==', ' ', text)
    # 4. 压缩连续多余空格
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()
```

### 3.5 抉择分支的台词归属与汇合标记
- **引擎结构**：`Set*Choice(group, 选项行…)` 声明一次抉择；此后每个选项的专属剧本以 `Set*ChoiceJumpTo{group, k}` 开始，到 `Set*ChoiceRollover{group}` 结束；`Set*ChoiceEnd{group}` 关闭整个构造。各段剧本在 Lua 文件里**顺序平铺**，玩家一局只看到自己选中的那一段，所以直接平铺进 Markdown 会让互斥台词读成连续剧情。
- **group 才是主键**：`group` 就是 `Set*Choice` 的 param 第 0 项。分支必须按 `JumpTo{group, k}` 定位，**不能按行序配对**——存在一个抉择嵌在另一个抉择分支里的级联（`STm01_07.lua` 4 层，group 99/3/1/4，且 `Set*ChoiceEnd` 不满足 LIFO），因此解析用按 group 查的帧栈。
- **输出规则**：分支首条台词前插入 `> **[若选「选项标题」↓]**`；当帧栈清空（含嵌套的全部抉择一起关闭）时插入**一条**汇合标记 `> **[▲ …]**`，嵌套多于单层时写明层数与分支总数，并列出去往空分支的选项名。
- **空分支不打标记**：`JumpTo` 之后紧跟 `Rollover` 的选项（如 JumpTo 序列为 `(1,3)`、`(2,3)` 的抉择）没有专属台词，不产生 `若选` 标记，只在汇合处以「其中「X」没有专属台词，选中即跳到汇合点」说明。官方数据里同一选项组存在重名项（`同意 / 同意 / 拒绝`），故该说明按选项名去重。
- **短信抉择不打标记**：`SetPhoneMsgChoiceBegin` 的正文由 `SetPhoneMsg` 指令承载，而该指令当前未被提取，文档中没有可归属的台词，因此不标注分支。
- **校验**：`.tmp_verify/validate_v2.py` 是与生成器实现相互独立的校验器（它用"最小包含行窗口"给台词归属，生成器用状态机），逐条验证：台词零增删、每条分支内容与 Lua 窗口一致、标记序列合法，并以植入错误反证校验器本身有效。

---

## 四、 拓扑图构建算法（Mermaid DAG）

主线剧情包含大量的分支抉择与支线结局（如 Bad End、提前终局）。必须通过每关的 `ParentStoryId` 字段构建依赖树，避免把非线性剧情排成一条单链。

### 核心构建逻辑
```python
# 1. 建立 code -> 标题/节点的映射
code_to_node = {}
for s in chap_sections:
    s_code = s.get('StoryId')
    s_idx = clean_text(lang_story.get(s.get('Index', ''), ''))
    s_title = clean_text(lang_story.get(s.get('Title', ''), ''))
    code_to_node[s_code] = f"{s_idx}_{s_title}"

# 2. 遍历依赖关系生成连线
edges = []
for s in chap_sections:
    current_code = s.get('StoryId')
    current_name = code_to_node.get(current_code)
    parents = s.get('ParentStoryId', [])
    for p in parents:
        parent_name = code_to_node.get(p)
        if parent_name and current_name:
            edges.append(f"    {parent_name}[\"{parent_name}\"] --> {current_name}[\"{current_name}\"]")

# 3. 渲染为标准 Mermaid
mermaid_doc = "```mermaid\ngraph LR\n" + "\n".join(edges) + "\n```"
```

---

## 五、 完整提取与生成参考脚本（Python 独立实现）

已沉淀为全量生产脚本 [build_wiki_knowledge_base.py](file:///j:/学习/项目/星塔机器人/scratch/build_wiki_knowledge_base.py)。后续 AI 可直接查阅或复用其中的以下函数：
1. `parse_lua_avg(script_name)`：负责单文件剧本、SetIntro概要、SetTalk与抉择支解析。
2. `parse_choices(cmd, param_str)`：负责上述三大抉择项的清洗与解包。
3. `format_choice_block(d)`：负责生成标准优雅的 Markdown 引用块。
4. `generate_main_story()`：主线 10 章的遍历、DAG 构建与分小节落盘。
5. `generate_event_stories()`：11 个大型活动的逐小节生成。
6. `generate_characters()`：40 位角色的突破属性、专属约会全剧情整合。

---

---

---

## 六、 常见踩坑记录与 FAQ（交接备忘）
1. **Q：为什么有的关卡只有概要，没有“## 3. 详细剧情与逐句台词”？**  
   **A**：检查该关卡的 `s.get('IsBattle')`。如果是星塔纯战斗关卡（如 `BT01`、`BT02`），官方数据中本就没有配置 `AvgLuaName` 剧本，因此只展示战斗目标与跳过概要，绝不要胡编台词。
2. **Q：为什么某个小节生成出来的文件名带乱码？**  
   **A**：Windows 控制台默认 GBK 编码，运行 Python 时必须在最顶部执行：  
   `sys.stdout.reconfigure(encoding='utf-8')`，写入文件必须指定 `open(..., encoding='utf-8')`。
3. **Q：如何确保没有遗漏小节？**  
   **A**：全库主线共 10 章，总小节数严格等于 **604 个 Markdown 文件**。生成完毕后检查文件数量即可确认是否完整无损。
4. **Q：前端渲染时 Mermaid 图报错？**  
   **A**：Mermaid 节点标签内如果包含括号、连字符等字符，必须加英文双引号包裹（例如 `Node["01_序幕 (上)"]`），否则解析器会语法报错。

## 七、 剧情管道 v2：`scripts/build_story.py`（当前唯一在推进的模块）

`build_wiki.py` 已经塞进太多非剧情内容（数值、唱片、纹章、索引），剧情相关的后续改动一律走
`scripts/build_story.py`，它只做**主线章节 + 活动章节 + 战斗气泡**三件事，输出到 `story_docs/`。
它与 `build_wiki.py` 互不影响，可各自重跑。

### 7.1 换掉正则的原因
`build_wiki.py` 用 `param\s*=\s*\{([^}]*)\}` 抓参数，遇到**嵌套表**会在第一个 `}` 处截断，
因此 `SetChoiceBegin`（选项文本在嵌套表里，且 group 是 `"a_1"` 这类字符串）整族读不出来；
Lua 字符串里的 `\"`、`\t` 转义也没还原，直接漏进产物文本。新脚本实现了真正的 Lua 表解析器
（平衡括号 + 转义还原 + `nil/true/false`），顺带修掉了这两个问题。

### 7.2 带文本的指令清单（全库 588 个 `_cn/Config` 剧本实测）
| 指令 | 全库条数 | 说明 | 新脚本 |
|---|---|---|---|
| `SetTalk` | 48004 | 主线台词，param = `{TalkType, 说话人, 文本, …}` | ✅ |
| `SetMainRoleTalk` | 19382 | **没有文本**，是主角口型/表情驱动，紧跟下一条 SetTalk | 忽略（正确） |
| `SetTalkShake` | 1058 | **没有文本**，镜头震动 | 忽略（正确） |
| `SetPhoneMsg` | 10733 | 手机聊天正文，param 形状与 SetTalk 相同 | ✅ 主线+活动内 400 行已补出 |
| `SetBubble` | 399 | **战斗关卡内的头顶气泡**，只存在于 29 个 `BBm*.lua`；`SetGroupId` 分波次 | ✅ |
| `SetSceneHeading` | 472 | 场景卡，固定 5 槽：时刻/月/日/区域/地点（游戏历法：花月…鸣月） | ✅ |
| `SetChoiceBegin` | 522 | 第三种抉择，group 是字符串；实测 161/165 只有 1 个选项（玩家单句回应） | ✅ 单选项标「玩家回应」 |

### 7.3 战斗气泡的挂接规则
`BBm{Chapter 补零}_{Index 文案}.lua`。**必须用 `Chapter` 字段**：`Story.json` 的 `StoryId`
在 7~10 章是错位的（第十章的行仍写作 `BAm09_BT0x`）。27 个主线战斗关卡命中 22 个。

### 7.4 已确认的遗漏（下一步的活，别再重新发现一遍）
- **整族剧本没渲染**（`build_wiki.py` 只渲染了 268/588 个剧本）：
  - `CG_*` 152 个 —— 由 `Plot.json`(120，字段 `Char`+`AvgId`，即**角色个人剧情**，旧产物只有标题没有正文)、
    `NPCAffinityPlot.json`(8，星塔 NPC 好感线)、`MiningStory.json`(8)、`DiscIP.json`(24) 引用；
  - `PM_*` 63 个 —— `Chat.json`(498 行，字段 `AddressBookId`+`AVGId`) 的**手机聊天全篇**，含 822 条表情发送；
  - `STsp_*` 56 个 —— `StorySetSection.json` + `StorySetChapter.json`(18 章，官方名如「刀尖之寒，掌心之暖」) 的**支线故事集**；
  - `DP_*` 17 个 —— `AgentSpecialPerformance.json`(111 行，字段 `CharId`+`Avg`) 的约会/特殊演出；
  - `BBm00_01..06`、`BBm07_BT03` —— 无关卡引用（教学关或未上线）；`GD_gacha` 1 个。
- **流程控制指令未处理**：`IfTrue`/`IfUnlock`/`IfUnlockElse`/`IfUnlockEnd`（按解锁状态分支）、
  `JUMP_AVG_ID`（跳到另一个剧本的指定位置，说明存在跨剧本连续剧情）、
  `CheckBE`/`CheckBECase`/`CheckBEEnd`/`GetEvidence`（坏结局与"证据"判定，关系多结局 DAG）。
  相关表：`StoryCondition.json`(200)、`StoryEvidence.json`(40)、`StoryPersonality.json`、`StoryRolePersonality.json`。
- `NewCharIntro`(40) 角色首次登场卡（名字+头衔）未渲染。
- `CN/bubble/_cn/BubbleData.json`(4262 条) 是**语音→文案**表（按性别分列），能补战斗语音/角色语音的字幕文本，目前完全没用上。
- 第十章剧情只开放了部分线路：`STm09_0x_c/_d` 与 `BBm10_BT0x` 在包里本就不存在，不是解包缺陷；
  对账见 `story_docs/_battle_reconciliation.md`。

### 7.5 校验
`.tmp_verify/validate_story.py`（独立行扫描实现，不 import 新脚本）四条契约：
逐句对齐旧产物（268 篇，真实分歧 0）、气泡完整性（330 条 0 分歧）、
新增行来源计数（场景卡/气泡/短信/通用抉择 与 Lua 指令数逐一对等）、变异测试（改字/错阶段号/删气泡均被抓到）。

---

## 八、 修订记录（2026-10-02）
- 本文档 604 小节的说法过时：`Story.json` 196 行 + `ActivityStory.json` 124 行 = **320 个剧情小节**，
  旧产物共 510 个 md。以表为准。
