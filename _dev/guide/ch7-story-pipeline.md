> 《AI 技术交接手册》第 七 章正文分册；总索引与「按需索取」表见 [AI_HANDOVER_GUIDE.md](../AI_HANDOVER_GUIDE.md)。章节编号沿用原书，跨章引用（如「见 3.6」）按索引定位。

## 七、 剧情管道 v2：`scripts/build_story.py`（当前唯一在推进的模块）

`build_wiki.py` 已经塞进太多非剧情内容（数值、纹章、索引），剧情相关的后续改动一律走
`scripts/build_story.py`，它只管**剧情**：主线章节、活动章节、序章、战斗气泡、角色个人剧情、
星塔 NPC 好感剧情、唱片剧情、故事集支线，输出到 `story_docs/`。
它与 `build_wiki.py` 互不影响，可各自重跑。

### 7.0 数据加载：`context.py` 的 DataContext（Phase A 起）

上游表与共享服务的加载集中在 `scripts/story/context.py`，**编排器 `build_story.py` 不再在
import 期加载任何表**（改造前它在模块级无条件加载约 40 张 BIN/LANG 表并构造全部服务，
`import build_story` = 全量加载，单族运行/隔离测试不可能）：

- `DataContext(root, out=None)`：持 BIN/LANG/CFG/PRESET 路径与输出目录；`table(scope, name)`
  按 `(scope, name)` **懒加载 + 进程内缓存**（缺文件返回 `{}`）；`lang_table` 同门。
- 共享服务**构造一次、经 ctx 注入**，族模块不得自行构造：`text_compiler`
  （`markup.TextCompiler.load`，PRESET 词表 + BIN/LANG ContentWord）、`speaker_resolver`
  （PRESET AvgCharacter.lua）、`conditions`（`ConditionCatalog.load`）、`script_commands`
  （CFG 剧本解析缓存）、`extract_script`、`character_name`（BIN/LANG Character）、
  `story_lines`/`chapter_slugs`（章节目录与 URL slug 唯一来源）、`time_slots`、`diag`
  （进程级唯一 Diagnostics）。其表依赖在 `context.SHARED_NEEDS` 一次性声明并审计。
- 表工具纯函数 `lang_of`/`rows_of`/`field_lang` 同在 `context.py`；文件工具
  `write`/`safe_name` 在 `sink.py`（Phase B）。
- `ScopedDataContext(ctx, needs)`：Phase C 起编排器按族 `NEEDS` 白名单包装后传入
  `fam.build(scoped, sink)`；未声明表的解析调用立即 raise `UndeclaredTableError`
  （fail-loud：auto_sync 会停，修复动作是补一行 NEEDS）。透传面收为显式白名单
  `PASSTHROUGH`（读表服务如 `time_slots` 的表依赖并入 `SHARED_NEEDS`）；构建末端
  打烊对账：凡进过登记簿的表必须归属某声明面（族 NEEDS / `aggregate.needs()` /
  `SHARED_NEEDS`），账外读取即 raise。全量构建中对 declared-but-untouched 表输出
  **非阻塞 warning**。
- **目录扫描型族**（returnee/prologue/orphan_battles/chat）走 `os.listdir(ctx.cfg)`
  不读表，`NEEDS` 为空是**正确形态**，不是漏声明——门控覆盖率天然不是 100%。
- 测试取数同样经 ctx：`tests/story/test_conditions.py` 构造 `DataContext(ROOT)` 后调
  `ctx.extract_script`，不再 import 编排器。

### 7.1 换掉正则的原因
`build_wiki.py` 用 `param\s*=\s*\{([^}]*)\}` 抓参数，遇到**嵌套表**会在第一个 `}` 处截断，
因此 `SetChoiceBegin`（选项文本在嵌套表里，且 group 是 `"a_1"` 这类字符串）整族读不出来；
Lua 字符串里的 `\"`、`\t` 转义也没还原，直接漏进产物文本。新脚本实现了真正的 Lua 表解析器
（平衡括号 + 转义还原 + `nil/true/false`），顺带修掉了这两个问题。

