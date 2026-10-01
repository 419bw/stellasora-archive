# -*- coding: utf-8 -*-
"""Build the static story site from story_docs/ (Markdown) + story_docs/_data (JSON).

    python scripts/build_site.py        # -> site/

Content comes from the reviewed Markdown; structure (navigation, counts, the chapter
graph) comes from the sidecars. Nothing here re-parses Lua.
"""
import sys, os, re, json, collections, shutil

import md2html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'story_docs')
DATA = os.path.join(SRC, '_data')
SITE = os.path.join(ROOT, 'site')

FAMILIES = [
    ('main', '主线剧情', '第十章尚未上线的线路在包内没有剧本，已在对账里列出。'),
    ('events', '活动剧情', '11 个活动的剧情关卡全文。'),
    ('characters', '角色个人剧情', '40 位旅人 × 好感 1 / 5 / 10 三篇。'),
    ('npc_bonds', '星塔 NPC 好感', '波西亚、贝缇丽、珀尔娜、维嘉尔各两话。'),
    ('discs', '唱片剧情', '带剧本的 24 张唱片，附官方散文。'),
    ('storysets', '故事集支线', '4 个栏目 17 个故事集 56 小节。'),
    ('prologue', '序章', '注册流程里播的《最初的起点》。'),
    ('battles_unmounted', '存目战斗气泡', '没有任何关卡表引用的 BBm 剧本。'),
]
FAMILY_NAME = {k: n for k, n, _ in FAMILIES}
BASELINE = '数据基准：官方公测客户端解包（zh_CN）。'


def load(name):
    return json.load(open(os.path.join(DATA, name), encoding='utf-8'))


CH = load('chapters.json')
SEC = load('sections.json')
PERS = load('personality.json')
PAGES = SEC['pages']
BY_FAMILY = collections.defaultdict(list)
for p in PAGES:
    BY_FAMILY[p['family']].append(p)


def rel(root, target):
    """Relative href from a page living at `root` depth to `target`."""
    return ('../' * root) + target if target else '#'


def layout(title, body, depth, crumb, note=''):
    root = '../' * depth
    nav = ' '.join('<a href="%s%s/index.html">%s</a>' % (root, slug_of(f), n)
                   for f, n, _ in FAMILIES)
    return """<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s · 星塔旅人 剧情档案</title>
<link rel="stylesheet" href="%sassets/tokens.css">
</head><body>
<header class="top"><a class="brand" href="%sindex.html">星塔旅人 剧情档案</a>
<nav class="nav">%s</nav></header>
<main class="wrap">
%s%s
</main>
<footer class="foot">%s %s</footer>
<script src="%sdata/search.js"></script>
<script src="%sassets/site.js"></script>
</body></html>
""" % (esc(title), root, root, nav,
       '<nav class="crumb">%s</nav>\n' % crumb if crumb else '', body,
       esc(note), BASELINE, root, root)


def slug_of(family):
    return {'main': 'main', 'events': 'events', 'characters': 'characters',
            'npc_bonds': 'npc', 'discs': 'discs', 'storysets': 'storysets',
            'prologue': 'prologue', 'battles_unmounted': 'battles'}[family]


def esc(s):
    from html import escape
    return escape(str(s if s is not None else ''))


def depth_of(page):
    return page.count('/')


def script_page(rec):
    md = open(os.path.join(SRC, rec['page_md']), encoding='utf-8').read()
    body, stats = md2html.convert(md)
    g = rec['group']
    up = g.get('label') or ''
    page = rec['page']
    d = depth_of(page)
    root = '../' * d
    crumb = '<a href="%sindex.html">首页</a> › <a href="%s%s/index.html">%s</a> › %s' % (
        root, root, slug_of(rec['family']), esc(FAMILY_NAME[rec['family']]),
        esc(('%s ' % rec['code']) + rec['title'] if rec['code'] else rec['title']))
    facets = ' '.join('<a class="facet" href="%s%s/index.html?q=%s">%s</a>'
                      % (root, slug_of(rec['family']), esc(s), esc(s))
                      for s in rec['speakers'][:14])
    extra = []
    if rec['family'] == 'characters':
        extra.append('好感等级 %s 解锁' % rec.get('affinity'))
    if rec.get('twins'):
        extra.append('同剧本档案：' + '、'.join(t for t in rec['twins'] if t))
    if rec.get('prose_lines'):
        extra.append('附官方散文 %d 行' % rec['prose_lines'])
    if rec.get('mount_note'):
        extra.append(rec['mount_note'])
    aside = ('<p class="aside">%s</p>' % esc('　·　'.join(x for x in extra if x))
             if extra else '')
    head = ('<h1>%s</h1>' % esc(rec['title']) if not body.startswith('<h1>') else '')
    return layout(rec['title'] or page, """
%s
<div class="page" data-family="%s" data-counts='%s'>
%s
</div>
<details class="cast"><summary>出场说话人（%d）</summary><div class="facets">%s</div></details>
""" % (aside, esc(rec['family']),
       json.dumps(rec['counts'], ensure_ascii=False), body,
       len(rec['speakers']), facets), d, crumb)


