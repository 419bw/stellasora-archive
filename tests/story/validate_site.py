# -*- coding: utf-8 -*-
"""
Independent validator for the site-facing sidecars in story_docs/_data/.

Ground truth is re-derived from the raw tables and a naive line scan of the Lua; this
file imports neither build_story.py nor graph_layout.py.

G  图数据  : chapters.json 的每个节点字段 == 独立重导，且图不变量成立
G2 侧车一致: sections.json 的页面集合 == 磁盘上的 md 集合，stems/计数与剧本原文对得上
G3 变异测试: 篡改 JSON 后必须被同一套断言抓到
"""
import sys, os, re, json, shutil, collections, functools

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, 'story_docs', '_data')
OUT = os.path.join(ROOT, 'story_docs')
SITE = os.path.join(ROOT, 'site')
BIN = os.path.join(ROOT, 'data', 'StellaSoraData', 'CN', 'bin')
LANG = os.path.join(ROOT, 'data', 'StellaSoraData', 'CN', 'language', 'zh_CN')
CFG = os.path.join(ROOT, 'data', 'ss_lua', 'Lua', 'Game', 'UI', 'Avg', '_cn', 'Config')


def table(name, folder=BIN):
    o = json.load(open(os.path.join(folder, name + '.json'), encoding='utf-8'))
    return o if isinstance(o, dict) else {str(r['Id']): r for r in o}


def lang(name):
    return json.load(open(os.path.join(LANG, name + '.json'), encoding='utf-8'))


STORY, CHAP = table('Story'), table('StoryChapter')
TS = table('StoryChapterTimeStamp')
L_STORY, L_CHAP, L_TS = lang('Story'), lang('StoryChapter'), lang('StoryChapterTimeStamp')


def txt(table_lang, key):
    return re.sub(r'\s+', ' ', table_lang.get(key, '')).strip()


def first_scene(stem):
    """(clock, month, day) of the first SetSceneHeading, by naive line scan.

    Values are whitespace-normalised the same way the generator does it, so a double
    space inside an official line is not reported as a divergence.
    """
    p = os.path.join(CFG, stem + '.lua')
    if not os.path.exists(p):
        return None
    ls = [l.rstrip('\r') for l in open(p, encoding='utf-8').read().splitlines()]
    for i, l in enumerate(ls):
        if 'cmd = "SetSceneHeading"' not in l:
            continue
        vals = []
        for j in range(i + 1, len(ls)):
            s = ls[j].strip()
            if s.startswith('}'):
                break
            if not s.startswith('cmd') and not s.startswith('param') and not s.startswith('{'):
                vals.append(s.rstrip(',').strip())
            if s.startswith('param') and '{' in s and s.rstrip().endswith('}'):
                vals += [v.strip().rstrip('}') for v in s.split('{', 1)[1].split(',')]
        if len(vals) >= 3:
            norm = lambda x: re.sub(r'\s+', ' ', x.strip('"')).strip()
            return (norm(vals[0]), norm(vals[1]), norm(vals[2]))
        return None
    return None


def expect_node(row):
    """What the tables say about one stage, with no help from the generator."""
    battle = bool(row.get('IsBattle'))
    stem = None if battle else row.get('StoryId')
    scene = first_scene(stem) if stem else None
    return {
        'sid': row['Id'],
        'story_id': row.get('StoryId'),
        'code': txt(L_STORY, row.get('Index', '')),
        'title': txt(L_STORY, row.get('Title', '')),
        'kind': 'battle' if battle else 'story',
        'is_branch': bool(row.get('IsBranch')),
        'is_last': bool(row.get('IsLast')),
        'memory': row.get('MemoryType'),
        'condition': row.get('ConditionId'),
        'parents': [p for p in (row.get('ParentStoryId') or []) if isinstance(p, str)],
        'time': None if not scene else {'clock': scene[0], 'date': "%s %s" % (scene[1], scene[2])},
    }


CH = json.load(open(os.path.join(DATA, 'chapters.json'), encoding='utf-8'))
nodes = {n['sid']: n for c in CH['chapters'] for n in c['nodes']}
STORIES_CHAPTER = {r['StoryId']: r['Chapter'] for r in STORY.values()}

print("=" * 66)
print("G  chapters.json == 表 + 剧本独立重导（196 节点，逐字段）")
print("=" * 66)
bad = []
for row in STORY.values():
    exp = expect_node(row)
    got = nodes.get(exp['sid'])
    if got is None:
        bad.append(('缺节点', exp['sid']))
        continue
    for k, v in exp.items():
        if k == 'parents':
            if sorted(got.get(k, [])) != sorted(v):
                bad.append((exp['sid'], k, v, got.get(k)))
        elif got.get(k) != v:
            bad.append((exp['sid'], k, v, got.get(k)))
extra = sorted(set(nodes) - {r['Id'] for r in STORY.values()})
print('表行数 %d  JSON 节点数 %d  字段不符 %d  JSON 多出的节点 %d'
      % (len(STORY), len(nodes), len(bad), len(extra)))
for x in bad[:8]:
    print('   ~', x)

