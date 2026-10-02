# 《星塔旅人》高保真全量剧情与剧本知识库 (Stella Sora Chronicle Wiki)

> **全网首创**：首个 1:1 官方解包高保真《星塔旅人》逐句台词文本、多分支抉择支、灰色心理独白与 DAG 流程拓扑导图知识库。

---

## 🌟 核心特性
- 📖 **100% 官方数据源高保真**：覆盖公测全 10 大主线章节、604 个独立小节、11 个大型活动剧情，支持原生 Ruby 注音（`<ruby><rt>`）精准对齐。
- 🎭 **沉浸式台词与角色还原**：
  - **正名“魔王”**：彻底修复底层开发代号“塞拉”与 `==PLAYER_NAME==`，忠实呈现主角身份。
  - **精准区分思考与发声**：基于官方引擎 `TalkType = 2`（主角想），全库 1,185 处灰色气泡心理活动赋予 `**魔王**（思考）` 标识。
  - **三类分支抉择净化**：重大抉择（带副标题）、性格倾向抉择、终端短信回复全量清洗。
- 🗺️ **官方同款 SVG 拓扑节点图**：按官方 `Story.ParentStoryId` 与活动条件表复原游戏内主线与活动连线图谱——分叉抉择、终局归属、平移缩放、列单调性。
- ⚔️ **全自动独立战斗关卡档案**：针对主线特别篇及 11 个活动中无 AVG 剧本的纯战斗关卡，自适应生成包含官方关卡代号、解锁条件、简介文案与双向流程导航的独立档案页。
- ⚡ **零依赖静态站**：`python scripts/build_site.py` 直接生成 549 篇纯静态网页至 `site/`，内嵌即时搜索，双击 `index.html` 或任意静态空间均可直接离线运行。

---

## 📁 目录结构与脚本分类

```text
星塔旅人剧情知识库/
├── data/                       # 官方解密数据源（配置表与 Lua 剧本，不入库）
├── story_docs/                 # 剧情 Markdown 产物 + _data/ 结构化侧车（评审与校验基线）
├── site/                       # 生成的静态站产物（549 个 HTML 页面，纯前端离线运行）
├── docs/                       # 早期全量 Markdown（保留作校验对齐基线）
├── scripts/                    # 工具与生成脚本库（详见下方分类）
│   ├── build_story.py          # 【数据管道】八族剧本提取 → story_docs/ + _data/*.json
│   ├── build_site.py           # 【主构建器】读取 story_docs 与元数据 → 编译生成 site/ 全站
│   ├── site_templates.py       # 【模板引擎】全站 HTML 模板（拓扑地图、剧本阅读、战斗档案等）
│   ├── site_css.py             # 【样式模块】设计系统（暗色/浅色、牌板、SVG拓扑、响应式）
│   ├── site_js.py              # 【前端交互】毫秒级即时检索、拓扑图缩放拖拽、主题切换
│   ├── md2html.py              # 【解析模块】轻量 Markdown 转 HTML，支持 <r=注音> 渲染
│   ├── graph_layout.py         # 【算法模块】DAG 章节拓扑分层布局几何纯函数
│   ├── build_wiki.py           # 早期原型全量脚本（保留作为历史比对基准）
│   └── run_benchmark.py        # 离线事实检索评估基准
├── tests/story/                # 自动化测试与质量契约验证器 A–M（含变异注入测试）
├── AI_HANDOVER_GUIDE.md        # 逆向提取与数据契约交接手册
├── OPERATION_MANUAL.md         # 运维、构建与版本迭代操作手册
├── package.json
└── README.md
```

---

## 🚀 快速开始

### 0. 剧情管道 + 静态站（当前在做的）
```bash
python scripts/build_story.py     # → story_docs/（507 个剧本页 + _data/*.json 结构化侧车）
python scripts/build_site.py      # → site/（纯 Python 生成，零 npm 依赖）
python tests/story/validate_story.py && python tests/story/validate_site.py   # 契约 A–K
```
覆盖八族剧情：主线 185、活动 105、角色个人剧情 120、星塔 NPC 好感 8、唱片 24、故事集 56、
序章 2、无关卡引用的战斗气泡 6；逐句之外还带场景卡、聊天正文、抉择/回应块、战斗气泡，
以及抉择分支的互斥归属标记。主线按官方 `ParentStoryId` 画成游戏那种节点图。
包里剩下 81 个剧本未渲染：`PM_*` 63 个是**心链**聊天全文（外部已有收录，决定不做），
`DP_*` 17 个是委托玩法结算短演出、`GD_gacha` 1 个是抽卡小演出（均待决），
清单与已知遗漏见 `AI_HANDOVER_GUIDE.md` 第 7.5 节，逐族覆盖数字由 `story_docs/_coverage.md` 自动给出。

本地直接双击 `site/index.html` 就能看（检索索引以 `data/search.js` 内嵌，不受 file:// 限制）；
要挂到端口：`python -m http.server 8000 --directory site`。

### 1. 重新生成早期全量知识库（非剧情内容）
```bash
python scripts/build_wiki.py
```
> 输出结果将自动覆盖 `docs/` 目录。剧情部分已被上面取代，这里只剩数值/纹章/世界观，
> 保留它是为了校验器 A 契约的"新旧产物逐句对齐"基线。

### 2. 运行基准自动化测试
```bash
python scripts/run_benchmark.py
```
> 验证 8 组核心事实（包含复杂多分支、约会台词、材料、词条）检索准确率，预期为 **100% 通过**。

### 3. 备选：VitePress 前端
```bash
npm install && npm run docs:dev     # 需先安装依赖；当前站点并不依赖它
```

---

## 🤝 开发者与 AI 交接
如果您是后续接手此项目的 AI 助手或新开发者，请**务必先阅读**根目录下的：
- [AI_HANDOVER_GUIDE.md](./AI_HANDOVER_GUIDE.md)：涵盖客户端 XXTEA 解密、数据表映射、AVG 状态机规则与踩坑经验。
- [OPERATION_MANUAL.md](./OPERATION_MANUAL.md)：涵盖 VitePress 静态站配置、自动化部署与日常版本迭代规范。
