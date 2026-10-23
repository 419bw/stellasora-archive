> 《AI 技术交接手册》第 九 章正文分册；总索引与「按需索取」表见 [AI_HANDOVER_GUIDE.md](../AI_HANDOVER_GUIDE.md)。章节编号沿用原书，跨章引用（如「见 3.6」）按索引定位。

## 九、 修订记录（2026-10-02）

- 2026-10-05：**补上"官方还没开放的内容不该发布"这道闸**。新增 `scripts/story/release_gate.py`
  与建站侧门控；故事集 #18《眠于秋分之日》（`OpenTime 2026-10-13 12:00`）此前连同 286 句台词一起上线。
  判据表、页面形态、加新族的纪律、失败开放语义与已知残留全部写进 8.5；`validate_site.py` 新增未开放门控检查；
  `tests/story/test_release_gate.py` 入库。站点侧被门控组的页面改为只出占位与提示页。
- 本文档早期"604 个 Markdown 文件"的说法已作废：文件数随上游数据增长，改以 `sections.json` 的
  `meta.pages` 与 `_coverage.md` 为准（见 7.7 与 FAQ 3）。
- 同日：`build_story.py` 接入 `CG_*`(角色/NPC/唱片) + `STsp_*` + 序章 `STm00_*` + 存目战斗气泡，
  产物侧车进 `story_docs/_data/`，`story_docs/_coverage.md` 改为构建时自动生成。
- 同日：撤回"BBm00_* 是教学关"的推测（`TutorialLevel*` 引的是 `TrainingLevels_01`，与 BBm 无关），
  改判为注册流程序章那一战，证据见 7.3。
- 同日：修掉两处抽取缺陷 —— 手机回复抉择把 `param[0]`（组号）当选项输出（产物里出现 `> - **1**`），
  以及 `avg1_144_BB_002` 这类带后缀的说话人 id 解析不出姓名（回落基 id → 千都世/冬香）。
- 同日：新增纯 Python 静态站（`build_site.py` + `graph_layout.py` + `md2html.py`），
  主线按 `ParentStoryId` 出游戏式节点图；结构化侧车进 `story_docs/_data/`，
  独立校验器 `tests/story/validate_{story,site}.py`（契约 A–K）入库。
- 同日：修站点三处交互缺陷 —— 台词折行跑到说话人名下（`.line` 改两列网格）、
  节点卡片 `<a>` 丢了 `href` 导致整图点不动、`.map` 被内联宽度撑宽使横向滚动条挂到页面上
  （连带修好列锚点跳转，它一直是 `map.scrollTo`）。新增契约 H3 管卡片可点数与链接可达。
- 同日：**战斗气泡整批挂错章**。拼名规则应为关卡 `StoryId` 里的章号（`BAm07_01` → `BBm07_BT01`），
  此前按 `Story.Chapter` 拼，而 `Chapter` 把特别篇记成 7、特别篇关卡却记作 `06x5`，
  于是第七章的三场气泡挂到了特别篇，后面两章依次错位。判据与复现见 7.3，并固化成一组校验。
  修正后主线战斗关卡大部分能命中气泡剧本，剩下无剧本的都是"包里确实没有"；
  存目 BBm 相应减少。`build_story.py` 同时改为先删后写 `story_docs/`
  （残留旧页会让校验器读到没写过的文件）。
- 同日：查清 `SetTalk` 第一个参数是**显示通道**（通道名在 `AvgCmdParamOptionDefine.lua`，0 起算，
  分支链印证），一度把 4136 句标上通道标签（`efcd711`），随后**全部还原**：`CG对话` 不等于回忆
  （开场 CG 也走这条通道），且标签太吵。判据与实测留在 7.8，产物维持只有「思考 / 短信 / 战斗气泡」三种标记。