print()
print("-- 图不变量 --")
inv = []
for c in CH['chapters']:
    by_sid = {n['story_id']: n for n in c['nodes']}
    for n in c['nodes']:
        for p in n['parents']:
            q = by_sid.get(p)
            if q is None:
                inv.append(('悬空父引用', c['id'], n['sid'], p))
            elif q['sid'] == n['sid']:
                inv.append(('自环', c['id'], n['sid']))
            elif STORIES_CHAPTER.get(p) != c['id']:
                inv.append(('跨章父引用', c['id'], n['sid'], p))
    roots = [n for n in c['nodes'] if not n['parents']]
    if c['edge_source'] == 'ParentStoryId' and len(roots) != 1:
        inv.append(('根不唯一', c['id'], len(roots)))
    if c['edge_source'] == 'none' and c['id'] != 7:
        inv.append(('无边章不是特别篇', c['id']))
print('不变量违例：%d' % len(inv))
for x in inv[:8]:
    print('   ~', x)

SEC = json.load(open(os.path.join(DATA, 'sections.json'), encoding='utf-8'))
pages = SEC['pages']
page_links = {p['page'] for p in pages}
unrel = [n for n in nodes.values() if n['state'] == 'unreleased']
main_battle_archive_nodes = {
    n['sid'] for n in nodes.values()
    if n.get('kind') == 'battle' and n.get('page') and n['page'] not in page_links
}
orphan_page = [n['sid'] for n in nodes.values()
               if n['page'] and n['page'] not in page_links and n['sid'] not in main_battle_archive_nodes]


def script_in_pack(n):
    """Does the pack actually hold the script this node would render? Existence only —
    whether the *name* is the right one is contract K's job in validate_story.py."""
    sid = str(n['story_id'])
    if n['kind'] != 'battle':
        return os.path.isfile(os.path.join(CFG, sid + '.lua'))
    m = re.match(r'^BA([0-9a-zA-Z]+)_[^_]+$', sid)
    if not m:
        return False
    cand = 'BB%s_%s' % (m.group(1), re.sub(r'[^A-Za-z0-9]', '', n['code'] or ''))
    return os.path.isfile(os.path.join(CFG, cand + '.lua'))


no_pack = {str(n['sid']) for n in nodes.values() if not script_in_pack(n)}
wrong_page = [n['sid'] for n in nodes.values()
              if bool(n['page']) == (str(n['sid']) in no_pack and n['sid'] not in main_battle_archive_nodes)]
by_chap = collections.Counter(c['id'] for c in CH['chapters']
                              for n in c['nodes'] if n['state'] != 'released')
print('包内无剧本的节点：%d（按表章 %s）   page 指向不存在的剧本页：%d'
      % (len(unrel), dict(by_chap), len(orphan_page)))
print('page 与「包里是否真有剧本」不符的节点：%d（应 0）' % len(wrong_page))
bad_state = [n['sid'] for n in nodes.values()
             if (n['page'] is not None) != (n['state'] == 'released')]
print('state 与 page 不自洽的节点：%d' % len(bad_state))

print()
print("=" * 66)
print("G2 sections.json 与磁盘 md / 剧本原文对账")
print("=" * 66)
md_on_disk = set()
for dp, _d, fs in os.walk(OUT):
    for f in fs:
        if f.endswith('.md') and not os.path.basename(dp).startswith('_') and not f.startswith('_'):
            md_on_disk.add(os.path.relpath(os.path.join(dp, f), OUT).replace(os.sep, '/'))
declared = {p['page_md'] for p in pages}
print('sections 声明 %d 页   磁盘 md %d 篇   声明但缺文件 %d   磁盘上没登记 %d'
      % (len(declared), len(md_on_disk), len(declared - md_on_disk), len(md_on_disk - declared)))
for x in sorted(declared - md_on_disk)[:3]:
    print('   ~ 缺文件', x)
for x in sorted(md_on_disk - declared)[:3]:
    print('   ~ 未登记', x)

dup = [k for k, v in collections.Counter((p['family'], p['id']) for p in pages).items() if v > 1]
nopagelink = [p for p in pages if not p['page']]
badcount = []
for p in pages:
    if not p['stems']:
        badcount.append((p['family'], p['id'], '无剧本代号'))
        continue
    beats = collections.Counter()
    for stem in p['stems']:
        t = open(os.path.join(CFG, stem + '.lua'), encoding='utf-8', errors='replace').read()
        for k, cmd in (('talk', 'SetTalk'), ('msg', 'SetPhoneMsg'), ('bubble', 'SetBubble'),
                       ('scene', 'SetSceneHeading'), ('wave', 'SetGroupId')):
            beats[k] += len(re.findall(r'cmd = "%s"' % cmd, t))
    c = p['counts']
    want_talk = beats['talk'] + beats['msg']
    if c.get('talk', 0) > want_talk or c.get('bubble', 0) != beats['bubble']:
        badcount.append((p['family'], p['id'], 'talk %s<=%s bubble %s==%s'
                         % (c.get('talk', 0), want_talk, c.get('bubble', 0), beats['bubble'])))
print('重复 (family,id)：%d   缺 page 链接：%d   计数与剧本指令数矛盾：%d'
      % (len(dup), len(nopagelink), len(badcount)))
for x in badcount[:6]:
    print('   ~', x)

print()
print("=" * 66)
print("G3 变异测试（篡改 JSON 后同一套断言必须抓到）")
print("=" * 66)