### 7.2 带文本的指令清单（全库 `_cn/Config` 剧本实测）
| 指令 | 全库条数 | 说明 | 新脚本 |
|---|---|---|---|
| `SetTalk` | 48004 | 主线台词，param = `{通道号, 说话人, 文本, …}`；通道号是**显示通道**，见 7.8 | ✅ |
| `SetMainRoleTalk` | 19382 | **没有文本**，是主角口型/表情驱动，紧跟下一条 SetTalk | 忽略（正确） |
| `SetTalkShake` | 1058 | **没有文本**，镜头震动 | 忽略（正确） |
| `SetPhoneMsg` | 10733 | 手机聊天正文，param 形状与 SetTalk 相同 | ✅ 主线+活动内 400 行已补出；心链全篇见 `_chat/`（7.6） |
| `SetBubble` | 399 | **战斗关卡内的头顶气泡**，只存在于 29 个 `BBm*.lua`；`SetGroupId` 分波次 | ✅ |
| `SetSceneHeading` | 472 | 场景卡，固定 5 槽：时刻/月/日/区域/地点（游戏历法：花月…鸣月） | ✅ |
| `SetIntro` | 478 | 剧本头：`[0]`代号 `[1]`话数 `[2]`标题 **`[3]`官方跳过概要**（`==RT==` 是换行标记）；旧脚本用 `"([^"]*)"` 抠它，遇到文本里的 `\"` 会在半个字上截断（实测 1008 这节被截） | ✅ |
| `SetChoiceBegin` | 522 | 第三种抉择，group 是字符串；实测 161/165 只有 1 个选项（玩家单句回应） | ✅ 单选项标「玩家回应」 |

### 7.3 战斗气泡的挂接规则
`BB{关卡 StoryId 里的章号}_{Index 文案}.lua`——章号取自关卡自己的 `StoryId`（`BAm07_01` → `07`，
`BAm09_BT01` → `09`），**不是 `Story.Chapter`**。本文件此前写的是"必须用 `Chapter` 字段"，
方向正好反了：`Chapter` 才是错位的那个，因为它把特别篇记成第 7 章，而特别篇的关卡记作 `06x5`。
按表号拼名会把第七章的三场气泡整批挂到特别篇和它后面两章上（表现：特别篇《沙漠来客》里冒出夏花/小禾）。

判据不看文件名，只看人：把每个 BBm 的说话人集合拿去和各章正篇演员表比对——
`BBm07_*`（夏花/小禾/千都世）全员见于第七章（表 Id 8），特别篇正篇里一个都没有；
`BBm08_*`（含黎明近卫士兵）见于表 Id 9 及以后，第七章没有。
这条判据固化成了 `tests/story/validate_story.py` 的一组检查，植入变异可抓到本条 bug 的原样。

27 个主线战斗关卡命中 23 个；无剧本的 4 个 = 特别篇两场（期望名 `BBm06x5_BT01/02`，包里确实没有）
\+ 第九章 `BAm09_BT04/BT05`。BBm 一律**不写进任何配置表**（对全部 `CN/bin` 的字符串字段做过穷举匹配，
`BBm*` 零命中），文件名完全由客户端拼。因此剩下 6 个只能按代号存目：

- `BBm00_01..06`（63 条气泡，说话人只有鸢尾/琥珀/尘沙）—— 就是**注册流程打的那一关**。
  同场序章剧本 `STm00_01`《最初的起点》`SetIntro = {ep_mainline_001, "序", "最初的起点", 三位少女在沙漠星塔找到许愿箱…}`
  与它内容严格对上（许愿箱、沙漠、同一批人），`Story`/`StoryChapter` 都从第 1 章起列，所以表里查不到；
  先前推测的"教学关"不成立，`TutorialLevel`/`TutorialLevelFloor` 引的是 `TrainingLevels_01`。

