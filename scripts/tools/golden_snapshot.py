#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""黄金基线快照工具（管线重构 Phase 0 引入，重构完成后可保留作回归工具）。

用法：
  python scripts/tools/golden_snapshot.py            # 生成基线清单（覆盖旧清单）
  python scripts/tools/golden_snapshot.py --compare  # 当前产物 vs 基线，输出差异清单

覆盖三类产物（与重构计划的字节一致门槛对应）：
  story_docs/**/*.md        人审真源 Markdown
  story_docs/_data/*.json   侧车数据（契约 G 字段锁对象）
  site/**/*                 站点全部构建产物（本地生成，不入 git）

清单存 .tmp_verify/golden/manifest.json（.tmp_verify/ 已 gitignore）。
量化口径（剧本页数 / 节点数 / 台词行数）从 story_docs/_data/sections.json
现场派生：台词行 = Σ(talk + bubble − sticker)。基线以快照时刻实测值为准，
重构期间要求「相对基线不变」，而非锚定计划文档写作时的历史绝对值。

退出码：--compare 模式 0 = 与基线全等；1 = 存在差异或缺基线。
"""
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLDEN_DIR = os.path.join(ROOT, '.tmp_verify', 'golden')
MANIFEST = os.path.join(GOLDEN_DIR, 'manifest.json')


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _walk(root):
    """yield 相对 ROOT 的 posix 风格路径（跳过 __pycache__）。"""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != '__pycache__']
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            yield os.path.relpath(full, ROOT).replace(os.sep, '/')


def collect():
    files = {}
    story_md = os.path.join(ROOT, 'story_docs')
    for rel in _walk(story_md):
        if rel.endswith('.md'):
            files['md:' + rel] = _sha256(os.path.join(ROOT, rel))
    data_dir = os.path.join(ROOT, 'story_docs', '_data')
    if os.path.isdir(data_dir):
        for rel in _walk(data_dir):
            if rel.endswith('.json'):
                files['data:' + rel] = _sha256(os.path.join(ROOT, rel))
    site_dir = os.path.join(ROOT, 'site')
    if os.path.isdir(site_dir):
        for rel in _walk(site_dir):
            files['site:' + rel] = _sha256(os.path.join(ROOT, rel))
    return files


def metrics():
    """从 sections.json 派生量化口径；缺文件时返回 None（基线阶段视为错误）。"""
    path = os.path.join(ROOT, 'story_docs', '_data', 'sections.json')
    if not os.path.isfile(path):
        return None
    with open(path, encoding='utf-8') as f:
        s = json.load(f)
    meta = s.get('meta', {})
    lines = 0
    for p in s.get('pages', []):
        c = p.get('counts') or {}
        lines += c.get('talk', 0) + c.get('bubble', 0) - c.get('sticker', 0)
    return {
        'script_pages': len(s.get('pages', [])),
        'nodes': meta.get('nodes'),
        'dialogue_lines': lines,
    }


def snapshot():
    files = collect()
    m = metrics()
    if m is None:
        print('[golden] 错误：story_docs/_data/sections.json 不存在，请先跑 build_story')
        return 1
    os.makedirs(GOLDEN_DIR, exist_ok=True)
    with open(MANIFEST, 'w', encoding='utf-8') as f:
        json.dump({'metrics': m, 'files': files}, f, ensure_ascii=False,
                  separators=(',', ':'), sort_keys=True)
    by = {}
    for k in files:
        by[k.split(':', 1)[0]] = by.get(k.split(':', 1)[0], 0) + 1
    print('[golden] 基线已写入 %s' % os.path.relpath(MANIFEST, ROOT))
    print('[golden] 文件数：md=%d data=%d site=%d' % (by.get('md', 0), by.get('data', 0), by.get('site', 0)))
    print('[golden] 量化口径：%(script_pages)s 剧本页 / %(nodes)s 节点 / %(dialogue_lines)s 台词行' % m)
    return 0


def compare():
    if not os.path.isfile(MANIFEST):
        print('[golden] 错误：基线清单不存在（%s），先跑无参模式生成' % os.path.relpath(MANIFEST, ROOT))
        return 1
    with open(MANIFEST, encoding='utf-8') as f:
        base = json.load(f)
    base_files = base['files']
    cur_files = collect()
    added = sorted(set(cur_files) - set(base_files))
    removed = sorted(set(base_files) - set(cur_files))
    changed = sorted(k for k in set(base_files) & set(cur_files)
                     if base_files[k] != cur_files[k])
    cur_m = metrics()
    base_m = base.get('metrics')
    m_delta = (cur_m != base_m)

    ok = not (added or removed or changed or m_delta)
    print('[golden] 对比基线：%s' % ('全等 ✓' if ok else '存在差异 ✗'))
    for label, items in (('新增', added), ('缺失', removed), ('内容变更', changed)):
        if items:
            print('[golden] %s %d 个文件：' % (label, len(items)))
            for k in items[:50]:
                print('    %s' % k)
            if len(items) > 50:
                print('    …其余 %d 个省略' % (len(items) - 50))
    if m_delta:
        print('[golden] 量化口径变化：基线=%s 当前=%s' % (base_m, cur_m))
    return 0 if ok else 1


def main(argv):
    if '--compare' in argv:
        return compare()
    return snapshot()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
