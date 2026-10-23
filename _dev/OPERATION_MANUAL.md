# 《星塔旅人》全量剧情与剧本知识库：独立建站与运维操作手册（索引）

> **文档版本**：v2.1.0（2026-10-23：拆分为渐进式披露的索引 + `_dev/manual/` 主题分册，章节编号不变；除第十章陈旧条目修正外正文与 v2.0.0 一致）
> **数据基准**：官方公测版本资产（涵盖主线各章节、限时活动、旅人专属档案与好感剧情、秘闻与故事集）
> **项目定位**：全网首个且唯一的《星塔旅人》1:1 逐句台词、分支抉择与拓扑导图高保真静态剧情数据库。
> **配套文档**：实现细节、踩坑与判据见 `_dev/AI_HANDOVER_GUIDE.md`（索引）；本手册讲"怎么建站、怎么运维"。
> **组织方式**：本文件只是索引，各章正文在 `_dev/manual/` 分册。

---

## 按需索取

| 你要做什么 | 看哪里 |
|---|---|
| 了解项目定位、架构与数据流 | [ch1-2](manual/ch1-2-overview.md)（背景调研、架构图、四条设计主线、"规模数字不写死"纪律） |
| 了解底层解析规范（正名/独白/分支） | [ch3](manual/ch3-parse-spec.md) |
| 查 `scripts/` 各模块职责 | [ch4](manual/ch4-modules.md)（全模块表 + 主线节点图 + 已知边界） |
| 本地构建、预览、部署 | [ch5-6](manual/ch5-6-build-deploy.md) |
| 官方出新版本后的更新维护 | [ch7](manual/ch7-maintenance.md)（五步标准流水线） |
| 校验变红 / 产物异常排查 | [ch8](manual/ch8-troubleshooting.md)（两套契约集、常见故障对照表、兜底三纪律） |
| `docs/` 目录是什么、能不能删 | [ch9](manual/ch9-legacy-docs.md)（处置纪律：不编辑、不删除） |

## 章节索引（编号与原全书一致）

| 章 | 标题 | 分册 |
|---|---|---|
| 一 | 背景与全网现状调研 | [manual/ch1-2-overview.md](manual/ch1-2-overview.md) |
| 二 | 知识库核心架构与数据流 | 同上 |
| 三 | 官方底层解析技术规范（3.1 正名 / 3.2 TalkType / 3.3 抉择与历史条件） | [manual/ch3-parse-spec.md](manual/ch3-parse-spec.md) |
| 四 | 静态站方案：纯 Python 生成 `site/` | [manual/ch4-modules.md](manual/ch4-modules.md) |
| 五 | 构建与本地预览 | [manual/ch5-6-build-deploy.md](manual/ch5-6-build-deploy.md) |
| 六 | 部署 | 同上 |
| 七 | 后续游戏版本更新与日常维护规范 | [manual/ch7-maintenance.md](manual/ch7-maintenance.md) |
| 八 | 契约校验与故障排查（8.1 契约集 / 8.2 故障对照 / 8.3 兜底与诊断） | [manual/ch8-troubleshooting.md](manual/ch8-troubleshooting.md) |
| 九 | 遗留产物 `docs/` 说明 | [manual/ch9-legacy-docs.md](manual/ch9-legacy-docs.md) |
