# 《星塔旅人》剧情档案 (Stella Sora Archive)

在线访问：[https://stellasora-archive.pages.dev/](https://stellasora-archive.pages.dev/)  
开源仓库：[https://github.com/419bw/stellasora-archive](https://github.com/419bw/stellasora-archive)

---

## 阅读提示与剧透预警

> **剧透预警**：本档案库默认完整展开所有主线及活动剧情的全部交互抉择、分支路线与多重结局，包含全流程剧透。尚未通关或希望亲自探索剧情的玩家建议谨慎查阅。
> 
> **收录范围说明**：游戏内仅有 CG 动画演示而无台词字幕的纯过场片段，不包含在游戏剧本数据中，因此不会收录在站内。本站专注于完整收录游戏数据源里包含对白文本、角色内心独白、分支选项与战斗气泡的剧情内容。

---

## 档案库收录内容

本站收录公测版本以来的全量文本与分支剧情：

- **主线全章节（含特别篇）**：主线各章节及特别篇《谜影的序曲》，还原游戏内交互式拓扑连线图，支持分支抉择、多结局推演与纯战斗档案。
- **活动剧情**：各期主题活动的关卡剧情全文与阶段收录，支持活动专属分支拓扑。
- **角色个人剧情**：旅人专属故事，好感等级逐级解锁的专属剧情全文本。
- **星塔 NPC 羁绊**：星塔驻留人员与常驻 NPC 的日常好感羁绊剧情。
- **秘闻**：收录秘闻剧本与散文、故事集日常回忆与侧写。
- **战场气泡与战斗档案**：随战斗阶段推进的角色实时气泡对白，以及零对白战斗关卡的独立档案与流程跳转。

---

## 本地构建

```bash
# 1. 从数据源重新解析并生成 Markdown 与拓扑侧车
python scripts/story/build_story.py

# 2. 编译全量静态网页
python scripts/site/build_site.py

# 3. 运行自动化契约校验（确保 0 漂移与 0 违例）
python tests/story/validate_site.py
```

如需本地预览，可进入 `site/` 目录直接用浏览器打开 `index.html`（离线检索已内嵌）。

---

## 自动化同步与持续部署 (CI/CD)

本项目配置了完整的 GitHub Actions 持续集成与部署工作流（`.github/workflows/deploy.yml`）：
- **定时监控**：每 6 小时自动比对上游数据镜像仓库的最新提交。
- **自动同步与构建**：发现上游数据更新时，自动提取更新差异、重新构建剧本库与静态站点，并通过所有断言测试。
- **自动部署**：构建完成后自动推送到 Cloudflare Pages 全球边缘网络，确保在线网站与游戏更新保持同步。

推送（push）事件下的流水线：收集提交生成更新日志 → 全量单元测试 → 两份契约校验 → 构建静态站 → 部署。
定时（schedule）事件改为跑 `scripts/automation/auto_sync.py`，由它自己完成构建与提交。

`auto_sync.py` 以 `check=True` 运行生成器，因此**生成器任何未捕获异常都会让整条流水线停止**。管线的对应方针是"降级不崩 + 必登记"，详见 `_dev/AI_HANDOVER_GUIDE.md` 的「兜底与诊断策略」一节。

---

## 免责声明 (Disclaimer)

1. **非官方非关联声明**：本站为玩家自制的非官方资料整理工具，与游戏官方运营团队无任何关联。
2. **知识产权与版权归属**：YOSTAR GAMES（悠星网络）拥有游戏的原始资产，站内涉及的游戏文案、剧本、立绘、头像、图标等素材版权均归原发行商及原版权方所有。
3. **交流学习与非盈利用途**：本站仅供剧情研读、世界观考据与个人交流学习使用，100% 为非盈利性粉丝项目，不以任何形式盈利，不提供素材下载与游戏客户端修改。如因使用相关内容产生任何争议或损失，本站概不负责。
4. **侵权反馈与联系**：若官方团队或版权所有方认为本站收录内容有所不妥，请联系维护者邮箱 `1950537289@qq.com`，我们将第一时间配合调整或删除。

---

## 授权说明 (License)

本仓库按组成部分采用分包授权：

| 范围 | 协议 |
|---|---|
| 仓库默认，含 `story_docs/` 等由上游数据生成的再分发产物 | [GNU General Public License v3.0](LICENSE) |
| `scripts/`、`tests/`、CI 配置等原创构建代码 | GPL-3.0，同时可由版权人另行按 MIT 条款单独授权使用 |
| 游戏内文本、立绘、头像等素材 | 版权归 YOSTAR GAMES（悠星网络）所有，本仓库不授予任何权利 |

**关于 GPL-3.0 覆盖的数据产物**：

- `story_docs/` 与 `story_docs/_beats/` 的内容由上游 GPL-3.0 数据仓库经本仓库 `scripts/story` 管线清洗、折叠、结构化后生成，属于 GPL-3.0 许可的修改版再分发，完整许可证见根目录 [LICENSE](LICENSE)，修改类型清单与知识产权声明见根目录 [NOTICE](NOTICE)。
- 再分发本仓库内容时，须保留相同协议并注明来源；对产物的修改处需作显著标注。
- 上游 [StellaSoraData](https://github.com/AutumnVN/StellaSoraData) 与 [ss-lua](https://github.com/MakoStar/ss-lua) 同样为 GPL-3.0，版权归各自维护者所有。

---

## 数据来源与上游鸣谢 (Upstream Data Sources)

本档案库的高保真内容生成依赖社区开源维护的数据镜像。在此向以下优秀的上游开源项目致以诚挚谢意：

- **[StellaSoraData](https://github.com/AutumnVN/StellaSoraData)**（由 AutumnVN 维护）：整理并维护了游戏内的结构化数据配置与中文文案表，涵盖关卡、章节、好感度与活动等信息。
- **[ss-lua](https://github.com/MakoStar/ss-lua)**（由 MakoStar 维护）：整理了游戏内 AVG 剧情脚本与角色相关配置，使本项目能够还原逐句对话、内心独白与分支抉择。

---

## 最近更新记录

### 2026-10-09
- fix(story): 更正终局已阅读比例文案
- feat(story):支持解析历史条件分支

---

## 项目架构与脚本目录

项目采用清晰的职责分层架构（数字规模一律不写死，以 `story_docs/_data/*.json` 的 `meta` 字段与两个校验器的输出为准）：

```
stellasora-archive/
├── story_docs/              # Markdown 真源文档库与结构化侧车数据（build_story 全量生成，勿放手工文件）
│   ├── _data/               # chapters/sections/search/personality 等侧车（meta 带权威计数）
│   ├── _beats/              # PageDoc IR 侧车：md 与 HTML 两个后端共同的上游
│   ├── _battle_reconciliation.md   # 人读版对账报告（代号错配/气泡缺失/未引用 BBm）
│   └── _diagnostics.json    # 上游数据异常与编译器兜底的机器可读登记（口径见 pipeline/diagnostics.py 的 CATEGORIES）
├── docs/                    # 遗留生成器的冻结输出，被 git 跟踪；仅供历史对照契约，见下文说明
├── scripts/                 # 构建与维护脚本工具集
│   ├── story/               # 剧情抽取与拓扑计算模块
│   │   ├── build_story.py   # 编排器：解析上游数据源 -> 生成 Markdown 与侧车数据
│   │   ├── release_gate.py  # 未开放内容门控（按官方 OpenTime/StartTime 过滤发布面）
│   │   ├── graph_layout.py  # DAG 分层拓扑几何纯函数（坐标与连线计算）
│   │   └── pipeline/        # 编译管线（自上而下单向依赖，无环）
│   │       ├── lua_lexer.py / lua_parser.py   # Stage 1 前端：Lua 词法 + 递归下降语法 -> T 表
│   │       ├── command_ir.py                  # 带稳定 idx 的命令序列（动画帧折叠的身份基准）
│   │       ├── passes.py      # Stage 2 语义：帧折叠 / 说话人解析 / 抉择分支归属 / 历史条件标记
│   │       ├── conditions.py  # 历史条件（已阅读/已选择/终局比例）的中文标签与共享正文合并
│   │       ├── speakers.py    # 说话人 id -> 显示名（预置表 + 最长点分前缀兜底）
│   │       ├── markup.py      # 内联标记编译：性别变体 / 注音 / 强调 / 官方词表 / 未知标记保留原文
│   │       ├── text_rules.py  # 文本清洗与动画帧签名比对
│   │       ├── diagnostics.py # 兜底统一登记：所有降级都进同一个收集器与分类注册表
│   │       ├── pagedoc.py     # PageDoc IR（md/HTML 双后端的共同输入）
│   │       ├── render_md.py   # Stage 4a 后端：人审真源 Markdown（字节锁）
│   │       └── domain.py      # 主角 id / 显示名等官方口径常量
│   ├── site/                # 静态站点生成引擎
│   │   ├── build_site.py    # 驱动模板生成全部 HTML 静态页面（消费前先过 release_gate）
│   │   ├── site_templates.py# 拓扑图、剧情阅读牌板、战斗档案等页面模板
│   │   ├── site_css.py      # 设计规范 Tokens 与全局样式
│   │   ├── site_js.py       # 离线检索、拓扑图手势交互等前端脚本
│   │   └── render_html.py   # PageDoc 侧车（_beats/*.json）-> HTML 正文与 Ruby 注音
│   ├── automation/          # 自动化持续集成模块
│   │   ├── auto_sync.py     # 上游数据比对、增量同步与 CI 发版（check=True，故生成器不可抛异常）
│   │   └── changelog_from_commits.py  # push 事件驱动的提交变更日志
│   └── tools/               # 辅助与基准测试工具
│       ├── run_benchmark.py # 耗时与解析性能基准压测
│       ├── golden_snapshot.py  # 黄金快照（对拍旧实现）
│       └── build_wiki.py    # 早期原型生成器，输出 docs/；已不在主链路，见下文说明
├── site/                    # 编译输出目录（不纳入版本控制，本地构建后生成）
├── tests/                   # 测试套件
│   ├── story/               # 地面真相严格契约与变异测试（两份校验器 + pytest）
│   └── automation/          # 自动化与变更日志单元测试
├── _dev/                    # 维护者文档：AI_HANDOVER_GUIDE.md（实现细节与踩坑）、OPERATION_MANUAL.md（操作手册）
└── .github/workflows/       # GitHub Actions 自动化构建与定时同步流水线
```

### 关于 `docs/`（重要，不要删）

`docs/` 是**早期原型生成器** `scripts/tools/build_wiki.py` 的冻结输出，约 5 MB，**仍在 git 跟踪下**。它的初衷是把剧情库做成"渐进式披露、便于 AI 检索"的知识库（Wiki-grade progressive disclosure knowledge base），后来主链路切换到 `story_docs/` + 静态站方案，`docs/` 便不再参与构建。

它今天唯一的用途是：`tests/story/validate_story.py` 的历史对照契约以它为基线，用来盯住"新实现没有悄悄改掉已评审内容"。因此：

- **不要手工编辑** `docs/`（改了会让历史对照失真）；
- **不要删除** `docs/`（对照契约会直接失败）；
- 它是可再生的（`python scripts/tools/build_wiki.py`），但重新生成前先想清是否要重置历史基线。

> 提示：在 `scripts/` 根目录下提供了 `build_site.py`、`build_story.py` 与 `auto_sync.py` 的轻量转发器，直接在根目录执行旧命令依然 100% 兼容。`build_wiki.py` **没有**转发器，需写全 `scripts/tools/build_wiki.py`。
