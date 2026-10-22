# 剧情管线与站点前端模块化改造设计文档

> **状态：待评审 —— 截至本文档落笔，未改动任何代码。**
> 日期：2026-10-22（同日评审修订 R1–R6，见文末修订记录）
> 范围：`scripts/story/` 编排层、`scripts/site/` 模板与样式层。
> 不在范围：`scripts/story/pipeline/`（编译前端）、产物布局、契约校验器逻辑、上游数据。
> 维护纪律：每个 Phase 合并时同步更新本文档状态与 `_dev/AI_HANDOVER_GUIDE.md` 对应章节；
> 文中行数为 **2026-10-22 快照**，仅作改造基线参照，不作为权威数字引用。

---

## 一、背景

### 1.1 项目与管线概述

本仓库是《星塔旅人》(Stella Sora) 的非官方剧情档案库。主链路为：

```
上游镜像（repo 外 data/：StellaSoraData 配置表 + ss_lua AVG 剧本）
        │
        ▼
scripts/story/build_story.py（编排器）
        │  解析 Lua 剧本与配置表 → PageDoc IR
        ├──► story_docs/**/*.md        人审真源（字节锁）
        ├──► story_docs/_beats/*.json  PageDoc 侧车
        └──► story_docs/_data/*.json   站点结构侧车（chapters/sections/search/personality）
        ▼
scripts/site/build_site.py（建站驱动，消费侧车前过 release_gate 门控）
        ▼
site/ 纯静态站 → Cloudflare Pages；CI 每 6 小时 auto_sync 上游并重跑全链路
```

### 1.2 改造诉求的来源

维护者提出的目标（原话归纳）：

1. **剧情侧**：每个内容族（主线/活动/角色/NPC/唱片/委托/逸闻/回归/尖兵/心链/故事集/序章/存目气泡）独立成模块，**各取所需解析**——自己需要哪几张上游表就声明哪几张，不再全量加载。
2. **站点侧**：公共页面样式与组件放一份（总汇总页、默认二级索引页、对话展示页等复用面），**每个族的前端样式与模板独立成文件**，构建期按确定性顺序"超级拼接"。
3. 动机原话："现在全部塞在一个文件里，太难维护。"

设计草图（维护者手绘）表达的正是目标形态：Lua 经共享 Pipeline 产出对白 IR（beats）；各族配置表 json 经各族解析产出该族 IR；两者拼装后渲染为各族 md。本设计是该草图的形式化。

### 1.3 事实触发点（证据）

- 族接入是月度级 recurring 活动：逸闻笔记 2026-10-17（d06aeba）、回归+尖兵 2026-10-21（06be294）；且族配色是**事后补的独立提交** 078727f——"加族漏改共享文件"已实际发生。
- 仓库有多位贡献者（PR #13、#14），而站点样式是 2972 行单文件 Python 字符串：不同族的样式改动会在同一段字符串上产生合并冲突。
- 手册中专门存在"加新族纪律"条目——用文档补偿代码缺陷的信号。

---

## 二、现状

### 2.1 剧情侧数据流（已分层部分，保持不动）

```
Stage 1 前端   lua_lexer → lua_parser → command_ir      Lua 源码 → T 表 → [Command]（稳定 idx）
Stage 2 语义   passes.extract_beats（+speakers/conditions/markup/text_rules）→ beats + meta
IR             pagedoc.PageDoc（md 与 HTML 双后端共同输入）
Stage 4a 后端  render_md → story_docs/**/*.md（字节锁）
Stage 4b 后端  scripts/site/render_html.py 消费 _beats/ 侧车 → HTML 正文
横切           diagnostics（兜底统一登记）、markup（内联标记/词表）
叶子模块       chapter_path（slug/时间线唯一解析处）、graph_layout（拓扑坐标纯函数）、
               release_gate（未开放门控）、phone_chat（心链渲染，不碰文件系统）
```

`pipeline/` 包单向无环、内容无关；这是本项目最健康的部分，**本次改造不碰**。

### 2.2 编排层结构（`scripts/story/build_story.py`，1366 行快照）