def index_table(recs, columns):
    rows = []
    for r in recs:
        cells = ''.join('<td>%s</td>' % c for c in columns(r))
        rows.append('<tr>%s</tr>' % cells)
    return rows


def family_index(family, intro):
    recs = sorted(BY_FAMILY[family], key=lambda r: (str(r['group'].get('id', '')), r['id']))
    page = '%s/index.html' % slug_of(family)
    d = depth_of(page)
    groups = collections.OrderedDict()
    for r in recs:
        key = (r['group'].get('label') or '未分组', r['group'].get('id'))
        groups.setdefault(key, []).append(r)
    blocks = []
    for (label, gid), items in groups.items():
        links = ''.join('<li><a href="%s">%s</a><span class="sub">%s</span></li>'
                        % (rel(d, it['page']),
                           esc(('%s ' % it['code'] if it['code'] else '') + it['title']),
                           esc('%d 句' % it['counts'].get('talk', 0)
                               + (' / %d 气泡' % it['counts']['bubble']
                                  if it['counts'].get('bubble') else '')))
               for it in items)
        blocks.append('<section class="grp"><h3>%s</h3><ul class="plain">%s</ul></section>'
                      % (esc(label), links))
    crumb = '<a href="%sindex.html">首页</a> › %s' % ('../' * d, FAMILY_NAME[family])
    return layout(FAMILY_NAME[family], """
<h1>%s</h1>
<p class="lede">%s</p>
<div class="searchbox"><input type="search" placeholder="在本类中检索标题、概要、说话人…"
     data-scope="%s" data-root="%s"><div class="results" hidden></div></div>
%s
""" % (esc(FAMILY_NAME[family]), esc(intro), slug_of(family), '../' * d, ''.join(blocks)),
        d, crumb)


def main_index():
    page = 'main/index.html'
    d = depth_of(page)
    cards = []
    for c in sorted(CH['chapters'], key=lambda x: x['id']):
        nodes = [n for n in c['nodes']]
        rel_pages = '%s/index.html' % slug_of('main')
        cards.append("""<li><a class="chapcard" href="%s">
<span class="chapno">%s</span><span class="chaptitle">%s</span>
<span class="chapmeta">%s　节点 %d　已开放 %d　战斗 %d</span>
<span class="chapline">%s</span></a></li>""" % (
            rel(d, 'main/ch%s/index.html' % (c['no'] or 'sp')),
            esc(c['name'] or '特别篇'), esc(c['title']), esc(c['year']),
            len(nodes), sum(1 for n in nodes if n['state'] == 'released'),
            sum(1 for n in nodes if n['kind'] == 'battle'),
            esc('' if c['edge_source'] != 'none' else '官方表未记录此篇连线，按关卡顺序列出')))
    crumb = '<a href="%sindex.html">首页</a> › 主线剧情' % ('../' * d)
    return layout('主线剧情', """
<h1>主线剧情</h1>
<p class="lede">按官方关卡表画出节点图：编号与标题取自表内文案，分叉与汇合取自
<code>ParentStoryId</code>。表 Id 与游戏内章号相差一章（表 Id 8 是游戏内第七章），页面按游戏内章号显示。</p>
<ul class="chaplist">%s</ul>
""" % ''.join(cards), d, crumb)


