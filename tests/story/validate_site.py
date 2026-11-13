# -*- coding: utf-8 -*-
"""
Independent validator for the site-facing sidecars in story_docs/_data/.

Ground truth is re-derived from the raw tables and a naive line scan of the Lua; this
file imports neither build_story.py nor graph_layout.py.

G  图数据  : chapters.json 的每个节点字段 == 独立重导，且图不变量成立
G2 侧车一致: sections.json 的页面集合 == 磁盘上的 md 集合，stems/计数与剧本原文对得上
G3 独立重导正对照: audit 重跑 G 的断言，真实数据必须 0 错
M  页内锚点: 页内 href="#x" 都必须落在同页的 id="x" 上
M2 玩家回应: 「玩家回应」标记渲染成聊天气泡，提示词保留为前置句
M3 单选项抉择: 只提供一个选项的抉择不是分叉，不得渲染 若选 分支框/分支导航
    （上游 CG_126_03.lua 的 SetChoiceEnd 写错帧，见 _dev/AI_HANDOVER_GUIDE.md 3.5；
     生成器照实吐标记，兜底在渲染层压制，md 不动）

本文件只做数据对账（含各 audit 的正对照），CI 直接跑它。植入变异自检（篡改产物后
同一套 audit 必须抓到）拆在 mutation_site.py，改校验器/生成器代码时手动跑：
    python tests/story/mutation_site.py
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

sys.path.insert(0, os.path.join(ROOT, 'scripts', 'story'))
import release_gate
import chapter_path

# ---- 分级退出码（管线重构 Phase 0 引入）----------------------------------------
# validate_site 的全部契约（G/G2/G3/H/H2/H3/I/I2/J/J2/L/L2/M/M2/M3/N/N2）都是
# 绝对真值：侧车 JSON vs 表数据/剧本独立重导、site HTML 结构、门控泄露面。
# 任一 FAIL / MISSED / 违例非零 → exit 1（CI 红灯）。
HARD = []


def hard(cond, label):
    if not cond:
        HARD.append(label)



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
# 时间线目录（StoryLine.json 的侧车镜像）：章节的 story_line.id 必须落在其中。
STORY_LINE_IDS = {ln['id'] for ln in (CH.get('meta') or {}).get('story_lines') or []}

print("=" * 66)
print("G  chapters.json == 表 + 剧本独立重导（%d 节点，逐字段）" % len(nodes))
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
hard(not bad, 'G 节点字段不符：%d 处' % len(bad))
hard(not extra, 'G JSON 多出未声明节点：%d' % len(extra))

print()
print("-- 图不变量 --")


def chapter_invariants(chapters):
    """G 组的图不变量。G 段与 G3 变异测试共用同一套断言，避免两处漂移。

    特别篇 ⇔ 无边 ⇔ 无编号是三条双向充要（判据见 scripts/story/chapter_path.py）：
    特别篇在游戏里只有线性清单、没有拓扑图、不带章节号，所以不存在
    "特别篇却有边/却有编号"的合法形态；上游填表手滑（新增普通章漏填
    ParentStoryId 或 Index）也必须在这里炸掉，而不是静默落进 chsp 撞目录。
    """
    inv = []
    for c in chapters:
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
        if (c['edge_source'] == 'none') != bool(c.get('special')):
            inv.append(('无边与特别篇标记不一致', c['id'],
                        c['edge_source'], bool(c.get('special'))))
        if (c['no'] is None) != bool(c.get('special')):
            inv.append(('无编号与特别篇标记不一致', c['id'],
                        c['no'], bool(c.get('special'))))
        if not c.get('slug'):
            inv.append(('缺少章节目录', c['id']))
        line = c.get('story_line') or {}
        if line.get('id') is not None and line['id'] not in STORY_LINE_IDS:
            inv.append(('章节归属的时间线不存在', c['id'], line.get('id')))
    slugs = [c.get('slug') for c in chapters]
    if len(slugs) != len(set(slugs)):
        dup = sorted({s for s in slugs if slugs.count(s) > 1})
        inv.append(('章节目录撞车', dup))
    return inv


inv = chapter_invariants(CH['chapters'])
print('不变量违例：%d' % len(inv))
for x in inv[:8]:
    print('   ~', x)
hard(not inv, 'G 图不变量违例：%d 处' % len(inv))

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

# Release gate: a group whose official open time is still in the future is published
# as a locked placeholder only (scripts/site/release_gate.py, consumed by build_site).
# story_docs/ is NOT touched by the gate, so the sidecar audits below run on the full
# sidecars while every site-facing audit runs on the published subset.
GATE = release_gate.load_gate()
locked_pages = [p for p in pages if GATE.is_page(p['family'], p['id'])]
published = [p for p in pages if not GATE.is_page(p['family'], p['id'])]


def script_in_pack(n):
    """Does the pack actually hold the script this node would render? Existence only —
    whether the *name* is the right one is contract B/K's job in validate_story.py
    (StoryId battle token vs display code). Same rule as there: the battle token in the
    node's own story_id wins, the display code is only a fallback."""
    sid = str(n['story_id'])
    if n['kind'] != 'battle':
        return os.path.isfile(os.path.join(CFG, sid + '.lua'))
    m = re.match(r'^BA([0-9a-zA-Z]+)_([^_]+)$', sid)
    if not m:
        return False
    tail = re.sub(r'[^A-Za-z0-9]', '', m.group(2))
    battle_no = tail if re.fullmatch(r'BT\d+', tail) else re.sub(r'[^A-Za-z0-9]', '', n['code'] or '')
    cand = 'BB%s_%s' % (m.group(1), battle_no)
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
hard(not orphan_page, 'G page 指向不存在的剧本页：%d' % len(orphan_page))
hard(not wrong_page, 'G page 与包内剧本存在性不符：%d' % len(wrong_page))
hard(not bad_state, 'G state 与 page 不自洽：%d' % len(bad_state))

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
hard(not (declared - md_on_disk), 'G2 声明但缺文件：%d' % len(declared - md_on_disk))
hard(not (md_on_disk - declared), 'G2 磁盘上没登记：%d' % len(md_on_disk - declared))