| 行范围 | 内容 |
|---|---|
| 52-63 | pipeline 各符号导入 |
| 88-135 | **import 期**无条件加载约 40 张上游表（`BIN_*`/`LANG_*` 模块级全局）+ 构造 `TEXT_COMPILER`/`SPEAKERS`/`SPEAKER_RESOLVER`/`CONDITIONS`/`STORY_LINES`/`CHAPTER_SLUGS` |
| 140-174 | `script_commands` 缓存、`extract_script` |
| 197-200 | 全局可变累加器 `_PAGES`/`_SEARCH_ENTRIES`/`_CHAPTER_NODES`/`_RENDERED` |
| 203-284 | `write_beats`/`record_page`（侧车记录，`**extra` 大杂烩 kwargs） |
| 387-1131 | 13 个族 builder：`build_main`/`build_events`/`build_character_plots`/`build_npc_plots`/`build_discs`/`build_dispatch`/`build_anecdotes`/`build_returnee`/`build_soldier`/`build_chat`/`build_storysets`/`build_prologue`/`build_orphan_battles` |
| 1139-1270 | `write_data`/`write_coverage`/`write_diagnostics` 聚合 |
| 1273-1366 | `main()`：硬编码执行顺序 + 对账报告 + `--out` CLI |

### 2.3 站点侧页面生成分发（`scripts/site/build_site.py:444-544` 实测）

| 页型 | 渲染函数 | 实现归属 | 消费族 |
|---|---|---|---|
| 顶层总汇总页 | `home_page` | 公共 | 全站 |
| 默认二级索引页 | `family_index`（`:523-526`，显式跳过 main） | 公共组件 | 除 main 外 12 族 |
| main 二级索引页 | `main_index`（时间线滚轮定制，`:448`） | main 私有 | main |
| 对话展示页（约 507 页） | `script_page`（`:543`，正文来自 PageDoc 侧车） | 公共 | 全族 |
| 章拓扑图页 | `chapter_graph_page`（`:452`） | main 私有页 | main |
| 活动拓扑图页 | `activity_graph_page`（`:514`） | events 私有页 | events |
| 战斗档案页 | `battle_archive_page`（`:464` 与 `:519` 两处调用） | 公共组件 | main + events |
| 门控遮罩/提示页 | `locked_*`（`:530-532`） | 公共 | 全站 |

文件体量快照：`site_css.py` 2972 行（全部样式）、`site_templates.py` 915 行（全部模板）、`build_site.py` 496 行、`render_html.py` 422 行、`site_js.py` 390 行。

### 2.4 已有良好基础（冻结清单，改造不得破坏）

1. `pipeline/` 分层与内容无关性；PageDoc 双后端共 IR。
2. `diagnostics.py` 的 CATEGORIES 注册表与"降级不崩 + 必登记"方针（CI `check=True` 的配套）。
3. `chapter_path.py` 的 slug/时间线唯一解析、撞车即 raise。
4. `release_gate.py` 门控位置：任何新消费点不得绕过。
5. 两份契约校验器 `validate_story.py`/`validate_site.py`：**不 import 生成器**、只读产物 + 独立重解上游、带植入变异测试；契约 P3 子进程重建 `_diagnostics.json` 逐字节比对。
6. Markdown 字节锁（人审真源）；`docs/` 冻结基线（契约 A/A2 历史对照）。
7. 对外公共面：入口路径 `scripts/story/build_story.py`、`--out` CLI、README 三条构建命令、产物目录布局。

### 2.5 痛点清单（含出处）

1. **import 即全量加载**：`build_story.py:88-135` 的模块级副作用使"import = 全量加载 + 构造全部服务"；`tests/story/test_conditions.py:13` 因此付全量代价；单族运行/增量构建不可能。
2. **全局可变状态决定执行顺序**：`_PAGES` 等累加器（`:197-200`）使族无法隔离、并行、单独重跑；`record_page` 的 `**extra` 使侧车 schema 只能靠读调用点归纳。
3. **族↔表依赖不可见**：依赖散落在函数体（`build_chat` 用 `BIN_ITEM`、`build_anecdotes` 用 `BIN_NPC`、多家共用 `character_name`），无声明清单。
4. **挂载知识双份真相**：`write_coverage()`（`:1204-1207`）硬编码 `(表, 字段)` 挂载对，与各族 builder 取表逻辑重复；加族需改两处。
5. **站点硬编码清单**：活动拓扑的分支活动 `10106/20101` 硬编码于 `build_site.py:468-471`。
6. **拓扑图实现重复**：`chapter_graph_page`（`site_templates.py:417-477`）与 `activity_graph_page`（`:765-812`）约 90% 结构重复（pad/edges 循环/卡片循环/列锚点/`.map,.canvas,.wires` markup），差异仅切换条、lede、`data-family`。
7. **样式与模板单体文件**：2972 行 CSS 字符串无语法高亮/lint，diff 与合并冲突面大；915 行模板文件承载全部页型。
8. **顺序依赖人肉传递**：`build_orphan_battles(used)` 依赖 `build_main` 的 battle_map；`battle_map/skipped` 流经 `main()` 进对账与诊断。

