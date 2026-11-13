# -*- coding: utf-8 -*-
"""剧情校验器的手动变异审计（不在 CI 里跑）。

validate_story.py 只做数据对账；本文件复用它的真实 audit 函数，往产物 md / 诊断
侧车里植入错误，断言「同一套断言必须抓到」——用来证明校验器本身没被改瞎。

用法（改了校验器/生成器代码后手动跑）：
    python tests/story/mutation_story.py

import validate_story 会先跑一遍数据对账（不退出），其违例数在结尾一并报告；
本文件的植入结果单独累计，任一 MISSED / 还原后复检 FAIL → exit 1。
"""
import sys, os

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_story import *  # noqa: F401,F403  复用 audit 函数与已加载数据
from validate_story import _diag_obj, _REGISTRY, _ANEC_FILES, _parse_anecdote_md

# 植入结果单独累计，与 import 进来的数据对账 HARD 区分开。
MUT_HARD = []


def hard(cond, label):  # noqa: F811  遮蔽 validate_story.hard
    if not cond:
        MUT_HARD.append(label)


print()
print('=' * 66)
print('剧情校验器变异审计（植入错误必须被 validate_story 的同一套 audit 抓到）')
print('=' * 66)

# ---- D 气泡序列植入 ------------------------------------------------------------
print()
print('D 变异测试')
raw_bubble = next(BUBBLE.match(l).group(2) for l in orig.splitlines() if BUBBLE.match(l))
v1 = orig.replace(raw_bubble, raw_bubble + 'X', 1)
first_wave_line = next(l for l in orig.splitlines() if WAVE.match(l.strip()))
v2 = orig.replace(first_wave_line, "> **[战斗阶段 99]**", 1)
first_bubble_line = next(l for l in orig.splitlines() if BUBBLE.match(l.strip()))
v3 = orig.replace(first_bubble_line + "\n", "", 1)
_d1 = bubble_seq(v1) != truth
_d2 = bubble_seq(v2) != truth
_d3 = bubble_seq(v3) != truth
hard(_d1, 'D 植入[改一个字] MISSED')
hard(_d2, 'D 植入[阶段号写错] MISSED')
hard(_d3, 'D 植入[删掉一条气泡] MISSED')
print('植入[改一个字]      : %s' % ('CAUGHT' if _d1 else 'MISSED'))
print('植入[阶段号写错]    : %s' % ('CAUGHT' if _d2 else 'MISSED'))
print('植入[删掉一条气泡]  : %s' % ('CAUGHT' if _d3 else 'MISSED'))

# ---- E 逐句序列植入 ------------------------------------------------------------
print()
print('E 变异测试')
probe_key = next(k for k in sorted(set(expect) & set(actual), key=str)
                 if k[0] == 'storysets' and len(lua_dialogue_seq(expect[k][0]) or []) > 8)
pstem, _ = expect[probe_key]
ppath = actual[probe_key][2]
base_seq = lua_dialogue_seq(pstem)
md = open(ppath, encoding='utf-8').read()
first = next(l for l in md.splitlines() if TALK.match(l))
mut = md.replace(first, first.replace('」', 'X」'), 1)
tmp = ppath + '.mut.md'
open(tmp, 'w', encoding='utf-8', newline='\n').write(mut)
caught_line = dialogue(tmp) != base_seq
recap_line = next(l for l in md.splitlines() if l.startswith('> ') and recap_of(ppath).split(' ')[0][:6] in l) if recap_of(ppath) else ''
mut2 = md.replace(recap_line, '> 被改写过的概要', 1) if recap_line else md.replace('# ', '# X', 1)
open(tmp, 'w', encoding='utf-8', newline='\n').write(mut2)
caught_recap = recap_of(tmp) != lua_setintro_recap(pstem)
os.remove(tmp)
hard(caught_line, 'E 变异[改一句台词] MISSED')
hard(caught_recap, 'E 变异[改概要] MISSED')
print('变异测试（%s / %s，%d 句）: 改一句台词->%s   改概要->%s'
      % (probe_key, pstem, len(base_seq),
         'CAUGHT' if caught_line else 'MISSED', 'CAUGHT' if caught_recap else 'MISSED'))

