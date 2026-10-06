# -*- coding: utf-8 -*-
"""星塔旅人剧情编译管线。

分层（管线重构 Phase 1 起，详见 _dev/AI_HANDOVER_GUIDE.md 第七/八章）：

  Stage 1 前端    lua_lexer → lua_parser → command_ir
  Stage 2 语义    passes/fold_animations、passes/resolve_speakers、
                  passes/attribute_branches → PageDoc IR（pagedoc）
  Stage 4a 后端   render_md（人审真源 Markdown，字节锁）
  横切            diagnostics（Phase 3 引入）、markup（Phase 3 引入）

站点 HTML 后端在 scripts/site/render_html.py（Phase 2 引入），与本包共享
落盘的 PageDoc 侧车（story_docs/_beats/）。
"""