---

## 三、为什么改

### 3.1 收益定义（结构性可维护性四轴）

1. **依赖可见**：族↔表、族↔页型的关系从"读全文归纳"变为文件头声明清单，可 grep、可审计、可测试。
2. **diff 局部化**：族样式/模板改动的影响面从 2972/915 行单文件降为族片段文件；跨族贡献者不再冲突。
3. **可隔离测试**：族 = `build(ctx, sink)` 纯函数，单测可用假 ctx/sink 不碰磁盘；import 无副作用。
4. **加族成本**：从"改编排器 + 改 coverage 清单 + 改站点共享文件 + 翻手册"降为"加两个族文件 + 两处注册表各一行"。

### 3.2 ROI 证据

族接入与样式调整在近一个月内发生 ≥4 次（1.3 节证据），收益兑现有明确场景；安全网（2.4 节）使每步改造可字节级验证，改造风险低于常规重构。

### 3.3 不会改善的部分（预期管理）

- **语义维护成本不变**：上游数据坑（气泡拼名、特别篇判定、官方代号笔误、门控口径）的考古成本由手册与契约承载，与文件组织无关。
- **代码总量不变**：本次是重排不是删减；唯一净删减是拓扑图去重（痛点 6）。
- **运行时性能基本不变**（懒加载仅改变加载时机）。

### 3.4 为什么是现在

接缝已存在（pipeline/IR/双后端干净分离；族边界在 13 个 builder 与 `FAMILIES` 清单中可见），安全网完备，且族接入频率证明投入可摊薄。

---

## 四、怎么改

### 4.1 目标目录树

```
scripts/story/
├── pipeline/            # 不动（2.4-1）
├── context.py           # 新：DataContext——表懒加载+缓存；共享服务构造一次注入；
│                        #     ScopedDataContext 运行时 NEEDS 门控（4.5-1）
├── sink.py              # 新：SidecarSink——record_page/record_node/write_beats/对账记录；
│                        #     累加器实例化
├── families/            # 新：一族一文件
│   ├── __init__.py      #     FAMILY_ORDER 注册表（执行顺序唯一声明处）
│   ├── main.py  events.py  characters.py  npc_bonds.py  discs.py  dispatch.py
│   ├── anecdotes.py  returnee.py  soldier.py  chat.py  storysets.py
│   └── prologue.py  orphan_battles.py
├── aggregate.py         # 新：write_data / write_coverage（挂载审计自动汇总）/
│                        #     write_diagnostics / 对账报告
└── build_story.py       # 瘦身 ≤200 行：建 ctx → 按 FAMILY_ORDER 跑族 → 聚合
scripts/site/
├── theme/               # 公共组件（判据见 4.3）
│   ├── tokens.css  base.css  graph_base.css
│   ├── layout.py  gate.py  home.py  index.py  reading.py  graph.py  battle.py
├── families/            # 一族一目录
│   ├── main/      templates.py（main_index 覆盖 + 章图组装）+ style.css
│   ├── events/    templates.py（活动图组装 + BRANCHING_ACTS 声明）+ style.css
│   └── <其余各族>/ style.css（accent+条纹）+ 可选 templates.py / INDEX_INTRO
├── assemble.py          # 新：CSS 超级拼接（manifest 显式有序清单）+ 模板分发注册表
├── render_html.py       # 不动
├── site_js.py           # 共享核心保留单份；族级 js 为可选扩展点（初期零个）
└── build_site.py        # 瘦身驱动：侧车 → release_gate → (family,kind) 分发 → 落盘
```

### 4.2 剧情侧核心概念与接口