# ---- N 委托分段植入 ------------------------------------------------------------
print()
print('N 变异测试')
if DISPATCH:
    _mp = DISPATCH[0]
    _mtxt = open(_mp, encoding='utf-8').read()
    _mm = PERF_MARK.search(_mtxt)
    _tstem, _tgrp = _mm.group(1), _mm.group(2)
    _tline = next(l for l in _mtxt.splitlines() if TALK.match(l))
    _tmp = _mp + '.mut.md'
    open(_tmp, 'w', encoding='utf-8', newline='\n').write(_mtxt.replace(_tline, _tline + '变', 1))
    _n_ok = lua_segment_seq(_tstem, _tgrp) != dialogue(_tmp)
    os.remove(_tmp)
    hard(_n_ok, 'N 变异[改一句结算台词] MISSED')
    print('变异测试（%s / %s 第 %s 段）: 改一句台词 -> %s'
          % (os.path.basename(_mp), _tstem, _tgrp, 'CAUGHT' if _n_ok else 'MISSED'))
else:
    print('（无委托分段页，N 无样本可跑）')

# ---- F 序章/存目战斗页植入 -----------------------------------------------------
print()
print('F 变异测试')
for label, pick in (('序章台词', lambda q: q[1].startswith('STm00')),
                    ('存目气泡阶段', lambda q: q[1].startswith('BBm00'))):
    tgt = next((q for q in pages if pick(q)), None)
    if not tgt:
        hard(False, 'F %s：找不到变异样本' % label)
        print('%s：找不到样本' % label)
        continue
    p, stem = tgt
    md = open(p, encoding='utf-8').read()
    tmp = p + '.mut.md'
    if label == '序章台词':
        first = next(l for l in md.splitlines() if TALK.match(l))
        mut = md.replace(first, first.replace('」', 'X」'), 1)
        open(tmp, 'w', encoding='utf-8', newline='\n').write(mut)
        ok = dialogue(tmp) != lua_dialogue_seq(stem)
    else:
        wl = next(l for l in md.splitlines() if WAVE.match(l.strip()))
        mut = md.replace(wl, '> **[战斗阶段 99]**', 1)
        open(tmp, 'w', encoding='utf-8', newline='\n').write(mut)
        ok = md_bubbles(tmp) != (lua_bubbles(stem) or [])
    os.remove(tmp)
    hard(ok, 'F %s 变异 MISSED' % label)
    print('%s 变异（%s）-> %s' % (label, stem, 'CAUGHT' if ok else 'MISSED'))

# ---- K2 挂载语义植入 -----------------------------------------------------------
print()
print('K2 变异测试')
sp = next(p for p, s in pages if s == 'BBm07_BT01')
_k2_pos = not audit_mount(sp, 'BBm07_BT01')
hard(_k2_pos, 'K2 正对照 FAIL')
print('正对照（第七章 BT01 挂 BBm07_BT01）: %s'
      % ('PASS' if _k2_pos else 'FAIL'))
sp_row = next(str(r['Id']) for r in story.values()
              if r.get('IsBattle') and int(r['Chapter']) == 7)
fake = os.path.join(NEW, 'main', 'x', 'sections', '%s_BT01_x.md' % sp_row)
_k2a = bool(audit_mount(fake, 'BBm07_BT01'))
_k2b = bool(audit_mount(sp, 'BBm08_BT01'))
hard(_k2a, 'K2 植入[把 BBm07_BT01 挂回特别篇] MISSED')
hard(_k2b, 'K2 植入[把 BBm08_BT01 挂到第七章] MISSED')
print('植入[把 BBm07_BT01 挂回特别篇]: %s'
      % ('CAUGHT' if _k2a else 'MISSED'))
print('植入[把 BBm08_BT01 挂到第七章]: %s'
      % ('CAUGHT' if _k2b else 'MISSED'))

