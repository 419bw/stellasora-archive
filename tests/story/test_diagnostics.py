# -*- coding: utf-8 -*-
"""统一兜底机制：Diagnostics 收集器 + conditions 各降级点 + markup 两处保留原文。"""
import json
import logging
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'story'))

from pipeline import markup  # noqa: E402
from pipeline.command_ir import Command  # noqa: E402
from pipeline.conditions import ConditionCatalog, condition_markers  # noqa: E402
from pipeline.diagnostics import CATEGORIES, Diagnostics, warn  # noqa: E402


# ============================================================ Diagnostics 收集器
def test_add_dedups_by_key_and_keeps_distinct_entries():
    d = Diagnostics()
    assert d.add('choice_frame_anomalies', ('s', 1, 'c', 'g', 'e'), stem='s', idx=1)
    assert d.add('choice_frame_anomalies', ('s', 1, 'c', 'g', 'e'), stem='s', idx=1) is False
    assert d.add('choice_frame_anomalies', ('s', 2, 'c', 'g', 'e'), stem='s', idx=2)
    assert d.entries('choice_frame_anomalies') == [
        {'stem': 's', 'idx': 1}, {'stem': 's', 'idx': 2}]


def test_entries_are_sorted_by_key_not_insertion_order():
    d = Diagnostics()
    d.add('choice_frame_anomalies', ('z', 9, 'c', 'g', 'e'), stem='z')
    d.add('choice_frame_anomalies', ('a', 1, 'c', 'g', 'e'), stem='a')
    assert [e['stem'] for e in d.entries('choice_frame_anomalies')] == ['a', 'z']


def test_as_dict_key_order_follows_the_registry():
    d = Diagnostics()
    assert list(d.as_dict()) == list(CATEGORIES)


def test_every_category_is_emitted_even_when_empty():
    d = Diagnostics()
    out = d.as_dict()
    for name, (shape, _desc) in CATEGORIES.items():
        assert out[name] == (0 if shape == 'count' else []), name


def test_unregistered_category_is_a_hard_error():
    d = Diagnostics()
    with pytest.raises(KeyError, match='未注册的诊断分类'):
        d.add('not_a_category', ('k',))
    with pytest.raises(KeyError, match='未注册的诊断分类'):
        d.bump('not_a_category')
    with pytest.raises(KeyError, match='未注册的诊断分类'):
        d.count('not_a_category')


def test_shape_mismatch_is_a_hard_error():
    d = Diagnostics()
    with pytest.raises(TypeError, match='计数类分类'):
        d.add('emph_tags_preserved', ('k',))
    with pytest.raises(TypeError, match='列表类分类'):
        d.bump('choice_frame_anomalies')


def test_count_accumulates_without_key_and_dedups_with_key():
    d = Diagnostics()
    d.bump('emph_tags_preserved', 2)
    d.bump('emph_tags_preserved', 3)
    assert d.count('emph_tags_preserved') == 5          # 无 key：累加
    d.bump('speaker_inline_names', key=('avg1_1',))
    d.bump('speaker_inline_names', key=('avg1_1',))
    d.bump('speaker_inline_names', key=('avg1_2',))
    assert d.count('speaker_inline_names') == 2         # 有 key：按 key 去重


def test_scalar_entries_and_extend():
    d = Diagnostics()
    assert d.add_value('unattached_bbm_scripts', 'BBm00_02')
    assert d.add_value('unattached_bbm_scripts', 'BBm00_02') is False
    d.extend('unattached_bbm_scripts', ['BBm00_01', 'BBm00_02'])
    assert d.entries('unattached_bbm_scripts') == ['BBm00_01', 'BBm00_02']


def test_as_dict_is_json_serializable_and_byte_stable():
    d = Diagnostics()
    d.add('choice_frame_anomalies', ('s', 1, 'c', 'g', 'e'), stem='s', idx=1)
    d.bump('emph_tags_preserved', 7)
    d.add_value('unattached_bbm_scripts', 'BBm00_01')
    first = json.dumps(d.as_dict(), ensure_ascii=False, indent=1)
    second = json.dumps(d.as_dict(), ensure_ascii=False, indent=1)
    assert first == second
    assert json.loads(first)['emph_tags_preserved'] == 7


