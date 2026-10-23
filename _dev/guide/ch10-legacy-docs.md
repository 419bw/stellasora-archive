> 《AI 技术交接手册》第 十 章正文分册；总索引与「按需索取」表见 [AI_HANDOVER_GUIDE.md](../AI_HANDOVER_GUIDE.md)。章节编号沿用原书，跨章引用（如「见 3.6」）按索引定位。

## 十、 遗留产物与目录处置

### `docs/` —— 早期原型生成器的冻结输出

`docs/` 约 5 MB、500+ 文件，**仍在 git 跟踪下**。它的来历与今天的用途：

- **初衷**：`scripts/tools/build_wiki.py`（原名 `build_wiki_knowledge_base.py`）是要把剧情库做成
  "渐进式披露、便于 AI 检索"的知识库（Wiki-grade progressive disclosure knowledge base）——
  按世界观/角色/剧情分层组织，让读者和 AI 都能逐层深入，而不是一屏铺开。
- **为什么不再是主链路**：主链路后来转向 `story_docs/`（人审 Markdown 真源）+ `scripts/site/`
  （纯 Python 静态站）+ `_beats/`（PageDoc IR 双后端）方案，可校验性（契约 A–P）和发布可控性
  （release gate）都更强。`build_wiki.py` 的正则参数解析还有两个硬缺陷（见 7.1），已不适合继续演进。
- **今天的用途**：仅历史资料。原 **A / A2 历史对照契约**已于 2026-10-20 退役——上游持续加章后
  `docs/` 与上游表不再覆盖同一批关卡，基线必然失配；绝对真值部分由 E 组承担。改完产物用
  `git diff -- story_docs/` 自查即可（见 8.3）。
- **处置纪律**：
  1. **不要手工编辑** `docs/`——它只是历史资料，改了没有校验器会报，但会污染历史记录。
  2. **不要删除** `docs/`——它仍在 git 跟踪下，是早期知识库形态的历史存档。
  3. 它是可再生的（`python scripts/tools/build_wiki.py`，输出到 `docs/`），但重新生成等于
     重置历史基线，做之前先想清。
  4. 它**不参与** CI 构建，也不随站点发布。
- 如果将来要做 AI 检索向的知识库，正确做法是基于 `story_docs/_data/*.json` 侧车另做一个投影，
  而不是复活 `build_wiki.py`。
