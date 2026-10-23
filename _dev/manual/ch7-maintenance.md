> 《建站与运维操作手册》第 七 章正文分册；总索引与「按需索取」表见 [OPERATION_MANUAL.md](../OPERATION_MANUAL.md)。章节编号沿用原书，跨章引用（如「见 3.6」）按索引定位。

## 七、 后续游戏版本更新与日常维护规范

当官方推出新主线或新活动时，按以下标准流水线更新：

1. **替换官方解包资产**：将最新解包出的配置表放入 `data/StellaSoraData/CN/bin/` 与文案目录，将新 AVG 剧本放入 `data/ss_lua/.../Config/`。
2. **运行构建脚本**：
   ```bash
   python scripts/build_story.py    # 提取官方数据 -> story_docs/ 与 _data/*.json
   python scripts/build_site.py     # 编译静态站 -> site/
   ```
3. **运行契约回归测试**（任一变红都不要提交）：
   ```bash
   python tests/story/validate_story.py
   python tests/story/validate_site.py
   python -m pytest tests -q
   ```
4. **人审 diff**：重点看 `story_docs/_diagnostics.json` 有没有新增登记——那是上游数据结构变动或
   管线兜底被触发的信号，逐条确认是"上游真变了"还是"管线该修了"（见第八章）。
5. **Git 提交并推送**：
   ```bash
   git add story_docs/ site/
   git commit -m "feat: 更新最新游戏版本剧情与剧本档案"
   git push origin main
   ```
   静态托管平台（如 Cloudflare Pages / Vercel / GitHub Pages）将自动同步最新站点。