### 7.4 已接入的剧本族

> **模块化落位（Phase B/C，2026-10-22）**：一族一文件 `scripts/story/families/<id>.py`，
> 统一契约 `build(ctx, sink) -> collections.Counter`；文件头声明 `NEEDS`（运行时门控白名单，
> 见 7.0）与 `MOUNTS`（(表, 字段) 挂载对，由 `aggregate.write_coverage` 自动汇总——
> 挂载审计不再有双份真相）。执行顺序唯一声明处是 `families/__init__.py` 的 `FAMILY_ORDER`
> （同时决定 `sections.json` 的 pages 追加序）；编排器 `build_story.py` 仅剩零特判循环，
> **加族 = 加一个族文件 + `FAMILY_ORDER` 一行**（dry-run 演练实证见设计文档 6.4）。
> 13 族：`main`/`events`/`characters`/`npc_bonds`/`discs`/`storysets`/`prologue`/
> `dispatch`/`anecdotes`/`returnee`/`soldier`/`chat`/`orphan_battles`。
| 族 | 文件数 | 挂载源（字段名实测，别再猜） | 产物目录 |
|---|---|---|---|
| 角色个人剧情 | 120 篇（129 行） | `Plot.json`：`AvgId`+`Char`+`UnlockAffinityLevel`(1/5/10)+`Name`/`Desc` 文案键 | `story_docs/characters/<角色号>_<姓名>/sections/` |
| 星塔 NPC 好感 | 8 | `NPCAffinityPlot.json`：`avgId`（小写 a）+`NPCId`，NPC 名在 `StarTowerNPC.json` | `story_docs/npc_bonds/` |
| 唱片剧情 | 24 | `DiscIP.json`：102 行里只有 24 行带 `AvgId`，标题 `StoryName`、散文 `StoryDesc` | `story_docs/discs/` |
| 故事集支线 | 56 节 / 18 章 | `StorySetSection.json`：`AVGId`，上级 `StorySetChapter`(1..18)+`StorySetTab`（1 是"全部"过滤器，不是栏目） | `story_docs/storysets/<栏目>/<章号>_<章名>/sections/` |
| 序章 | 2 | 无表引用，剧本代号 `STm00_*` | `story_docs/prologue/` |
| 委托结算演出 | 111 篇（= 111 段/行） | `AgentSpecialPerformance.json`：`Avg`(脚本)+`CharId`(上阵旅人)+`Weight`(50/150/300)+`AVGGroupId`(段号) | `story_docs/dispatch/<单人\|多人>/` |
| 逸闻笔记 | 一人一页 | **表驱动，无剧本**：`StarTowerBookEventReward.json`：`Name`/`Source`/`Story` 文案键 + `Type`(2=星塔 NPC，其余=旅人)+`NPCId`+`Sort`；`IsBanned` 行过滤掉 | `story_docs/anecdotes/{char,npc}/` |
| 回归剧情 | `ActivityReturnee.AVG` 点名的剧本（现 1 篇） | `ActivityReturnee.json`：`AVG` 字段直接点名剧本（Id 101004），Story/ActivityStory 均无行；标题走官方 `UIText.MainView_Reengagement`（归星漫途），取不到回退「回归剧情」 | `story_docs/returnee/sections/` |
| 尖兵陷阵 | 开场 1 剧本 + 终局每表行一页 | 开场 `ST_sys_soldier_intro` 无表引用（自走棋模式入口直接调用）；终局**表驱动**：`SoldierEndingPlan.json`：`EndingTitle`/`Desc` 文案键 + `EndingCondition1`（表内无条件文案，原样显示） | `story_docs/soldier/sections/`（md 全在此；终局页 URL 走 `soldier/endings/`） |

要点：
- `Plot.json` 有 9 行是"换皮角色"复用同一剧本（薇洛（盛夏）160 与魔侍巨像 997/998/999 指向同一
  `CG_160_0x`），**按剧本代号去重**、只有带标题文案的那一行出页面，其余记在该页的「复用此剧本的档案」里。