def audit(chapters):
    """Re-run G's per-field + invariant checks against a possibly tampered tree."""
    flat = {n['sid']: n for c in chapters for n in c['nodes']}
    errs = []
    for row in STORY.values():
        exp = expect_node(row)
        got = flat.get(exp['sid'])
        if got is None:
            errs.append(('缺节点', exp['sid']))
            continue
        for k, v in exp.items():
            if k == 'parents':
                if sorted(got.get(k, [])) != sorted(v):
                    errs.append((exp['sid'], 'parents'))
            elif got.get(k) != v:
                errs.append((exp['sid'], k))
    for c in chapters:
        ids = {n['story_id'] for n in c['nodes']}
        for n in c['nodes']:
            for p in n['parents']:
                if p not in ids:
                    errs.append((c['id'], '悬空父引用', n['sid'], p))
    return errs


base = audit(CH['chapters'])
print('正对照（未篡改）: %s（%d 条错误）' % ('PASS' if not base else 'FAIL', len(base)))
clone = json.loads(open(os.path.join(DATA, 'chapters.json'), encoding='utf-8').read())
n817 = next(n for c in clone['chapters'] if c['id'] == 8 for n in c['nodes'] if n['sid'] == 817)
n824 = next(n for c in clone['chapters'] if c['id'] == 8 for n in c['nodes'] if n['sid'] == 824)
before = list(n824['parents'])
n824['parents'] = [n817['parents'][0]]
print('植入[改汇合父引用]  : %s' % ('CAUGHT' if audit(clone['chapters']) else 'MISSED'))
n824['parents'] = before
next(n for c in clone['chapters'] if c['id'] == 8 for n in c['nodes'] if n['sid'] == 804)['code'] = '00'
print('植入[改卡面编号]    : %s' % ('CAUGHT' if audit(clone['chapters']) else 'MISSED'))
clone = json.loads(open(os.path.join(DATA, 'chapters.json'), encoding='utf-8').read())
next(n for c in clone['chapters'] if c['id'] == 8 for n in c['nodes'] if n['sid'] == 817)['time']['clock'] = '09:99'
print('植入[改节点时刻]    : %s' % ('CAUGHT' if audit(clone['chapters']) else 'MISSED'))
clone = json.loads(open(os.path.join(DATA, 'chapters.json'), encoding='utf-8').read())
clone['chapters'][0]['nodes'].pop()
print('植入[删一个节点]    : %s' % ('CAUGHT' if audit(clone['chapters']) else 'MISSED'))


# ============================================================ H  节点图几何
print()
print("=" * 66)
print("H  布局几何：列单调、同列不撞位、卡片矩形互不相交、边只在相邻列之间")
print("=" * 66)


def audit_geometry(chapters):
    errs = []
    for c in chapters:
        g = c['geometry']
        if c['edge_source'] == 'none':
            if g is not None:
                errs.append((c['id'], '无边却有几何'))
            continue
        if g is None:
            errs.append((c['id'], '有边却无几何'))
            continue
        by = {n['story_id']: n for n in c['nodes']}
        cw, chh = g['card']
        memo = {}

        def depth(s, trail=()):
            if s in memo:
                return memo[s]
            ps = [p for p in by[s]['parents'] if p in by]
            memo[s] = 0 if not ps else 1 + max(depth(p, trail) for p in ps)
            return memo[s]

        lanes = collections.defaultdict(list)
        for n in c['nodes']:
            if n['col'] != depth(n['story_id']):
                errs.append((c['id'], n['sid'], '列 != 最长路径'))
            if n['x'] != n['col'] * g['step_x']:
                errs.append((c['id'], n['sid'], 'x 与列不符'))
            lanes[n['col']].append(n)
        for col, group in lanes.items():
            if len({n['lane'] for n in group}) != len(group):
                errs.append((c['id'], col, '同列撞位'))
        top = min(n['lane'] for n in c['nodes'])
        for n in c['nodes']:
            if n['y'] != (n['lane'] - top) * g['step_y']:
                errs.append((c['id'], n['sid'], 'y 与 lane 不符'))
        rects = [(n['x'], n['y'], n['x'] + cw, n['y'] + chh) for n in c['nodes']]
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                a, b = rects[i], rects[j]
                if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                    errs.append((c['id'], '卡片矩形重叠', i, j))
        for u, v in g['edges']:
            if u not in by or v not in by:
                errs.append((c['id'], '边端点不存在', u, v))
            elif by[v]['col'] - by[u]['col'] != 1:
                errs.append((c['id'], '边跨了非相邻列', u, v))
            elif u not in by[v]['parents']:
                errs.append((c['id'], '边不是 ParentStoryId 里的关系', u, v))
        if len(g['edges']) != sum(len(n['parents']) for n in c['nodes']):
            errs.append((c['id'], '边数与父引用总数不等'))
        if g['width'] < max(r[2] for r in rects) or g['height'] < max(r[3] for r in rects):
            errs.append((c['id'], '画布装不下卡片'))
    return errs


h_errs = audit_geometry(CH['chapters'])
print('几何违例：%d' % len(h_errs))
for x in h_errs[:8]:
    print('   ~', x)
