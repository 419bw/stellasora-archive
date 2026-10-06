# -*- coding: utf-8 -*-
"""Unit tests for scripts/story/pipeline/text_rules.py 的强调标记与签名行为
（Phase 4b）。

钉死四条：
  1. clean_dialogue 对成对 <b>/<i>（含嵌套）原样保留，孤儿/交叉标记剥离
     且不丢正文字，排版类 TMP 标签（color/size/align…）照旧全剥；
  2. EMPH_STATS 计数 paired/orphan，供 _diagnostics.json 登记；
  3. _sig 排除 <b>/<i>：渐显帧折叠的签名口径与 4b 之前逐字节一致
     （<i><b>Y</b></i> 与 <i><b>Y O</b></i> 剥标记后保持子串包含关系）；
  4. 强调标记与 ruby 双形式可共存，互不干扰。
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'story'))

from pipeline import text_rules  # noqa: E402
from pipeline.passes import _related  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_stats():
    text_rules.EMPH_STATS['paired'] = 0
    text_rules.EMPH_STATS['orphan'] = 0
    yield


def test_paired_emph_preserved():
    # 语料原型：CG_147_02 台词语义强调
    assert text_rules.clean_dialogue('既然<b>我们目标一致</b>，就好好准备吧。') == \
        '既然<b>我们目标一致</b>，就好好准备吧。'
    # 语料原型：CG_disc4055 排版帧，嵌套成对 + 排版标签全剥
    assert text_rules.clean_dialogue(
        '_NOT_IN_LOG_<br><margin-left=5em><align=left><i><b><size=800%>'
        '<alpha=#88>Y</size></b></i></align></margin>==A0.15=='
    ) == '<i><b>Y</b></i>'
    assert text_rules.EMPH_STATS['paired'] == 6   # 2（第一句）+ 4（<i> <b> </b> </i>）
    assert text_rules.EMPH_STATS['orphan'] == 0


def test_orphan_and_crossing_emph_stripped():
    # 语料原型：STm06_01 悬空 </b>（open 缺失）——只丢标记，不丢字
    assert text_rules.clean_dialogue(
        '<size=47>——佚名 《旧诺瓦前史》</b></size>') == '——佚名 《旧诺瓦前史》'
    assert text_rules.EMPH_STATS['orphan'] == 1
    # 语料原型：disc4055 未闭合 <i>（计数为进程内累计）
    assert text_rules.clean_dialogue('<i><voffset=0.3em>It’s</voffset> nothing') == \
        'It’s nothing'
    assert text_rules.EMPH_STATS['orphan'] == 2
    # 真交叉 <b><i></b></i>：close 只配栈顶同种 open —— </b> 遇栈顶 i 判孤儿，
    # </i> 配 i 成对；b 的 open 遗留栈底同判孤儿（尽力保留原则）
    assert text_rules.clean_dialogue('前<b><i>中</b></i>后尾') == '前<i>中</i>后尾'
    assert text_rules.EMPH_STATS == {'paired': 2, 'orphan': 4}
    # 合法嵌套 <b><i></i></b> 不受影响
    assert text_rules.clean_dialogue('前<b><i>中</i>后</b>尾') == '前<b><i>中</i>后</b>尾'
    assert text_rules.EMPH_STATS == {'paired': 6, 'orphan': 4}


def test_layout_tags_still_stripped():
    # 表现类 TMP 标签不在保留范围（与 <b>/<i> 的语义标记边界）
    assert text_rules.clean_dialogue(
        '<color=#3faeae>庆典·暗黑觉醒颂！</color>') == '庆典·暗黑觉醒颂！'
    assert text_rules.clean_dialogue('<align=left>……</align>') == '……'


def test_sig_excludes_emph():
    """渐显帧签名剥表现标记：折叠判定口径与 4b 之前一致。"""
    s1 = text_rules._sig('<alpha=#22><i><b>Y</b></i>')
    s2 = text_rules._sig('<i><b>Y O</b></i>')
    assert s1 == 'Y' and s2 == 'YO'
    assert _related(s1, s2)          # 'Y' in 'YO' —— 折叠链不断
    # 若签名含标签，'<i><b>Y</b></i>' in '<i><b>YO</b></i>' 不成立 → 链断。
    # ruby 是内容，保留在签名里：
    assert text_rules._sig('魔<r=x></r>王') == '魔<r=x></r>王'
    assert text_rules._sig('<r=·>非</r>常') == '<r=·>非</r>常'


def test_emph_and_ruby_coexist():
    assert text_rules.clean_dialogue('<b>魔<r=BOSS></r>王</b>来了') == \
        '<b>魔<r=BOSS></r>王</b>来了'
    assert text_rules.clean_dialogue('<b>魔<r=momowang>魔</r>王</b>') == \
        '<b>魔<r=momowang>魔</r>王</b>'
    # 排版标签被剥后强调标记可能变成新的相邻关系，仍按字面配对
    assert text_rules.clean_dialogue('<b><size=50>字</size></b>') == '<b>字</b>'