- 唱片的 `StoryDesc` 是一篇 600–1650 字的**散文**，与 AVG 剧本是两份文本（实测剧本 109 句里没有任何一句
  出自该散文），所以单独作为第 4 节存目，不能混进逐句台词。
- 栏目 `StorySetTab` 的"异界秘辛"目前没有任何已上线章节（`IsShow` 为空），产物里不出现该目录是正确的。
- `MiningStory.json`(8 行) 的 `AvgId` 复用了 103/107/108/110 四个角色个人剧情的前两篇，已随角色族渲染。
- 委托结算演出按**一页 = 一段结算演出**收录（111 篇 = `AgentSpecialPerformance` 的 111 行/段），
  按「该段出场的旅人 / 组合」归类：单人段归到对应旅人名下（每位 2 变体各一页），双人/三人段按组合成页。
  一份 `DP_*` 脚本按 `SetGroupId` 被几十段共用（如 `DP_single01` 含 40 段），一页只含其中一段。
  因此 dispatch 是**分段挂载**、自外于 F/E/M 的「一页 == 整份剧本」模型——做法与约定：
  - md 放 `dispatch/` 下、**不进各族的 sections/ 子目录**，页首写 `- **结算演出**：\`<脚本>\`（第 \`<段号>\` 段）`
    而**不写** `AVG 剧本**：` 那一行。这样 validate_story 的逐句/概要/气泡类检查都不会把它当整剧本页收编。
  - 新增契约 **N（`validate_story.py` 委托分段保真）**：独立扫 Lua、按 `SetGroupId` 段号裁出该段台词序列，
    与页面逐句对账（变异"改一句台词"可被抓到）。F 的覆盖对账改为
    `去重整本剧本数 + 委托分段涉及剧本数`，与 `_coverage.md` 声明一致。
  - 想换回整脚本一页、或将来别的族也分段共用，直接复用 N 这套"按 `(脚本, 段号)` 切段"即可。
- **逸闻笔记与尖兵陷阵终局是「表驱动页」**：内容来自配置表行而非 AVG 剧本，登记时 `stems=[]`，
  正文直接取语言表原文（只做 `\r\n`→`\n` 归一并按行去空，**不过 `lang_of`/`clean_text`**——
  `clean_text` 会把段落换行压成空格）。识别判据有两代：逸闻笔记按 `family == 'anecdotes'` 认
  （一页多则，`notes` 字段驱动索引页锚点，导航分组用 `group.kind` 而非 `group.id`）；
  尖兵终局引入通用的 `table_refs: ['SoldierEndingPlan#<Id>']` 标记（一页一则），
  `validate_site` 据此逐条核对表行存在、索引页副题显示「终局文本 · N 字」。
  **纪律**：`table_refs` 的现有消费端把「终局」语义写死（副题文案硬编码、校验只认 `SoldierEndingPlan`）；
  第三个表驱动族出现时，先把判据收编进 `FAMILIES`/`FAMILY_META` 注册表再接入，**不要再加第三处硬判**。
- 回归活动的挂载方式与序章 `STm00_*` 同款——流程直接调用、关卡表内无行；
  `write_coverage()` 的挂载审计已加 `('ActivityReturnee', 'AVG')`，剧本前缀族 `ST_*` 就此清零。

### 7.5 流程控制指令：历史条件分支（已实现）

剧本里有三族指令**不在运行时由玩家操作触发**，而是读玩家存档的既有状态来分流剧情。它们在
2026-10-09 之前被整段丢弃，导致第十章等"多周目"剧情在档案里看起来是断裂的重复段落。