print('各章：列数 / 宽 / 高 / 边数')
for c in CH['chapters']:
    g = c['geometry']
    print('   ch=%-3d %-5s %s' % (c['id'], c['no'] or '特别篇',
          '-' if not g else '列=%-3d 宽=%-5d 高=%-4d 边=%d' % (g['columns'], g['width'], g['height'], len(g['edges']))))

print()
print('H2 变异测试')
CLONE = lambda: json.loads(open(os.path.join(DATA, 'chapters.json'), encoding='utf-8').read())
print('正对照（未篡改）: %s（%d 条错误）' % ('PASS' if not h_errs else 'FAIL', len(h_errs)))
k = CLONE()
ns = [n for c in k['chapters'] if c['id'] == 8 for n in c['nodes']]
a = next(n for n in ns if n['sid'] == 810)
b = next(n for n in ns if n['sid'] == 811)
a['lane'] = b['lane']
a['y'] = b['y']
print('植入[两卡挤同一轨道] : %s' % ('CAUGHT' if audit_geometry(k['chapters']) else 'MISSED'))
k = CLONE()
n824 = next(n for c in k['chapters'] if c['id'] == 8 for n in c['nodes'] if n['sid'] == 824)
n824['col'] = 3
n824['x'] = 3 * 264
print('植入[汇合点挪到左边] : %s' % ('CAUGHT' if audit_geometry(k['chapters']) else 'MISSED'))
k = CLONE()
c8 = next(c for c in k['chapters'] if c['id'] == 8)
c8['geometry']['edges'] = [e for e in c8['geometry']['edges'] if e[1] != 'STm07_15']
print('植入[删掉进汇合点的边]: %s' % ('CAUGHT' if audit_geometry(k['chapters']) else 'MISSED'))


# ---- H3 图页面渲染出来的落点：锚点、卡片可点性、链接是否指向真实文件
CARD = re.compile(r'<(a|div)( id="col\d+")? class="node [^"]*" style="[^"]*"'
                  r' data-col="(\d+)"(?: href="([^"]*)")?>')
ANCH = re.compile(r'<a href="#(col\d+)" data-scroll-to="\d+">')


def audit_graph_page(c, site):
    g = c['geometry']
    rel = ['main', 'ch%s' % (c['no'] or 'sp'), 'index.html']
    path = os.path.join(site, *rel)
    if not os.path.isfile(path):
        return [(c['id'], '图页面缺失', path)]
    html = open(path, encoding='utf-8').read()
    errs = []
    if g is None:
        # 特别篇官方无连线，渲染成有序列表，但"有剧本才可点"这条规则一样要成立
        items = re.findall(r'<li>(<a href="([^"]*)">)?<span class="code">', html)
        if len(items) != len(c['nodes']):
            errs.append((c['id'], '列表条目数与节点数不等', len(items), len(c['nodes'])))
        want = sum(1 for n in c['nodes'] if n['page'])
        got = sum(1 for a, _h in items if a)
        if want != got:
            errs.append((c['id'], '可点条目数 != 有剧本的节点数', want, got))
        for a, href in items:
            if a and not os.path.isfile(os.path.normpath(os.path.join(os.path.dirname(path), href))):
                errs.append((c['id'], '列表链接指向空处', href))
        if 'href="#"' in html:
            errs.append((c['id'], '无剧本的关卡仍给了占位链接'))
        return errs
    cards = CARD.findall(html)
    if len(cards) != len(c['nodes']):
        errs.append((c['id'], '卡片数与节点数不等', len(cards), len(c['nodes'])))
    want_link = sum(1 for n in c['nodes'] if n['page'])
    got_link = sum(1 for t, _i, _c, h in cards if t == 'a')
    if want_link != got_link:
        errs.append((c['id'], '可点卡片数 != 有剧本的节点数', want_link, got_link))
    for tag, cid, col, href in cards:
        if cid and int(cid.split('"')[1][3:]) != int(col):
            errs.append((c['id'], '锚点 id 挂在了别的列上', cid, col))
        if tag == 'a':
            target = os.path.normpath(os.path.join(os.path.dirname(path), href))
            if not os.path.isfile(target):
                errs.append((c['id'], '卡片链接指向空处', href))
        if tag == 'div' and href:
            errs.append((c['id'], '未开放节点却带链接', col))
    ids = [cid.split('"')[1] for _t, cid, _c, _h in cards if cid]
    if sorted(ids) != sorted('col%d' % i for i in range(g['columns'])):
        errs.append((c['id'], '每列首卡锚点不齐', len(ids), g['columns']))
    jump = ANCH.findall(html)
    if jump != ['col%d' % i for i in range(g['columns'])]:
        errs.append((c['id'], '跳转条与列数不符', len(jump)))
    for j in jump:
        if j not in ids:
            errs.append((c['id'], '跳转条指向不存在的落点', j))
    return errs


h3_errs = []
for c in CH['chapters']:
    h3_errs += audit_graph_page(c, SITE)
print()
print('H3  图页面落点：卡片可点数 / 锚点 id / 链接可达')
print('违例：%d' % len(h3_errs))
for x in h3_errs[:8]:
    print('   ~', x)
