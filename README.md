# 《星塔旅人》高保真全量剧情与剧本知识库 (Stella Sora Chronicle Wiki)

> **全网首创**：首个 1:1 官方解包高保真《星塔旅人》逐句台词文本、多分支抉择支、灰色心理独白与 DAG 流程拓扑导图知识库。

---

## 🌟 核心特性
- 📖 **100% 官方数据源高保真**：覆盖公测全 10 大主线章节、604 个独立小节、11 个大型活动剧情。
- 🎭 **沉浸式台词与角色还原**：
  - **正名“魔王”**：彻底修复底层开发代号“塞拉”与 `==PLAYER_NAME==`，忠实呈现主角身份。
  - **精准区分思考与发声**：基于官方引擎 `TalkType = 2`（主角想），全库 1,185 处灰色气泡心理活动赋予 `**魔王**（思考）` 标识。
  - **三类分支抉择净化**：重大抉择（带副标题）、性格倾向抉择、终端短信回复全量清洗。
- 🗺️ **拓扑导图 (Mermaid DAG)**：每章自动生成有向无环流程图，清晰呈现分支与多结局走向。
- ⚡ **开箱即用的静态站与离线全文检索**：完美适配 VitePress / Cloudflare Pages / Vercel。

---

## 📁 目录结构
```text
星塔旅人剧情知识库/
├── data/                       # 官方解密数据源
│   ├── StellaSoraData/         # 二进制配置表 JSON
│   └── ss_lua/                 # 官方 AVG 剧本 Lua 脚本
├── docs/                       # 知识库 Markdown 核心文档 (也是 VitePress 站点根目录)
│   ├── basics/                 # 世界观设定与组织势力
│   ├── story/
│   │   ├── main/               # 主线剧情 (按章节及独立小节划分)
│   │   └── events/             # 活动剧情 (按活动划分)
│   ├── characters/             # 40 位旅人突破档案与专属约会剧情
│   └── search/                 # 倒排索引与别名表
├── scripts/
│   ├── build_story.py          # 【剧情专用·当前主线】全部剧情族 → story_docs/
│   ├── build_wiki.py           # 早期全量构建脚本（含数值/纹章/索引，剧情部分已被上面取代）
│   └── run_benchmark.py        # 离线验证测试套件 (8/8 事实检索基准)
├── AI_HANDOVER_GUIDE.md        # 面向后续 AI 与开发者的逆向提取交接手册
├── OPERATION_MANUAL.md         # 部署运维与 VitePress 建站手册
├── package.json
└── README.md
```

---

## 🚀 快速开始

### 0. 剧情管道 v2（当前在做的）
```bash
python scripts/build_story.py     # → story_docs/，507 个剧本页 + _coverage.md + _battle_reconciliation.md
```
覆盖八族剧情：主线 185、活动 105、角色个人剧情 120、星塔 NPC 好感 8、唱片 24、故事集 56、
序章 2、无关卡引用的战斗气泡 7；逐句之外还带 472 张场景卡、559 行聊天正文、
474 个 `SetChoiceBegin` 抉择/回应、399 条战斗气泡，以及抉择分支的互斥归属标记。
包里剩下 81 个剧本（`PM_*` 手机聊天 63 / `DP_*` 委托演出 17 / `GD_gacha` 1）待决，
清单与已知遗漏见 `AI_HANDOVER_GUIDE.md` 第 7.5 节，逐族覆盖数字由 `story_docs/_coverage.md` 自动给出。

### 1. 重新生成全量知识库
```bash
python scripts/build_wiki.py
```
> 输出结果将自动覆盖 `docs/` 目录。

### 2. 运行基准自动化测试
```bash
python scripts/run_benchmark.py
```
> 验证 8 组核心事实（包含复杂多分支、约会台词、材料、词条）检索准确率，预期为 **100% 通过**。

### 3. 本地启动静态站预览 (VitePress)
```bash
npm install
npm run docs:dev
```
访问 `http://localhost:5173` 即可浏览。

---

## 🤝 开发者与 AI 交接
如果您是后续接手此项目的 AI 助手或新开发者，请**务必先阅读**根目录下的：
- [AI_HANDOVER_GUIDE.md](./AI_HANDOVER_GUIDE.md)：涵盖客户端 XXTEA 解密、数据表映射、AVG 状态机规则与踩坑经验。
- [OPERATION_MANUAL.md](./OPERATION_MANUAL.md)：涵盖 VitePress 静态站配置、自动化部署与日常版本迭代规范。