| 指令族 | 参数形状 | 判据来源 |
|---|---|---|
| `IfUnlock{id}` / `IfUnlockElse{id}` / `IfUnlockEnd{id}` | `id` 是 `StoryCondition.ConditionId` | `StoryCondition` 行：`StoryId_a`（全部读过）、`StoryId_b`（任一读过）、`EvIds_a`（全部取得）/`EvIds_b`（任一取得）、`AchieveIds`、`PlayerWorldLevel` |
| `IfTrue{group,kind,stem,choice_group,rule}` / `EndIf{group}` | 5 元组；`kind` 0=重大抉择 / 1=性格抉择；`rule` 形如 `A`、`A+B`、`A|C` | 回到 `stem` 剧本里那条 `SetMajorChoice`/`SetPersonalityChoice` 的选项表，`A`/`B`/`C` 是选项下标，`+` 是与，`|` 是或，数字后缀（`A2`）是"本轮至少 N 次" |
| `CheckBE{id,start,end,threshold}` / `CheckBECase{id,case}` / `CheckBEEnd{id}` | `case` ∈ 1..4 | 按 `start`..`end` 章的终局已阅读比例分 4 档：0% / (0, threshold] / (threshold, 100%) / 100% |

**实现分层**（`pipeline/conditions.py`，301 行）：
- `ConditionCatalog` —— 查表把 ID 翻成中文人话（剧情名走 `Story.Index`+`Title` 文案，选项名回到源剧本的选项表，比例档位按 `CheckBE` 的 range 生成）。`load()` 读 5 张表 + 4 张文案表。
- `condition_markers(commands, catalog)` —— 按 `(族, group)` 聚簇指令，产出 `{'k': 'condition_branch'|'condition_end', 'group', 'labels'}` 标记，挂在原指令位置上。
- `reading_beats(beats)` —— md / HTML / 侧车三个后端**共用**的投影：相邻且正文完全相同的分支合并成一条标记 + 多行标签。

**三个容易踩的点**：
1. `IfUnlock` 的 `StoryId_b` 是"任一"不是"全部"，`EvIds_a`/`EvIds_b` 同理，连接词分别是 `、` 和 `，或`——混用会让标签意思反了。
2. `CheckBECase` 的档位标签必须由组内 `CheckBE` 的 range 生成，同组出现不同 range 会张冠李戴（已登记 `condition_be_case_unknown`）。
3. `GetEvidence` 要反查"哪个剧本、哪个选项给的这个证据"，是全表扫描，`ConditionCatalog.evidence_sources` 用懒加载缓存，只跑一次。

**查表失败的兜底**见 3.6：所有 ID 查不到都降级成可读标签并登记，不会让 build 崩。

