> 《建站与运维操作手册》第 四 章正文分册；总索引与「按需索取」表见 [OPERATION_MANUAL.md](../OPERATION_MANUAL.md)。章节编号沿用原书，跨章引用（如「见 3.6」）按索引定位。

## 四、 静态站方案：纯 Python 生成 `site/`

站点由纯 Python 模块化脚本负责，全部只依赖标准库，不需要 npm：

| 模块分类 | 脚本路径 | 输入 | 输出 | 核心职责 |
|---|---|---|---|---|
| **剧情处理** | `scripts/story/pipeline/diagnostics.py` | 各降级点注入的收集器 | （无 IO，只被 build_story 汇总） | 兜底统一登记：`Diagnostics` 收集器 + `CATEGORIES` 分类注册表 + 统一 `warn()`；所有"降级不崩"都必须在这里登记 |
| **剧情处理** | `scripts/story/pipeline/lua_lexer.py` / `lua_parser.py` | `Config/*.lua` | token 流 / T 表 | Stage 1 前端：真正的 Lua 词法 + 递归下降语法（平衡括号、转义还原、`nil/true/false`） |
| **剧情处理** | `scripts/story/pipeline/command_ir.py` | T 记录序列 | `[Command]` | 带稳定 `idx` 的命令序列；动画帧折叠以 `idx` 为身份，不再用 `id()` |
| **剧情处理** | `scripts/story/pipeline/passes.py` | `[Command]` + 说话人/编译器 | beat 列表 | Stage 2 语义：帧折叠、说话人解析、抉择分支归属、历史条件标记 |
| **剧情处理** | `scripts/story/pipeline/conditions.py` | 5 张官方表 + 4 张文案表 | 中文标签 / 分支标记 | 历史条件（已阅读/已选择/终局比例）解析与共享正文合并 |
| **剧情处理** | `scripts/story/pipeline/markup.py` | 词表 + 台词原文 | 内联节点树 | 性别变体、注音、强调配对、官方词表、未知标记保留原文 |
| **剧情处理** | `scripts/story/pipeline/speakers.py` | `AvgCharacter.lua` 预设 | 显示名 | 说话人 id → 显示名（预置表 + 最长点分前缀兜底） |
| **剧情处理** | `scripts/story/pipeline/pagedoc.py` / `render_md.py` | beat 列表 | PageDoc IR / Markdown | md 与 HTML 两个后端的共同上游；`render_md` 产物是人审真源（字节锁） |
| **剧情处理** | `scripts/story/build_story.py` | `data/` 解包表 + AVG 剧本 | `story_docs/`（md + `_data/*.json` + `_beats/*.json` + `_diagnostics.json`） | 编译管线编排、魔王正名、独白识别、图谱生成、上游异常与编译器兜底登记（口径由注册表生成） |
| **剧情处理** | `scripts/story/graph_layout.py` | 节点关系 (`sid/parents`) | 列、轨道、SVG 坐标 | DAG 分层拓扑几何纯函数（无 IO） |
| **剧情处理** | `scripts/story/release_gate.py` | 官方 `OpenTime`/`StartTime` | 过滤后的 pages/chapters | 未开放内容门控：只出占位与提示页，零台词泄露 |
| **静态站点** | `scripts/site/build_site.py` | `story_docs/_data/` + `_beats/` | `site/` 全量静态页面 | 站点编译主入口（消费前先过 release_gate） |
| **静态站点** | `scripts/site/registry.py` + `theme/` + `families/` + `assemble.py` | 关卡元数据与排版内容 | 结构化 HTML 字符串 / `site/assets/tokens.css` | 族注册表；公共页型（layout/gate/home/index/reading/battle/graph）；族片段（accent CSS + 章图/活动图组装）；(family, kind) 分发与 CSS 超级拼接 |
| **静态站点** | `scripts/site/site_js.py` | 前端交互事件 | `site/assets/site.js` | 离线即时检索、拓扑平移拖拽缩放、回到顶部 |
| **静态站点** | `scripts/site/render_html.py` | `story_docs/_beats/*.json`（PageDoc 侧车） | 干净的 HTML 片段 | beat IR → 正文 HTML、抉择/分支锚点与 `<ruby><rt>` 注音转换 |
| **自动化CI** | `scripts/automation/auto_sync.py` | GitHub 上游最新提交 | 全量增量更新 & CI 产物 | 自动化监控两上游变更，提取差异并触发自动化发布（`check=True`，故生成器不可抛异常） |
| **自动化CI** | `scripts/automation/changelog_from_commits.py` | 提交区间 | README 更新记录 | push 事件驱动的变更日志 |
| **辅助工具** | `scripts/tools/run_benchmark.py` | 基准测试用例集 | 耗时与性能报告 | 性能压测与解析效率分析 |
| **辅助工具** | `scripts/tools/golden_snapshot.py` | 语料 | 黄金快照 | 对拍旧实现，防回归 |
| **遗留工具** | `scripts/tools/build_wiki.py` | `data/` | `docs/` | 早期原型生成器，已不在主链路；见第九章 |

> 注：根目录 `scripts/` 下保留了 `build_site.py`、`build_story.py` 与 `auto_sync.py` 的轻量转发器，直接在根目录执行旧命令依然 100% 兼容。`build_wiki.py` **没有**转发器，需写全路径。

内容真源是 `story_docs/` 的 Markdown（它已被逐句校验过，是两份校验器的对照真源）；
站点正文则由 `story_docs/_beats/*.json`（PageDoc IR 侧车，`build_story` 的 `record_page`
落盘）渲染：`scripts/story/pipeline/render_md.py` 与 `scripts/site/render_html.py` 是共同
消费同一份 beat IR 的两个平行后端，站点不再从 md 文本反解结构（旧的 `md2html.py`
反编译层已删除），因此不存在"第二套渲染器"与产物漂移的问题。

**主线节点图**：边取 `Story.ParentStoryId`，卡面编号取 `Story.Index` 的文案，章头取
`StoryChapter` 的 `Name/Desc/ChapterYear`。列 = 最长路径深度，轨道 = 分叉围绕父节点上下展开、
汇合取父轨道均值，一遍重心扫描降交叉。坐标写进 `chapters.json`，页面只是把卡片按坐标摆好、
连线画在一张扁平 SVG 里。

**已知边界（不要当成 bug）**：
- 表 `StoryChapter.Id` 与游戏内章号差一章（Id 7 = 特别篇、Id 8 = 第七章），站内按游戏内章号显示。
- 官方界面每条时间槽属于哪一列写在 UI 预制体里，解包表内没有，所以节点时间条取该关剧本自己的
  场景头（`猎月 14日 10:36`），不冒充官方的按列分组文案。
- 特别篇全无 `ParentStoryId`，官方就没记录连线，页面按编号顺序列出并注明。
- 游戏右下角"直觉/分析/混沌"百分比来自玩家存档，表里只有三轴定义，本站不显示数值。

VitePress 作为备选保留在 `package.json` 的 `docs:*` 脚本里，未安装依赖，也不参与当前构建。