def home():
    counts = collections.Counter(p['family'] for p in PAGES)
    lines = sum(p['counts'].get('talk', 0) + p['counts'].get('bubble', 0) for p in PAGES)
    tiles = ''.join('<li><a href="%s/index.html">%s<span>%d 篇</span></a></li>'
                    % (slug_of(f), esc(n), counts.get(f, 0)) for f, n, _ in FAMILIES)
    axes = ''.join('<li><span class="dot" style="background:%s"></span>%s</li>'
                   % (esc(a['color']), esc(a['name'])) for a in PERS['axes'])
    return layout('首页', """
<h1>星塔旅人 剧情档案</h1>
<p class="lede">官方剧本的逐句全文、分支抉择与关卡拓扑。共 %d 篇、%s 句台词与气泡。</p>
<div class="searchbox"><input type="search" placeholder="检索标题、概要、说话人…"
 data-scope="_all" data-root=""><div class="results" hidden></div></div>
<ul class="tiles">%s</ul>
<section class="card"><h3>魔王倾向三轴（术语）</h3>
<p class="aside">表内只有三轴定义；游戏里那个百分比来自玩家存档，解包数据中没有，本站不显示数值。</p>
<ul class="axes">%s</ul></section>
<section class="card"><h3>数据基准与已知边界</h3>
<p class="aside">%s 第十章（游戏内第九章）有 11 个关卡行在包内还没有剧本；
心链聊天（<code>PM_*</code> 63 篇）与委托结算演出（<code>DP_*</code> 17 篇）未收录。</p></section>
""" % (len(PAGES), format(lines, ','), tiles, axes, BASELINE), 0, '')


STATE_LABEL = {'battle': '战斗', 'story': '剧情'}


def node_state_label(n):
    if n['state'] == 'unreleased':
        return '未开放'
    if n['memory'] == 1:
        return '追忆'
    if n['memory'] == 2:
        return '真·终局'
    if n['is_last']:
        return '本章终幕'
    if n['is_branch']:
        return '终局'
    if n['code'].startswith('幕间'):
        return '幕间'
    if n['code'].startswith('尾声'):
        return '尾声'
    return STATE_LABEL[n['kind']]


def node_state_class(n):
    if n['state'] == 'unreleased':
        return 'locked'
    if n['memory'] in (1, 2):
        return 'memory'
    if n['is_branch'] or n['is_last']:
        return 'final'
    if n['code'].startswith(('幕间', '尾声')):
        return 'between'
    return 'battle' if n['kind'] == 'battle' else 'story'


