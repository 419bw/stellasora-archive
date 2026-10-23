# -*- coding: utf-8 -*-
"""build_story.py —— 星塔旅人剧情知识库生成器（Markdown 后端 + 结构化侧车）。

从 GitHub 上游镜像 ``data/StellaSoraData`` 与 ``data/ss_lua`` 出发，产出
``story_docs/``（人读 Markdown + 站点消费的 JSON 侧车）。数据层（约 40 张表）与
共享服务集中在 ``context.py`` 的 DataContext；侧车记录与落盘在 ``sink.py`` 的
SidecarSink；13 个剧情族在 ``families/``（统一契约 build(ctx, sink)）；侧车汇总与
对账在 ``aggregate.py``。本文件只做编排：建 ctx/sink、按 FAMILY_ORDER 零特判
循环、收尾打印。

用法：
    python scripts/story/build_story.py [--out DIR]

--out 仅供校验用（tests/story/validate_story.py 的 P3 组重建到临时目录后逐字节
比对 _diagnostics.json）。默认 story_docs/，行为与加参数前完全一致。
"""
import sys
import os
import json
import shutil
import collections

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, SCRIPT_DIR)
import graph_layout
import chapter_path

sys.stdout.reconfigure(encoding='utf-8')
OUT = os.path.join(ROOT, 'story_docs')

# 主角域常量（PROTAG_ID/PROTAG_NAME）已随语义 pass 移入 pipeline/domain.py

# Stages whose own StoryId carries a `BTnn` battle token that disagrees with the display
# code the localization table publishes for them (upstream official labelling slip).
# Filled by build_main(), reported in _battle_reconciliation.md.
# （Phase B-12 起由 families/main.py 经 sink.record_code_mismatch 写入。）

# ============================================================== Lua table parser
# 解析器已拆分为 pipeline/lua_lexer.py（词法，token 流带 SourcePos）与
# pipeline/lua_parser.py（语法，递归下降 → T(list)）；剧本解析（command_ir 的
# build_commands）改由 context.DataContext.script_commands 提供（Phase A），
# 此处不再保留兼容壳（对 git 4496bd1 原实现做过 588 Config + AvgCharacter
# 预设全量对拍）。
from pipeline.text_rules import clean_text  # noqa: E402
# 表懒加载 + 共享服务一次构造注入（import 无副作用；族取数经 ctx）。
from context import DataContext, ScopedDataContext, lang_of  # noqa: E402
from families import FAMILY_ORDER, FAMILY_LABELS  # noqa: E402
import aggregate  # noqa: E402
import sink as sink_mod  # noqa: E402


def run_family(ctx, sink, fam_id):
    """按 FAMILY_ORDER 调一个族：ScopedDataContext NEEDS 门控 + 统一契约。"""
    import importlib
    mod = importlib.import_module('families.%s' % fam_id)
    scoped = ScopedDataContext(ctx, getattr(mod, 'NEEDS', ()))
    stats = mod.build(scoped, sink)
    # declared-but-untouched：非阻塞提示（族可能按数据条件分支没走到某张表）
    untouched = scoped.untouched(getattr(mod, 'NEEDS', ()))
    if untouched:
        print("  [提示] %s 族声明但本次未触发的表：%s"
              % (fam_id, ', '.join('%s/%s' % t for t in untouched)))
    return stats


def main():
    # story_docs/ is fully generated: a mount change removes pages, and leaving the old
    # files behind would let the validators read a tree this script never wrote
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    # 上游数据与共享服务：构造一次，族经 ScopedDataContext（NEEDS 门控）取数
    ctx = DataContext(ROOT, out=OUT)
    sink = sink_mod.SidecarSink(ctx.out, ctx.lang_table('LANG', 'Story'))
    stats = {}
    for fam_id in FAMILY_ORDER:
        print("Parsing %s (%s) scripts..." % (FAMILY_LABELS.get(fam_id, fam_id), fam_id))
        stats[fam_id] = run_family(ctx, sink, fam_id)
        st = stats[fam_id]
        if fam_id == 'chat':
            continue        # chat 族自行打印心链统计行
        if fam_id == 'orphan_battles':
            print("  无关卡引用的战斗气泡剧本：脚本=%d 气泡=%d" % (st['sections'], st['lines']))
            continue
        print("  小节=%d 台词行=%d" % (st['sections'], st['lines']))
    # 主线汇总行（原 build_main 的 sections/bubbles/lines/empty 口径不变）
    m = stats['main']
    m['empty'] = len(sink.skipped)
    print("主线汇总：sections=%(sections)s 战斗气泡关卡=%(bubbles)s "
          "台词行=%(lines)s 无剧本关卡行=%(empty)s" % m)
    dstats = aggregate.write_data(ctx, sink)
    print("结构化侧车：章=%d 节点=%d 页=%d" % (dstats['chapters'], dstats['nodes'], dstats['pages']))
    total, done, todo = aggregate.write_coverage(ctx, sink)
    print("剧本覆盖对账：包内 %d 个，已渲染 %d 个，未渲染 %d 个" % (total, done, todo))
    aggregate.write_reconciliation(ctx, sink)
    aggregate.write_diagnostics(ctx, sink)
    print("诊断侧车 _diagnostics.json：%s"
          % (' '.join('%s=%s' % kv for kv in sorted(ctx.diag.nonzero().items()))
             or '本次构建无任何兜底触发'))
    print("Wrote %s" % OUT)


if __name__ == '__main__':
    # --out 仅供校验用（tests/story/validate_story.py 的 P3 组重建到临时目录后逐字节
    # 比对 _diagnostics.json）。默认仍是 story_docs/，行为与加参数前完全一致。
    import argparse
    ap = argparse.ArgumentParser(description='解析上游数据源并生成 story_docs/')
    ap.add_argument('--out', default=OUT,
                    help='输出目录（默认 %s；仅校验用临时重建时才覆盖）' % OUT)
    args = ap.parse_args()
    OUT = args.out
    main()