dup = [k for k, v in collections.Counter((p['family'], p['id']) for p in pages).items() if v > 1]
nopagelink = [p for p in pages if not p['page']]
badcount = []
ENDING_T = table('SoldierEndingPlan')
for p in pages:
    if p['family'] == 'anecdotes':
        n_anec = p['counts'].get('anecdote', 0)
        if n_anec <= 0 or n_anec != len(p.get('notes') or []):
            badcount.append((p['family'], p['id'], '逸闻笔记则数异常 %s!=%s'
                             % (n_anec, len(p.get('notes') or []))))
        continue
    if p.get('table_refs'):
        # 表驱动页（尖兵陷阵终局）：无剧本代号，逐条核对表行存在
        if p['stems']:
            badcount.append((p['family'], p['id'], '表驱动页不应有剧本代号 %s' % p['stems']))
        if p['counts'].get('anecdote', 0) != 1:
            badcount.append((p['family'], p['id'], '表驱动页 anecdote 计数异常 %s'
                             % p['counts'].get('anecdote', 0)))
        for ref in p['table_refs']:
            tbl, _, rid = ref.partition('#')
            if tbl != 'SoldierEndingPlan' or rid not in ENDING_T:
                badcount.append((p['family'], p['id'], '表行不存在 %s' % ref))
        continue
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
hard(not dup, 'G2 重复 (family,id)：%d' % len(dup))
hard(not nopagelink, 'G2 缺 page 链接：%d' % len(nopagelink))
hard(not badcount, 'G2 计数与剧本指令数矛盾：%d' % len(badcount))

print()
print("=" * 66)
print("G3  独立重导正对照（audit 重跑 G 的逐字段+不变量，真实数据必须 0 错）")
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
    errs.extend(chapter_invariants(chapters))
    return errs


base = audit(CH['chapters'])
hard(not base, 'G3 正对照 FAIL（%d 条错误）' % len(base))
print('正对照（未篡改）: %s（%d 条错误）' % ('PASS' if not base else 'FAIL', len(base)))
# 植入变异（篡改 JSON 后 audit 必须抓到）已拆到 mutation_site.py，手动审计时运行。


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
hard(not h_errs, 'H 布局几何违例：%d 处' % len(h_errs))
print('各章：列数 / 宽 / 高 / 边数')
for c in CH['chapters']:
    g = c['geometry']
    print('   ch=%-3d %-5s %s' % (c['id'], c['no'] or '特别篇',
          '-' if not g else '列=%-3d 宽=%-5d 高=%-4d 边=%d' % (g['columns'], g['width'], g['height'], len(g['edges']))))

# H2 几何植入变异已拆到 mutation_site.py。


# ---- H3 图页面渲染出来的落点：锚点、卡片可点性、链接是否指向真实文件
CARD = re.compile(r'<(a|div)( id="col\d+")? class="node [^"]*" style="[^"]*"'
                  r' data-col="(\d+)"(?: href="([^"]*)")?>')
ANCH = re.compile(r'<a href="#(col\d+)" data-scroll-to="\d+">')


def audit_graph_page(c, site):
    g = c['geometry']
    rel = ['main', c['slug'], 'index.html']
    path = os.path.join(site, *rel)
    if not os.path.isfile(path):
        return [(c['id'], '图页面缺失', path)]
    html = open(path, encoding='utf-8').read()
    errs = []
    if c.get('special'):
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
hard(not h3_errs, 'H3 图页面落点违例：%d 处' % len(h3_errs))
# H3 落点植入变异（含特别篇占位链接植入）已拆到 mutation_site.py。


# ============================================================ I  HTML 与 md 不漂移
print()
print("=" * 66)
print("I  生成的 HTML 逐句序列 == 已评审的 md 逐句序列（md 对剧本由 validate_story F 保证）")
print("=" * 66)
MD_LINE = re.compile(r'^\*\*(.+?)\*\*(?:（[^）]*）)?：「(.*)」$', re.M)
HTML_LINE = re.compile(r'<p class="line[^"]*"><b class="who">.*?</b>(?:<i class="tag">.*?</i>)?'
                       r'<span class="say">「(.*?)」</span>')