```python
# context.py
class DataContext:
    def table(self, scope, name): ...        # scope ∈ {'BIN','LANG'}；懒加载+进程内缓存
    def extract_script(self, stem): ...      # 共享 script_commands 缓存
    def character_name(self, cid): ...       # 小服务，backed by Character 表
    def lang_of(self, scope_name, key): ...
    # 共享服务属性（编排器构造一次注入）：
    #   .text_compiler .speaker_resolver .conditions .diag

class ScopedDataContext:                     # R2：运行时 NEEDS 白名单门控（4.5-1）
    """包装 DataContext；未声明表的任何解析调用 raise UndeclaredTableError。
    共享服务属性原样透传（服务基于全量 ctx 构造，依赖走 SHARED_NEEDS）。"""

# sink.py
class SidecarSink:
    def record_page(self, family, path, doc, ident, title, *, code='', group=None,
                    stems=(), page=None, story_id=None, kind=None, parents=None,
                    hint=None, aim=None, affinity=None, twins=None, prose_lines=None,
                    cast=None, weight=None, notes=None, table_refs=None,
                    mount_note=None): ...    # R4：显式 keyword-only 可选参，None=缺省
    def record_node(self, ch, row, page, bubble_stem, beats=None): ...
    def write_beats(self, page, doc): ...
    # R1：主线对账记录收归 sink，保持 13 族签名同构
    def record_battle_map(self, entry): ...     # (sid, expected_stem, state, chapter)
    def record_skipped(self, entry): ...        # (ch, sid, stem, title, kind)
    def record_code_mismatch(self, entry): ...  # 官方显示代号与 StoryId 交叉行
    # 实例状态：.pages .search_entries .chapter_nodes .rendered
    #           .battle_map .skipped .code_mismatches

# families/events.py（族模块统一形态）
NEEDS  = (('BIN', 'ActivityStory'), ('LANG', 'ActivityStory'), ('LANG', 'ActivityGroup'))
MOUNTS = (('ActivityStory', 'AvgLuaName'),)     # 供 coverage 自动汇总

def build(ctx, sink):
    stats = collections.Counter()
    ...                                        # 原 build_events 逻辑，改读 ctx/sink
    return stats
```

要点：

- **族契约 100% 同构（R1）**：13 族一律 `build(ctx, sink) -> stats`（Counter）。跨族顺序依赖数据全部经 sink 显式 record 方法承载：`battle_map`/`skipped`/`CODE_MISMATCHES` 由 main 族记录进 sink；`orphan_battles` 的 `used` 从 `sink.battle_map`（attached 项）或 `sink.rendered` 取；aggregate 从 sink 读对账输入。编排器循环对任何族无特判分支。
- **NEEDS** 是"各取所需"的声明面，由 `ScopedDataContext` 在运行期强制执行（4.5-1）；**MOUNTS** 消灭痛点 4 的双份真相（`write_coverage` 改为汇总各族 MOUNTS）。
- **record_page schema 收口（R4）**：扩展字段收敛为显式 keyword-only 可选参（签名即当前全部调用点的并集），`None` 表示缺省，未知键由签名直接 TypeError；`sections.json` 字段集合从此可从 `sink.py` 签名 grep 得到。产物与现状 `**extra` 透传逐字节一致（各族传值不变）。
- 共享服务（TextCompiler/SpeakerResolver/ConditionCatalog/脚本缓存/character_name）由编排器构造一次、经 ctx 注入；族模块不得自行构造；其表依赖在 `SHARED_NEEDS` 一次性声明并审计。
- `phone_chat.py` 原样保留为叶子渲染器，由 chat 族模块调用；其 `ChatDiagnostics` 与进程级 `DIAG` 的统一**不在本次范围**。

### 4.3 站点侧：组件归类三问与清单

**三问判据**（任何代码块归公共或归族，按序回答）：

1. 页面归属谁（URL 挂在哪个族索引下）→ 族；
2. 实现被几个族复用（≥2 族同 markup 结构）→ 公共组件；1 族 → 族私有；
3. 族间差异是内容参数（切换条/lede/accent）还是结构（特别篇平铺 vs 图）→ 参数走组件入参、由族组装层传入；结构差异留在族组装层。

按判据落位：

- **theme/（公共）**：layout 壳与面包屑、门控 `locked_*`、`home_page` 总汇总、`family_index` 默认二级索引、`script_page` 阅读牌板、**拓扑图组件**（main 章图与 events 活动图双消费，顺带消灭痛点 6 的重复）、**战斗档案组件**（main+events 双消费）、tokens/base/graph_base CSS。
- **families/（族）**：族 accent 与条纹样式、索引引言、图页组装（切换条/lede/特别篇平铺变体）、main 的 `main_index` 索引覆盖、events 的 `BRANCHING_ACTS` 声明（消灭痛点 5）。
- **注册表钩子**：族站点模块可声明 `INDEX_OVERRIDE`（覆盖默认二级索引）与独有页型渲染函数；分发键为 `(family, kind)`，kind taxonomy 保持极小：`reading / chapter_graph / activity_graph / battle_archive / index / home`。

**超级拼接机制**：