- 2026-10-05（门控自查修订，四条都是复核时才发现自己写错的）：
  ① **遮罩文案自编了**——客户端 `RefreshItem` 把未开放章名换成 `StorySet_Chapter_Empty`，
     zh_CN 实际是「敬请期待」，我写成了「？？？」；已改并用单测把常量钉在上游 `UIText` 那一行上。
  ② `load_activity_battle_pages()` 那类**不经过 `pages` 的消费点**：锁定活动若落在写死的拓扑活动清单
     （10106 / 20101）里，会在 `act_all[-1]` 上 IndexError；改为跳过拓扑页，让组级 index 也走提示页。
  ③ 移除 `_preview(kind, at)` / `locked_block(item, d)` 的死参数（留着会让人以为开放时间是预览的判据）。
  ④ 占位徽标原先用 `!important` 盖 `.grp-count` 的填充配色，和 `clip-path + ::before` 的实现冲突，
     改设 `--grp-accent` / `--chap-accent` 吃既有设计令牌。
- 2026-10-05（CI 自动提交的更新日志会改源文件里的首页"更新时间"串，例如 `fcc9228`：
  只碰 README 与 `scripts/site/theme/home.py` 的 `home_page` 文案，与功能改动不同行， rebase 不会冲突）。
- 2026-10-09：**接入历史条件分支**（PR #4）。新增 `pipeline/conditions.py`，`IfUnlock`/`IfTrue`/`CheckBE`
  三族指令不再被丢弃，改为渲染成「历史条件分支」标记 + 汇合点，正文相同的相邻分支自动合并。
  `extract_beats` 增加可选 `conditions` 参数；`fold_animations` 改为按条件边界分段，避免淡入帧跨分支错误折叠。
- 2026-10-09：更正终局已阅读比例文案（8% 边界），`Story.json` 200 行条件表的标签文案随侧车落盘。
- 2026-10-10：**兜底机制统一**（本轮）。新增 `pipeline/diagnostics.py`（`Diagnostics` 收集器 +
  `CATEGORIES` 分类注册表 + 统一 `warn()`），`markup`/`speakers`/`passes`/`conditions`/`build_story`
  五个通道原先各自为政（裸 list / 裸 dict / 只打 logger / 静默 / 直接 KeyError），现在全部注入同一个
  进程级 `DIAG`。`conditions.py` 里 9 处会崩掉 build 的裸查找改为「可读标签 + 登记」。
  `validate_story.py` 新增契约 **P**（schema + note 一致 + 子进程重建逐字节无漂移 + 6 项变异测试）；
  新增 `tests/story/test_diagnostics.py`；`build_story.py` 增加 `--out` 供临时目录重建。
- 2026-10-10：**文档大更**。修正 8 处过时规模数字（改为读侧车 `meta`，不再写死）、重写 3.4
  （旧伪代码与实现几乎全不符）、把 7.5「尚未实现的指令」改写为已实现的历史条件分支详解、
  补全目录缺失的 6 个条目、新增第九章（遗留产物 `docs/` 的处置）与第五章（CI/CD 流水线）。
- 2026-10-17：**接入逸闻笔记**（d06aeba）。`StarTowerBookEventReward` 表驱动、一人一页
  （旅人归 `anecdotes/char/`、星塔 NPC 归 `anecdotes/npc/`），复用 anecdote beat 渲染；
  页面无「官方跳过概要」时正文与附录自动顺延为第 2、3 节。`validate_story.py` 新增契约 **Q**
  （逸闻笔记 1:1 对齐源表）。本条与 7.4/7.7 的对应内容为 2026-10-21 补记。
- 2026-10-21：**接入回归剧情与尖兵陷阵**（365227d、2a9be4a）。回归活动《归星漫途》
  （`ActivityReturnee.AVG` 直接点名剧本）入 `returnee/`；尖兵陷阵开场剧本 + `SoldierEndingPlan`
  终局表驱动页入 `soldier/`，引入 `table_refs` 通用表驱动标记（`validate_site` 新增表驱动页校验分支，
  族索引副题「终局文本 · N 字」）；局内随机事件五表因结果文案大量缺失，议定不纳入（见 7.6）。
  `write_coverage()` 挂载审计加 `('ActivityReturnee', 'AVG')`，`ST_*` 前缀族清零。
  同日补手册：7.4 补逸闻笔记/回归剧情/尖兵陷阵三族与「表驱动页」判据纪律，7.7 目录树补三行，
  8.3 补表驱动页对账描述，并修正目录（TOC）与实际章节标题的多处漂移（2.x 幽灵条目、7.x 旧标题、九/十顺序）。
