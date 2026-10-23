> 《AI 技术交接手册》第 八 章正文分册；总索引与「按需索取」表见 [AI_HANDOVER_GUIDE.md](../AI_HANDOVER_GUIDE.md)。章节编号沿用原书，跨章引用（如「见 3.6」）按索引定位。

## 八、 站点与数据契约（`build_site.py` / `graph_layout.py` / `tests/story/`）

### 8.0 站点结构（Phase D/E，2026-10-22 模块化后）

`scripts/site/` 从"单文件堆叠"拆为注册表 + 公共组件 + 族片段三层，`build_site.py` 只做驱动：

```
scripts/site/
├── registry.py          族注册表：FAMILIES（族序=导航/bento 展示序）、FAMILY_META、
│                         slug_of（例外 slug 查表，其余恒等于族 id）、STATE_LABEL
├── theme/               公共页型与组件（一族不独占的全部在此）
│   ├── layout.py        页面骨架 + helper（depth_of/rel/full_title/node_state_*）
│   ├── gate.py          未开放门控 UI（locked_*）
│   ├── home.py          首页（bento 总汇总）
│   ├── index.py         默认二级索引（main 被覆盖，见下）
│   ├── reading.py       对话展示牌板（全族共用）
│   ├── battle.py        战斗档案页（main+events 双消费）
│   ├── graph.py         拓扑图共用骨架：连线层/卡片层/列锚点/map 容器
│   └── tokens.css base.css graph_base.css   （E1 起 CSS 切片）
├── families/<id>/       族级片段：style.css（accent+条纹，选择器必须带本族作用域，
│                         lint 把守）+ 可选 templates.py（main 的章图组装与索引覆盖
│                         INDEX_OVERRIDE、events 的活动图组装与 BRANCHING_ACTS 声明）
├── assemble.py          (family, kind) 模板分发注册表 render() + CSS 超级拼接
│                         assemble_css()（块级 manifest：tokens→base→graph_base→
│                         FAMILY_ORDER；片段内 @@ 为块分隔，拼接时剔除）
├── build_site.py        驱动：侧车 → release_gate → render() 分发 → 落盘（零族特判）
├── site_js.py / render_html.py / graph_layout.py / release_gate.py（后者住 scripts/story/）
```

几条落地纪律（改动前必读）：

- **加族只动两处注册表各一行**：`scripts/story/families/__init__.py` 的 `FAMILY_ORDER`
  与 `scripts/site/registry.py` 的 `FAMILIES`，外加两个族文件（dry-run 演练实证，
  共享层 diff 为零，见设计文档 6.4）。
- **族间差异是参数不是结构**：切换条/lede/`data-family` 走组件入参；结构差异（特别篇平铺）
  留族组装层。拓扑图两页型共用 `theme/graph.py`，防两处规则漂移。
- **CSS 只改片段不改产物**：`site/assets/tokens.css` 是拼接生成的（首部有 manifest 注释），
  手改会在下次构建被覆盖；族样式必须带 `[data-family="<id|slug>"]`/`.fam-<id>` 作用域，
  theme/ 片段不得定义族令牌具体值（两条都有 pytest 把守）。
- `build_site.py` 的 `sys.path` 顺序是 `scripts/site` 在前、`scripts/story` 在后——
  两侧各有一个 `families` 包，顺序反了会互相掩蔽。

### 8.1 数据流
`build_story.py` 在写 md 的同一次解析里顺手记录结构化侧车（`record_page` / `record_node`），
`write_data()` 落到 `story_docs/_data/`：