- `assemble.py` 持**显式有序 manifest 清单**（顺序是清单数据，不隐含等于 FAMILY_ORDER）。Phase E1 的 manifest = `site_css.py` 现有样式块的**发现序**（无论其是否与族序一致、是否夹杂），且不注入文件头注释——由此 E1 的字节不变按构造成立（R3）；Phase E3 才把 manifest 归一为 `tokens → base → graph_base → FAMILY_ORDER` 并注入文件头 manifest 注释，走"声明式预期 diff"流程（6.2）。拼接顺序确定性 = 字节稳定 = 契约可继续生效。
- 族样式片段边界规则（lint 语法见 4.5-2）：只允许 (a) 本族令牌覆盖（`--grp-accent` 等，现 `site_css.py:1144-1233` 那批块天然按族分组），(b) 本族作用域内选择器。跨族复用一律上提 theme/。防止拼接顺序退化为新的隐性 cascade 耦合。
- 模板首迁为**纯搬运**（切函数进族模块，不改逻辑）；CSS 首迁为**按现有行序原样切片**（不重排不改选择器）；整理（合并重复规则、调层级、归一 manifest）作为独立提交并人工目视。

### 4.4 分阶段计划

| Phase | 内容 | 提交粒度 | 随附文档 |
|---|---|---|---|
| A | `context.py` 上线：表懒加载+缓存、共享服务注入、ScopedDataContext 门控；移除 build_story 模块级全局 | 1–2 提交 | 手册 7.x 数据加载小节 |
| B | `sink.py` 上线（含 R1 对账记录方法与 R4 显式 schema）；13 族逐一搬迁为 `families/*.py`（含 NEEDS/MOUNTS 声明） | 每族 1 提交（13）+ sink 1 提交 | 手册 7.4 族清单改写 |
| C | 编排器瘦身 ≤200 行；coverage 挂载审计自动汇总；注册表完整性契约入库 | 2 提交 | 手册 7.x/8.1 |
| D | D1 站点模板族拆分纯搬运 1 提交；D2 拓扑图二合一去重 1 提交（优先参数化严格复刻原 HTML 字符串做到字节不变；若确需结构归一，走声明式预期 diff，diff 范围限章图/活动图两类页）；D3 分发注册表 + 索引覆盖钩子 + BRANCHING_ACTS 声明 1 提交 | 3 提交 | 手册 8.1/8.3 |
| E | E1 CSS 切片 + `assemble.py` 超级拼接（manifest=发现序、无文件头注释，字节不变）1 提交；E2 CSS 作用域 lint 契约 1 提交；E3 manifest 归一 FAMILY_ORDER + 文件头注释 + 样式整理（声明式预期 diff + 人工目视）1 提交 | 3 提交 | 手册 8.x 站点结构 |

Phase 顺序理由：A→B→C 先让族边界与声明面在剧情侧成立（站点族 id 与故事族 id 同源），D/E 消费同一批 id；E1 风险最低，也可提前作为信心建立步骤，但不得早于 D3 的注册表（族 id 清单以注册表为准）。

### 4.5 边界契约（防声明腐烂，进 pytest）

1. **NEEDS 运行时门控（R2，取代静态扫描方案）**：编排器按族 `NEEDS` 构造 `ScopedDataContext` 包装器传入 `fam.build(scoped_ctx, sink)`；运行期任何解析调用（`ctx.table(scope, name)`、`ctx.lang_of(...)` 及一切内部会解析表名的方法）命中未声明表立即 raise `UndeclaredTableError`（实现约十几行，动态调用路径亦 100% 精确覆盖，省去维护 AST 扫描器）。共享服务属性在包装器上原样透传——服务基于全量 ctx 构造，其表依赖由 `SHARED_NEEDS` 一次性声明并审计。两条配套：(a) 运行时门控发现不了"声明了但没用"的过度声明，全量构建结束时对 declared-but-untouched 表输出**非阻塞 warning**（仅提示，不失败）；(b) 仅在新上游数据下才触发的未声明依赖会让 auto_sync 以 `UndeclaredTableError` 停止（`check=True` 语义）——这是预期的 fail-loud 行为，修复动作是补一行 NEEDS；该失败模式写入手册值班手册。
2. **CSS 作用域 lint（R5 修正语法）**：族 style.css 片段中每条选择器必须含本族作用域组件——`[data-family="<id>"]`（挂于任意复合选择器，兼容现有 `.grp-grid[data-family="events"]`、`.chapsel[data-family="main"]`、`.map[data-family="main"] .node.story` 形态，见 `site_css.py:1145-1233, 1397-1404, 1607-1614, 1674-1772`）或 `.fam-<id>`（未来 markup 预留）；允许可选 `[data-theme="dark"]` 前缀与外层 `@media`/`@supports` 包裹（现有暗色 accent 覆盖即此形态，`site_css.py:1190-1233`）。theme/ 片段不允许引用族令牌具体值。此语法防止现有拓扑图/配色块样式在 lint 阶段被误杀。
3. **注册表完整性**：`FAMILY_ORDER` 每族都有故事族模块；侧车 `sections.json` 出现的每个 family 都有站点族模块或显式 fallback；族 accent 缺失即失败（挡 078727f 类遗漏）。
4. **冻结面断言**：入口路径、`--out` CLI、产物布局的冒烟测试（契约 P3 按路径子进程调用生成器，入口不可移动）。