k = CLONE()
first = next(c for c in k['chapters'] if c['geometry'])
h3_page = os.path.join(SITE, 'main', 'ch%s' % (first['no'] or 'sp'), 'index.html')
src = open(h3_page, encoding='utf-8').read()
tmp = h3_page + '.bak'
shutil.copyfile(h3_page, tmp)
try:
    open(h3_page, 'w', encoding='utf-8').write(src.replace(' id="col1"', '', 1))
    print('植入[抹掉一个列锚点]: %s'
          % ('CAUGHT' if audit_graph_page(first, SITE) else 'MISSED'))
    open(h3_page, 'w', encoding='utf-8').write(
        src.replace('data-col="0" href="../../main/ch%s/' % (first['no'] or 'sp'),
                    'data-col="0" href="../../main/gone/', 1))
    print('植入[卡片链接指空]  : %s'
          % ('CAUGHT' if audit_graph_page(first, SITE) else 'MISSED'))
finally:
    shutil.move(tmp, h3_page)
print('还原后复检: %s' % ('PASS' if not audit_graph_page(first, SITE) else 'FAIL'))
sp_c = next(c for c in CH['chapters'] if c['geometry'] is None)
sp_page = os.path.join(SITE, 'main', 'chsp', 'index.html')
sp_src = open(sp_page, encoding='utf-8').read()
shutil.copyfile(sp_page, sp_page + '.bak')
try:
    open(sp_page, 'w', encoding='utf-8').write(sp_src.replace('<li><a href="../../main/chsp/BAm06x5_01.html"><span class="code">BT01',
                                                              '<li><a href="#"><span class="code">BT01', 1))
    print('植入[无剧本关卡给占位链接]: %s'
          % ('CAUGHT' if audit_graph_page(sp_c, SITE) else 'MISSED'))
finally:
    shutil.move(sp_page + '.bak', sp_page)
print('还原后复检(特别篇): %s' % ('PASS' if not audit_graph_page(sp_c, SITE) else 'FAIL'))


# ============================================================ I  HTML 与 md 不漂移
print()
print("=" * 66)
print("I  生成的 HTML 逐句序列 == 已评审的 md 逐句序列（md 对剧本由 validate_story F 保证）")
print("=" * 66)
MD_LINE = re.compile(r'^\*\*(.+?)\*\*(?:（[^）]*）)?：「(.*)」$', re.M)
HTML_LINE = re.compile(r'<p class="line[^"]*"><b class="who">.*?</b>(?:<i class="tag">.*?</i>)?'
                       r'<span class="say">「(.*?)」</span>')
MD_RUBY = re.compile(r'<r=([^<>]*)></r>')
HTML_RUBY = re.compile(r'<ruby>(.)<rt>(.*?)</rt></ruby>')


def md_view(text):
    """(去掉注音的正文, [(紧跟注音前面的字, 注音)]) as md writes it."""
    marks = []
    for m in MD_RUBY.finditer(text):
        base = MD_RUBY.sub('', text[:m.start()])
        marks.append((base[-1] if base else '', m.group(1)))
    return MD_RUBY.sub('', text), marks


def html_view(text):
    """The same two projections read back out of the rendered HTML."""
    marks = [(a, unesc(n)) for a, n in HTML_RUBY.findall(text)]
    return unesc(HTML_RUBY.sub(lambda m: m.group(1), text)), marks