| 文件 | 内容 | 谁在用 |
|---|---|---|
| `chapters.json` | 每章一个节点数组：`code/title/kind/parents/state/time/col/lane/x/y/page` + 章级 `geometry{columns,width,height,step_x,step_y,edges,card}` 与官方 `time_slots`；章级另有 `special`（`StoryChapter.Type==2`）、`story_line{id,title,subtitle,sort_index}`、`slug`（站点 URL 目录），`meta.story_lines` 是 `StoryLine.json` 的目录 | 主线节点图、主线索引的时间线分组 |
| `sections.json` | 每页一条：`family/group/code/title/page/page_md/stems/recap/speakers/counts/preview` | 索引页、检索、覆盖统计 |
| `search.json` → `site/data/search.js` | 每条 `{id,family,code,title,group,page,speakers,hay}`；`hay` = 标题 + 概要 + **全量 talk/bubble/choice 台词**（男主变体仅在与默认文本不同时才收录） | 前端检索：页面不再内嵌该 script，首次与搜索框交互时动态注入加载（内嵌成 js 而非 json 是为了 `file://` 下动态注入不受 CORS 限制） |
| `personality.json` | 三轴定义与颜色 | 术语卡（**不**用于给选项上色，见 8.4） |

> 📏 **规模数字一律不写死**。每份侧车的 `meta` 里都带权威计数（`chapters.meta = {chapters, nodes,
> pages, source, edge_field, story_lines}`、`sections.meta = {chapters, nodes, pages, families}`、
> `search.meta = {pages}`）。要报数就读 `meta` 或看两个校验器结尾的汇总，**不要**在文档里抄一份——
> 抄了就会过时（本文档历史上已经因此错过一批，页数从 507 一路漂到 626）。
> ```bash
> python -c "import json;print(json.load(open('story_docs/_data/sections.json',encoding='utf-8'))['meta'])"
> ```

坐标进数据不进代码：`graph_layout.layout()` 由 `build_story.py` 调用，所以布局在**建站之前**就能被校验。

**章节目录与时间线的唯一解析处是 `scripts/story/chapter_path.py`**（叶子模块，不 import pipeline）：
`build_story` / `build_site` / `release_gate` / `validate_site` 四个消费端共用它，各自初始化时调一次
`build_slug_map()` 拿 `{章 Id: slug}`。三个"编号"不要混：`StoryChapter.Id`（表主键，用于 `chsp{Id}`）、
`StoryChapter.Index`（游戏内显示编号 `'01'`–`'09'`，特别篇没有，用于 `ch{Index}`）、`Story.StoryId`
（关卡 Id，与章编号无关）。`Id` 与 `Index` 错开一位（特别篇占 Id=7 但无显示编号），所以 `ch07`
（第八章）与 `chsp7`（特别篇）并存不冲突。slug 撞车时 `build_slug_map` 直接 `raise`——
旧实现是"后写的章覆盖先写的章"这种静默故障。

建站侧在消费上面任何一份侧车**之前**，先过 `release_gate`（见 8.5）：官方还没到开放时间的组，
只出「未开放」占位与提示页，`pages` / `chapters` / 活动战斗页、以及 copytree 到 `site/data/` 的
三份侧车都会剔除对应记录。**不要让任何新消费点绕过这一层。**

### 8.2 主线节点图的地面真相（实测，别再重新发现）
- 边只有一个来源：`Story.ParentStoryId`（前驱 `StoryId` 字符串数组）。节点数 = `chapters.meta.nodes`，
  **零跨章引用、零悬空引用**，除特别篇外每章根唯一。分叉度分布读 `chapters.json` 自己数
  （`len(node['parents'])`），**别信任何文档里写的分布**——上游加关卡就会变。
- 卡面编号 = `Story.Index` 的文案（`Story.<id>.4`）：`幕间 / 幕间 上 / 01 / 02A / BT01 / 终局 / 追忆 / 真·终局 / 尾声`。
- 状态判定：`IsBattle` 战斗、`IsBranch` 终局、`IsLast` 本章终幕、`MemoryType` 1 追忆 / 2 真·终局、
  `code` 以「幕间/尾声」开头者单独标。**无剧本 = 表里有行但包里找不到 `.lua`**，具体行数读
  `sections.json` 里 `kind` 为 `no_script` 的节点，或看 `_coverage.md` 的未渲染清单。站点据此分两种措辞：
  剧情行标「未开放」，战斗行标「无对白剧本」——战斗本身可能早就开放了，只是包里没它的气泡剧本，
  统一说"未开放"会误导读者。
