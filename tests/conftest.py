# -*- coding: utf-8 -*-
"""共享 fixture。

data_ctx 的存在理由是成本与时机，不是便利：DataContext 构造要加载
TextCompiler / ConditionCatalog / speakers（数 MB 表 + preset lua），
session 级共享让全量跑只付一次；惰性构造让 `-m "not slow"` 的快循环
在没人用到它时完全不付（模块级 `CTX = DataContext(ROOT)` 在收集期
import 时就会执行，-k 排除也照跑不误）。

注意：急切读取审计（test_registry_integrity 的 eager-reads 契约）**不得**
用本 fixture——它断言的是"新鲜 DataContext 构造期的可观察读取 ⊆ SHARED_NEEDS"，
共享实例会被其他测试的懒读污染 resolved_tables()，审计自噬。
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope='session')
def data_ctx():
    story = os.path.join(ROOT, 'scripts', 'story')
    if story not in sys.path:
        sys.path.insert(0, story)
    from context import DataContext
    return DataContext(ROOT)