### 7.6 剩余遗漏（下一步的活，别再重新发现一遍）
- `PM_*` 63 个 —— **心链**（游戏内手机聊天功能的官方名，见 `OpenFunc.Phone.1` = 心链、
  `UIText.Guide_43_1.1` = "「心链」可以和结识的旅人发送信息，是手机最重要的功能"）。
  `Chat.json`(498 行) 的**心链聊天全篇**：10174 条短信（其中 820 条是发送表情/图片）、
  340 组回复抉择；40 个角色，每文件分 9 段（另 23 个文件只有 6 段），`TriggerType` 1/2、
  `TriggerCond` 用 `[103]`/`[103,5]` 这类参数（后者是角色+好感等级），属好感内容。
  **已接入**（2026-10-10，`build_story.build_chat()` + `scripts/story/phone_chat.py`）：
  产物 `story_docs/_chat/`，一页 = 一个 PM 剧本、按 `SetGroupId` 切段一节，**不进站点**——
  目录名本身带 `_` 前缀（G2 只收编非 `_` 目录里的 md，且**必须扁平、不能再建子目录**，
  否则 `_chat/103_琥珀/PM10301.md` 会被当成站点页收编、撞"sections.json 没登记"）、
  不建 `sections/` 子目录（A/C 按它收编）、信息行写 `心链剧本**：` 而非 `AVG 剧本**：`
  （F 按该标签认"整本页"，dispatch 族同款规避），也不 `record_page()`，故不进
  `sections.json`/`search.json`/`_beats`、不生成 HTML、不计入 `_coverage.md` 的已渲染数
  （改了就要同步动 validate_story 的 F 覆盖对账）。
  要点：
  - **分支归属自研**：`SetPhoneMsgChoiceJumpTo{组, 下标}` 之后到同组下一个 JumpTo/End 之前
    的消息 = 该选项的专属台词，渲染成 `> **[若选「…」↓]**` … `> **[▲ 分支汇合]**`（文案与
    render_md 对齐）。**不改 passes.py**：它对 phone 方言"平铺不推帧"是既定设计，
    `STev_03_01` 等已渲染活动剧照此输出，改推帧会撞 `docs/` 冻结基线的字节锁。
  - **脚本段是权威**：537 个 `SetGroupId` 段 vs Chat 表 498 行，多出的 39 个 `08` 段是上游
    缺行（含 783 条真实消息，如 PM10301 的生日聊天），照常渲染并标注；`PM13501` 的 `08`
    段在剧本中为空，跳过。
  - **表情/图片按消息类型判**（`AllEnum.PhoneMsgType` 3/4）：杏子（PM12301）两句 type 0 的
    口头禅 "mumu"/"mumumu" 用"渲染文本是否资源名"的粗规则会被误判成表情——本手册此前记的
    "822 条发送表情"即是那个粗规则的计数，真实值 820（437 + 383，`pic_*` 图片也在内）。
  - **已知上游怪象白名单**（`story_docs/_chat/_diagnostics.json`，其余类别必须为 0）：
    39 个 `08` 段无表行；2 处 Begin 无 End（PM11701 第 04 段、PM14101 第 05 段）；
    PM14101 第 05 段一个越界 JumpTo（同段两个同组 Begin，前一个只声明 1 个选项）；
    PM13501 的空 `08` 段。
- `DP_*` 17 个 —— `AgentSpecialPerformance.json`(111 行) 按上阵人数(1/2/3 人)与权重(50/150/300)随机选
  一段**委托玩法结算短演出**，共 321 句台词（平均 19 句/文件），`SetGroupId` 用的就是委托 Plot id（10301…）。
  委托单本身在 `Agent.json`(36 行，含 `Consignor` 委托人)。**已接入**：family=`dispatch`（见 7.4），
  `/dispatch/` 板块，**一页 = 一段、按出场旅人/组合归类**（共 111 篇），由 validate_story 契约 N 做分段保真。
- 尖兵陷阵**局内随机事件**五表（`SoldierStoryType` / `SoldierOptionType` / `SoldierStoryPersonalityOption` /
  `SoldierStoryResult` / `SoldierEventPersonalityStory`）—— 3 选 1、性格轴检定与奖励结算为主的玩法内容，
  结果文案大量缺失（语言表 114 条去重后仅 7 条独立文本），2026-10-21 议定**不纳入**；
  开场与终局已接入（见 7.4）。想再接入的先复核这个结论，别重新发现一遍。
- `GD_gacha` 1 个 —— 抽卡时的 4 句小车演出，无表引用，建议不做。
- **流程控制指令：`IfTrue`/`IfUnlock`/`IfUnlockElse`/`IfUnlockEnd`/`CheckBE`/`CheckBECase`/`CheckBEEnd` 已实现**（2026-10-09），见 7.5。相关表：`StoryCondition.json`(200)、`StoryEvidence.json`(40)、`StoryPersonality.json`、`StoryRolePersonality.json`。
- `JUMP_AVG_ID`（跳到另一个剧本的指定位置，说明存在跨剧本连续剧情）仍未处理。
- `NewCharIntro`(40) 角色首次登场卡（名字+头衔）未渲染。
- `CN/bubble/_cn/BubbleData.json`(4262 条) 是**语音→文案**表（按性别分列），能补战斗语音/角色语音的字幕文本，目前完全没用上。
- 最新一章（表 Id 10，游戏内第九章《遥远的塔》）只开放了部分线路：`STm09_0x_c/_d` 与
  `BBm09_BT04/BT05` 在包里本就不存在，不是解包缺陷；对账见 `story_docs/_battle_reconciliation.md`。
  特别篇的两场战斗（`BAm06x5_01/02`）同样无气泡剧本，但那是**包里就没有**，不是没开放。