# ---- M2 注音植入 ---------------------------------------------------------------
print()
print('M2 变异测试')
rp = next(p for p, s in pages if '<r=mowang></r>' in open(p, encoding='utf-8').read())
rstem = next(s for p, s in pages if p == rp)
src = open(rp, encoding='utf-8').read()
tmp = rp + '.mut.md'
try:
    _m_pos = not audit_ruby(rp, rstem)
    hard(_m_pos, 'M2 正对照 FAIL')
    print('正对照（未篡改）: %s' % ('PASS' if _m_pos else 'FAIL'))
    for label, mut in [
            ('植入[删掉一处注音]', src.replace('<r=mowang></r>', '', 1)),
            ('植入[注音挪到字后]', src.replace('魔<r=mowang></r>王', '魔王<r=mowang></r>', 1)),
            ('植入[改注音文字]', src.replace('<r=mowang></r>', '<r=BOSS></r>', 1))]:
        if mut == src:
            print('%s : 样本里没有该形状，跳过' % label)
            continue
        open(tmp, 'w', encoding='utf-8', newline='\n').write(mut)
        _m_ok = bool(audit_ruby(tmp, rstem))
        hard(_m_ok, 'M2 %s MISSED' % label)
        print('%s : %s' % (label, 'CAUGHT' if _m_ok else 'MISSED'))
finally:
    if os.path.exists(tmp):
        os.remove(tmp)
_m_re = not audit_ruby(rp, rstem)
hard(_m_re, 'M2 还原后复检 FAIL')
print('还原后复检: %s' % ('PASS' if _m_re else 'FAIL'))

# ---- P4 诊断侧车植入 -----------------------------------------------------------
print()
print('P4 变异测试')
if _REGISTRY:
    for label, mutated in [
            ('植入[多加一个分类]', dict(_diag_obj, not_a_category=[])),
            ('植入[删一个分类]', {k: v for k, v in _diag_obj.items()
                                if k != 'unknown_control_markers'}),
            ('植入[改坏 note]', dict(_diag_obj, note='手抄的说明')),
            ('植入[加重复条目]', dict(
                _diag_obj, choice_frame_anomalies=(
                    _diag_obj['choice_frame_anomalies']
                    + _diag_obj['choice_frame_anomalies'][:1]))),
            ('植入[打乱排序]', dict(
                _diag_obj, unattached_bbm_scripts=list(reversed(
                    _diag_obj['unattached_bbm_scripts'])))),
            ('植入[计数改成负数]', dict(_diag_obj, emph_tags_preserved=-1))]:
        _p4 = audit_diag_schema(mutated)
        hard(_p4, 'P4 %s MISSED' % label)
        print('%s : %s' % (label, 'CAUGHT' if _p4 else 'MISSED'))
else:
    print('（分类注册表为空，P4 无样本可跑）')

# ---- Q2 逸闻笔记植入 -----------------------------------------------------------
print()
print('Q2 变异测试')
if _ANEC_FILES:
    _qp = _ANEC_FILES[0]
    _qtxt = open(_qp, encoding='utf-8').read()
    _qbase = _parse_anecdote_md(_qp)
    _qtmp = _qp + '.mut.md'
    try:
        _qmut1 = _qtxt.replace('获取条件**：', '获取条件**：篡改', 1)
        open(_qtmp, 'w', encoding='utf-8', newline='\n').write(_qmut1)
        _q_ok1 = _parse_anecdote_md(_qtmp) != _qbase
        _qmut2 = _qtxt.rstrip() + '篡改\n'
        open(_qtmp, 'w', encoding='utf-8', newline='\n').write(_qmut2)
        _q_ok2 = _parse_anecdote_md(_qtmp) != _qbase
    finally:
        if os.path.exists(_qtmp):
            os.remove(_qtmp)
    hard(_q_ok1, 'Q2 变异[改获取条件] MISSED')
    hard(_q_ok2, 'Q2 变异[改散文正文] MISSED')
    print('Q2 变异测试（%s）: 改获取条件->%s   改散文正文->%s'
          % (os.path.basename(_qp), 'CAUGHT' if _q_ok1 else 'MISSED', 'CAUGHT' if _q_ok2 else 'MISSED'))
else:
    print('（无逸闻笔记页，Q2 无样本可跑）')

# ---- 汇总 ---------------------------------------------------------------------
print()
print('=' * 66)
if HARD:
    print('注：数据对账本身有 %d 处违例（见上方 validate_story 输出），与变异审计无关。' % len(HARD))
if MUT_HARD:
    print('MUTATION RESULT: FAIL —— %d 处植入未被抓到：' % len(MUT_HARD))
    for x in MUT_HARD:
        print('   ✗', x)
    sys.exit(1)
print('MUTATION RESULT: PASS —— 全部植入变异都被同一套 audit 抓到')
sys.exit(0)