def chapter_graph_page(c):
    """The in-game style node map: positioned cards over one flat SVG connector layer."""
    page = 'main/ch%s/index.html' % (c['no'] or 'sp')
    d = depth_of(page)
    root = '../' * d
    g = c['geometry']
    crumb = '<a href="%sindex.html">首页</a> › <a href="%smain/index.html">主线剧情</a> › %s' % (
        root, root, esc(c['name'] or '特别篇'))
    by_sid = {n['story_id']: n for n in c['nodes']}
    pad = 24
    if g is None:                       # 特别篇: the official table records no links at all
        items = ''.join(
            '<li><a href="%s"><span class="code">%s</span><span class="t">%s</span>'
            '<span class="s">%s</span></a></li>'
            % (rel(d, n['page']) if n['page'] else '#', esc(n['code']), esc(n['title']),
               esc(node_state_label(n)))
            for n in sorted(c['nodes'], key=lambda x: x['sid']))
        body = ('<h1>%s《%s》</h1><p class="lede">%s</p>'
                '<p class="aside">官方表未记录此篇的关卡连线，因此这里按关卡编号顺序列出，'
                '不画虚构的分支。</p><ul class="plain linelist">%s</ul>'
                % (esc(c['name'] or '特别篇'), esc(c['title']), esc(c['year']), items))
        return layout(c['name'] or '特别篇', body, d, crumb)

    paths = []
    for u, v in g['edges']:
        a, b = by_sid[u], by_sid[v]
        x1, y1 = a['x'] + g['card'][0], a['y'] + g['card'][1] / 2.0
        x2, y2 = b['x'], b['y'] + g['card'][1] / 2.0
        mx = x1 + (x2 - x1) / 2.0
        cls = node_state_class(b)
        dash = ' dash' if b['state'] == 'unreleased' else ''
        paths.append('<path class="edge %s%s" d="M%d %d C%d %d,%d %d,%d %d"/>'
                     % (cls, dash, x1, y1, mx, y1, mx, y2, x2, y2))
    cards = []
    seen_col = set()
    for n in sorted(c['nodes'], key=lambda x: (x['col'], x['lane'])):
        style = 'left:%dpx;top:%dpx;width:%dpx;height:%dpx' % (
            n['x'] + pad, n['y'] + pad, g['card'][0], g['card'][1])
        t = n['time']
        chip = '<span class="chip">%s</span>' % esc('%s %s' % (t['date'], t['clock'])) if t else ''
        inner = ('<span class="code">%s</span><span class="t">%s</span>%s'
                 % (esc(n['code'] or '·'), esc(n['title']), chip))
        # the first card of each column is the anchor the jump bar points at
        cid = '' if n['col'] in seen_col else ' id="col%d"' % n['col']
        seen_col.add(n['col'])
        if n['page']:
            cards.append('<a%s class="node %s" style="%s" data-col="%d" href="%s">%s'
                         '<span class="state">%s ›</span></a>'
                         % (cid, node_state_class(n), style, n['col'], rel(d, n['page']), inner,
                            esc(node_state_label(n))))
        else:
            cards.append('<div%s class="node %s" style="%s" data-col="%d">%s'
                         '<span class="state">%s</span></div>'
                         % (cid, node_state_class(n), style, n['col'], inner,
                            esc(node_state_label(n))))
    anchors = ''.join('<a href="#col%d" data-scroll-to="%d">%s</a>'
                      % (col, col * g['step_x'] + pad,
                         esc(min((n['code'] or '·') for n in c['nodes'] if n['col'] == col)))
                      for col in range(g['columns']))
    switch = ' '.join('<a href="%sch%s/index.html"%s>%s</a>' % (
        root, x['no'] or 'sp', ' class="on"' if x['id'] == c['id'] else '',
        esc(x['name'] or '特别篇')) for x in sorted(CH['chapters'], key=lambda y: y['id']))
    unreleased = sum(1 for n in c['nodes'] if n['state'] == 'unreleased')
    return layout('%s《%s》' % (c['name'], c['title']), """
<h1>%s《%s》</h1>
<p class="lede">%s　节点 %d　已开放 %d　战斗 %d%s</p>
<nav class="chapsel">%s</nav>
<nav class="anchors">%s</nav>
<div class="map">
<div class="canvas" style="width:%dpx;height:%dpx">
<svg class="wires" width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>
%s
</div>
</div>
<p class="aside">连线取自官方 <code>Story.ParentStoryId</code>（该关卡的前置关卡），列序与轨道
由本库按最长路径确定性算出并逐页校验；游戏里每条时间槽属于哪一列写在 UI 预制体里，解包表内没有，
所以时间条按关卡自身剧本的场景头显示，不冒充官方的按列分组。</p>
""" % (esc(c['name']), esc(c['title']), esc(c['year']), len(c['nodes']),
       sum(1 for n in c['nodes'] if n['state'] == 'released'),
       sum(1 for n in c['nodes'] if n['kind'] == 'battle'),
       '　未开放 %d' % unreleased if unreleased else '',
       switch, anchors,
       g['width'] + pad * 2, g['height'] + pad * 2,
       g['width'] + pad * 2, g['height'] + pad * 2,
       g['width'] + pad * 2, g['height'] + pad * 2, ''.join(paths), ''.join(cards)),
        d, crumb)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text if text.endswith('\n') else text + '\n')


def main():
    if os.path.isdir(SITE):
        shutil.rmtree(SITE)
    os.makedirs(SITE)
    shutil.copytree(DATA, os.path.join(SITE, 'data'))
    # file:// cannot fetch() a JSON sibling, so the index ships as a script assignment
    index = load('search.json')
    write(os.path.join(SITE, 'data', 'search.js'),
          'window.STORY_INDEX = %s;\n' % json.dumps(index, ensure_ascii=False,
                                                    separators=(',', ':')))
    write(os.path.join(SITE, 'assets', 'tokens.css'), CSS)
    write(os.path.join(SITE, 'assets', 'site.js'), JS)
    write(os.path.join(SITE, 'index.html'), home())
    n = 0
    for rec in PAGES:
        write(os.path.join(SITE, rec['page'].replace('/', os.sep)), script_page(rec))
        n += 1
    for family, name, intro in FAMILIES:
        if family == 'main':
            write(os.path.join(SITE, 'main', 'index.html'), main_index())
            for c in CH['chapters']:
                write(os.path.join(SITE, 'main', 'ch%s' % (c['no'] or 'sp'), 'index.html'),
                      chapter_graph_page(c))
        else:
            write(os.path.join(SITE, slug_of(family), 'index.html'),
                  family_index(family, intro))
    graphs = sum(1 for c in CH['chapters'])
    print("站点已生成：site/  剧本页 %d 篇 + 索引 %d 页 + 章节点图 %d 页"
          % (n, 1 + len(FAMILIES), graphs))