### 7.7 产物目录与覆盖对账
```text
story_docs/
├── main/chapter_NN_<章名>/sections/            主线关卡
├── events/activity_NN_<活动名>/sections/        活动关卡
├── characters/<角色号>_<姓名>/sections/         角色个人剧情（好感 1/5/10 三篇）
├── npc_bonds/<NPC号>_<姓名>/sections/            星塔 NPC 好感
├── discs/<唱片 ID>_<唱片名>.md                   唱片剧情（含散文附文）
├── storysets/<栏目>/<章号>_<章名>/sections/      故事集
├── prologue/sections/                            序章
├── battles_unmounted/                            无关卡引用的战斗气泡
├── dispatch/<solo|multi>/<标题>_<演出ID>.md      委托结算演出（一页=一段，按出场旅人/组合归类；目录用英文避免 URL 中文编码）
├── anecdotes/<char|npc>/                         逸闻笔记（表驱动：StarTowerBookEventReward，一人一页；扁平，无 sections/ 子目录）
├── returnee/sections/                            回归剧情《归星漫途》（ActivityReturnee.AVG 直接点名剧本）
├── soldier/sections/                             尖兵陷阵（开场剧本 + 终局表驱动页的 md 同放此目录；终局页 URL 走 soldier/endings/）
├── _chat/PM<编号>.md                          心链全篇（build_chat 生成；**必须扁平**，`_` 前缀 = 非站点页，不进站点）
├── _data/                                       结构化侧车（meta 带权威计数）
├── _beats/                                      PageDoc IR 侧车（md/HTML 双后端共同上游）
├── _diagnostics.json                            兜底登记（口径见 3.6）
├── _battle_reconciliation.md   战斗气泡挂接对账
└── _coverage.md                全部剧本的逐族覆盖表 + 未渲染清单（每次构建自动重算）
```
各族篇数、已渲染/未渲染数**以 `_coverage.md` 和 `sections.json` 的 `meta.pages` 为准**，
由 `write_coverage()` 生成，不手工维护。未渲染的大头是 `PM_*`（心链已提取至 `_chat/`，
不进站点故不计入已渲染，见 7.6）与 `GD_gacha`；`DP_*` 已接入 `dispatch` 板块，不再计未渲染。

### 7.8 校验
`tests/story/validate_story.py`（独立行扫描实现，不 import 新脚本）契约见 8.3 契约总表。
各契约的具体篇数/条数以校验器自己的输出为准，此处只讲**判据**：
- `A2` 跳过概要：旧产物 == 新产物 == 剧本 `SetIntro[3]`（旧脚本 `"([^"]*)"` 的截断缺陷保留 1 处证据）
- `A`  逐句台词序列：旧产物 == 新产物
- `B`  战斗气泡逐阶段完整性
- `C`  新增行来源计数与 Lua 指令数对等（场景卡/气泡/短信/通用抉择）
- `D`/`E`/`F` 变异测试 + 新族挂载审计 + **全树逐页**（台词序列、气泡+阶段号、跳过概要三项各自对齐剧本原文；
  植入"改一句台词/改阶段号/改概要"均被抓到）
- `K`  **气泡剧本挂得对不对**：不看文件名，只看人——挂载的 BBm 剧本里每个说话人都必须在该关卡
  `Chapter` 所指那一章的正篇演员表里出现过。加这条是因为 F 只验证"页面内容 ==
  声明的那份剧本"，声明本身错了它看不见；植入"把 `BBm07_BT01` 挂回特别篇"被抓到。