def test_note_documents_every_registered_category():
    note = Diagnostics().note()
    for name in CATEGORIES:
        assert '%s=' % name in note, name


def test_nonzero_and_bool():
    d = Diagnostics()
    assert not d
    assert d.nonzero() == {}
    d.bump('orphan_emph_tags_stripped', 4)
    assert d
    assert d.nonzero() == {'orphan_emph_tags_stripped': 4}


def test_warn_logs_through_the_pipeline_logger(caplog):
    with caplog.at_level(logging.WARNING, logger='pipeline.diagnostics'):
        warn('统一告警出口自检')
    assert len(caplog.records) == 1
    assert '统一告警出口自检' in caplog.records[0].getMessage()


# ============================================================ markup 两处保留原文
def test_unknown_control_marker_is_logged_and_registered(caplog):
    diag = Diagnostics()
    compiler = markup.TextCompiler({'==SEX1==': ['她', '他']}, diagnostics=diag)
    raw = '==SEX1==前==NEW_MARKER==后'
    with caplog.at_level(logging.WARNING, logger='pipeline.markup'):
        text = compiler.compile(raw)
        compiler.compile(raw)                      # 缓存命中：不重复登记
    assert text.to_data() == {'cn_f': '她前==NEW_MARKER==后', 'cn_m': '他前==NEW_MARKER==后'}
    assert len(caplog.records) == 1                # 日志一条
    entries = diag.entries('unknown_control_markers')
    assert entries == [{'marker': '==NEW_MARKER==', 'text': raw}]   # 侧车也一条


def test_known_preset_word_is_not_registered():
    diag = Diagnostics()
    compiler = markup.TextCompiler({}, {'1234': '你好'}, diagnostics=diag)
    assert compiler.compile('说$1234啊').to_data() == '说你好啊'
    assert diag.entries('unknown_preset_words') == []


def test_unknown_preset_word_keeps_the_token_and_registers_it():
    diag = Diagnostics()
    compiler = markup.TextCompiler({}, {'1234': '你好'}, diagnostics=diag)
    text = compiler.compile('价值 $9999 金币')
    assert text.to_data() == '价值 $9999 金币'
    assert diag.entries('unknown_preset_words') == [
        {'word': '9999', 'text': '价值 $9999 金币'}]


def test_emph_counters_go_through_the_collector():
    diag = Diagnostics()
    compiler = markup.TextCompiler({}, diagnostics=diag)
    compiler.compile('既然<b>我们目标一致</b>，就好好准备吧。')
    assert diag.count('emph_tags_preserved') == 2
    assert diag.count('orphan_emph_tags_stripped') == 0
    compiler.compile('<size=47>——佚名</b></size>')     # 悬空 </b>
    assert diag.count('orphan_emph_tags_stripped') == 1


# ============================================================ conditions 降级点
def _compiler():
    return markup.TextCompiler({})


def _catalog(diag=None, **overrides):
    """假表构造的 ConditionCatalog：不碰文件系统，专测降级路径。"""
    tables = {
        'Story': {'1': {'Id': 1, 'StoryId': 'STm01_01', 'Index': 'Story.100.1',
                        'Title': 'Story.100.2'}},
        'StoryCondition': {'1': {'Id': 1, 'ConditionId': 'C01_01', 'StoryId_a': ['STm01_01']}},
        'StoryEvidence': {'1': {'Id': 1, 'EvId': 'E101', 'Name': 'StoryEvidence.101.1'}},
        'StoryChapter': {'1': {'Id': 1, 'Name': 'StoryChapter.1.1'},
                         '8': {'Id': 8, 'Name': 'StoryChapter.8.1'}},
        'Achievement': {},
    }
    language = {
        'Story': {'Story.100.1': '01', 'Story.100.2': '梦醒时分'},
        'StoryEvidence': {'StoryEvidence.101.1': '放弃思考'},
        'StoryChapter': {'StoryChapter.1.1': '第一章', 'StoryChapter.8.1': '第八章'},
        'Achievement': {},
    }
    tables.update(overrides.get('tables', {}))
    language.update(overrides.get('language', {}))
    commands = overrides.get('commands', lambda stem: [])
    return ConditionCatalog(tables, language, commands, _compiler(), diagnostics=diag)


