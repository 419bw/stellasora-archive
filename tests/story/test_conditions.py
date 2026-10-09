"""Historical branches from real scripts through the reading projections."""
import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'story'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'site'))

import build_story
import render_html
from pipeline import markup
from pipeline.pagedoc import PageDoc
from pipeline.render_md import page_markdown


@pytest.mark.parametrize('stem,branches,visible', [
    ('STm02_02_c', 1, 1),
    ('STm08_19_b', 2, 2),
    ('STm09_00_b', 4, 4),
    ('STm09_05_a', 4, 2),
    ('STm07_06_ba', 4, 4),
])
def test_historical_conditions_survive_json_and_rendering(stem, branches, visible):
    parsed = build_story.extract_script(stem)
    beats = parsed['beats']
    cases = [b for b in beats if b['k'] == 'condition_branch']
    assert len(cases) == branches
    assert sum(b['k'] == 'condition_end' for b in beats) == (2 if stem == 'STm07_06_ba' else 1)
    assert all(b['labels'] for b in cases)
    if stem == 'STm09_00_b':
        assert 'StoryEvidence.' not in str(cases)
        assert cases[0]['labels'] == ['若已阅读《终局 指尖的沙》、《终局 身旁的她》、《终局 遥远的塔》']
        assert cases[-1]['labels'] == ['否则']
    doc = PageDoc('# 剧情', [], '', '正文', beats)
    stored = json.loads(json.dumps(doc.to_dict(), ensure_ascii=False))
    restored = PageDoc.from_dict(stored)
    assert page_markdown(restored) == page_markdown(doc)
    assert render_html.render_body(stored)[0] == render_html.render_body(doc.to_dict())[0]
    assert '历史条件' in page_markdown(doc)
    assert 'condition-branch' in render_html.render_body(stored)[0]
    html, _ = render_html.render_body(stored)
    targets = re.findall(r'href="#(condition-merge-\d+)"', html)
    assert len(targets) == visible
    for target in targets:
        assert html.count('id="%s"' % target) == 1
        assert html.rindex('href="#%s"' % target) < html.index('id="%s"' % target)


def test_shared_be_cases_keep_source_and_merge_only_reading_text():
    parsed = build_story.extract_script('STm09_05_a')
    repeated = '不，不对。在过去的冒险里，我又不是没遇到死亡的情况。'
    source = [b for b in parsed['beats'] if b['k'] == 'talk'
              and markup.plain(b['text']).startswith(repeated)]
    assert len(source) == 3
    doc = PageDoc('# 剧情', [], '', '正文', parsed['beats'])
    assert page_markdown(doc).count(repeated) == 1
    html, _ = render_html.render_body(doc.to_dict())
    assert html.count(repeated) == 1
    assert '8%' in html
    assert '若第一章至第八章的终局已阅读比例为 0%' in html


def test_choice_condition_ends_at_the_real_jump_destination():
    beats = build_story.extract_script('STm02_02_c')['beats']
    case = next(b for b in beats if b['k'] == 'condition_branch')
    assert case['labels'] == ['若已选择《07 不同的许愿》中的「放弃思考」']
    end = next(i for i, b in enumerate(beats) if b['k'] == 'condition_end')
    assert markup.plain(beats[end + 1]['text']) == '她们的面容姣好而陌生，不是我认识的人。'


def test_historical_choice_markers_use_the_source_option():
    beats = build_story.extract_script('STm08_11')['beats']
    case = next(b for b in beats if b['k'] == 'condition_branch')
    assert case['labels'] == ['若已阅读《05B 亿万》，且已选择《05B 亿万》中的「默默等待时机」']
