# -*- coding: utf-8 -*-
"""公开构建入口、校验器独立性与 CSS 组装的结构回归。"""
import os
import re
import subprocess
import sys

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


def test_validators_do_not_import_build_orchestrators():
    """校验器不经过两个构建编排器或已拆除的共享模板取数。"""
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
