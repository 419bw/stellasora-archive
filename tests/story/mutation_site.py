# -*- coding: utf-8 -*-
"""站点校验器的手动变异审计（不在 CI 里跑）。

validate_site.py 只做数据对账；本文件复用它的真实 audit 函数，往数据/HTML 里
植入错误，断言「同一套断言必须抓到」——用来证明校验器本身没被改瞎。

用法（改了校验器/生成器代码后手动跑）：
    python tests/story/mutation_site.py

import validate_site 会先跑一遍数据对账（不退出），其违例数在结尾一并报告；
本文件的植入结果单独累计，任一 MISSED / 还原后复检 FAIL → exit 1。
"""
import sys, os

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_site import *  # noqa: F401,F403  复用 audit 函数与已加载数据

# 植入结果单独累计，与 import 进来的数据对账 HARD 区分开。
MUT_HARD = []


def hard(cond, label):  # noqa: F811  遮蔽 validate_site.hard
    if not cond:
        MUT_HARD.append(label)


# 变异专用辅助（原本内联在 validate_site 的变异块里，拆出后自带）。
CLONE = lambda: json.loads(open(os.path.join(DATA, 'chapters.json'), encoding='utf-8').read())
K = lambda: json.loads(open(os.path.join(DATA, 'search.json'), encoding='utf-8').read())


def html_lines(path):
    return [html_view(m.group(1)) for m in HTML_LINE.finditer(
        open(path, encoding='utf-8').read())]


print()
print('=' * 66)
print('站点校验器变异审计（植入错误必须被 validate_site 的同一套 audit 抓到）')
print('=' * 66)

# ---- G3 图数据植入 -------------------------------------------------------------
print()
print('G3 变异测试')
clone = CLONE()
n817 = next(n for c in clone['chapters'] if c['id'] == 8 for n in c['nodes'] if n['sid'] == 817)
n824 = next(n for c in clone['chapters'] if c['id'] == 8 for n in c['nodes'] if n['sid'] == 824)
before = list(n824['parents'])
n824['parents'] = [n817['parents'][0]]
_g3a = bool(audit(clone['chapters']))
hard(_g3a, 'G3 植入[改汇合父引用] MISSED')
print('植入[改汇合父引用]  : %s' % ('CAUGHT' if _g3a else 'MISSED'))
n824['parents'] = before
next(n for c in clone['chapters'] if c['id'] == 8 for n in c['nodes'] if n['sid'] == 804)['code'] = '00'
_g3b = bool(audit(clone['chapters']))
hard(_g3b, 'G3 植入[改卡面编号] MISSED')
print('植入[改卡面编号]    : %s' % ('CAUGHT' if _g3b else 'MISSED'))
clone = CLONE()
next(n for c in clone['chapters'] if c['id'] == 8 for n in c['nodes'] if n['sid'] == 817)['time']['clock'] = '09:99'
_g3c = bool(audit(clone['chapters']))
hard(_g3c, 'G3 植入[改节点时刻] MISSED')
print('植入[改节点时刻]    : %s' % ('CAUGHT' if _g3c else 'MISSED'))
clone = CLONE()
clone['chapters'][0]['nodes'].pop()
_g3d = bool(audit(clone['chapters']))
hard(_g3d, 'G3 植入[删一个节点] MISSED')
print('植入[删一个节点]    : %s' % ('CAUGHT' if _g3d else 'MISSED'))
clone = CLONE()
normal = next(c for c in clone['chapters'] if not c.get('special'))
normal['special'] = True
_g3e = bool(audit(clone['chapters']))
hard(_g3e, 'G3 植入[给有边章盖特别篇标记] MISSED')
print('植入[给有边章盖特别篇标记]: %s' % ('CAUGHT' if _g3e else 'MISSED'))
clone = CLONE()
normal = next(c for c in clone['chapters'] if not c.get('special'))
normal['no'] = None
_g3f = bool(audit(clone['chapters']))
hard(_g3f, 'G3 植入[把普通章的编号置空] MISSED')
print('植入[把普通章的编号置空]  : %s' % ('CAUGHT' if _g3f else 'MISSED'))

