> 《建站与运维操作手册》第 五、六 章正文分册；总索引与「按需索取」表见 [OPERATION_MANUAL.md](../OPERATION_MANUAL.md)。章节编号沿用原书，跨章引用（如「见 3.6」）按索引定位。

## 五、 构建与本地预览

```bash
# 剧情库：解析上游数据 -> story_docs/（md + 侧车）
python scripts/build_story.py            # 或 python scripts/story/build_story.py

# 静态站：story_docs/ -> site/
python scripts/build_site.py             # 或 python scripts/site/build_site.py

# 契约回归（两个都要跑，都要全绿）
python tests/story/validate_story.py     # story_docs 侧
python tests/story/validate_site.py      # site 侧

# 单元测试
python -m pytest tests -q

# 本地预览
python -m http.server 8000 --directory site
```

直接双击 `site/index.html` 也能完整使用：检索索引以 `site/data/search.js` 形式内嵌，
绕开了 `file://` 不能 `fetch()` 本地 JSON 的限制。

`build_story.py` 每次运行**先删后写** `story_docs/`，所以不要在里面放任何手工文件。
`--out <目录>` 可把产物写到别处（仅供校验用，例如诊断侧车的临时目录重建），默认仍是 `story_docs/`。

## 六、 部署

站点是纯静态目录，任何静态托管都行，两种常见做法：

1. **CI 里构建**（推荐，仓库不带产物）：构建命令 `python scripts/build_story.py && python scripts/build_site.py`，
   输出目录 `site`，运行时选 Python 3.10+。Cloudflare Pages 与 Vercel 都支持。
2. **本地构建后上传**：把 `site/` 整目录拖进 Cloudflare Pages / 对象存储 / 任意静态空间。

若改用 VitePress 前端，需要重写第四节并让 `docs/.vitepress/` 消费同一份 `_data/*.json`——
数据结构与渲染层是解耦的，换栈不必重跑解析。