### 4.6 冻结面（重构期间一律不动）

- 入口 `scripts/story/build_story.py` 路径与 `--out` 参数；README 三条命令；`scripts/` 根转发器。
- 产物布局：`story_docs/`（含 `_beats/_data/_chat/_` 前缀约定）、`site/` 目录结构。
- md 字节锁；`release_gate` 门控位置；`docs/` 冻结基线；两份校验器的"不 import 生成器"独立性。

### 4.7 范围外（backlog，不混入本次）

1. **增量构建**（表/剧本内容哈希缓存，仅重跑变更族）——本次重构解锁的后续机会，单列。
2. 族间并行构建。
3. `ChatDiagnostics` 与进程级 `DIAG` 的统一。
4. `pipeline/` 进一步拆分、族级私有解析器（明确禁止：解析前端保持内容无关）。
5. 局内随机事件五表（Soldier 系）接入（手册 7.6 已议定不纳入）。

### 4.8 风险与对策

| 风险 | 对策 |
|---|---|
| `common.py` 退化为新杂物抽屉 | 共享小服务只允许存在于 ctx（character_name/lang_of 等），不设自由生长的 common 模块 |
| CSS 拼接顺序成为隐性耦合 | 4.5-2 作用域 lint + 令牌唯一来源 theme/tokens.css |
| 注册表间接层降低可 grep 性 | kind taxonomy 极小（6 种）；注册表文件保持 ≤40 行 |
| 手册/README 漂移 | 每 Phase 提交随附文档更新（4.4 表末列）；本文档状态同步 |
| 搬运期手滑改逻辑 | 每提交字节级验收（6.2）；搬运提交禁止混入逻辑修改 |
| ScopedDataContext 透传面过宽削弱门控 | 包装器仅透传 4.2 列明的共享服务属性；新增服务须同步 SHARED_NEEDS 评审 |

---

## 五、改完效果

### 5.1 加一族流程对比

- **现状**：改编排器（新 builder + 取表全局）→ 改 `write_coverage` 挂载清单 → 改站点 `FAMILIES`/配色/模板 → 翻手册补纪律；漏任一处靠人审发现（078727f 为先例）。
- **改后**：新建 `scripts/story/families/<fam>.py`（NEEDS+MOUNTS+build）与 `scripts/site/families/<fam>/`（style.css，可选 templates.py）→ 两处注册表各加一行 → 契约 4.5-1/3 自动挡住漏声明与漏配色。共享层零改动。

### 5.2 影响面对比（2026-10-22 快照）

| 项 | 现状 | 改后 |
|---|---|---|
| 编排器 | 1366 行单文件 | ≤200 行 + 13 个 30–120 行族文件 |
| 站点样式 | 2972 行单文件字符串 | tokens/base/graph_base + 每族数十行片段，编辑器原生 .css |
| 站点模板 | 915 行单文件 | theme 7 组件 + 族组装文件（多数族无 templates.py） |
| 拓扑图实现 | 两份 90% 重复 | 一份组件 + 两处 ≈30 行组装 |
| 族↔表依赖 | 读全文归纳 | 文件头 NEEDS 清单 + 运行时门控 |

### 5.3 测试与调试

- 单族单测：假 ctx/sink（含 ScopedDataContext 真门控），不碰磁盘、不全量加载；`test_conditions.py` 改 import `pipeline`+ctx，移除最后一处测试对编排器的耦合。
- 单族重跑/调试回路成立；为增量构建（backlog）铺路。

### 5.4 净删减

拓扑图重复实现合一（痛点 6）；`write_coverage` 硬编码清单删除（痛点 4）；`branching_acts` 硬编码删除（痛点 5）。其余为等量重排。

---

## 六、最终验收

### 6.0 验收不变量总纲（R6）

- **story_docs：硬字节门**——全流程任何提交后与基线逐字节一致，无例外。
- **site：显示效果不变为不变量**；字节清单一致是**默认目标**（"能全对上最好"），允许个别提交走"声明式预期 diff"（6.2-2）。

### 6.1 基线快照（改造开始前一次性执行）