def test_unknown_story_id_falls_back_to_the_raw_id_and_registers():
    diag = Diagnostics()
    assert _catalog(diag).story('NO_SUCH_STORY') == 'NO_SUCH_STORY'
    assert diag.entries('condition_story_unknown') == [{'ident': 'NO_SUCH_STORY'}]


def test_known_story_id_still_renders_the_full_title():
    assert _catalog().story('STm01_01') == '《01 梦醒时分》'


def test_unknown_condition_id_keeps_its_label_and_registers():
    diag = Diagnostics()
    assert _catalog(diag).unlock('NO_SUCH_COND') == '解锁条件 NO_SUCH_COND 成立'
    assert diag.entries('condition_unlock_unknown') == [{'ident': 'NO_SUCH_COND'}]


def test_known_condition_id_is_unchanged():
    assert _catalog().unlock('C01_01') == '已阅读《01 梦醒时分》'


def test_unknown_achievement_degrades_instead_of_key_error():
    diag = Diagnostics()
    tables = {'StoryCondition': {'9': {'Id': 9, 'ConditionId': 'C99', 'AchieveIds': [498]}}}
    assert _catalog(diag, tables=tables).unlock('C99') == '已完成成就「498」'
    assert diag.entries('condition_achievement_unknown') == [{'achieve_id': '498'}]


def test_known_achievement_resolves_through_the_language_table():
    tables = {'StoryCondition': {'9': {'Id': 9, 'ConditionId': 'C99', 'AchieveIds': [498]}}}
    tables['Achievement'] = {'498': {'Id': 498, 'Title': 'Achievement.498.1'}}
    language = {'Achievement': {'Achievement.498.1': '初次探索'}}
    assert _catalog(tables=tables, language=language).unlock('C99') == '已完成成就「初次探索」'


def test_unknown_evidence_id_degrades_instead_of_key_error():
    diag = Diagnostics()
    kind, label = _catalog(diag).evidence_condition('E999')
    assert (kind, label) == ('item', '已取得「E999」')
    assert diag.entries('condition_evidence_unknown') == [
        {'ev_id': 'E999', 'missing': 'row'}]


def test_evidence_row_without_name_degrades_and_registers():
    diag = Diagnostics()
    tables = {'StoryEvidence': {'1': {'Id': 1, 'EvId': 'E101'}}}   # 缺 Name
    assert _catalog(diag, tables=tables).evidence_condition('E101') == ('item', '已取得「E101」')
    assert diag.entries('condition_evidence_unknown') == [{'ev_id': 'E101'}]


def test_known_evidence_id_is_unchanged():
    assert _catalog().evidence_condition('E101') == ('item', '已取得「放弃思考」')


def test_missing_choice_command_degrades_instead_of_stop_iteration():
    diag = Diagnostics()
    label = _catalog(diag).choice(('g', 0, 'STm01_01', 'a_1', 'A'))
    assert label == '已选择《01 梦醒时分》中的选项'
    assert diag.entries('condition_choice_frame_missing') == [
        {'stem': 'STm01_01', 'cmd': 'SetMajorChoice', 'group': 'a_1'}]


def _major_commands(stem=None):
    return [Command(0, 'SetMajorChoice', ['a_1', 'AvgChoice_item_01', '放弃思考', 'E101'])]


def test_out_of_range_choice_option_is_skipped_and_registered():
    diag = Diagnostics()
    label = _catalog(diag, commands=_major_commands).choice(('g', 0, 'STm01_01', 'a_1', 'C'))
    assert label == '已选择《01 梦醒时分》中的选项'
    assert diag.entries('condition_choice_option_missing') == [
        {'stem': 'STm01_01', 'group': 'a_1', 'item': 'C'}]


def test_empty_choice_option_is_skipped_and_registered():
    diag = Diagnostics()
    label = _catalog(diag, commands=_major_commands).choice(('g', 0, 'STm01_01', 'a_1', 'A+'))
    assert label == '已选择《01 梦醒时分》中的「放弃思考」'
    assert diag.entries('condition_choice_option_missing') == [
        {'stem': 'STm01_01', 'group': 'a_1', 'item': '(空)'}]


def test_valid_choice_option_label_is_unchanged():
    diag = Diagnostics()
    assert _catalog(diag, commands=_major_commands).choice(
        ('g', 0, 'STm01_01', 'a_1', 'A')) == '已选择《01 梦醒时分》中的「放弃思考」'
    assert not diag