MD_RUBY = re.compile(r'<r=([^<>]*)>([^<>]+)</r>|<r=([^<>]*)></r>')
HTML_RUBY = re.compile(r'<ruby(?: class="ruby-point")?>(.*?)<rt>(.*?)</rt></ruby>')
# Phase 4b：<b>/<i> 强调标记。md 侧原样字面，HTML 侧映射 <b class="emph">；
# 文字投影两边都剥掉（对照的是字，不是表现），计数另做对账。
MD_EMPH = re.compile(r'</?[bi]>')
MD_EMPH_OPEN = re.compile(r'<[bi]>')
HTML_EMPH_OPEN = re.compile(r'<[bi] class="emph">')


def md_view(text):
    """(去掉注音与强调标记的正文, [(注音落点字, 注音)]) as md writes it.

    带体 ruby <r=note>base</r> 的 base 是正文字符，投影时保留；空体 ruby
    <r=note></r> 整体删除（base 字在标签外）。HTML 侧 <ruby>base<rt> 同构。
    """
    marks = []
    for m in MD_RUBY.finditer(text):
        if m.group(2) is not None:
            marks.append((m.group(2)[-1], m.group(1)))
        else:
            base = MD_RUBY.sub(lambda x: x.group(2) or '',
                               MD_EMPH.sub('', text[:m.start()]))
            marks.append((base[-1] if base else '', m.group(3)))
    return MD_RUBY.sub(lambda m: m.group(2) or '', MD_EMPH.sub('', text)), marks


def female_html(text):
    text = re.sub(r'<span class="text-variant-controls".*?</span>', '', text, flags=re.S)
    text = re.sub(r'<span class="text-variants">(.*)</span>', r'\1', text, flags=re.S)
    text = re.sub(r'<span data-text-version="[^"]+" hidden>.*?</span>', '', text, flags=re.S)
    return re.sub(r'<span data-text-version="[^"]+">(.*?)</span>', r'\1', text, flags=re.S)


def html_view(text):
    """The same two projections read back out of the rendered HTML.

    强调标记在 unesc 之前剥（只命中真实标签；正文里字面的 &lt;b&gt; 不受影响）。
    """
    text = female_html(text)
    marks = []
    for m in HTML_RUBY.finditer(text):
        base = m[1] or re.sub(r'<[^>]*>', '', HTML_RUBY.sub(lambda x: x[1], text[:m.start()]))
        base = unesc(base)
        marks.append((base[-1] if base else '', unesc(m[2])))
    t = HTML_RUBY.sub(lambda m: m.group(1), text)
    t = re.sub(r'</?[bi](?: class="emph")?>', '', t)
    return unesc(t), marks