- 表 `StoryChapter.Id` 与游戏内章号差一章（Id 7 = 特别篇、Id 8 = 第七章）。md 目录名仍用表 Id（`chapter_08_星之竞拍`），
  站点 URL 与页面标题用 `Index/Name`，**不要**为了对齐去改历史目录名（改过一次，代价是全文链接失效）。
- 时间条：官方按**列**给一条 `StoryChapterTimeStamp.<章 Id*100+列序>`，列序归属写在 UI 预制体里，解包表没有。
  所以节点上的时间取该关剧本自己的首个 `SetSceneHeading`（`时刻/月/日`），有多少节点带 `time` 字段
  读 `chapters.json` 自己数。拿"时刻相同"去反查列号**不成立**（实测会把 `猎月 13日 18:00` 误配成别列的
  `刻木鸟日 18:00`），且游戏历法的"日名"与剧本里的"编号日"不同源（13 日在猎月是吠啸枭日、在别处是刻木鸟日）。
- 特别篇全无 `ParentStoryId`：官方没记录连线，页面按编号顺序列出并注明，不画假线。
- **特别篇判定读 `StoryChapter.Type == 2`**（侧车 `special` 字段），**不要**再用"本章一个父引用都没有"
  去倒推——那正是把"上游漏填 ParentStoryId 的普通章"误判成特别篇的通道。校验器 G 组把三条锁成
  双向充要：`special ⇔ edge_source=='none' ⇔ Index is None`。特别篇在游戏里只有线性清单、没有拓扑图、
  不带章节号，所以"特别篇却有边/却有编号"一律按构建失败处理。
- **时间线是正交的另一个维度**，读 `StoryChapter.StoryLineId` + `StoryLine.json`（标题/SortIndex/图标）。
  第 7 章是特别篇但属于时间线 1，第 11 章是特别篇且属于时间线 2——"特别篇"不等于"另一条线"。
  站点主线索引左侧的滚轮按 `sort_index` 升序（与游戏内左侧入口一致），默认激活章节数最多的那条线；
  章图页内的 `chapsel` 切换条同样按时间线分段。上游加线只改数据，不改代码。

### 8.3 契约总表（`tests/story/`，两份都不 import 生成器）

`validate_story.py`（story_docs 侧）与 `validate_site.py`（site 侧）是两套独立的契约集，
**都不 import 生成器**，只读产物 + 独立重解上游，且每个检查组都带**植入变异测试**
（故意改坏产物，同一套断言必须抓到；只看"正对照 PASS"不算数）。

**`validate_story.py`** 覆盖：战斗气泡逐阶段完整性、气泡剧本的挂载语义（说话人必须出自该章演员表）、
增量行来源计数与指令数对等、逐页台词序列对齐剧本原文（含跳过概要 vs `SetIntro[3]`）、
各族挂载审计、注音保真、委托结算分段、单选项抉择不画分支框、诊断侧车的 schema / note / 重建漂移、
逸闻笔记 1:1 对齐源表。

> **历史对照已退役**（2026-10-20）：原 A / A2 两组拿 `docs/`（旧世代生成器的冻结快照）与
> `story_docs/` 逐句 / 逐概要对比，配一份手工维护的 `A_WHITELIST`。退役原因两条：
> A2 的绝对真值部分与 E 组完全重复；A 的前提是"`docs/` 与上游表覆盖同一批关卡"，
> 上游每加一章就失配一次（第 11 章整章不在 `docs/` 里 → 表推导 34 ≠ 快照推导 21），
> 只能不断补白名单。现在 `story_docs/` 本身在 git 里，**改完直接
> `git diff -- story_docs/` 就是更贴近的历史对照**（比的是上一次提交，不是几年前的生成器），
> 也不需要维护白名单。`docs/` 目录保留作历史资料，不再被任何脚本读取。