1. 在干净工作区跑 `python scripts/story/build_story.py && python scripts/site/build_site.py`，提交为 tag `refactor-baseline`（story_docs 在 git 跟踪下，基线即该 commit 树）。
2. site/ 不在版本控制下：生成 sha256 清单留档（临时脚本，run-and-burn 纪律，用后删除）：

```python
import hashlib, os
out = []
for d, _, fs in os.walk('site'):
    for f in sorted(fs):
        p = os.path.join(d, f)
        out.append('%s  %s' % (hashlib.sha256(open(p, 'rb').read()).hexdigest(),
                               p.replace(os.sep, '/')))
open('site_manifest_baseline.txt', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
```

### 6.2 每 Phase 验收（硬门槛）

1. **story_docs 硬字节门**：`git status --porcelain story_docs/` 为空。
2. **site 默认字节门**：重建后 sha256 清单与基线 `diff` 为空。**声明式预期 diff** 提交豁免（当前预见：D2 若发生结构归一、E3），豁免条件全部满足才允许合并：
   a. 提交 message 与本文档 Phase 表列明受影响文件/页型范围；
   b. 实际 manifest diff 集合 ⊆ 声明范围（越界即失败）；
   c. 同一提交内更新 `site_manifest_baseline.txt`；
   d. 双校验器全绿；
   e. diff 可能影响视觉时附人工目视抽查记录（前后对照截图或明确结论）。
3. `python tests/story/validate_story.py` 与 `validate_site.py` 全绿（含植入变异测试）。
4. `pytest tests/` 全绿。
5. 任一失败 → **整提交回滚**，不允许补丁式修复（保护 bisect 能力）。

### 6.3 全量结构断言（改造完成时）

- `scripts/story/build_story.py` ≤200 行；文件内无模块级 `load_json(` 调用。
- 每个 `families/*.py` 含 `NEEDS` 与 `MOUNTS`；4.5-1 运行时门控在全量构建中零 `UndeclaredTableError`。
- `scripts/site/site_css.py` 不存在；`site/assets/style.css` 由 assemble 产出（文件头 manifest 注释自 E3 起存在）；4.5-2 lint 绿。
- 4.5-3 注册表完整性绿；4.5-4 冻结面冒烟绿。
- 全局累加器 `_PAGES/_SEARCH_ENTRIES/_CHAPTER_NODES/_RENDERED` 与 `CODE_MISMATCHES` 在仓库中零残留（仅 sink 实例属性）。
- site 侧终态抽查：各页型（home/索引/阅读/章图/活动图/战斗档案/门控页）明暗双主题目视与基线站点对照无回归（呼应 6.0 显示效果不变量）。

### 6.4 行为验收：加族演练

在验收分支做一次 dry-run 加族（候选：`GD_*` 抽卡演出，现 `_coverage.md` 挂"待决"）：

- 仅新增 `scripts/story/families/gacha.py`、`scripts/site/families/gacha/` 与两处注册表各一行；
- `git diff --name-only` 对共享层文件（theme/、pipeline/、aggregate.py、build_site.py 等）为零；
- 全链路构建绿后**回滚该分支**（或经评审转正为真实接入，二选一，评审时定）。

### 6.5 CI 验收

合并后观察：一次 schedule 事件 `auto_sync.py` 全链路绿（含 check=True 生成器不抛异常）；一次 push 事件流水线（changelog → 单测 → 双契约 → 建站 → 部署）绿；Cloudflare Pages 部署产物与基线站点目视抽查无回归。

### 6.6 文档验收

- 本文档状态改为"已完成"，Phase 表逐行勾选；
- `_dev/AI_HANDOVER_GUIDE.md` 第七/八章与本文档目标形态一致（族清单、数据加载、站点结构小节）；
- README 架构树同步（`families/`、`theme/`、`assemble.py` 条目）。

### 6.7 回滚红线

任何 Phase 的 6.2 门槛失败且一次回滚后仍无法通过 → 停止后续 Phase，维持已合并部分（各 Phase 独立可留存），在本文档记录阻塞原因与决议。

---

## 附录 A：族 ↔ 上游表依赖初稿（NEEDS draft，Phase B 以运行时门控定稿）