CSS = """
:root{
  --paper:#FBF9F5; --card:#FFFFFF; --ink:#2A2622; --ink2:#6E6862;
  --rule:#E3DCD2; --grid:#F0EBE3;
  --story:#3E6B5A; --battle:#B4553B; --between:#8A7A55; --final:#5A4A7A; --locked:#A9A29A;
  --serif:"Source Han Serif SC","Noto Serif CJK SC","Songti SC",STSong,serif;
  --sans:-apple-system,"Segoe UI","Microsoft YaHei","PingFang SC","Noto Sans CJK SC",sans-serif;
}
*{box-sizing:border-box}
html{background:var(--paper)}
body{margin:0;color:var(--ink);font-family:var(--sans);font-size:16px;line-height:1.75;
  background-image:linear-gradient(var(--grid) 1px,transparent 1px);background-size:100% 32px}
a{color:inherit;text-decoration:none;border-bottom:1px solid var(--rule)}
a:hover{border-bottom-color:var(--ink)}
code{font-family:ui-monospace,Consolas,monospace;font-size:.86em;background:var(--grid);
  padding:1px 4px;border-radius:3px}
.top{display:flex;align-items:baseline;gap:20px;padding:14px 24px;border-bottom:1px solid var(--rule);
  background:var(--paper);position:sticky;top:0;z-index:5}
.brand{font-family:var(--serif);font-size:19px;border:0;font-weight:600}
.nav{display:flex;flex-wrap:wrap;gap:14px;font-size:14px;color:var(--ink2)}
.nav a{border:0}
.wrap{max-width:960px;margin:0 auto;padding:20px 24px 64px}
.crumb{font-size:13px;color:var(--ink2);margin-bottom:18px}
h1{font-family:var(--serif);font-size:30px;line-height:1.3;margin:0 0 6px;font-weight:600}
h2{font-family:var(--serif);font-size:19px;margin:34px 0 10px;padding-bottom:6px;
  border-bottom:1px solid var(--rule);font-weight:600}
h3{font-family:var(--serif);font-size:17px;margin:26px 0 8px;font-weight:600}
.lede{color:var(--ink2);max-width:70ch}
.aside{font-size:13px;color:var(--ink2)}
.meta{margin:2px 0;font-size:14px;color:var(--ink2)}
.meta b:first-child{display:inline-block;min-width:6.5em;color:var(--ink);font-weight:600}
.meta b:first-child::after{content:"："}
blockquote{margin:14px 0;padding:10px 16px;background:var(--card);
  border-left:3px solid var(--rule);border-radius:0 4px 4px 0}
blockquote p{margin:2px 0}
.line{margin:6px 0;line-height:2.1;max-width:68ch;display:grid;
  grid-template-columns:max-content 1fr;column-gap:6px}
.who{font-family:var(--serif);font-weight:600}
.who::after{content:"："}
.tag{font-style:normal;font-size:12px;color:var(--ink2);border:1px solid var(--rule);
  border-radius:3px;padding:0 4px;margin-left:6px;vertical-align:2px}
.thought .say,.thought .who{color:var(--ink2)}
.thought .say{font-style:normal}
.bubble .who,.chat .who{color:var(--story)}
.sticker .say{color:var(--ink2)}
.scene{margin:22px 0 10px;padding:6px 12px;font-size:13px;letter-spacing:.04em;color:var(--ink2);
  background:var(--card);border:1px solid var(--rule);border-radius:4px}
.wave{margin:22px 0 6px;font-size:13px;color:var(--battle);border-left:3px solid var(--battle);
  padding-left:10px;font-weight:600}
.choice{margin:22px 0 4px;font-size:14px;font-weight:600;border-left:3px solid var(--between);
  padding-left:10px}
.options{margin:0 0 14px;padding-left:26px}
.options li{margin:3px 0}
.options b{font-weight:600}
.branch-open{margin:20px 0 4px;font-size:13px;color:var(--story);border-left:3px solid var(--story);
  padding-left:10px}
.merge{margin:18px 0 4px;font-size:13px;color:var(--final);border-left:3px solid var(--final);
  padding-left:10px}
.note{font-size:12px;color:var(--ink2);margin:2px 0 14px 14px}
.marker{font-size:13px;color:var(--ink2)}
.tiles{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));
  gap:12px}
.tiles a{display:block;padding:14px 16px;background:var(--card);border:1px solid var(--rule);
  border-radius:4px}
.tiles span{display:block;font-size:13px;color:var(--ink2)}
.card,.grp{background:var(--card);border:1px solid var(--rule);border-radius:4px;padding:14px 18px;
  margin:14px 0}
.chaplist{list-style:none;padding:0}
.chaplist li{margin:0 0 10px}
.chapcard{display:block;padding:14px 16px;background:var(--card);border:1px solid var(--rule);
  border-left-width:3px;border-left-color:var(--story);border-radius:4px}
.chapno{font-family:var(--serif);font-size:18px;font-weight:600;margin-right:10px}
.chaptitle{font-family:var(--serif)}
.chapmeta{display:block;font-size:13px;color:var(--ink2)}
.chapline{display:block;font-size:12px;color:var(--battle)}
.plain{list-style:none;padding:0;margin:0}
.plain li{padding:5px 0;border-bottom:1px dotted var(--rule)}
.plain .sub{float:right;font-size:12px;color:var(--ink2)}
.facets{display:flex;flex-wrap:wrap;gap:8px;font-size:13px}
.facet{border:1px solid var(--rule);border-radius:3px;padding:1px 7px}
.cast{margin:28px 0 0;font-size:14px;color:var(--ink2)}
.axes{list-style:none;padding:0;font-size:14px}
.dot{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:8px}
.searchbox{margin:18px 0}
.searchbox input{width:100%;max-width:420px;padding:9px 12px;font:inherit;background:var(--card);
  border:1px solid var(--rule);border-radius:4px}
.foot{max-width:960px;margin:0 auto;padding:18px 24px 40px;font-size:12px;color:var(--ink2);
  border-top:1px solid var(--rule)}
mark{background:#FFF1C9;color:inherit}
.chapsel{display:flex;flex-wrap:wrap;gap:8px;font-size:13px;margin:14px 0 6px}
.chapsel a{padding:2px 8px;border:1px solid var(--rule);border-radius:3px}
.chapsel a.on{border-color:var(--ink);font-weight:600}
.anchors{display:flex;flex-wrap:wrap;gap:6px;font-size:12px;color:var(--ink2);margin:0 0 10px}
.anchors a{border:0;padding:1px 6px;background:var(--grid);border-radius:3px}
.map{overflow-x:auto;overflow-y:hidden;border:1px solid var(--rule);background:var(--card);
  border-radius:4px;scrollbar-color:var(--rule) transparent}
.canvas{position:relative}
.wires{position:absolute;left:0;top:0;pointer-events:none}
.edge{fill:none;stroke:var(--rule);stroke-width:1.5}
.edge.battle{stroke:var(--battle)}
.edge.final,.edge.memory{stroke:var(--final)}
.edge.between{stroke:var(--between)}
.edge.locked{stroke:var(--locked)}
.edge.dash{stroke-dasharray:5 4}
.node{position:absolute;display:block;padding:8px 10px;background:var(--card);
  border:1px solid var(--rule);border-left-width:3px;border-radius:4px;overflow:hidden}
.node:hover{border-color:var(--ink)}
.node.story{border-left-color:var(--story)}
.node.battle{border-left-color:var(--battle)}
.node.between{border-left-color:var(--between)}
.node.final,.node.memory{border-left-color:var(--final)}
.node.locked{border-left-color:var(--locked);border-style:dashed;color:var(--ink2)}
.node .code{display:block;font-family:var(--serif);font-size:17px;font-weight:600;line-height:1.25}
.node .t{display:block;font-size:13px;line-height:1.4;white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis}
.node .chip{display:block;font-size:11px;color:var(--ink2);letter-spacing:.02em}
.node .state{position:absolute;right:8px;bottom:6px;font-size:10px;color:var(--ink2)}
.linelist .code{display:inline-block;min-width:3.5em;font-family:var(--serif);font-weight:600}
.linelist .t{margin-right:10px}
.linelist .s{font-size:12px;color:var(--ink2)}
.results{margin-top:10px;background:var(--card);border:1px solid var(--rule);border-radius:4px;
  padding:8px 14px}
.results[hidden]{display:none}
.hits{list-style:none;padding:0;margin:0}
.hits li{padding:4px 0;border-bottom:1px dotted var(--rule)}
.hits a{border:0;display:block}
.hits b{font-family:var(--serif);font-weight:600;margin-right:8px}
.hits span{font-size:12px;color:var(--ink2)}
@media (max-width:900px){
  .map{overflow:visible;border:0}
  .canvas{width:auto!important;height:auto!important}
  .wires{display:none}
  .node{position:static;width:auto!important;height:auto!important;margin:0 0 8px}
  .node .state{position:static;display:block}
}
@media (prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
@media (max-width:760px){.wrap{padding:16px 14px 48px}.top{padding:12px 14px}.line{line-height:1.95}}
"""