**`validate_site.py`** 覆盖：节点逐字段重导与图不变量、`sections.json` 与磁盘 md/剧本对账、
表驱动页（`table_refs`）逐条核对表行存在且不得携带剧本代号、
布局几何（列 = 最长路径、同列不撞位、卡片矩形互不相交、边只跨相邻列）、图页面落点与链接可达、
逐页 HTML 台词序列 == md 台词序列、检索索引路径/说话人/行数、重大抉择角标映射、
页内锚点与聊天气泡、未开放组只出占位零台词泄露。

> 具体的检查组编号会随迭代增删，**不要在文档里抄清单**——要当前有哪些，跑一遍看输出开头的小节标题。

未开放门控的判据与实现见 8.5；诊断侧车的分类口径见 3.6。

`validate_site.py` 的**未开放门控检查**（2026-10-05 新增）：未开放内容只准显示未开放占位。断言被门控组的
组名不出现在 `site/` 任何文件、提示页不含台词行也不含话数标题、未开放 URL 不被任何页面引用、
该组 URL 目录下只有提示页、族索引的占位数量/遮罩/开放时间齐全。五种植入（把正文页写回锁定 URL、
给占位卡写组名、给提示页写话数标题、把锁定 URL 塞回 `search.js`、删掉一个提示页）全部 CAUGHT。
判据与门控本身见 8.5。

`build_story.py` 每次运行**先删后写** `story_docs/`：挂载规则一变就会少写文件，
留着旧文件会让校验器读到这份脚本从没写过的页面（2026-10-02 的挂错就是靠残留文件才显形的）。

### 8.4 刻意没做的东西
- 不给抉择选项标"直觉/分析/混沌"轴色：`SetPersonalityChoice` 参数里只有组号、槽位整数和三句文案，
  轴身份不在数据里，标了就是编造。
- 不做"只看我选的那条线"折叠：默认全展开 + 互斥标记，静态可读、可打印、不依赖 JS。
- 不引任何 webfont / 图标 / CDN；不加阴影、渐变、模糊、光效（第一版扁平是硬要求）。
- 站点 URL 里不放中文（用 `main/node/STm07_08.html`、`characters/144/14401.html`），md 文件名保留中文便于人工核对。
- 特别篇的 URL 目录**不做**历史别名双写：第 7 章从 `main/chsp/` 改到 `main/chsp7/` 之后，
  旧外链会 404。静态站没有重定向，双写别名页只会让"哪个是真的"变含糊；托管平台若支持
  `_redirects`（Cloudflare Pages 支持）可在静态根放一行 `/main/chsp/* /main/chsp7/:splat 301`，
  这是部署层的事，不进构建脚本。
- **门控只做页面层**：不删 `story_docs/`、不改 `build_story.py`、不重写 git 历史。存档保持完整，
  人工核对才有的对；"连仓库历史一起干净"是另一个决定，要做先想清 fork/star/PR 的代价。
- 门控**不做**倒计时、红点、`IsHighLight` 高亮视觉；也**不读** `LockText`——zh_CN 里 18 个故事集章
  全都没有对应文本，客户端实际走的是"倒计时"分支（见 8.5）。
- 门控**不做**章内节点级判定：官方没有这个字段（见 8.5 已知残留）。

### 8.5 未开放内容的门控（`release_gate.py`）

**为什么单独一节**：2026-10-05 之前，只要上游 `StorySetSection` 挂上章节，建站就把台词原文发出去，
不管官方开没开放。故事集 #18（`眠于秋分之日`，`OpenTime = 2026-10-13T12:00:00+08:00`、
`IsHighLight`、`StoryPreview.20` = 诺瓦异闻 #18）就是这么连同 286 句台词一起上线的。
门控就是堵这个口子；同类事故再来一次，读者先于版本看到剧情。