def test_unknown_be_case_degrades_instead_of_key_error():
    diag = Diagnostics()
    label = _catalog(diag).be_case_label(['a1', 1, 8, 8], 5)
    assert label == '第一章至第八章的终局已阅读比例为未知档位 5'
    assert diag.entries('condition_be_case_unknown') == [
        {'group': 'a1', 'case': '5', 'missing': '档位号不在 1..4'}]


def test_known_be_case_labels_are_unchanged():
    catalog = _catalog()
    assert catalog.be_case_label(['a1', 1, 8, 8], 1) == '第一章至第八章的终局已阅读比例为 0%'
    assert catalog.be_case_label(['a1', 1, 8, 8], 2) == \
        '第一章至第八章的终局已阅读比例大于 0%，且不超过 8%'
    assert catalog.be_case_label(['a1', 1, 8, 8], 4) == '第一章至第八章的终局已阅读比例为 100%'
    assert catalog.be_cases(['a1', 1, 8, 8])[3] == \
        '第一章至第八章的终局已阅读比例大于 8%，且小于 100%'


def test_malformed_check_be_param_degrades_and_registers():
    diag = Diagnostics()
    assert _catalog(diag).be_case_label(['a1'], 1) == 'None至None的终局已阅读比例为 0%'
    # 参数形状错一次、两个章号又查不到一次（start/end 都是 None，同一去重键合并）：
    # 两条都登记，标签仍可读
    assert [e['missing'] for e in diag.entries('condition_be_case_unknown')] == [
        'StoryChapter 查不到', 'CheckBE 参数不是 4 元组']


def test_unknown_chapter_in_be_scope_degrades_and_registers():
    diag = Diagnostics()
    assert _catalog(diag).be_case_label(['a1', 99, 8, 8], 1) == \
        '99至第八章的终局已阅读比例为 0%'
    assert [e['missing'] for e in diag.entries('condition_be_case_unknown')] == \
        ['StoryChapter 查不到']


def test_row_without_primary_key_is_skipped_instead_of_crashing_import():
    diag = Diagnostics()
    tables = {'Story': {'1': {'Id': 1, 'StoryId': 'STm01_01'},
                        '2': {'Id': 2},                      # 缺 StoryId
                        '3': 'not even an object'}}
    catalog = _catalog(diag, tables=tables)
    assert list(catalog.stories) == ['STm01_01']
    assert sorted(e['row_id'] for e in diag.entries('condition_row_malformed')) == ['2', '3']


def test_conflicting_check_be_ranges_in_one_group_are_registered():
    diag = Diagnostics()
    commands = [Command(0, 'CheckBE', ['a1', 1, 8, 8]),
                Command(1, 'CheckBE', ['a1', 1, 4, 8]),
                Command(2, 'CheckBECase', ['a1', 1]),
                Command(3, 'CheckBEEnd', ['a1'])]
    markers = condition_markers(commands, _catalog(diag))
    assert [e['missing'] for e in diag.entries('condition_be_case_unknown')] == \
        ['组内 CheckBE range 不一致']
    assert markers[2] == [{'k': 'condition_branch', 'group': 'be:a1',
                           'labels': ['若第一章至第八章的终局已阅读比例为 0%']}]


def test_malformed_command_params_degrade_without_registration():
    """结构性缺参（上游指令形状变了）不登记：与 slot()/fork_options() 同一性质。"""
    diag = Diagnostics()
    assert _catalog(diag).choice(('too', 'short')) == '已选择历史选项'
    assert not diag


def test_short_if_unlock_param_falls_back_to_always_true():
    diag = Diagnostics()
    commands = [Command(0, 'IfUnlock', ['g_1']), Command(1, 'IfUnlockEnd', ['g_1'])]
    markers = condition_markers(commands, _catalog(diag))
    assert markers[0][0]['labels'] == ['若条件始终成立']
    assert not diag


def test_catalog_builds_its_own_collector_when_none_injected():
    catalog = _catalog()
    assert catalog.story('NO_SUCH_STORY') == 'NO_SUCH_STORY'
    assert catalog.diagnostics.entries('condition_story_unknown')