# ---- H2 几何植入 ---------------------------------------------------------------
print()
print('H2 变异测试')
k = CLONE()
ns = [n for c in k['chapters'] if c['id'] == 8 for n in c['nodes']]
a = next(n for n in ns if n['sid'] == 810)
b = next(n for n in ns if n['sid'] == 811)
a['lane'] = b['lane']
a['y'] = b['y']
_h2a = bool(audit_geometry(k['chapters']))
hard(_h2a, 'H2 植入[两卡挤同一轨道] MISSED')
print('植入[两卡挤同一轨道] : %s' % ('CAUGHT' if _h2a else 'MISSED'))
k = CLONE()
n824 = next(n for c in k['chapters'] if c['id'] == 8 for n in c['nodes'] if n['sid'] == 824)
n824['col'] = 3
n824['x'] = 3 * 264
_h2b = bool(audit_geometry(k['chapters']))
hard(_h2b, 'H2 植入[汇合点挪到左边] MISSED')
print('植入[汇合点挪到左边] : %s' % ('CAUGHT' if _h2b else 'MISSED'))
k = CLONE()
c8 = next(c for c in k['chapters'] if c['id'] == 8)
c8['geometry']['edges'] = [e for e in c8['geometry']['edges'] if e[1] != 'STm07_15']
_h2c = bool(audit_geometry(k['chapters']))
hard(_h2c, 'H2 植入[删掉进汇合点的边] MISSED')
print('植入[删掉进汇合点的边]: %s' % ('CAUGHT' if _h2c else 'MISSED'))

# ---- H3 落点植入 ---------------------------------------------------------------
print()
print('H3 变异测试')
k = CLONE()
first = next(c for c in k['chapters'] if c['geometry'])
h3_page = os.path.join(SITE, 'main', first['slug'], 'index.html')
src = open(h3_page, encoding='utf-8').read()
tmp = h3_page + '.bak'
shutil.copyfile(h3_page, tmp)
try:
    open(h3_page, 'w', encoding='utf-8').write(src.replace(' id="col1"', '', 1))
    _h3a = bool(audit_graph_page(first, SITE))
    hard(_h3a, 'H3 植入[抹掉一个列锚点] MISSED')
    print('植入[抹掉一个列锚点]: %s' % ('CAUGHT' if _h3a else 'MISSED'))
    open(h3_page, 'w', encoding='utf-8').write(
        src.replace('data-col="0" href="../../main/%s/' % first['slug'],
                    'data-col="0" href="../../main/gone/', 1))
    _h3b = bool(audit_graph_page(first, SITE))
    hard(_h3b, 'H3 植入[卡片链接指空] MISSED')
    print('植入[卡片链接指空]  : %s' % ('CAUGHT' if _h3b else 'MISSED'))
finally:
    shutil.move(tmp, h3_page)
_h3re = not audit_graph_page(first, SITE)
hard(_h3re, 'H3 还原后复检 FAIL')
print('还原后复检: %s' % ('PASS' if _h3re else 'FAIL'))

sp_chapters = [c for c in CH['chapters'] if c.get('special')]
hard(bool(sp_chapters), 'H3 侧车里没有任何特别篇(special)章')
for sp_c in sp_chapters:
    sp_page = os.path.join(SITE, 'main', sp_c['slug'], 'index.html')
    sp_src = open(sp_page, encoding='utf-8').read()
    m = re.search(r'<li><a href="([^"]+)"><span class="code">', sp_src)
    hard(bool(m), 'H3 特别篇页面里找不到可点条目: %s' % sp_c['slug'])
    shutil.copyfile(sp_page, sp_page + '.bak')
    try:
        open(sp_page, 'w', encoding='utf-8').write(
            sp_src.replace('<li><a href="%s"><span class="code">' % m.group(1),
                           '<li><a href="#"><span class="code">', 1))
        _h3c = bool(audit_graph_page(sp_c, SITE))
        hard(_h3c, 'H3 植入[无剧本关卡给占位链接] MISSED (%s)' % sp_c['slug'])
        print('植入[无剧本关卡给占位链接] %s: %s'
              % (sp_c['slug'], 'CAUGHT' if _h3c else 'MISSED'))
    finally:
        shutil.move(sp_page + '.bak', sp_page)
    _h3re2 = not audit_graph_page(sp_c, SITE)
    hard(_h3re2, 'H3 还原后复检(特别篇) FAIL (%s)' % sp_c['slug'])
    print('还原后复检(特别篇) %s: %s' % (sp_c['slug'], 'PASS' if _h3re2 else 'FAIL'))

# ---- I2 HTML 逐句植入 ----------------------------------------------------------
print()
print('I2 变异测试')
victim = next(p for p in pages if '<r=' in open(
    os.path.join(OUT, *p['page_md'].split('/')), encoding='utf-8').read())
