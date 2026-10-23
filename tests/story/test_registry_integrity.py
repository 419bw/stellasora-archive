# -*- coding: utf-8 -*-
"""注册表完整性契约（设计 4.5-3，Phase C 上线）。

防声明腐烂的静态断言，全部走 import 不做构建：
  1. FAMILY_ORDER 每个族都有 families/<id>.py 模块，且含 build/NEEDS/MOUNTS；
  2. 每个族的 NEEDS/MOUNTS 是 (scope, name) / (表, 字段) 二元组格式，scope 合法；
  3. MOUNTS 引用的表在 data/ 里真实存在（上游不会凭空多表）；
  4. sections.json（git 跟踪的侧车快照）出现的每个 family 都有对应族模块；
  5. 站点侧每个族 id 都有 CSS accent 片段（依赖 Phase E1 的 CSS_MANIFEST 落位，缺则 skip）；
  6. 站点分发表覆盖 kind taxonomy 全集（Phase D3，子进程隔离 import）。
"""
import os
import sys
import json
import subprocess
import importlib

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'story'))

from families import FAMILY_ORDER  # noqa: E402

# sections.json 的 family 值是站点 slug，与族 id 的差异只有 orphan_battles 一族
# （族 id orphan_battles ↔ 站点 family/slug battles_unmounted，与站点侧
# registry.slug_of 的别名同源）。
FAMILY_TO_SITE = {'orphan_battles': 'battles_unmounted'}


def _module(fam_id):
    return importlib.import_module('families.%s' % fam_id)


def test_family_order_matches_modules_and_contract():
    """FAMILY_ORDER ↔ 模块存在 ↔ build/NEEDS/MOUNTS 契约。"""
    assert len(FAMILY_ORDER) == len(set(FAMILY_ORDER)), 'FAMILY_ORDER 有重复族'
    for fam_id in FAMILY_ORDER:
        mod = _module(fam_id)
        assert callable(getattr(mod, 'build', None)), '%s 缺 build()' % fam_id
        assert isinstance(mod.NEEDS, tuple), '%s.NEEDS 必须是 tuple' % fam_id
        assert isinstance(mod.MOUNTS, tuple), '%s.MOUNTS 必须是 tuple' % fam_id


def test_needs_and_mounts_shape():
    """NEEDS 是 ('BIN'|'LANG', 表名)；MOUNTS 是 (表名, 字段名)。"""
    for fam_id in FAMILY_ORDER:
        mod = _module(fam_id)
        for pair in mod.NEEDS:
            assert len(pair) == 2, '%s.NEEDS 项必须是二元组: %r' % (fam_id, pair)
            assert pair[0] in ('BIN', 'LANG'), '%s.NEEDS scope 非法: %r' % (fam_id, pair)
            assert pair[1].endswith('.json') is False, '%s.NEEDS 表名不带 .json: %r' % (fam_id, pair)
        for pair in mod.MOUNTS:
            assert len(pair) == 2, '%s.MOUNTS 项必须是二元组: %r' % (fam_id, pair)


def test_mounts_tables_exist_upstream():
    """MOUNTS 引用的 BIN 表在 data/ 真实存在（缺失=声明腐烂或上游改名）。"""
    bin_dir = os.path.join(ROOT, 'data', 'StellaSoraData', 'CN', 'bin')
    if not os.path.isdir(bin_dir):
        pytest.skip('上游 data/ 不在位，跳过表存在性断言')
    for fam_id in FAMILY_ORDER:
        for tbl, _fld in _module(fam_id).MOUNTS:
            assert os.path.exists(os.path.join(bin_dir, tbl + '.json')), \
                '%s.MOUNTS 引用的表缺失: %s.json' % (fam_id, tbl)


def test_sections_families_all_have_modules():
    """侧车 sections.json 出现的每个 family 都有族模块（无孤岛 family）。"""
    path = os.path.join(ROOT, 'story_docs', '_data', 'sections.json')
    if not os.path.exists(path):
        pytest.skip('story_docs/_data/sections.json 不在位')
    with open(path, encoding='utf-8') as f:
        pages = json.load(f)['pages']
    seen = {p['family'] for p in pages}
    site_names = {FAMILY_TO_SITE.get(f, f) for f in FAMILY_ORDER}
    assert seen <= site_names, 'sections.json 出现未注册族: %s' % (seen - site_names)


def test_family_css_accent_exists():
    """站点侧每个族 id 都有 CSS accent 片段（Phase E1 后 scripts/site/families/<id>/style.css）。

    D3 先建 assemble.py（彼时只有模板分发注册表），CSS 超级拼接要等 E1；
    用 assemble.py 里的 CSS_MANIFEST 声明做"E1 已完工"信号，落位前 skip，
    落位后任一族缺 style.css 立即红。
    """
    assemble_py = os.path.join(ROOT, 'scripts', 'site', 'assemble.py')
    if not os.path.exists(assemble_py) or \
            'CSS_MANIFEST' not in open(assemble_py, encoding='utf-8').read():
        pytest.skip('Phase E1 未落位（assemble.py 无 CSS_MANIFEST），族 style.css 切片尚未生成')
    fam_dir = os.path.join(ROOT, 'scripts', 'site', 'families')
    for fam_id in FAMILY_ORDER:
        if fam_id in ('chat',):        # 心链自外于站点，无 accent
            continue
        # 站点侧族 id 与剧情侧的差异只有 orphan_battles ↔ battles_unmounted
        site_id = FAMILY_TO_SITE.get(fam_id, fam_id)
        assert os.path.exists(os.path.join(fam_dir, site_id, 'style.css')), \
            '站点侧缺 %s 族 accent 片段' % site_id


def test_site_dispatch_table_covers_kind_taxonomy():
    """站点分发表覆盖 kind taxonomy 全集且条目可调用（Phase D3 契约）。

    子进程隔离 import assemble——测试进程里 scripts/story 与 scripts/site 各有
    一个 ``families`` 包，同进程 import 会互相掩蔽。
    """
    assemble_py = os.path.join(ROOT, 'scripts', 'site', 'assemble.py')
    if not os.path.exists(assemble_py):
        pytest.skip('Phase D3 未落位（assemble.py 不存在）')
    code = (
        "import sys; sys.path.insert(0, %r); import assemble; "
        "kinds = {k for _, k in assemble.DISPATCH}; "
        "need = {'home', 'index', 'reading', 'battle_archive', "
        "'chapter_graph', 'activity_graph'}; "
        "assert need <= kinds, '缺 kind: %%s' %% (need - kinds); "
        "assert all(callable(v) for v in assemble.DISPATCH.values()); "
        "assert ('main', 'index') in assemble.DISPATCH; "
        "assert ('events', 'activity_graph') in assemble.DISPATCH; "
        "print('ok')" % os.path.join(ROOT, 'scripts', 'site')
    )
    res = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
