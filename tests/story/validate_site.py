# -*- coding: utf-8 -*-
"""
Independent validator for the site-facing sidecars in story_docs/_data/.

Ground truth is re-derived from the raw tables and a naive line scan of the Lua; this
file imports neither build_story.py nor graph_layout.py.

G  图数据  : chapters.json 的每个节点字段 == 独立重导，且图不变量成立
G2 侧车一致: sections.json 的页面集合 == 磁盘上的 md 集合，stems/计数与剧本原文对得上
G3 变异测试: 篡改 JSON 后必须被同一套断言抓到
"""
import sys, os, re, json, collections, functools

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, 'story_docs', '_data')
OUT = os.path.join(ROOT, 'story_docs')
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
orphan_page = [n['sid'] for n in nodes.values() if n['page'] and n['page'] not in page_links]
print('未开放节点：%d（应 11，全在第 %s 章）   page 指向不存在的剧本页：%d'
      % (len(unrel), sorted({n['sid'] // 100 for n in unrel}), len(orphan_page)))
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


# ============================================================ I  HTML 与 md 不漂移
print()
print("=" * 66)
print("I  生成的 HTML 逐句序列 == 已评审的 md 逐句序列（md 对剧本由 validate_story F 保证）")
print("=" * 66)
SITE = os.path.join(ROOT, 'site')
MD_LINE = re.compile(r'^\*\*(.+?)\*\*(?:（[^）]*）)?：「(.*)」$', re.M)
HTML_LINE = re.compile(r'<p class="line[^"]*"><b class="who">.*?</b>(?:<i class="tag">.*?</i>)?'
                       r'<span class="say">「(.*?)」</span>')


def unesc(s):
    return (s.replace('&quot;', '"').replace('&#x27;', "'")
            .replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&'))


drift, missing_html = [], []
for p in pages:
    hp = os.path.join(SITE, *p['page'].split('/'))
    if not os.path.exists(hp):
        missing_html.append(p['page'])
        continue
    md = open(os.path.join(OUT, *p['page_md'].split('/')), encoding='utf-8').read()
    want = [m.group(2) for m in MD_LINE.finditer(md)]
    got = [unesc(m.group(1)) for m in HTML_LINE.finditer(
        open(hp, encoding='utf-8').read())]
    if want != got:
        drift.append((p['page'], len(want), len(got)))
print('应生成 HTML：%d 篇   缺文件：%d   逐句漂移：%d' % (len(pages), len(missing_html), len(drift)))
for x in drift[:5]:
    print('   ~', x)

html_all = {os.path.relpath(os.path.join(dp, f), SITE).replace(os.sep, '/')
            for dp, _d, fs in os.walk(SITE) for f in fs if f.endswith('.html')}
expected = {p['page'] for p in pages} | {'index.html', 'main/index.html'} | \
           {'main/ch%s/index.html' % (c['no'] or 'sp') for c in CH['chapters']} | \
           {'%s/index.html' % s for s in ('events', 'characters', 'npc', 'discs',
                                          'storysets', 'prologue', 'battles')}
print('HTML 总数 %d   未登记的页面 %d   该有却没有的页面 %d'
      % (len(html_all), len(html_all - expected), len(expected - html_all)))
for x in sorted(expected - html_all)[:5]:
    print('   ~ 缺', x)

print()
print('I2 变异测试')
victim = next(p for p in pages if p['family'] == 'main')
vp = os.path.join(SITE, *victim['page'].split('/'))
orig = open(vp, encoding='utf-8').read()
tmp = vp + '.mut'
open(tmp, 'w', encoding='utf-8', newline='\n').write(orig.replace('」', 'X」', 1))
got = [unesc(m.group(1)) for m in HTML_LINE.finditer(open(tmp, encoding='utf-8').read())]
want = [m.group(2) for m in MD_LINE.finditer(
    open(os.path.join(OUT, *victim['page_md'].split('/')), encoding='utf-8').read())]
print('植入[改 HTML 一个字] : %s' % ('CAUGHT' if got != want else 'MISSED'))
open(tmp, 'w', encoding='utf-8', newline='\n').write(
    orig.replace('<p class="line', '<p class="x" data-line="', 1))
got = [unesc(m.group(1)) for m in HTML_LINE.finditer(open(tmp, encoding='utf-8').read())]
print('植入[弄坏一行结构]   : %s' % ('CAUGHT' if got != want else 'MISSED'))
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