vp = os.path.join(SITE, *victim['page'].split('/'))
orig = open(vp, encoding='utf-8').read()
want = [md_view(m.group(2)) for m in MD_LINE.finditer(
    open(os.path.join(OUT, *victim['page_md'].split('/')), encoding='utf-8').read())]
tmp = vp + '.mut'
_i2_pos = html_lines(vp) == want
hard(_i2_pos, 'I2 正对照 FAIL')
print('正对照（未篡改）    : %s' % ('PASS' if _i2_pos else 'FAIL'))
for label, mut in [
        ('植入[改 HTML 一个字]', orig.replace('」', 'X」', 1)),
        ('植入[弄坏一行结构]  ', orig.replace('<p class="line', '<p class="x" data-line="', 1)),
        ('植入[HTML 丢一处注音]', orig.replace('魔<ruby class="ruby-point"><rt>mowang</rt></ruby>', '魔', 1)),
        ('植入[注音挪了位置]  ', orig.replace('魔<ruby class="ruby-point"><rt>mowang</rt></ruby>',
                                             '王<ruby class="ruby-point"><rt>mowang</rt></ruby>', 1))]:
    if mut == orig:
        print('%s : 样本里没有该形状' % label)
        continue
    open(tmp, 'w', encoding='utf-8', newline='\n').write(mut)
    _i2_ok = html_lines(tmp) != want
    hard(_i2_ok, 'I2 %s MISSED' % label.strip())
    print('%s : %s' % (label, 'CAUGHT' if _i2_ok else 'MISSED'))
os.remove(tmp)

# ---- J2 索引植入 ---------------------------------------------------------------
print()
print('J2 变异测试')
k = K()
k['entries'] = k['entries'][:-1]
_j2a = bool(audit_index(k['entries']))
hard(_j2a, 'J2 植入[从索引删一页] MISSED')
print('植入[从索引删一页] : %s' % ('CAUGHT' if _j2a else 'MISSED'))
k = K()
k['entries'][0]['speakers'] = ['不存在的人']
_j2b = bool(audit_index(k['entries']))
hard(_j2b, 'J2 植入[写入假说话人] MISSED')
print('植入[写入假说话人] : %s' % ('CAUGHT' if _j2b else 'MISSED'))
k = K()
k['entries'][3]['page'] = 'nowhere/ghost.html'
_j2c = bool(audit_index(k['entries']))
hard(_j2c, 'J2 植入[页面链接指空] MISSED')
print('植入[页面链接指空] : %s' % ('CAUGHT' if _j2c else 'MISSED'))

# ---- J3 全文覆盖植入 -----------------------------------------------------------
print()
print('J3 变异测试')
k = K()
_pub = [e for e in k['entries'] if not GATE.is_page(e['family'], e['id'])]
_v = _pub[0]
_orig_hay = _v['hay']
_v['hay'] = _orig_hay[:20]
_j3a = bool(audit_fulltext(_pub))
hard(_j3a, 'J3 植入[截断一条 hay] MISSED')
print('植入[截断一条 hay] : %s' % ('CAUGHT' if _j3a else 'MISSED'))
k = K()
_pub = [e for e in k['entries'] if not GATE.is_page(e['family'], e['id'])]
_pub[0]['hay'], _pub[1]['hay'] = _pub[1]['hay'], _pub[0]['hay']
_j3b = bool(audit_fulltext(_pub))
hard(_j3b, 'J3 植入[对调两条 hay] MISSED')
print('植入[对调两条 hay] : %s' % ('CAUGHT' if _j3b else 'MISSED'))

# ---- J4 懒加载植入 -------------------------------------------------------------
print()
print('J4 变异测试')
_victim = os.path.join(SITE, 'index.html')
_orig_v = open(_victim, encoding='utf-8').read()
try:
    open(_victim, 'w', encoding='utf-8', newline='\n').write(
        _orig_v.replace('</body>', '<script src="data/search.js"></script></body>', 1))
    _j4a = bool(audit_lazy())
    hard(_j4a, 'J4 植入[把 search.js 写回页面] MISSED')
    print('植入[把 search.js 写回页面] : %s' % ('CAUGHT' if _j4a else 'MISSED'))
finally:
    open(_victim, 'w', encoding='utf-8', newline='\n').write(_orig_v)
_j4b = not audit_lazy()
hard(_j4b, 'J4 植入[还原后未恢复] MISSED')
print('植入[还原后恢复]           : %s' % ('CAUGHT' if _j4b else 'MISSED'))