def unesc(s):
    return (s.replace('&quot;', '"').replace('&#x27;', "'")
            .replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&'))


drift, missing_html = [], []
ruby_md = ruby_html = 0
for p in pages:
    hp = os.path.join(SITE, *p['page'].split('/'))
    if not os.path.exists(hp):
        missing_html.append(p['page'])
        continue
    md = open(os.path.join(OUT, *p['page_md'].split('/')), encoding='utf-8').read()
    want = [md_view(m.group(2)) for m in MD_LINE.finditer(md)]
    got = [html_view(m.group(1)) for m in HTML_LINE.finditer(
        open(hp, encoding='utf-8').read())]
    ruby_md += sum(len(w[1]) for w in want)
    ruby_html += sum(len(g[1]) for g in got)
    if want != got:
        drift.append((p['page'], len(want), len(got)))
print('应生成 HTML：%d 篇   缺文件：%d   逐句漂移：%d' % (len(pages), len(missing_html), len(drift)))
print('注音渲染：md %d 处 == HTML %d 处，一致=%s' % (ruby_md, ruby_html, ruby_md == ruby_html))
for x in drift[:5]:
    print('   ~', x)

BIN_ACT = json.load(open(os.path.join(ROOT, 'data', 'StellaSoraData', 'CN', 'bin', 'ActivityStory.json'), encoding='utf-8'))
activity_battle_pages = {
    'events/%s/%s.html' % (s['ChapterId'], s['Id'])
    for s in BIN_ACT.values() if s.get('AvgLuaName') is None
}

html_all = {os.path.relpath(os.path.join(dp, f), SITE).replace(os.sep, '/')
            for dp, _d, fs in os.walk(SITE) for f in fs if f.endswith('.html')}
main_battle_archive_pages = {
    n['page'] for n in nodes.values() if n['sid'] in main_battle_archive_nodes
}
expected = {p['page'] for p in pages} | {'index.html', 'main/index.html'} | \
           {'main/ch%s/index.html' % (c['no'] or 'sp') for c in CH['chapters']} | \
           {'%s/index.html' % s for s in ('events', 'characters', 'npc', 'discs',
                                          'storysets', 'prologue', 'battles')} | \
           main_battle_archive_pages | \
           {'events/10106/index.html', 'events/20101/index.html'} | \
           activity_battle_pages
print('HTML 总数 %d   未登记的页面 %d   该有却没有的页面 %d'
      % (len(html_all), len(html_all - expected), len(expected - html_all)))
for x in sorted(expected - html_all)[:5]:
    print('   ~ 缺', x)

# Verify battle archives (activity + main story) and activity topology maps
bt_errs = []
if len(activity_battle_pages) != 19:
    bt_errs.append(('活动战斗关卡数不符', len(activity_battle_pages), 19))
for bp in (activity_battle_pages | main_battle_archive_pages):
    full_p = os.path.join(SITE, *bp.split('/'))
    if not os.path.exists(full_p):
        bt_errs.append(('缺少战斗档案页面', bp))
        continue
    h_txt = open(full_p, encoding='utf-8').read()
    if '战斗关卡' not in h_txt:
        bt_errs.append(('战斗档案缺少战斗关卡标识', bp))
    if 'story-nav' not in h_txt:
        bt_errs.append(('战斗档案缺少故事导航', bp))

for act_id in ('10106', '20101'):
    act_map_p = os.path.join(SITE, 'events', act_id, 'index.html')
    if not os.path.exists(act_map_p):
        bt_errs.append(('缺少活动拓扑图', act_id))
    else:
        m_txt = open(act_map_p, encoding='utf-8').read()
        if 'class="node battle"' not in m_txt:
            bt_errs.append(('活动拓扑图缺少战斗节点样式', act_id))

print('活动战斗关卡与拓扑图检查违例：%d' % len(bt_errs))
for x in bt_errs[:5]:
    print('   ~', x)

print()
print('I2 变异测试')
victim = next(p for p in pages if '<r=' in open(
    os.path.join(OUT, *p['page_md'].split('/')), encoding='utf-8').read())
vp = os.path.join(SITE, *victim['page'].split('/'))
orig = open(vp, encoding='utf-8').read()
want = [md_view(m.group(2)) for m in MD_LINE.finditer(
    open(os.path.join(OUT, *victim['page_md'].split('/')), encoding='utf-8').read())]
tmp = vp + '.mut'


def html_lines(path):
    return [html_view(m.group(1)) for m in HTML_LINE.finditer(
        open(path, encoding='utf-8').read())]


print('正对照（未篡改）    : %s' % ('PASS' if html_lines(vp) == want else 'FAIL'))
for label, mut in [
        ('植入[改 HTML 一个字]', orig.replace('」', 'X」', 1)),
        ('植入[弄坏一行结构]  ', orig.replace('<p class="line', '<p class="x" data-line="', 1)),
        ('植入[HTML 丢一处注音]', orig.replace('<ruby>魔<rt>mowang</rt></ruby>', '魔', 1)),
        ('植入[注音挪了位置]  ', orig.replace('<ruby>魔<rt>mowang</rt></ruby>',
                                             '<ruby>王<rt>mowang</rt></ruby>', 1))]:
    if mut == orig:
        print('%s : 样本里没有该形状' % label)
        continue
    open(tmp, 'w', encoding='utf-8', newline='\n').write(mut)
    print('%s : %s' % (label, 'CAUGHT' if html_lines(tmp) != want else 'MISSED'))
os.remove(tmp)


# ============================================================ J  检索索引
print()
print("=" * 66)
print("J  search.json 条目可解析、说话人出自该页、计数与 HTML 对得上")
print("=" * 66)
SR = json.load(open(os.path.join(DATA, 'search.json'), encoding='utf-8'))
ent = SR['entries']
by_key = {}
bad_path, bad_speaker, bad_dup = [], [], []
for e in ent:
    key = (e['family'], e['id'])
    if key in by_key:
        bad_dup.append(key)
    by_key[key] = e
    hp = os.path.join(SITE, *(e['page'] or '?').split('/'))
    if not os.path.exists(hp):
        bad_path.append(e['page'])
        continue
    html_txt = open(hp, encoding='utf-8').read()
    md_txt = open(os.path.join(OUT, *next(p['page_md'] for p in pages
                                          if (p['family'], p['id']) == key).split('/')),
                  encoding='utf-8').read()
    for s in e['speakers']:
        if ('**%s**' % s) not in md_txt:
            bad_speaker.append((e['page'], s))
print('条目 %d   重复 (family,id) %d   路径不可解析 %d   说话人不在该页 %d'
      % (len(ent), len(bad_dup), len(bad_path), len(bad_speaker)))
for x in (bad_path + bad_speaker)[:5]:
    print('   ~', x)
# a sticker send renders as 〔发送表情〕 rather than 「台词」, so it is not an extractable line
want = sum(p['counts'].get('talk', 0) + p['counts'].get('bubble', 0)
           - p['counts'].get('sticker', 0) for p in pages)
got = sum(len(HTML_LINE.findall(open(os.path.join(SITE, *p['page'].split('/')),
                                      encoding='utf-8').read())) for p in pages)
print('应可比对台词行（talk+bubble-sticker）%d   HTML 实提取 %d   一致=%s'
      % (want, got, want == got))
js = open(os.path.join(SITE, 'data', 'search.js'), encoding='utf-8').read()
print('search.js 内嵌条目数 %d（与 json 一致=%s）'
      % (js.count('"family"'), js.count('"family"') == len(ent)))

print()
print('J2 变异测试')
K = lambda: json.loads(open(os.path.join(DATA, 'search.json'), encoding='utf-8').read())
def audit_index(entries):
    errs = []
    if len(entries) != len(pages):
        errs.append(('条目数与页数不符', len(entries), len(pages)))
    seen = set()
    for e in entries:
        key = (e['family'], e['id'])
        if key in seen:
            errs.append(('重复条目', key))
        seen.add(key)
        if not os.path.exists(os.path.join(SITE, *e['page'].split('/'))):
            errs.append(('路径不可解析', e['page']))
        rec = next((p for p in pages if (p['family'], p['id']) == key), None)
        if rec is None:
            errs.append(('索引里有未登记的页', key))
            continue
        md_txt = open(os.path.join(OUT, *rec['page_md'].split('/')), encoding='utf-8').read()
        for s in e['speakers']:
            if ('**%s**' % s) not in md_txt:
                errs.append(('说话人不在该页', e['page'], s))
    return errs

print('正对照（未篡改）: %s（%d 条错误）' % ('PASS' if not audit_index(ent) else 'FAIL',
                                       len(audit_index(ent))))
k = K()
k['entries'] = k['entries'][:-1]
print('植入[从索引删一页] : %s' % ('CAUGHT' if audit_index(k['entries']) else 'MISSED'))
k = K()
k['entries'][0]['speakers'] = ['不存在的人']
print('植入[写入假说话人] : %s' % ('CAUGHT' if audit_index(k['entries']) else 'MISSED'))
k = K()
k['entries'][3]['page'] = 'nowhere/ghost.html'
print('植入[页面链接指空] : %s' % ('CAUGHT' if audit_index(k['entries']) else 'MISSED'))


# ============================================================ L  「分支走向」角标 == 权威映射
print()
print("=" * 66)
print("L  重大抉择「分支走向」角标 == 权威「选项→跳转 EvId→关卡」映射")
print("=" * 66)
STORY_COND = table('StoryCondition')
ACT_COND = table('ActivityStoryCondition')
ACT_EVID = table('ActivityStoryEvidence')
COND_BY_EV = {}
for _row in STORY_COND.values():
    for _ev in (_row.get('EvIds_a') or []) + (_row.get('EvIds_b') or []):
        COND_BY_EV.setdefault(str(_ev), _row)
STORY_ROW_BY_COND = {}
for _row in STORY.values():
    if _row.get('ConditionId'):
        STORY_ROW_BY_COND.setdefault(_row['ConditionId'], _row)
node_by_story = {n['story_id']: n for n in nodes.values()}
main_children = collections.defaultdict(list)
for _n in nodes.values():
    for _p in (_n.get('parents') or []):
        main_children[_p].append(_n)
events_page_by_id = {str(p['id']): p for p in pages if p['family'] == 'events'}
act_children = collections.defaultdict(list)
for _lid, _row in ACT_COND.items():
    for _par in (_row.get('ActivityStoryId_a') or []) + (_row.get('ActivityStoryId_b') or []):
        act_children[str(_par)].append(str(_lid))


def lua_major_choices(stem):
    """[[(option title, jump EvId)]] per 重大抉择 in one AVG script (naive scan)."""
    p = os.path.join(CFG, stem + '.lua')
    if not os.path.exists(p):
        return []
    src = open(p, encoding='utf-8').read()
    out = []
    for m in re.finditer(r'cmd\s*=\s*"SetMajorChoice",\s*param\s*=\s*\{', src):
        seg = src[m.end():]
        cut = re.search(r'\n\s*\}\s*\},', seg)
        if cut:
            seg = seg[:cut.start()]
        strings = re.findall(r'"((?:[^"\\]|\\.)*)"', seg)
        prefabs = [i for i, s in enumerate(strings) if s.startswith('AvgChoice_')]
        opts = []
        for k, i in enumerate(prefabs):
            stop = prefabs[k + 1] if k + 1 < len(prefabs) else len(strings)
            block = strings[i + 1:stop]
            if not block:
                continue
            title = block[0]
            ev = next((s for s in block[1:] if re.fullmatch(r'E[A-Za-z0-9_]+', s)), '')
            opts.append((title, ev))
        if opts:
            out.append(opts)
    return out


BADGE_LI = re.compile(r'<li[^>]*>(.*?)</li>')


def clean_opt(s):
    s = re.sub(r'<[^>]*>', '', s)
    return re.sub(r'[.…—\s　]', '', s)


def html_choice_blocks(html):
    """[(option text, badge target text or None)] per .major-options block, in order."""
    blocks = []
    for m in re.finditer(r'<ul class="options major-options">(.*?)</ul>', html, re.S):
        opts = []
        for li in BADGE_LI.findall(m.group(1)):
            om = re.search(r'<div class="opt-main"><b>(.*?)</b>', li)
            bg = re.search(r'<a class="opt-target" href="([^"]*)"[^>]*>'
                           r'<span>分支走向</span><strong>(.*?) →</strong></a>', li)
            opts.append((unesc(om.group(1)) if om else '',
                         (unesc(bg.group(2)), bg.group(1)) if bg else (None, None)))
        blocks.append(opts)
    return blocks


def resolve_main_badge(stem, ev):
    """Expected (code title, page) for an option's jump EvId, or None if no page."""
    cur = node_by_story.get(stem)
    if not cur:
        return None
    row = COND_BY_EV.get(ev)
    if not row:
        return None
    parents = (row.get('StoryId_a') or []) + (row.get('StoryId_b') or [])
    if stem not in parents:
        return None
    child = STORY_ROW_BY_COND.get(row.get('ConditionId'))
    if not child:
        return None
    n = node_by_story.get(child.get('StoryId'))
    if not n or not n.get('page'):
        return None
    return "%s %s" % (n['code'] or '·', n['title'] or ''), n['page']


def resolve_act_badge(p, ev):
    """Events: EvId -> child activity level -> its page (child of this page only)."""
    cur_id = str(p['id'])
    want = None
    for level_id, row in ACT_EVID.items():
        if row.get('EvId') != ev:
            continue
        cond = ACT_COND.get(str(level_id), {})
        pars = (cond.get('ActivityStoryId_a') or []) + (cond.get('ActivityStoryId_b') or [])
        if cur_id in [str(x) for x in pars]:
            want = events_page_by_id.get(str(level_id))
            break
    if not want or not want.get('page'):
        return None
    return "%s %s" % (want.get('code') or '·', want.get('title') or ''), want['page']


def audit_branch_badges():
    errs = []
    checked_pages = checked_opts = 0
    for p in pages:
        if p['family'] not in ('main', 'events') or not p.get('stems') or not p.get('page'):
            continue
        stem = p['stems'][0]
        truths = []
        for st in p['stems']:
            truths += lua_major_choices(st)
        if not truths:
            continue
        # sidecar must equal the Lua re-derivation, or the badge data went stale
        side = [[(o.get('title'), o.get('ev')) for o in ch]
                for ch in (p.get('major_choices') or [])]
        if side != truths:
            errs.append((p['page'], 'sections.json major_choices 与剧本不符', side, truths))
            continue
        hp = os.path.join(SITE, *p['page'].split('/'))
        if not os.path.exists(hp):
            errs.append((p['page'], '页面缺失'))
            continue
        # badges only appear where the level actually branches (build_site gate)
        if p['family'] == 'main':
            multi = len(main_children.get(stem, [])) > 1
        else:
            multi = len(act_children.get(str(p['id']), [])) > 1
        rendered = html_choice_blocks(open(hp, encoding='utf-8').read())
        if len(rendered) != len(truths):
            errs.append((p['page'], '重大抉择块数不符', len(rendered), len(truths)))
            continue
        checked_pages += 1
        for k, (truth_ch, render_ch) in enumerate(zip(truths, rendered)):
            if len(render_ch) != len(truth_ch):
                errs.append((p['page'], '第%d个抉择选项数不符' % (k + 1), len(render_ch), len(truth_ch)))
                continue
            for (title, ev), (opt_text, badge) in zip(truth_ch, render_ch):
                checked_opts += 1
                r_text, r_href = badge if badge else (None, None)
                if not multi:
                    if r_text is not None:
                        errs.append((p['page'], '非分支关卡不该有角标', title, r_text))
                    continue
                if p['family'] == 'main':
                    want = resolve_main_badge(stem, ev)
                else:
                    want = resolve_act_badge(p, ev)
                if clean_opt(title) != clean_opt(opt_text):
                    errs.append((p['page'], '选项文本与剧本不符', title, opt_text))
                if want is None:
                    if r_text is not None:
                        errs.append((p['page'], '不该有角标', title, r_text))
                    continue
                want_text, want_page = want
                if r_text != want_text:
                    errs.append((p['page'], '角标指向错误', title, r_text, want_text))
                    continue
                target = os.path.normpath(os.path.join(os.path.dirname(p['page']), r_href or ''))
                if target.replace(os.sep, '/') != want_page:
                    errs.append((p['page'], '角标链接错误', title, r_href, want_page))
    return errs, checked_pages, checked_opts


L_errs, L_pages_n, L_opts_n = audit_branch_badges()
print('含重大抉择的页面 %d   校验选项 %d 个   违例 %d' % (L_pages_n, L_opts_n, len(L_errs)))
for x in L_errs[:8]:
    print('   ~', x)

print()
print('L2 变异测试')
victim = os.path.join(SITE, 'main', 'ch08', 'STm08_15.html')
orig_l = open(victim, encoding='utf-8').read()
mut_l = orig_l.replace('<strong>13A 白猫的过去 →</strong>', '<strong>13B 沙蝎的野望 →</strong>', 1)
shutil.copyfile(victim, victim + '.bak')
try:
    open(victim, 'w', encoding='utf-8', newline='\n').write(mut_l)
    mutted = open(victim, encoding='utf-8').read()
    l_errs, _p, _o = audit_branch_badges()
    # only the poisoned page may report an error
    caught = len([e for e in l_errs if e[0] == 'main/ch08/STm08_15.html']) > 0
    print('植入[把「听听艾蕾的意见」的角标改成 13B] : %s' % ('CAUGHT' if caught else 'MISSED'))
finally:
    shutil.move(victim + '.bak', victim)
print('还原后复检: %s' % ('PASS' if not audit_branch_badges()[0] else 'FAIL'))
