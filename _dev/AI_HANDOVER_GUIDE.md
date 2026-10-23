# 《星塔旅人》剧情文本逆向提取与知识库构建全流程技术交接手册（索引）

> **适用对象**：后续接手此项目的 AI 助手（如 Claude, GPT, Gemini）或开发人员
> **文档定位**：全链路工程落地手册——从数据源获取、表格与 Lua AVG 剧本关联，到清洗规则、状态机判定与 Markdown 自动化生成。
> **核心原则**：**100% 官方数据源高保真，0 幻觉、0 脑补、0 遗漏。**
> **组织方式（2026-10-23 起）**：渐进式披露——本文件只是**索引与按需索取表**，各章正文在 `_dev/guide/` 分册。
> **章节编号与原全书一致**：代码注释、提交信息里的 `3.5`、`7.6`、「兜底与诊断策略」等引用**不需要改**，按下表定位到分册即可。

---

## 按需索取

| 你要做什么 | 看哪里 |
|---|---|
| 第一次接手，建立全貌 | 本索引 → [OPERATION_MANUAL.md](OPERATION_MANUAL.md)（运维手册）→ [ch1-2](guide/ch1-2-data-sources.md)（数据源与三表映射） |
| 改解析管线 / 新增兜底 | [ch3](guide/ch3-parse-state-machine.md)：3.4 清洗标准、3.6 **兜底与诊断策略**（三条纪律）；[ch7](guide/ch7-story-pipeline.md)：7.0 DataContext 与门控 |
| 加剧本族 / 新板块 | ch7：7.4 族清单与挂载源、7.8 登记点三处；[ch8](guide/ch8-site-contracts.md)：8.0 站点侧纪律 |
| 改站点模板 / CSS | ch8：8.0（注册表 + 公共页型 + 族片段三层，CSS 只改片段不改产物） |
| 未开放内容 / 门控相关 | ch8：8.5（判据表、加新族纪律、失败开放、两个环境变量） |
| 上游剧本结构的坑 | ch3：3.5（`CG_126_03` End group 错配备案）；[ch6](guide/ch6-faq.md) FAQ |
| CI / 定时同步 / 测试分层 | [ch5](guide/ch5-cicd.md)（push 与 schedule 两条路、「单元测试必须全量」纪律、slow 标记） |
| 契约校验 / 诊断侧车排查 | ch7：7.8 判据；ch8：8.3 契约总表；ch3：3.6 分类口径 |
| 查历史决策与修订 | [ch9](guide/ch9-changelog.md) 修订记录、[ch10](guide/ch10-legacy-docs.md) `docs/` 处置、[MODULARIZATION_DESIGN.md](MODULARIZATION_DESIGN.md)（模块化设计，已完成） |

## 章节索引（编号与原全书一致）

| 章 | 标题 | 小节 | 分册 |
|---|---|---|---|
| 一 | 数据源层：开源数据规范与镜像结构 | 1.1 开源数据源仓库架构 | [guide/ch1-2-data-sources.md](guide/ch1-2-data-sources.md) |
| 二 | 数据结构与映射关系规范 | StoryChapter / Story / 剧本三表关系 | 同上 |
| 三 | 剧情解析核心状态机（关键业务逻辑） | 3.1 主角正名 · 3.2 TalkType · 3.3 抉择精准解析 · 3.4 占位符与富文本清洗 · 3.5 分支归属与汇合（含 `CG_126_03` 备案）· 3.6 **兜底与诊断策略** | [guide/ch3-parse-state-machine.md](guide/ch3-parse-state-machine.md) |
| 四 | 拓扑图构建算法（Mermaid DAG） | 历史方案；现行实现是 `graph_layout` SVG 坐标，见 8.2 | [guide/ch4-topology-mermaid.md](guide/ch4-topology-mermaid.md) |
| 五 | 自动化持续集成流水线（CI/CD） | push/schedule/dispatch、全量测试纪律、slow 分层、`STELLA_DIAG_REBUILD` | [guide/ch5-cicd.md](guide/ch5-cicd.md) |
| 六 | 常见踩坑记录与 FAQ（交接备忘） | 战斗关无剧本 / GBK 乱码 / 覆盖对账 / Mermaid 引号 | [guide/ch6-faq.md](guide/ch6-faq.md) |
| 七 | 剧情管道 v2：`build_story.py` | 7.0 DataContext · 7.1 换掉正则的原因 · 7.2 带文本的指令清单 · 7.3 战斗气泡挂接 · 7.4 已接入 13 族 · 7.5 历史条件分支 · 7.6 剩余遗漏 · 7.7 产物目录与覆盖对账 · 7.8 校验 · 7.9 台词显示通道（查清了，决定不显示） | [guide/ch7-story-pipeline.md](guide/ch7-story-pipeline.md) |
| 八 | 站点与数据契约 | 8.0 站点结构 · 8.1 数据流 · 8.2 主线节点图地面真相 · 8.3 契约总表 · 8.4 刻意没做的东西 · 8.5 未开放内容门控 | [guide/ch8-site-contracts.md](guide/ch8-site-contracts.md) |
| 九 | 修订记录 | 2026-10-02 起逐条（含 10-05 门控、10-09 历史条件、10-10 兜底统一、10-17 逸闻、10-21 回归与尖兵） | [guide/ch9-changelog.md](guide/ch9-changelog.md) |
| 十 | 遗留产物与目录处置 | `docs/` 来历、退役的 A/A2 对照、处置纪律 | [guide/ch10-legacy-docs.md](guide/ch10-legacy-docs.md) |

## 配套文档

- [OPERATION_MANUAL.md](OPERATION_MANUAL.md)：建站与运维操作手册（同为索引 + `_dev/manual/` 分册）。
- [MODULARIZATION_DESIGN.md](MODULARIZATION_DESIGN.md)：模块化改造设计文档（**状态：已完成**，历史存档；代码注释里的「设计 4.5-1 / 5.3 / 6.3」等编号引用均指向它）。
- [MCP_SERVER_PLAN.md](MCP_SERVER_PLAN.md)：MCP 服务端计划。
- `site_manifest_baseline.txt`：site 产物 sha256 字节锁基线（751 文件，验收用）。