# ---- L2 分支角标植入 -----------------------------------------------------------
print()
print('L2 变异测试')
victim = os.path.join(SITE, 'main', 'ch08', 'STm08_15.html')
orig_l = open(victim, encoding='utf-8').read()
mut_l = orig_l.replace('<strong>13A 白猫的过去 →</strong>', '<strong>13B 沙蝎的野望 →</strong>', 1)
shutil.copyfile(victim, victim + '.bak')
try:
    open(victim, 'w', encoding='utf-8', newline='\n').write(mut_l)
    l_errs, _p, _o = audit_branch_badges()
    caught = len([e for e in l_errs if e[0] == 'main/ch08/STm08_15.html']) > 0
    hard(caught, 'L2 植入[把「听听艾蕾的意见」的角标改成 13B] MISSED')
    print('植入[把「听听艾蕾的意见」的角标改成 13B] : %s' % ('CAUGHT' if caught else 'MISSED'))
finally:
    shutil.move(victim + '.bak', victim)
_l2re = not audit_branch_badges()[0]
hard(_l2re, 'L2 还原后复检 FAIL')
print('还原后复检: %s' % ('PASS' if _l2re else 'FAIL'))

# ---- M2 锚点/玩家回应植入 ------------------------------------------------------
print()
print('M2 变异测试')
victim = os.path.join(SITE, 'characters', '126', '12603.html')
orig_m = open(victim, encoding='utf-8').read()
shutil.copyfile(victim, victim + '.bak')
try:
    mut_page = mut_ref = None
    for _p in pages:
        _hp = os.path.join(SITE, *_p['page'].split('/'))
        if not os.path.exists(_hp):
            continue
        _m = re.search(r'href="#(choice-\d+)"', open(_hp, encoding='utf-8').read())
        if _m:
            mut_page, mut_ref = _hp, _m.group(1)
            break
    if mut_page is None:
        print('植入[抹掉被引用的气泡 id]: MISSED（站内已无 #choice 引用，测试失效）')
    else:
        mut = open(mut_page, encoding='utf-8').read()
        shutil.copyfile(mut_page, mut_page + '.bak')
        try:
            open(mut_page, 'w', encoding='utf-8', newline='\n').write(
                mut.replace(' id="%s"' % mut_ref, '', 1))
            _m2a = bool(audit_anchors())
            hard(_m2a, 'M2 植入[抹掉被引用的气泡 id] MISSED')
            print('植入[抹掉被引用的气泡 id #%s @ %s]: %s'
                  % (mut_ref, os.path.basename(mut_page),
                     'CAUGHT' if _m2a else 'MISSED'))
        finally:
            shutil.move(mut_page + '.bak', mut_page)
    open(victim, 'w', encoding='utf-8', newline='\n').write(
        re.sub(r'<div class="player-reply"[^>]*>', '<div class="removed-reply">', orig_m, count=1))
    _m2b = bool(audit_player_replies()[0])
    hard(_m2b, 'M2 植入[删掉一个回应气泡] MISSED')
    print('植入[删掉一个回应气泡]: %s' % ('CAUGHT' if _m2b else 'MISSED'))
finally:
    shutil.move(victim + '.bak', victim)
_m2re = not audit_anchors() and not audit_player_replies()[0]
hard(_m2re, 'M2 还原后复检 FAIL')
print('还原后复检: %s' % ('PASS' if _m2re else 'FAIL'))

# ---- M3 单选项分支框植入 -------------------------------------------------------
print()
print('M3 变异测试')
victim3 = os.path.join(SITE, 'characters', '126', '12603.html')
orig_3 = open(victim3, encoding='utf-8').read()
shutil.copyfile(victim3, victim3 + '.bak')
try:
    planted = ('<p class="branch-open" id="branch-6-0">'
               '若选「别拖了，快赶不上演出了」↓</p>\n')
    anchor = '<h2 data-part="3">'
    if anchor not in orig_3:
        hard(False, 'M3 变异测试失效：找不到插入点 %s' % anchor)
        print('植入[把单选项抉择的若选画回分支框]: MISSED（找不到插入点 %s）' % anchor)
    else:
        open(victim3, 'w', encoding='utf-8', newline='\n').write(
            orig_3.replace(anchor, planted + anchor, 1))
        _m3a = bool(audit_single_option_choices()[0])
        hard(_m3a, 'M3 植入[把单选项抉择的若选画回分支框] MISSED')
        print('植入[把单选项抉择的若选画回分支框]: %s'
              % ('CAUGHT' if _m3a else 'MISSED'))
