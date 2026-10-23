> 《建站与运维操作手册》第 八 章正文分册；总索引与「按需索取」表见 [OPERATION_MANUAL.md](../OPERATION_MANUAL.md)。章节编号沿用原书，跨章引用（如「见 3.6」）按索引定位。

## 八、 契约校验与故障排查

### 8.1 两套契约集（互不依赖，都不 import 生成器）

| 校验器 | 盯什么 | 契约组 |
|---|---|---|
| `tests/story/validate_story.py` | `story_docs/` 对剧本原文 | `B` 气泡逐阶段；`C` 行来源计数；`D`/`E`/`F` 变异 + 挂载审计 + 全树逐页（含跳过概要 vs `SetIntro[3]`）；`K` 气泡挂章；`M`/`M2` 注音保真；`M3` 单选项抉择；`N` 委托结算；`P` 诊断侧车；`Q` 逸闻笔记 |
| `tests/story/validate_site.py` | `site/` 对 `story_docs/` 与剧本 | `G`/`G2`/`G3` 节点重导与对账；`H`/`H2`/`H3` 几何与落点；`I`/`I2` HTML==md 逐句；`J`/`J2` 检索索引；`L`/`L2` 抉择角标；`M`/`M2` 锚点与气泡；`M3` 单选项；`N`/`N2` 未开放门控 |

每个契约组都带**植入变异测试**：故意改坏产物，同一套断言必须抓到。只看"正对照 PASS"不算数。

### 8.2 常见故障对照

| 现象 | 先查哪里 |
|---|---|
| 产物疑似被改坏 | 用 `git diff -- story_docs/` 自查（历史对照已退役，见第九章）；`validate_story.py` 只盯绝对真值，不再对照旧产物 |
| 报 F「计数与剧本指令数矛盾」 | 新接入的族没在 `write_coverage()` 登记，或挂载规则变了但旧文件没删（build 先删后写，重跑一次） |
| 报 K 违例 | 战斗气泡拼名规则：必须用关卡 `StoryId` 里的章号，**不是** `Story.Chapter` |
| 报未开放门控违例 | 新族/新页面没进 `release_gate`，或新侧车没在 `strip_locked_from_data()` 里加一条 |
| 报 P3「重建漂移」 | `_diagnostics.json` 与当前代码不同构：要么提交物过期（重跑 build），要么 `CATEGORIES` 改了但产物没重建 |
| `build_story.py` 中途异常退出 | 看 `_diagnostics.json` 新增了哪些登记；管线方针是"降级不崩 + 必登记"，异常说明有兜底漏网，按 3.6 补登记而不是 try/except 吞掉 |
| 定时同步 CI 失败 | `auto_sync.py` 用 `check=True`，生成器任何未捕获异常都会停摆；同上 |

### 8.3 兜底与诊断（`pipeline/diagnostics.py`）

所有"不抛异常、改变/保留原文"的降级都登记进 `story_docs/_diagnostics.json`，三条纪律：

1. **降级不崩** —— 遇到上游脏数据产出**可读**结果；
2. **必登记** —— 每次降级都过 `Diagnostics.add()/bump()/extend()`，只打 logger/print 不算登记；
3. **分类必须进注册表** —— `CATEGORIES` 是唯一真源，未注册分类名直接 `KeyError`（故意的）。

分类口径、新增分类怎么写、为什么结构型缺参不登记，见 `_dev/AI_HANDOVER_GUIDE.md` 3.6。
**人审 diff 时把 `_diagnostics.json` 的变化当作上游数据变动的信号灯。**