- `N`  **委托结算分段保真**（dispatch 专场）：一份 `DP_*` 脚本按 `SetGroupId` 被几十段共用，
  一个 dispatch 页只对应 `(脚本, AVGGroupId)` 一段。N 独立扫 Lua、按段号裁出该段台词序列，与页面逐句对账。
  dispatch 页不写 `AVG 剧本**：` 行，故那些逐句/概要/气泡类检查都不收编它们。

尺子自己的坑（已踩）：`unescape_lua` 用 `s.strip('"')` 会把 `"……\""` 结尾的反斜杠留成野字符，
必须只剥首尾各一个引号再单遍反转义，否则会假报 CG_126_03 一处分歧。

接**新家族/新板块**的登记点，改一处漏一处会红（Phase B/D 模块化后已从"改编排器+改 coverage+改站点共享文件"收敛为）：
① `scripts/story/families/<id>.py` 新族文件 + `families/__init__.py` 的 `FAMILY_ORDER` 加一行；
② `scripts/site/registry.py` 的 `FAMILIES` 加一行（URL slug 有例外才动 `slug_of`，否则恒等回退）+ 新建 `scripts/site/families/<id>/style.css`（选择器带本族作用域，lint 把守）；
③ `tests/story/validate_site.py` 契约 `I` 的 expected slug 元组**也要加一行**——它是**故意的双份真相**：校验器不读注册表（独立真值，防注册表写错校验也跟着错），所以加族的最后一手是同步它。
`release_gate` 对未知家族 fail-open，非开放家族不用动它。

### 7.9 台词的显示通道（查清了，决定不显示）
`SetTalk` 的第一个参数不是文本属性，是**用什么样式说**。通道名在客户端自己的表里：
`AvgCmdParamOptionDefine.lua` 的 `TalkType`，**0 起算**；索引基准由 `Avg_4_TalkCtrl.lua` 里
`SetTalk` 的分支链独立印证（`nType == 8` → `imgContentBg_Center`＝居中字幕、
`9` → `canvasGroup_CGTalk`＝CG对话、`1/2` → `canvasGroup_SayThink` 且 2 走"想"分支）。

| 通道 | 官方名 | 全库句数 | 产物里 |
|---|---|---|---|
| 0 | 角色说 | 33282 | 不标 |
| 1 | 主角说 | 8216 | 不标 |
| 2 | 主角想 | 2261 | 标「思考」（这条早于 7.8，保留） |
| 3 | 底部字幕 | 1043 | 不标 |
| 4 / 5 | 单人左 / 单人右 | 2 / 1 | 不标 |
| 6 / 7 | 双人左 / 双人右 | 49 / 49 | 只出现在委托结算 `DP_*`（已接 `dispatch/`）里 |
| 8 | 居中字幕 | 777 | 不标 |
| 9 | CG对话 | 1796 | 不标 |
| 10 | 全屏字幕 | 45 | 不标 |
| 11 | L2D对话 | 472 | 不标 |

`SetPhoneMsg` 共用参数形状但通道枚举不通用，产物一律标「短信」。

**曾经全量标过一版，又撤了**（`efcd711` 加、随后还原）。两个原因：
① 有人问"CG对话 是不是回忆"，实测**不能这么判**——1796 句里 73% 的前一个 `SetBg` 是 `story_*` 插画，
其余是 `BG_Black`、`circle_light`；第四章《旅人往事》里夏花那两句确实是回忆段落，
但第一章《梦醒时分》也有 53 句 `CG对话`，那是开场 CG。全库 68 种指令里没有任何以
memory / flash / back 命名的指令，"回忆"这个语义不在数据里，标出来就是替游戏下判断。
② 就算按官方名老老实实标，4136 句挂上通道标签，读者觉得吵。
所以：**通道号留在剧本里，产物不显示**。要重新捡起来的话，先想清楚这两条。

别和**关卡级**的 `Story.MemoryType`（1＝追忆、2＝真·终局）混谈，那个已经用在节点图的卡片状态上了。