finally:
    shutil.move(victim3 + '.bak', victim3)
_m3re = not audit_single_option_choices()[0]
hard(_m3re, 'M3 还原后复检 FAIL')
print('还原后复检: %s' % ('PASS' if _m3re else 'FAIL'))

# ---- N2 门控泄露植入 -----------------------------------------------------------
print()
print('N2 变异测试')
if not GATE:
    print('（当前没有被门控的组，N2 无样本可跑）')
else:
    first = next(it for items in GATE.groups.values() for it in items.values())
    f_names, f_titles = forbidden_strings(first)
    f_url = first['pages'][0]
    victim = os.path.join(SITE, *f_url.split('/'))
    donor = os.path.join(SITE, *published[0]['page'].split('/'))
    orig_v = open(victim, encoding='utf-8').read()
    orig_d = open(donor, encoding='utf-8').read()
    idx_page = os.path.join(SITE, SLUG[first['family']], 'index.html')
    orig_i = open(idx_page, encoding='utf-8').read()
    js_path = os.path.join(SITE, 'data', 'search.js')
    orig_js = open(js_path, encoding='utf-8').read()
    try:
        open(victim, 'w', encoding='utf-8', newline='\n').write(orig_d)
        _n2a = bool(audit_locked())
        hard(_n2a, 'N2 植入[把正文页写回锁定 URL] MISSED')
        print('植入[把正文页写回锁定 URL] : %s' % ('CAUGHT' if _n2a else 'MISSED'))
        open(victim, 'w', encoding='utf-8', newline='\n').write(orig_v)
        if f_names:
            open(idx_page, 'w', encoding='utf-8', newline='\n').write(
                orig_i.replace(release_gate.MASK, f_names[0], 1))
            _n2b = bool(audit_locked())
            hard(_n2b, 'N2 植入[给占位卡写上组名] MISSED')
            print('植入[给占位卡写上组名]     : %s' % ('CAUGHT' if _n2b else 'MISSED'))
            open(idx_page, 'w', encoding='utf-8', newline='\n').write(orig_i)
        if f_titles:
            open(victim, 'w', encoding='utf-8', newline='\n').write(
                orig_v.replace('<h1>尚未开放</h1>',
                               '<h1>尚未开放 %s</h1>' % f_titles[0], 1))
            _n2c = bool(audit_locked())
            hard(_n2c, 'N2 植入[给提示页写上话数标题] MISSED')
            print('植入[给提示页写上话数标题] : %s' % ('CAUGHT' if _n2c else 'MISSED'))
            open(victim, 'w', encoding='utf-8', newline='\n').write(orig_v)
        open(js_path, 'w', encoding='utf-8', newline='\n').write(
            orig_js.rstrip().rstrip(';') + ',{"id":999999999,"family":"%s","page":"%s"};\n'
            % (first['family'], f_url))
        _n2d = bool(audit_locked())
        hard(_n2d, 'N2 植入[把锁定 URL 塞回检索] MISSED')
        print('植入[把锁定 URL 塞回检索]  : %s' % ('CAUGHT' if _n2d else 'MISSED'))
        open(js_path, 'w', encoding='utf-8', newline='\n').write(orig_js)
        os.remove(victim)
        _n2e = bool(audit_locked())
        hard(_n2e, 'N2 植入[删掉一个提示页] MISSED')
        print('植入[删掉一个提示页]       : %s' % ('CAUGHT' if _n2e else 'MISSED'))
    finally:
        if not os.path.exists(victim):
            open(victim, 'w', encoding='utf-8', newline='\n').write(orig_v)
        open(idx_page, 'w', encoding='utf-8', newline='\n').write(orig_i)
        open(donor, 'w', encoding='utf-8', newline='\n').write(orig_d)
    _n2re = not audit_locked()
    hard(_n2re, 'N2 还原后复检 FAIL')
    print('还原后复检: %s' % ('PASS' if _n2re else 'FAIL'))

# ---- 汇总 ---------------------------------------------------------------------
print()
print('=' * 66)
if HARD:
    print('注：数据对账本身有 %d 处违例（见上方 validate_site 输出），与变异审计无关。' % len(HARD))
if MUT_HARD:
    print('MUTATION RESULT: FAIL —— %d 处植入未被抓到：' % len(MUT_HARD))
    for x in MUT_HARD:
        print('   ✗', x)
    sys.exit(1)
print('MUTATION RESULT: PASS —— 全部植入变异都被同一套 audit 抓到')
sys.exit(0)