**判据只认官方表里的开放时间字段**（对 `CN/bin/*.json` 全量扫 `OpenTime`/`StartTime`/`ShowTime` 的结论）：

| 族 | 表 | 字段 |
|---|---|---|
| 故事集 | `StorySetChapter` | `OpenTime` |
| 主线 | `StoryChapter` | `OpenTime` |
| 活动 | `ActivityGroup`（`ActivityStory.ChapterId` 即其 Id） | `StartTime` |

其余带时间的表（`VampireRankSeason` / `Gacha` / `BattlePass` / `TravelerDuelChallengeControl` / `ResidentShop` …）
都是玩法，不读。`StoryPreview`（`Type` 1=主线 / 2=故事集 + `ShowTime`）**只用来取预告横幅标题**，
不作判据——预告本身是官方提前公开的信息。

**实现位置与理由**：门控在建站侧，不在 `build_story.py`。`story_docs/` 是给人工核对的存档，
不动它；要控的只是"发布什么"。所以 `build_site.py` 在任何消费点之前过滤
`pages` / `chapters` / `act_battle_pages`，并覆写 `shutil.copytree` 出去的三份侧车。

**未开放时页面长什么样**（复刻客户端 `StorySetChapterItemCtrl.RefreshItem` 的行为）：
- 族索引里一张虚线占位卡：`敬请期待`（= `UIText.StorySet_Chapter_Empty.1`，**别自己编遮罩文案**，
  单测把它钉在上游那一行上）+ 章号（`StorySetChapter.Title`，如 `#18`）+ 官方预告标题 + 预计开放时间；
  无链接、无篇数、无话数列表。主线索引用同式样的锁定卡片。
- 原小节 URL 变成「尚未开放」提示页（`locked_notice_page`），只有状态 / 预计开放时间 / 官方预告，零台词。
  组级 URL（`main/ch<no>/index.html`、`events/<id>/index.html`）同样走提示页，旧链接不再 404。
- `release_gate._item()` 的描述对象**刻意不含**章名、话数标题、小节数量——它是未开放时唯一会被渲染的
  东西，不能自己变成新的泄露点。

**加新族 / 新页面类型的纪律（这条是防再犯的重点）**：
1. 先查上游表有没有开放时间字段；有，就必须进门控（`load_gate()` 里补一个 `_<族>()` 填充函数）。
2. 新消费点必须拿**过滤后**的 `pages` / `chapters`，不能自己去读 `sections.json`。
   `load_activity_battle_pages()` 就是活例子：它直读 `ActivityStory.json` 挑无 `AvgLuaName` 的战斗行，
   不经过 `pages`，所以那里必须单独再过滤一遍。
3. 任何会被 copytree 进 `site/data/` 的新侧车 / 新 JSON，都要在 `strip_locked_from_data()` 里加一条——
   `site/data/*.json` 与 `search.js` 能被人 view-source 直接读，这是最容易漏的旁路。
4. 新页面形态要补契约 N 的断言（`forbidden_strings()` + `audit_locked()`），否则回归没人管。

**失败开放**：`OpenTime` 缺失 / 空 / 不可解析 → 视为已开放并打一行告警。宁可偶尔多收，
不可因为一行脏数据把整库内容静默挡掉。

**两个环境变量**：
- `STELLA_RELEASE_NOW=<ISO-8601>`：换判据时刻，用来证明"到点自动解锁"（CI / 单测用，不影响线上）。
- `STELLA_RELEASE_GATE=off`：整体旁路，等价于本次改动之前的站点（紧急回滚用）。

**已知残留**：官方没有节点级开放时间字段，章内分批开放挡不住。实例：第九章「后篇」
`StoryPreview.ShowTime = 2026-10-06`，而章级 `StoryChapter.OpenTime` 是 2026-09-29（早过了）。
缓释事实：未开放那部分剧本上游还没进包（`STm09_0x_c/_d`、`BBm09_BT04/BT05` 包里没有），没有正文可漏。
真要治得等上游给节点级字段，别用猜的。
