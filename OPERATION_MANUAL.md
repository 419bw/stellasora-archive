# 《星塔旅人》全量剧情与剧本知识库：独立建站与运维操作手册

> **文档版本**：v1.0.0  
> **数据基准**：官方公测客户端解包资产（包含 10 个主线篇章、11 个限时活动、40 位旅人专属档案与约会剧情）  
> **项目定位**：全网首个且唯一的《星塔旅人》1:1 逐句台词、分支抉择与拓扑导图高保真静态剧情数据库。

---

## 目录
1. [背景与全网现状调研](#一背景与全网现状调研)
2. [知识库核心架构与数据流](#二知识库核心架构与数据流)
3. [官方底层解析技术规范](#三官方底层解析技术规范)
   - [3.1 主角正名与代号收束（魔王）](#31-主角正名与代号收束魔王)
   - [3.2 灰色对话框与内心独白判定（TalkType）](#32-灰色对话框与内心独白判定talktype)
   - [3.3 三类交互抉择分支清洗机制](#33-三类交互抉择分支清洗机制)
4. [静态站方案：纯 Python 生成 site/](#四静态站方案纯-python-生成-site)
5. [构建与本地预览](#五构建与本地预览)
6. [部署](#六部署)
7. [后续游戏版本更新与日常维护规范](#七后续游戏版本更新与日常维护规范)

---

## 一、 背景与全网现状调研

在目前的各大公开社区（B站 BWIKI、GameKee、Miraheze、NGA、贴吧等）中：
- **现有站点的局限**：所有的游戏资料站均聚焦于**数值养成、卡牌图鉴、副本关卡攻略、突破材料**，对于剧情仅提供粗略的文字大纲或指引去游戏内回看。
- **逐句台词与剧本的空白**：全网**没有任何一个公开网站**完整提取并结构化整理出游戏的**逐句剧情剧本、玩家分支抉择项、约会事件台词全文本**。
- **建站价值**：将本项目独立开源或部署为公共静态站，将填补全网《星塔旅人》剧情数据库的空白，成为玩家查阅剧情细节、考据世界观伏笔、二创作者检索台词的权威基准站。

---

## 二、 知识库核心架构与数据流

本项目的核心目标是**“零胡编、100% 官方数据源保真”**，采用自动化提取管道直接将 Unity 官方解包表转化为渐进式披露的 Markdown 文档树：

```mermaid
flowchart TD
    subgraph DataSources["官方解包原始数据"]
        A1["CN/bin/*.json (关卡配置/约会数据)"]
        A2["CN/language/zh_CN/*.json (官方文案)"]
        A3["ss_lua_repo/Avg/_cn/Config/*.lua (AVG剧本)"]
        A4["ss_lua_repo/Avg/_cn/Preset/*.lua (角色预设)"]
    end

    subgraph Pipeline["提取清洗与结构化流水线 (build_wiki.py)"]
        B1["主角正名收束 (塞拉/PLAYER_NAME -> 魔王)"]
        B2["TalkType 状态机 (0=说 / 2=思考)"]
        B3["抉择项解包 (Major / Personality / Phone)"]
        B4["DAG 章节拓扑图生成 (Mermaid graph LR)"]
        B5["双向倒排索引与别名表构建 (alias_index.json)"]
    end

    subgraph Output["知识库文档体系 (docs/)"]
        C1["story/main/ (10章共604个独立关卡文件)"]
        C2["story/events/ (11个活动剧情小节)"]
        C3["characters/ (40位旅人档案+约会全剧本)"]
        C4["basics/ & overview/ (世界观/唱片/纹章)"]
    end

    DataSources --> Pipeline
    Pipeline --> Output
```

---

## 三、 官方底层解析技术规范

为保证剧本阅读体验与游戏内完全一致，生成管道解决了三个关键的引擎还原问题：

### 3.1 主角正名与代号收束（魔王）
- **现象**：官方预设表 `AvgCharacter.lua` 中，男女主角开发代号为 `avg3_100`（女）与 `avg3_101`（男），名称均被硬编码为 `"塞拉"`（开发期代号）。
- **机制**：在游戏客户端中，该代号由引擎动态替换为玩家身份；主线剧情中主角的核心身份与公认称呼为**“魔王”**。
- **规范**：
  - 覆盖映射表：`avg3_100`、`avg3_101`、`avg3_1311`、`avg3_1312`、`1` 统一映射为 **“魔王”**。
  - 变量清洗：所有原文字符串中的 `==PLAYER_NAME==` 自动清洗替换为 **“魔王”**。

### 3.2 灰色对话框与内心独白判定（TalkType）
- **现象**：游戏内玩家常有未说出口的思考与内心独白，对话框呈现为灰色气泡。
- **机制**：根据官方剧本定义 `AvgCmdParamOptionDefine.lua`，`SetTalk` 的第 1 个参数为 `TalkType`：
  - `0`：角色说（NPC/其他旅人正常发言）
  - `1`：主角说（魔王对外正常说出的话）
  - `2`：**主角想**（官方枚举定义为“主角想”，对应**灰色对话框**）
- **规范**：
  - 当 `TalkType == 2` 时，发言人统一输出为：  
    `**魔王**（思考）：「……」`
  - 正常发言则输出为：  
    `**魔王**：「……」`

### 3.3 三类交互抉择分支清洗机制
官方 Lua 剧本中共有三类玩家交互指令，需彻底剔除 UI 预制体名字与引擎跳转标签：
1. **重大分支抉择 (`SetMajorChoice`)**：
   - 提取顶层的提问句（如 `该选哪个呢？`、`菲莱公司的未来，要怎么走呢？`）。
   - 将每个分支解析为 `【标题】: 【副标题/说明】`。
   - 剔除 `AvgChoice_item_*`、`E101`、`c`、`020` 等布局参数。
   - 渲染模板：
     ```markdown
     > **[重大抉择：该选哪个呢？]**
     > - **趁着夜色潜入**：没有计划的计划就是好计划
     > - **让密涅瓦侦查**：有算胜无算，多算胜少算
     > - **考虑其他办法**：藏在箱子里混进去
     ```
2. **性格回答抉择 (`SetPersonalityChoice`)**：
   - 提取 3 种不同性格/态度的回复选项，渲染为：
     ```markdown
     > **[玩家抉择：我该怎么回答她呢]**
     > - 你就是管理采购商店的布洛可吧？
     > - 我第一次来采购商店，你是谁？
     > - 光顾着领每日奖励了，没想到商店里居然有人。
     ```
3. **终端通讯短信抉择 (`SetPhoneMsgChoiceBegin`)**：
   - 过滤 `avg3_100` 标记，格式化为 `> **[通讯回复抉择]**`。

---

## 四、 静态站方案：纯 Python 生成 `site/`

站点由三个脚本负责，全部只依赖标准库，不需要 npm：

| 脚本 | 输入 | 输出 |
|---|---|---|
| `scripts/build_story.py` | `data/` 解包表 + AVG 剧本 | `story_docs/`（Markdown）+ `story_docs/_data/*.json`（结构化侧车，含节点图坐标） |
| `scripts/graph_layout.py` | 章节点（`sid/story_id/parents/code`） | 列、轨道、像素坐标（纯函数，无 IO） |
| `scripts/build_site.py` | `story_docs/` + `_data/` | `site/`（HTML + `assets/tokens.css` + `assets/site.js` + `data/search.js`） |

内容真源是 `story_docs/` 的 Markdown（它已被逐句校验过），`scripts/md2html.py` 只做本站
用到的那一小套 Markdown 语法 → HTML，因此不存在"第二套渲染器"与产物漂移的问题。

**主线节点图**：边取 `Story.ParentStoryId`，卡面编号取 `Story.Index` 的文案，章头取
`StoryChapter` 的 `Name/Desc/ChapterYear`。列 = 最长路径深度，轨道 = 分叉围绕父节点上下展开、
汇合取父轨道均值，一遍重心扫描降交叉。坐标写进 `chapters.json`，页面只是把卡片按坐标摆好、
连线画在一张扁平 SVG 里。

**已知边界（不要当成 bug）**：
- 表 `StoryChapter.Id` 与游戏内章号差一章（Id 7 = 特别篇、Id 8 = 第七章），站内按游戏内章号显示。
- 官方界面每条时间槽属于哪一列写在 UI 预制体里，解包表内没有，所以节点时间条取该关剧本自己的
  场景头（`猎月 14日 10:36`），不冒充官方的按列分组文案。
- 特别篇 12 行全无 `ParentStoryId`，官方就没记录连线，页面按编号顺序列出并注明。
- 游戏右下角"直觉/分析/混沌"百分比来自玩家存档，表里只有三轴定义，本站不显示数值。

VitePress 作为备选保留在 `package.json` 的 `docs:*` 脚本里，未安装依赖，也不参与当前构建。

## 五、 构建与本地预览

```bash
python scripts/build_story.py && python scripts/build_site.py   # 或 npm run build
python tests/story/validate_story.py && python tests/story/validate_site.py   # 契约 A–L
python -m http.server 8000 --directory site                     # 或 npm run serve
```
直接双击 `site/index.html` 也能完整使用：检索索引以 `site/data/search.js` 形式内嵌，
绕开了 `file://` 不能 `fetch()` 本地 JSON 的限制。

## 六、 部署

站点是纯静态目录，任何静态托管都行，两种常见做法：

1. **CI 里构建**（推荐，仓库不带产物）：构建命令 `python scripts/build_story.py && python scripts/build_site.py`，
   输出目录 `site`，运行时选 Python 3.10+。Cloudflare Pages 与 Vercel 都支持。
2. **本地构建后上传**：把 `site/` 整目录拖进 Cloudflare Pages / 对象存储 / 任意静态空间。

若改用 VitePress 前端，需要重写第四节并让 `docs/.vitepress/` 消费同一份 `_data/*.json`——
数据结构与渲染层是解耦的，换栈不必重跑解析。

## 七、 后续游戏版本更新与日常维护规范

当官方推出新主线或新活动时，按以下三步无痛更新：
1. **替换官方解包资产**：将最新解包出的 `Story.json`、`ActivityStory.json` 与新的 Lua 剧本放入 `data/` 目录。
2. **运行构建脚本**：再次执行 `python scripts/build_wiki.py`，增量关卡与新角色小节将自动生成，Mermaid 流程图自动重算。
3. **Git 提交并推送**：
   ```bash
   git add docs/
   git commit -m "feat: 更新主线第十章与新活动剧情"
   git push origin main
   ```
   Cloudflare Pages 或 Vercel 将通过 Webhook 自动触发部署，30 秒内全站自动同步更新。