| 族 | BIN 表 | LANG 表 | 其他输入 |
|---|---|---|---|
| main | Story, StoryChapter, StoryChapterTimeStamp | Story, StoryChapter, StoryChapterTimeStamp | chapter_path（StoryLine）、CFG `STm*/BAm*`、气泡拼名 |
| events | ActivityStory | ActivityStory, ActivityGroup | CFG `STev*` |
| characters | Plot, Character | Plot, Character | CFG `CG_*` |
| npc_bonds | NPCAffinityPlot, StarTowerNPC | NPCAffinityPlot, StarTowerNPC | CFG `CG_npc*` |
| discs | DiscIP, Character | DiscIP, Character | CFG `CG_disc*` |
| dispatch | AgentSpecialPerformance, Character | Character | CFG `DP_*` |
| anecdotes | StarTowerBookEventReward, StarTowerNPC, Character | StarTowerBookEventReward, StarTowerNPC, Character | 无（表驱动） |
| returnee | — | UIText | CFG `ST_sys_reengagement*`（目录扫描） |
| soldier | SoldierEndingPlan | SoldierEndingPlan | CFG `ST_sys_soldier_intro` |
| chat | Chat, Item, Character | Item, Character | CFG `PM_*` |
| storysets | StorySetTab, StorySetChapter, StorySetSection | 同 BIN 三表 | CFG `STsp_*` |
| prologue | — | — | CFG `STm00_*`/`BBm00_*`（目录扫描） |
| orphan_battles | — | — | CFG `BBm*`（目录扫描）+ sink.battle_map/rendered |

共享服务表依赖（`SHARED_NEEDS`，编排器声明，审计时并入全集）：TextCompiler（PRESET 词表 + BIN/LANG）、SpeakerResolver（PRESET `AvgCharacter.lua`）、ConditionCatalog（BIN/LANG 条件表）、script_commands 缓存（CFG）、character_name（BIN/LANG Character）。

## 附录 B：页型 ↔ 模板 ↔ 归属（改后落位）

| 页型 | 改后位置 | 说明 |
|---|---|---|
| home | theme/home.py | 总汇总页 |
| index（默认） | theme/index.py | 12 族默认二级索引 |
| index（main 覆盖） | families/main/templates.py | 时间线滚轮 `main_index` |
| reading | theme/reading.py | 对话展示牌板，全族共用 |
| chapter_graph | 组件 theme/graph.py + 组装 families/main/ | 特别篇平铺变体留 main 组装层 |
| activity_graph | 组件 theme/graph.py + 组装 families/events/ | BRANCHING_ACTS 由 events 声明 |
| battle_archive | theme/battle.py | main+events 双消费 |
| locked notice | theme/gate.py | 门控 UI |

## 附录 C：术语

- **族 (family)**：一个内容收录类别，故事侧与站点侧共用同一 id 字符串（现 `site_templates.FAMILIES` 清单）。
- **PageDoc IR**：md 与 HTML 双后端的共同中间表示（`pipeline/pagedoc.py`）。
- **侧车 (sidecar)**：构建期落盘的结构化伴生产物（`_beats/`、`_data/`、诊断 json）。
- **超级拼接**：构建期按 manifest 显式有序清单连接 CSS 片段的组装机制。
- **字节锁**：人审真源 Markdown 在重构期间必须逐字节不变的约束。
- **声明式预期 diff**：site 侧豁免字节门的受控流程（6.2-2 的 a–e 条件）。

## 修订记录

- 2026-10-22 初稿。
- 2026-10-22 评审修订（维护者评审意见 R1–R5 + 口头放宽 R6）：
  - **R1**：`battle_map`/`skipped`/`CODE_MISMATCHES` 收归 SidecarSink 显式 record 方法，13 族 `build(ctx, sink) -> stats` 保持 100% 同构，编排器循环零特判（→4.1/4.2/6.3）。
  - **R2**：NEEDS 审计由静态扫描改为 `ScopedDataContext` 运行时白名单门控；共享服务透传 + `SHARED_NEEDS`；过度声明以非阻塞 warning 提示；CI fail-loud 失败模式写入手册（→4.2/4.5-1/附录 A）。
  - **R3**：字节锁边界精确界定——E1 manifest 取发现序且不注入文件头注释，字节不变按构造成立（无需预先核对行序是否匹配 FAMILY_ORDER）；manifest 归一与文件头注释移入 E3；D2 优先严格复刻，结构归一走声明式预期 diff（→4.3/4.4/6.2）。
  - **R4**：`record_page` 的 `**extra` 收敛为显式 keyword-only 可选参（签名即 schema），未知键 TypeError（→4.2）。
  - **R5**：CSS lint 合法作用域按现有 CSS 实况修正：`[data-family="<id>"]` 复合形态 + `.fam-<id>` 预留 + `[data-theme="dark"]` 前缀 + `@media`/`@supports` 包裹（→4.5-2）。
  - **R6**：验收放宽——story_docs 保持硬字节门；site 以"显示效果不变"为不变量，字节一致为默认目标、允许声明式预期 diff（→6.0/6.2/6.3）。