def unesc(s):
    return (s.replace('&quot;', '"').replace('&#x27;', "'")
            .replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&'))


ANEC_MD_BLOCK = re.compile(
    r'^###[ \t]+([^\n]+)\n\n> - \*\*笔记 ID\*\*：`(\d+)`　\*\*获取条件\*\*：([^\n]+)\n\n(.*?)(?=\n###[ \t]+|\Z)',
    re.M | re.S,
)
ANEC_HTML_BLOCK = re.compile(
    r'<article class="anecdote-book" id="note-(\d+)" data-note-id="\1">.*?'
    r'<h3 class="anecdote-title">(.*?)</h3>.*?'
    r'<div class="anecdote-prose">(.*?)</div>.*?'
    r'<span class="anecdote-cond">(.*?)</span>',
    re.S,
)

drift, missing_html, anec_drift = [], [], []
ruby_md = ruby_html = emph_md = emph_html = 0
for p in published:
    hp = os.path.join(SITE, *p['page'].split('/'))
    if not os.path.exists(hp):
        missing_html.append(p['page'])
        continue
    md = open(os.path.join(OUT, *p['page_md'].split('/')), encoding='utf-8').read()
    html = open(hp, encoding='utf-8').read()
    if p['family'] == 'anecdotes' or p.get('table_refs'):
        md_notes = [
            (m.group(2), md_view(m.group(1).strip())[0], md_view(m.group(3).strip())[0],
             [md_view(x.strip())[0] for x in m.group(4).splitlines() if x.strip()])
            for m in ANEC_MD_BLOCK.finditer(md)
        ]
        html_notes = [
            (m.group(1), html_view(m.group(2))[0], html_view(m.group(4))[0],
             [html_view(pm.group(1))[0] for pm in re.finditer(r'<p>(.*?)</p>', m.group(3), re.S)])
            for m in ANEC_HTML_BLOCK.finditer(html)
        ]
        if not md_notes or md_notes != html_notes:
            anec_drift.append((p['page'], len(md_notes), len(html_notes)))
        continue
    want = [md_view(m.group(2)) for m in MD_LINE.finditer(md)]
    got = [html_view(m.group(1)) for m in HTML_LINE.finditer(html)]
    ruby_md += sum(len(w[1]) for w in want)
    ruby_html += sum(len(g[1]) for g in got)
    emph_md += sum(len(MD_EMPH_OPEN.findall(m.group(2))) for m in MD_LINE.finditer(md))
    emph_html += sum(len(HTML_EMPH_OPEN.findall(female_html(m.group(1)))) for m in HTML_LINE.finditer(html))
    if want != got:
        drift.append((p['page'], len(want), len(got)))
print('应生成 HTML：%d 篇（另有 %d 篇未到开放时间，只显示未开放占位）   缺文件：%d   逐句漂移：%d   逸闻笔记漂移：%d'
      % (len(published), len(locked_pages), len(missing_html), len(drift), len(anec_drift)))
print('注音渲染：md %d 处 == HTML %d 处，一致=%s' % (ruby_md, ruby_html, ruby_md == ruby_html))
print('强调渲染：md <b>/<i> %d 处 == HTML emph %d 处，一致=%s'
      % (emph_md, emph_html, emph_md == emph_html))
for x in (drift + anec_drift)[:5]:
    print('   ~', x)
hard(not missing_html, 'I 应生成的 HTML 缺文件：%d' % len(missing_html))
hard(not drift, 'I HTML/md 逐句漂移：%d 页' % len(drift))
hard(not anec_drift, 'I 逸闻笔记 HTML/md 漂移：%d 页' % len(anec_drift))
hard(ruby_md == ruby_html, 'I 注音渲染数不一致: md=%d html=%d' % (ruby_md, ruby_html))
hard(emph_md == emph_html, 'I 强调标记渲染数不一致: md=%d html=%d' % (emph_md, emph_html))

BIN_ACT = json.load(open(os.path.join(ROOT, 'data', 'StellaSoraData', 'CN', 'bin', 'ActivityStory.json'), encoding='utf-8'))
activity_battle_pages = {
    'events/%s/%s.html' % (s['ChapterId'], s['Id'])
    for s in BIN_ACT.values() if s.get('AvgLuaName') is None
}
activity_locked_battles = {u for u in activity_battle_pages
                           if u in set(GATE.page_urls())}
activity_battle_pages -= activity_locked_battles

html_all = {os.path.relpath(os.path.join(dp, f), SITE).replace(os.sep, '/')
            for dp, _d, fs in os.walk(SITE) for f in fs if f.endswith('.html')}
main_battle_archive_pages = {
    n['page'] for n in nodes.values() if n['sid'] in main_battle_archive_nodes
}
expected = {p['page'] for p in published} | {'index.html', 'main/index.html'} | \
           {chapter_path.chapter_page(c['slug']) for c in CH['chapters']} | \
           {'%s/index.html' % s for s in ('events', 'characters', 'npc', 'discs',
                                          'storysets', 'prologue', 'battles',
                                          'dispatch', 'anecdotes', 'returnee',
                                          'soldier')} | \
           main_battle_archive_pages | \
           {'events/10106/index.html', 'events/20101/index.html'} | \
           activity_battle_pages | set(GATE.page_urls())
print('HTML 总数 %d   未登记的页面 %d   该有却没有的页面 %d'
      % (len(html_all), len(html_all - expected), len(expected - html_all)))
for x in sorted(expected - html_all)[:5]:
    print('   ~ 缺', x)
hard(not (html_all - expected), 'I 未登记的页面：%d' % len(html_all - expected))
hard(not (expected - html_all), 'I 该有却没有的页面：%d' % len(expected - html_all))

# Verify battle archives (activity + main story) and activity topology maps
# 关卡总数随上游增长，不设硬编码计数断言；战斗档案页已并入 expected 集合，
# 上面的页面集合对账（未登记/缺失）足以抓住任何漏渲染或多渲染。
bt_errs = []
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
    if GATE.is_group('events', act_id):
        continue  # still locked: the URL holds a notice page, not a topology map
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
hard(not bt_errs, 'I 活动战斗关卡与拓扑图违例：%d 处' % len(bt_errs))

# I2 HTML 逐句植入变异已拆到 mutation_site.py。


# ============================================================ J  检索索引
print()
print("=" * 66)
print("J  search.json 条目可解析、说话人出自该页、计数与 HTML 对得上")
print("=" * 66)
SR = json.load(open(os.path.join(DATA, 'search.json'), encoding='utf-8'))
ent = [e for e in SR['entries'] if not GATE.is_page(e['family'], e['id'])]
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
hard(not bad_dup, 'J 重复 (family,id)：%d' % len(bad_dup))
hard(not bad_path, 'J 路径不可解析：%d' % len(bad_path))
hard(not bad_speaker, 'J 说话人不在该页：%d' % len(bad_speaker))
# a sticker send renders as 〔发送表情〕 rather than 「台词」, so it is not an extractable line
want = sum(p['counts'].get('talk', 0) + p['counts'].get('bubble', 0)
           - p['counts'].get('sticker', 0) for p in published)
got = sum(len(HTML_LINE.findall(open(os.path.join(SITE, *p['page'].split('/')),
                                      encoding='utf-8').read())) for p in published)
print('应可比对台词行（talk+bubble-sticker）%d   HTML 实提取 %d   一致=%s'
      % (want, got, want == got))
hard(want == got, 'J 台词行对账不符: 应 %d 实 %d' % (want, got))
js = open(os.path.join(SITE, 'data', 'search.js'), encoding='utf-8').read()
_m = re.match(r'\s*window\.STORY_INDEX\s*=\s*', js)
hard(bool(_m), 'J search.js 缺少 window.STORY_INDEX 赋值')
# 全文 hay 里可能出现 "family" 字面量，旧的字面量计数不再可靠，改为解析后深比较
_js_entries = json.loads(js[_m.end():].rstrip().rstrip(';'))['entries']
print('search.js 条目数 %d（与 json 一致=%s）' % (len(_js_entries), _js_entries == ent))
hard(_js_entries == ent, 'J search.js 与 search.json 条目不一致')

print()
print('J2  检索索引独立审计正对照（audit_index 重导，真实数据必须 0 错）')


def audit_index(entries):
    errs = []
    if len(entries) != len(published):
        errs.append(('条目数与页数不符', len(entries), len(published)))
    seen = set()
    for e in entries:
        key = (e['family'], e['id'])
        if key in seen:
            errs.append(('重复条目', key))
        seen.add(key)
        if not os.path.exists(os.path.join(SITE, *e['page'].split('/'))):
            errs.append(('路径不可解析', e['page']))
        rec = next((p for p in published if (p['family'], p['id']) == key), None)
        if rec is None:
            errs.append(('索引里有未登记的页', key))
            continue
        md_txt = open(os.path.join(OUT, *rec['page_md'].split('/')), encoding='utf-8').read()
        for s in e['speakers']:
            if ('**%s**' % s) not in md_txt:
                errs.append(('说话人不在该页', e['page'], s))
    return errs

_j2_pos = not audit_index(ent)
hard(_j2_pos, 'J2 正对照 FAIL（%d 条错误）' % len(audit_index(ent)))
print('正对照（未篡改）: %s（%d 条错误）' % ('PASS' if _j2_pos else 'FAIL',
                                       len(audit_index(ent))))
# J2 索引植入变异已拆到 mutation_site.py。


# ============================================================ J3  全文覆盖
print()
print("=" * 66)
print("J3  全文覆盖：published 条目的每句台词都出现在其 hay 中")
print("=" * 66)
# beats 侧车文本是 serialize_text 投影（带 ruby/emph 标记），hay 是 plain 投影；
# 两种投影对同一 node 流的字符输出只差这些标记，剥掉后做包含比对
# （ruby 序列化是 base<r=note></r> 与 <r=note>base</r> 两种形态，闭合 </r> 也要剥）
_TAGSTRIP = re.compile(r'</?r(?:=[^<>]*)?>|</?[bi]>')


def beat_lines(page):
    rel = page[:-len('.html')] + '.json' if page.endswith('.html') else page + '.json'
    path = os.path.join(OUT, '_beats', *rel.split('/'))
    if not os.path.exists(path):
        return None
    doc = json.load(open(path, encoding='utf-8'))
    out = []
    for b in doc.get('beats', []):
        if b['k'] == 'anecdote':
            for fld in ('title', 'source'):
                v = b.get(fld) or ''
                if v:
                    out.append(_TAGSTRIP.sub('', v))
            for para in (b.get('story') or '').split('\n'):
                if para.strip():
                    out.append(_TAGSTRIP.sub('', para.strip()))
            continue
        if b['k'] not in ('talk', 'bubble'):
            continue
        v = b.get('text') or ''
        if isinstance(v, dict):
            # hay 只收中文槽位，jp_* 不进索引
            v = v.get('cn_f') or ''
        if v:
            out.append(_TAGSTRIP.sub('', v))
    return out


def audit_fulltext(entries):
    errs = []
    for e in entries:
        lines = beat_lines(e['page'])
        if lines is None:
            errs.append((e['page'], 'beats 侧车缺失'))
            continue
        miss = next((t for t in lines if t not in e['hay']), None)
        if miss is not None:
            errs.append((e['page'], miss[:30]))
    return errs


_j3_pos = not audit_fulltext(ent)
hard(_j3_pos, 'J3 正对照 FAIL')
print('受检条目 %d   正对照（未篡改）: %s' % (len(ent), 'PASS' if _j3_pos else 'FAIL'))
# J3 全文覆盖植入变异已拆到 mutation_site.py。


# ============================================================ J4  懒加载契约
print()
print("=" * 66)
print("J4  懒加载契约：无页面内嵌 data/search.js，索引文件仍在 site/data/")
print("=" * 66)


def audit_lazy():
    errs = []
    for dirpath, _dirs, files in os.walk(SITE):
        for f in files:
            if not f.endswith('.html'):
                continue
            p = os.path.join(dirpath, f)
            if 'data/search.js' in open(p, encoding='utf-8').read():
                errs.append(os.path.relpath(p, SITE))
    if not os.path.exists(os.path.join(SITE, 'data', 'search.js')):
        errs.append('site/data/search.js 缺失')
    return errs


_j4_pos = not audit_lazy()
hard(_j4_pos, 'J4 正对照 FAIL')
print('正对照（未篡改）: %s' % ('PASS' if _j4_pos else 'FAIL'))
# J4 懒加载植入变异已拆到 mutation_site.py。


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
    # Phase 4c：选项文本两侧投影到纯文字再比——HTML 侧 <ruby>base<rt>note</rt>
    # 折叠为 base（rt 是注音不是正文，剥标签会残留），md 侧带体 <r=note>base</r>
    # 折叠为 base、空体 <r=note></r> 随其余标签剥除（base 字本就在标签外）。
    s = re.sub(r'<ruby(?: class="ruby-point")?>(.*?)<rt>.*?</rt></ruby>', r'\1', s)
    s = re.sub(r'<r=[^>]*>([^<>]*)</r>', r'\1', s)
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
    for p in published:
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
hard(not L_errs, 'L 分支走向角标违例：%d 处' % len(L_errs))

# L2 分支角标植入变异已拆到 mutation_site.py。


# ============================================================ M  页内锚点完整性 & 玩家回应气泡
print()
print("=" * 66)
print("M  页内锚点完整性 & 「玩家回应」聊天气泡渲染")
print("=" * 66)
PR_MARK = re.compile(r'^> \*\*\[玩家回应(：([^\]]+))?\]\*\*$', re.M)
LEAD_P = re.compile(r'<p class="reply-lead">(.*?)</p>', re.S)
BUBBLE = re.compile(r'class="player-reply"')


def audit_anchors():
    """Every in-page href="#x" must land on an id="x" of the same file."""
    errs = []
    for dp, _d, fs in os.walk(SITE):
        for f in fs:
            if not f.endswith('.html'):
                continue
            html = open(os.path.join(dp, f), encoding='utf-8').read()
            ids = set(re.findall(r' id="([^"]+)"', html))
            for m in re.finditer(r'href="#([^"]+)"', html):
                if m.group(1) not in ids:
                    errs.append((os.path.relpath(os.path.join(dp, f), SITE), '#' + m.group(1)))
    return errs


def audit_player_replies():
    """每处 玩家回应 标记都要渲染成气泡；带提示词的必须保留前置句。

    Phase 4c：前置句两侧都投影到纯文字再比——HTML 侧经 _inline/ruby_html
    渲染（<ruby>base<rt>note</rt></ruby>），md 侧是字面 <r=note></r>；
    直接剥标签会让 rt 注音文本残留进正文（现库 prompt 无 ruby，防御性统一）。
    """
    def _lead_html(x):
        t = HTML_RUBY.sub(lambda m: m.group(1), x)
        t = re.sub(r'</?[bi](?: class="emph")?>', '', t)
        return unesc(re.sub(r'<[^>]+>', '', t))

    errs = []
    checked = bubbles_total = leads_total = 0
    for p in published:
        md_path = os.path.join(OUT, *p['page_md'].split('/'))
        if not os.path.exists(md_path):
            continue
        marks = PR_MARK.findall(open(md_path, encoding='utf-8').read())
        if not marks:
            continue
        checked += 1
        hp = os.path.join(SITE, *p['page'].split('/'))
        if not os.path.exists(hp):
            errs.append((p['page'], '页面缺失'))
            continue
        html = open(hp, encoding='utf-8').read()
        bubbles = len(BUBBLE.findall(html))
        leads_html = [_lead_html(x) for x in LEAD_P.findall(html)]
        leads_md = [md_view(m[1])[0] for m in marks if m[1]]
        bubbles_total += bubbles
        leads_total += len(leads_html)
        if bubbles != len(marks):
            errs.append((p['page'], '气泡数与标记数不符', bubbles, len(marks)))
        if leads_html != leads_md:
            errs.append((p['page'], '前置句与标记不符', leads_html[:3], leads_md[:3]))
    return errs, checked, bubbles_total, leads_total


M_errs = audit_anchors()
M2_errs, M2_pages, M2_bubbles, M2_leads = audit_player_replies()
print('页内锚点悬空：%d' % len(M_errs))
for x in M_errs[:5]:
    print('   ~', x)
print('含「玩家回应」的页面 %d   气泡 %d   前置句 %d   违例 %d'
      % (M2_pages, M2_bubbles, M2_leads, len(M2_errs)))
for x in M2_errs[:5]:
    print('   ~', x)
hard(not M_errs, 'M 页内锚点悬空：%d 处' % len(M_errs))
hard(not M2_errs, 'M2 玩家回应气泡违例：%d 处' % len(M2_errs))

# M2 锚点/玩家回应植入变异已拆到 mutation_site.py。


# ============================================ M3  单选项父抉择不得渲染成分支框
print()
print("=" * 66)
print("M3  单选项抉择不渲染分支框（上游 SetChoiceEnd 错帧的展示层妥协）")
print("=" * 66)
M3_MARK = re.compile(r'^> \*\*\[(.+?)\]\*\*$', re.M)
M3_BULLET = re.compile(r'^> - \*\*(.+?)\*\*(?:：(.*))?$')
M3_OPEN = re.compile(r'<p class="branch-open"[^>]*>(.*?)</p>')
MARKER = re.compile(r'^> \*\*\[(.+?)\]\*\*$')
BULLET = re.compile(r'^> - \*\*(.+?)\*\*(?:：(.*))?$')


def _m3_is_choice(tag):
    return (tag.endswith('抉择') or '抉择：' in tag or '抉择:' in tag
            or tag == '玩家回应' or tag.startswith('玩家回应：')
            or tag.startswith('通讯回复抉择'))


def audit_single_option_choices():
    """A choice offering exactly one option is a reply, not a fork.

    Upstream CG_126_03.lua closes the a_10 choice group with a_4's SetChoiceEnd,
    so the frame never pops and build_story.py re-emits the same 若选 line for
    later beats (_dev/AI_HANDOVER_GUIDE.md 3.5). The generator stays faithful to the
    data; render_html.py suppresses the marker instead. This audit re-derives the
    single-option choices straight from the md and asserts the HTML kept quiet:
    no 若选 branch header, and no branch chrome pointing back at that choice.
    """
    errs = []
    checked = singles = ruose = 0
    for p in published:
        md_path = os.path.join(OUT, *p['page_md'].split('/'))
        if not os.path.exists(md_path):
            continue
        lines = open(md_path, encoding='utf-8').read().splitlines()
        one_opt = []   # (choice tag, single option) in document order
        tags = []      # every 若选 tag on the page
        i = 0
        while i < len(lines):
            m = MARKER.match(lines[i].rstrip())
            if not m:
                i += 1
                continue
            tag = m.group(1)
            if _m3_is_choice(tag):
                opts = []
                j = i + 1
                while j < len(lines) and (BULLET.match(lines[j].rstrip()) or not lines[j].strip()):
                    bm = BULLET.match(lines[j].rstrip())
                    if bm:
                        opts.append(bm.group(1))
                    j += 1
                if len(opts) == 1:
                    one_opt.append((tag, opts[0]))
                i = j
                continue
            if tag.startswith('若选'):
                tags.append(tag)
            i += 1
        if not one_opt and not tags:
            continue
        checked += 1
        singles += len(one_opt)
        ruose += len(tags)
        hp = os.path.join(SITE, *p['page'].split('/'))
        if not os.path.exists(hp):
            errs.append((p['page'], '页面缺失'))
            continue
        html = open(hp, encoding='utf-8').read()
        # rendered choice markers carry their anchor id: <p class="choice" id="choice-N">tag</p>
        # Phase 4c：标记文本与若选选项文本都经 markup 编译器渲染（ruby→<ruby>），
        # 与 md 字面 <r=…> 不同形——两侧统一 clean_opt 投影后再匹配。
        cid = {}
        for m in re.finditer(r'<p class="choice[^"]*" id="([^"]+)">(.*?)</p>', html):
            cid[clean_opt(m.group(2))] = m.group(1)
        html_ruose = {clean_opt(m.group(1))
                      for m in re.finditer(r'<p class="branch-open"[^>]*>若选「(.*?)」', html)}
        for tag, opt in one_opt:
            if clean_opt(opt) in html_ruose:
                errs.append((p['page'], '单选项抉择被渲染成若选分支框', tag))
            anchor = cid.get(clean_opt(tag))
            if anchor and re.search(r'href="#%s"' % re.escape(anchor), html):
                errs.append((p['page'], '分支导航指向单选项抉择', tag, anchor))
    return errs, checked, singles, ruose


M3_errs, M3_pages, M3_single, M3_ruose = audit_single_option_choices()
print('含单选项抉择或若选的页面 %d   单选项抉择 %d   md 中若选 %d   违例 %d'
      % (M3_pages, M3_single, M3_ruose, len(M3_errs)))
for x in M3_errs[:5]:
    print('   ~', x)
hard(not M3_errs, 'M3 单选项抉择渲染违例：%d 处' % len(M3_errs))

# M3 单选项分支框植入变异已拆到 mutation_site.py。


# ============================================ N  未开放内容只显示未开放，不透露内容
print()
print("=" * 66)
print("N  官方未开放的组：只显示未开放占位，不得出现任何内容（release_gate 门控）")
print("=" * 66)
L_SST = lang('StorySetChapter')
L_STORY = lang('Story')
L_ACT_STORY = lang('ActivityStory')
SST_SEC = table('StorySetSection')
SST_SEC_L = lang('StorySetSection')
SST_CHAP = table('StorySetChapter')
CHAP_L = lang('StoryChapter')
CHAP_T = table('StoryChapter')
STORY_T = table('Story')
ACT_STORY_T = table('ActivityStory')
ACT_STORY_L = lang('ActivityStory')


def forbidden_strings(item):
    """Official strings that must NOT show up for a locked group.

    Read live from the language tables so the audit follows the data (and so no
    spoiler string is hard-coded inside the test itself).  Returns
    ``(names, titles)``: ``names`` are group-level labels (unique, safe to look
    for anywhere on the site), ``titles`` are generic section titles such as
    「第一话」 that other released chapters share, so they are only searched
    inside the locked group's own directory.
    """
    names, titles = [], []
    if item['family'] == 'storysets':
        row = SST_CHAP.get(str(item['id'])) or {}
        names += [txt(L_SST, row.get('Name', '')), txt(L_SST, row.get('Desc', ''))]
        for s in SST_SEC.values():
            if s.get('ChapterId') == item['id']:
                titles += [txt(SST_SEC_L, s.get('Title', '')), txt(SST_SEC_L, s.get('Desc', ''))]
    elif item['family'] == 'main':
        row = CHAP_T.get(str(item['id'])) or {}
        names += [txt(CHAP_L, row.get('Name', '')), txt(CHAP_L, row.get('Desc', ''))]
        for s in STORY_T.values():
            if s.get('Chapter') == item['id']:
                titles += [txt(L_STORY, s.get('Title', ''))]
    else:
        for s in ACT_STORY_T.values():
            if s.get('ChapterId') == item['id']:
                titles += [txt(ACT_STORY_L, s.get('Title', '')),
                           txt(ACT_STORY_L, s.get('Desc', ''))]
    return [s for s in names if s], [s for s in titles if s]


def read_site():
    """Every text file under site/ (assets images are not searched for strings)."""
    out = {}
    for dp, _d, fs in os.walk(SITE):
        for f in fs:
            if not f.endswith(('.html', '.js', '.json', '.css', '.txt', '.md')):
                continue
            rel = os.path.relpath(os.path.join(dp, f), SITE).replace(os.sep, '/')
            try:
                out[rel] = open(os.path.join(dp, f), encoding='utf-8', errors='replace').read()
            except OSError:
                out[rel] = ''
    return out


def audit_locked(site_text=None):
    site_text = read_site() if site_text is None else site_text
    errs = []
    for family, items in GATE.groups.items():
        for gid, item in items.items():
            names, titles = forbidden_strings(item)
            urls = set(item['pages'])
            folder = (item['pages'][0].rsplit('/', 1)[0] + '/') if item['pages'] else ''
            # 1) the group's own name/desc must not appear anywhere on the site
            for s in names:
                hits = [p for p, t in site_text.items() if s in t]
                if hits:
                    errs.append(('组名泄露', family, gid, s, hits[:2]))
            # 2) its URL space holds nothing but the locked-notice pages
            got = {p for p in site_text if p.startswith(folder)}
            if got != urls:
                errs.append(('未开放目录文件不符', family, gid,
                             sorted(got - urls)[:3], sorted(urls - got)[:3]))
            # 3) no other page may link into a locked group
            for u in urls:
                hits = [p for p, t in site_text.items() if u in t and p != u]
                if hits:
                    errs.append(('未开放 URL 被引用', u, hits[:2]))
            # 4) notice pages carry no transcript and none of the group's titles
            for u in sorted(urls):
                t = site_text.get(u, '')
                if '<p class="line' in t or 'class="say"' in t:
                    errs.append(('提示页夹带台词', u))
                for s in names + titles:
                    if s in t:
                        errs.append(('提示页夹带组名/标题', u, s))
    return errs


n_errs = audit_locked()
locked_n = sum(len(v) for v in GATE.groups.values())
print('被门控的组 %d   未渲染的页面记录 %d   违例 %d'
      % (locked_n, len(locked_pages), len(n_errs)))
for x in n_errs[:8]:
    print('   ~', x)
hard(not n_errs, 'N 门控泄露违例：%d 处' % len(n_errs))
# 5) the family index shows the placeholder instead of the group
idx_errs = []
SLUG = {'storysets': 'storysets', 'events': 'events', 'main': 'main'}
for family, items in GATE.groups.items():
    if not items:
        continue
    idx = os.path.join(SITE, SLUG[family], 'index.html')
    if not os.path.exists(idx):
        idx_errs.append(('族索引缺失', family))
        continue
    t = open(idx, encoding='utf-8').read()
    marks = t.count('class="grp locked"') + t.count('class="chapcard locked"')
    if marks < len(items):
        idx_errs.append(('未开放占位数量不足', family, len(items), marks))
    if release_gate.MASK not in t:
        idx_errs.append(('占位缺少？？？遮罩', family))
    for gid, item in items.items():
        if item.get('open_text') and item['open_text'] not in t:
            idx_errs.append(('占位缺少开放时间', family, gid))
        # the placeholder must not link anywhere inside the locked group
        if '/%s/%d/' % (SLUG[family], gid) in t or '/%d/' % gid in t:
            idx_errs.append(('索引里仍有未开放组的链接', family, gid))
print('占位渲染违例：%d' % len(idx_errs))
for x in idx_errs[:5]:
    print('   ~', x)
hard(not idx_errs, 'N 占位渲染违例：%d 处' % len(idx_errs))

# N2 门控泄露植入变异已拆到 mutation_site.py。

# ---- 汇总与退出码 -------------------------------------------------------------
# 本文件只做数据对账（含各 audit 的正对照），CI 直接跑它。植入变异自检拆在
# mutation_site.py，改校验器/生成器代码时手动跑。作为模块被 import 时不退出，
# 以便 mutation_site.py 复用这里的 audit 函数与已加载数据。
if __name__ == '__main__':
    print()
    print('=' * 66)
    if HARD:
        print('RESULT: FAIL —— %d 处契约违例：' % len(HARD))
        for x in HARD:
            print('   ✗', x)
        sys.exit(1)
    print('RESULT: PASS —— 数据对账契约（G/G2/G3/H/H3/I/J/J2/J3/J4/L/M/M3/N）绿')
    sys.exit(0)
