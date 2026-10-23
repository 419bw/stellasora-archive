# -*- coding: utf-8 -*-
"""全量结构断言（设计 6.3，终验入库）。

守护模块化终态，防回归：
  1. 入口与冻结面：两个构建入口在位，--out CLI 在 help 里；
  2. 剧情编排器 ≤200 行且无模块级 load_json( 副作用；
  3. 遗留共享模块（site_css.py / site_templates.py）已不存在；
  4. 全局累加器零残留（只允许 sink 实例属性）；
  5. 双校验器不 import 生成器（保持"绝对真值"独立性）；
  6. assemble_css() 带 manifest 文件头、确定性强（子进程隔离 import——
     测试进程里 scripts/story 与 scripts/site 各有一个 families 包）。
"""
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STORY = os.path.join(ROOT, 'scripts', 'story')
SITE = os.path.join(ROOT, 'scripts', 'site')


def test_entrypoints_and_cli_frozen():
    """冻结面：两个构建入口在位；--out CLI 出现在 help 中。"""
    assert os.path.exists(os.path.join(STORY, 'build_story.py'))
    assert os.path.exists(os.path.join(SITE, 'build_site.py'))
    res = subprocess.run([sys.executable, os.path.join(STORY, 'build_story.py'), '--help'],
                         capture_output=True, text=True, encoding='utf-8')
    assert res.returncode == 0, res.stderr
    assert '--out' in res.stdout, '--out CLI 从 help 里消失了（冻结面被破坏）'


def test_orchestrator_is_thin():
    """剧情编排器 ≤200 行，且无模块级 load_json( 数据加载副作用。"""
    path = os.path.join(STORY, 'build_story.py')
    with open(path, encoding='utf-8') as f:
        lines = f.read().split('\n')
    assert len([ln for ln in lines if ln.strip()]) <= 200, '编排器超过 200 行'
    for ln in lines:
        if ln.startswith('load_json('):
            raise AssertionError('编排器仍有模块级 load_json( 调用: %s' % ln)


def test_legacy_shared_modules_removed():
    """E1/D1 拆分掉的单文件共享模块不得复活。"""
    assert not os.path.exists(os.path.join(SITE, 'site_css.py')), 'site_css.py 复活了'
    assert not os.path.exists(os.path.join(SITE, 'site_templates.py')), 'site_templates.py 复活了'


def test_no_global_accumulator_residue():
    """全局累加器只允许以 sink 实例属性存在（设计 2.2 痛点 1）。"""
    banned = ('_PAGES', '_SEARCH_ENTRIES', '_CHAPTER_NODES', '_RENDERED', 'CODE_MISMATCHES')
    pat = re.compile(r'^(%s)\s*=' % '|'.join(banned))
    hits = []
    for base in (os.path.join(ROOT, 'scripts', 'story'),
                 os.path.join(ROOT, 'scripts', 'site')):
        for d, _, fs in os.walk(base):
            if '__pycache__' in d:
                continue
            for name in fs:
                if not name.endswith('.py'):
                    continue
                p = os.path.join(d, name)
                with open(p, encoding='utf-8') as f:
                    for i, ln in enumerate(f.read().split('\n'), 1):
                        if pat.match(ln):
                            hits.append('%s:%d %s' % (os.path.relpath(p, ROOT), i, ln))
    assert not hits, '模块级累加器残留: %s' % hits


def test_validators_do_not_import_generators():
    """双校验器保持"绝对真值"独立性：不 import 任何生成器模块。"""
    pat = re.compile(r'^\s*(?:import|from)\s+(build_story|build_site|site_css|site_templates)\b')
    for name in ('validate_story.py', 'validate_site.py'):
        path = os.path.join(ROOT, 'tests', 'story', name)
        with open(path, encoding='utf-8') as f:
            for i, ln in enumerate(f.read().split('\n'), 1):
                assert not pat.match(ln), '%s:%d import 了生成器: %s' % (name, i, ln.strip())


def test_assemble_css_header_and_determinism():
    """assemble_css() 带 manifest 文件头，且重复调用结果一致（E3 起）。"""
    code = (
        "import sys; sys.path.insert(0, %r); import assemble; "
        "a = assemble.assemble_css(); b = assemble.assemble_css(); "
        "assert a == b, 'assemble_css 不确定'; "
        "assert a.startswith('/*'), '缺文件头注释'; "
        "assert 'CSS_MANIFEST' in a or '清单序' in a, '文件头不是 manifest 注释'; "
        "print(len(a))" % SITE
    )
    res = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True,
                         encoding='utf-8')
    assert res.returncode == 0, res.stderr
