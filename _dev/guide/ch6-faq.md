> 《AI 技术交接手册》第 六 章正文分册；总索引与「按需索取」表见 [AI_HANDOVER_GUIDE.md](../AI_HANDOVER_GUIDE.md)。章节编号沿用原书，跨章引用（如「见 3.6」）按索引定位。

## 六、 常见踩坑记录与 FAQ（交接备忘）
1. **Q：为什么有的关卡只有概要，没有“## 3. 详细剧情与逐句台词”？**  
   **A**：检查该关卡的 `s.get('IsBattle')`。如果是星塔纯战斗关卡（如 `BT01`、`BT02`），官方数据中本就没有配置 `AvgLuaName` 剧本，因此只展示战斗目标与跳过概要，绝不要胡编台词。
2. **Q：为什么某个小节生成出来的文件名带乱码？**  
   **A**：Windows 控制台默认 GBK 编码，运行 Python 时必须在最顶部执行：  
   `sys.stdout.reconfigure(encoding='utf-8')`，写入文件必须指定 `open(..., encoding='utf-8')`。
3. **Q：如何确保没有遗漏小节？**  
   **A**：不要数文件——文件数会随上游数据变。看 `story_docs/_coverage.md`（每次构建自动重算的
   逐族覆盖表 + 未渲染清单）与 `story_docs/_data/sections.json` 的 `meta.pages`，二者与
   `validate_story.py` 的 G2 对账（"声明页数 == 磁盘 md 数 == 有剧本的节点数"）一致才算完整。
4. **Q：前端渲染时 Mermaid 图报错？**  
   **A**：Mermaid 节点标签内如果包含括号、连字符等字符，必须加英文双引号包裹（例如 `Node["01_序幕 (上)"]`），否则解析器会语法报错。