JS = """
(function(){
  var IDX=(window.STORY_INDEX||{entries:[]}).entries;
  var FAM={npc:'npc_bonds',battles:'battles_unmounted'};
  function norm(s){return (s||'').toLowerCase();}
  function score(e,q){
    var s=0,t=norm(e.title+' '+e.code+' '+e.group),h=norm(e.hay),sp=norm(e.speakers.join(' '));
    if(t.indexOf(q)>=0)s+=6;
    if(sp.indexOf(q)>=0)s+=4;
    if(h.indexOf(q)>=0)s+=2;
    // Chinese has no word boundaries: a two-character sliding window catches partial names
    for(var i=0;i+2<=q.length;i++){var g=q.substr(i,2);
      if(h.indexOf(g)>=0)s+=1; if(sp.indexOf(g)>=0)s+=1;}
    return s;
  }
  function run(box,pane,scope,root,q){
    var hits=[];
    for(var i=0;i<IDX.length;i++){
      var e=IDX[i];
      if(scope!=='_all'&&(e.family!==(FAM[scope]||scope)))continue;
      var s=score(e,q);
      if(s>0)hits.push([s,e]);
    }
    hits.sort(function(a,b){return b[0]-a[0]||String(a[1].title).localeCompare(b[1].title);});
    pane.hidden=false;
    if(!hits.length){pane.innerHTML='<p class="aside">没有匹配的剧情页。</p>';return;}
    var out=['<p class="aside">命中 '+hits.length+' 篇（最多列 40）</p><ul class="hits">'];
    hits.slice(0,40).forEach(function(h){
      var e=h[1];
      out.push('<li><a href="'+root+e.page+'"><b>'+[e.code,e.title].filter(Boolean).join(' ')+'</b>'
        +'<span>'+e.group+'　'+e.speakers.slice(0,4).join('、')+'</span></a></li>');
    });
    pane.innerHTML=out.join('')+'</ul>';
  }
  [].slice.call(document.querySelectorAll('.searchbox input')).forEach(function(box){
    var pane=box.parentNode.querySelector('.results');
    var scope=box.getAttribute('data-scope'),root=box.getAttribute('data-root')||'';
    var groups=[].slice.call(document.querySelectorAll('.grp, .chaplist li, .tiles li'));
    box.addEventListener('input',function(){
      var q=box.value.trim().toLowerCase();
      groups.forEach(function(g){
        g.style.display=(!q||g.textContent.toLowerCase().indexOf(q)>=0)?'':'none';
      });
      if(q.length>=1&&IDX.length)run(box,pane,scope,root,q);
      else pane.hidden=true;
    });
  });
  var map=document.querySelector('.map');
  [].slice.call(document.querySelectorAll('[data-scroll-to]')).forEach(function(a){
    a.addEventListener('click',function(e){
      if(!map||window.innerWidth<=900)return;
      e.preventDefault();
      map.scrollTo({left:parseInt(a.getAttribute('data-scroll-to'),10)-40,behavior:'smooth'});
    });
  });
})();
"""

if __name__ == '__main__':
    main()
