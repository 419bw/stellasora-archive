# -*- coding: utf-8 -*-
"""Build the static story site from story_docs/ (Markdown) + story_docs/_data (JSON).

    python scripts/build_site.py        # -> site/

Refactored modular structure:
  - scripts/site_css.py: Design tokens and full layout CSS.
  - scripts/site_js.py: Client-side search, theme toggle, and map interactions.
  - scripts/site_templates.py: HTML layout, bento cards, chapter graphs, and reading views.
  - scripts/md2html.py: Markdown parser with major choices & player replies.
"""
import sys
import os
import json
import collections
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(SCRIPT_DIR)
ROOT = os.path.dirname(SCRIPTS_DIR)
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.join(SCRIPTS_DIR, 'story'))

from site_css import CSS
from site_js import JS
import site_templates as T
import graph_layout
import release_gate

SRC = os.path.join(ROOT, 'story_docs')
DATA = os.path.join(SRC, '_data')
SITE = os.path.join(ROOT, 'site')


def load(name):
    return json.load(open(os.path.join(DATA, name), encoding='utf-8'))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text if text.endswith('\n') else text + '\n')


def strip_locked_from_data(gate):
    """Drop locked groups from the sidecars copied into site/data/.

    ``shutil.copytree`` copies story_docs/_data verbatim, so a locked group's
    records (recap / preview / speakers / search text) would otherwise stay
    readable under site/data/*.json and in search.js. Only ids and open times
    survive -- the gate descriptor carries nothing that could spoil content.
    """
    for name, key in (('sections.json', 'pages'), ('search.json', 'entries')):
        path = os.path.join(SITE, 'data', name)
        if not os.path.exists(path):
            continue
        obj = json.load(open(path, encoding='utf-8'))
        kept = [r for r in (obj.get(key) or [])
                if not gate.is_page(r.get('family'), r.get('id'))]
        obj[key] = kept
        if isinstance(obj.get('meta'), dict) and 'pages' in obj['meta']:
            obj['meta']['pages'] = len(kept)
        write(path, json.dumps(obj, ensure_ascii=False, indent=1) + '\n')
    path = os.path.join(SITE, 'data', 'chapters.json')
    if os.path.exists(path):
        obj = json.load(open(path, encoding='utf-8'))
        obj['chapters'] = [c for c in (obj.get('chapters') or [])
                           if not gate.is_group('main', c.get('id'))]
        meta = obj.setdefault('meta', {})
        meta['chapters'] = len(obj['chapters'])
        meta['nodes'] = sum(len(c.get('nodes') or []) for c in obj['chapters'])
        write(path, json.dumps(obj, ensure_ascii=False, indent=1) + '\n')


def load_activity_battle_pages(sec_pages):
    """Load the 19 official battle stages from ActivityStory.json that have no dialogue script."""
    act_groups = {}
    for p in sec_pages:
        if p['family'] == 'events':
            act_groups[p['group']['id']] = p['group']['label']

    bin_act_file = os.path.join(ROOT, 'data', 'StellaSoraData', 'CN', 'bin', 'ActivityStory.json')
    lang_act_file = os.path.join(ROOT, 'data', 'StellaSoraData', 'CN', 'language', 'zh_CN', 'ActivityStory.json')
    cond_file = os.path.join(ROOT, 'data', 'StellaSoraData', 'CN', 'bin', 'ActivityStoryCondition.json')

    bin_act = json.load(open(bin_act_file, encoding='utf-8'))
    lang_act = json.load(open(lang_act_file, encoding='utf-8'))
    cond_data = json.load(open(cond_file, encoding='utf-8')) if os.path.exists(cond_file) else {}

    battle_stages = [s for s in bin_act.values() if s.get('AvgLuaName') is None]
    battle_stages.sort(key=lambda x: (x.get('ChapterId', 0), x['Id']))

    res = []
    for b in battle_stages:
        sid = b['Id']
        cid = b.get('ChapterId')
        code = lang_act.get(b.get('Index'), '')
        title = lang_act.get(b.get('Title'), '')
        desc = lang_act.get(b.get('Desc'), '')
        aim = lang_act.get(b.get('Aim'), '')
        grp_label = act_groups.get(cid, '活动剧情')
        c = cond_data.get(str(sid), {})
        pars = (c.get('ActivityStoryId_a') or []) + (c.get('ActivityStoryId_b') or [])

        parent_titles = []
        for pid in pars:
            p_row = bin_act.get(str(pid)) or bin_act.get(pid) or {}
            p_code = lang_act.get(p_row.get('Index'), '')
            p_title = lang_act.get(p_row.get('Title'), '')
            parent_titles.append(('%s %s' % (p_code, p_title)).strip())
        cond_text = ('通关前置关卡 ' + '、'.join(parent_titles)) if parent_titles else '初始开放'

        res.append({
            'id': sid,
            'sid': sid,
            'story_id': str(sid),
            'family': 'events',
            'code': code,
            'title': title,
            'group': {
                'kind': 'activity',
                'id': cid,
                'label': grp_label,
            },
            'chapter_name': grp_label,
            'page': 'events/%d/%d.html' % (cid, sid),
            'desc': desc,
            'aim': aim,
            'condition': str(b.get('ConditionId') or sid),
            'condition_text': cond_text,
            'parents': [str(p) for p in pars],
            'kind': 'battle',
            'state': 'released',
            'counts': {'talk': 0, 'bubble': 0, 'choice': 0, 'sticker': 0},
            'stems': [],
            'speakers': [],
        })
    return res


def build_navigation_index(pages, chapters, act_battle_pages=None):
    """Precompute previous, next, and branching targets for every story page."""
    nav_index = {}
    branch_index = {}
    act_battle_pages = act_battle_pages or []

    # 1. Main story graph navigation
    node_to_chap = {}
    sid_to_node = {}
    for c in chapters:
        for n in c['nodes']:
            sid_to_node[n['story_id']] = n
            node_to_chap[n['sid']] = c

    # Compute children map
    children_map = collections.defaultdict(list)
    for c in chapters:
        for n in c['nodes']:
            for p in n['parents']:
                children_map[p].append(n)

    # option jump EvId -> branch level. StoryCondition ties a child level's
    # ConditionId to the EvId(s) of the choice options that unlock it from a
    # given parent story, so branch badges can follow the option, not its index.
    story_cond_file = os.path.join(ROOT, 'data', 'StellaSoraData', 'CN', 'bin', 'StoryCondition.json')
    story_cond = json.load(open(story_cond_file, encoding='utf-8')) if os.path.exists(story_cond_file) else {}
    story_cond_by_cond = {}
    for row in story_cond.values():
        cid = row.get('ConditionId')
        if cid:
            story_cond_by_cond.setdefault(cid, row)
    unresolved_branches = []

    def target_info(ch, page_url, cur_d):
        return {
            'code': ch.get('code') or '·',
            'title': ch.get('title') or '',
            'url': T.rel(cur_d, ch['page']),
            'cls': T.node_state_class(ch),
            'tag': '终局' if ch.get('is_branch') or ch.get('is_last') else ('战斗' if ch.get('kind') == 'battle' else '剧情'),
        }

    for p in pages:
        if p['family'] == 'main':
            stem = p.get('story_id')
            n = sid_to_node.get(stem)
            cur_d = T.depth_of(p['page'])
            prev_items = []
            next_items = []
            if n:
                for parent_sid in n['parents']:
                    par = sid_to_node.get(parent_sid)
                    if par and par.get('page'):
                        prev_items.append({
                            'code': par.get('code') or '·',
                            'title': par.get('title') or '',
                            'url': T.rel(cur_d, par['page']),
                            'cls': T.node_state_class(par),
                        })
                ch_nodes = children_map.get(n['story_id'], [])
                for ch in ch_nodes:
                    if ch.get('page'):
                        next_items.append(target_info(ch, p['page'], cur_d))
                if len(ch_nodes) > 1:
                    ev_to_child = {}
                    for ch in ch_nodes:
                        if not ch.get('page'):
                            continue
                        entry = story_cond_by_cond.get(ch.get('condition'))
                        if not entry:
                            continue
                        parents = (entry.get('StoryId_a') or []) + (entry.get('StoryId_b') or [])
                        if n['story_id'] not in parents:
                            continue
                        evs = (entry.get('EvIds_a') or []) + (entry.get('EvIds_b') or [])
                        for ev in evs:
                            ev_to_child.setdefault(ev, ch)
                    groups = []
                    for choice in (p.get('major_choices') or []):
                        targets = []
                        for opt in choice:
                            ch = ev_to_child.get(opt.get('ev'))
                            if ch:
                                info = target_info(ch, p['page'], cur_d)
                                info['opt'] = opt.get('title') or ''
                                targets.append(info)
                            elif opt.get('ev'):
                                unresolved_branches.append((p['page'], opt.get('title') or '', opt.get('ev')))
                        if targets:
                            groups.append(targets)
                    if groups:
                        branch_index[p['page']] = groups

            nav_index[p['page']] = {'prev': prev_items, 'next': next_items}

    # Chapter 7 (特别篇) sequential navigation
    sp_nodes = [n for c in chapters if c['id'] == 7 for n in c['nodes']]
    for i, n in enumerate(sp_nodes):
        page_url = n.get('page')
        if not page_url:
            continue
        cur_d = T.depth_of(page_url)
        prev_items = []
        next_items = []
        if i > 0 and sp_nodes[i - 1].get('page'):
            prev_n = sp_nodes[i - 1]
            prev_items.append({
                'code': prev_n.get('code') or '·',
                'title': prev_n.get('title') or '',
                'url': T.rel(cur_d, prev_n['page']),
                'cls': T.node_state_class(prev_n),
            })
        if i < len(sp_nodes) - 1 and sp_nodes[i + 1].get('page'):
            next_n = sp_nodes[i + 1]
            next_items.append({
                'code': next_n.get('code') or '·',
                'title': next_n.get('title') or '',
                'url': T.rel(cur_d, next_n['page']),
                'cls': T.node_state_class(next_n),
                'tag': '战斗' if next_n.get('kind') == 'battle' else '剧情',
            })
        nav_index[page_url] = {'prev': prev_items, 'next': next_items}

    # 2. Activity DAG & linear navigation for all 11 activities via ActivityStoryCondition.json
    cond_file = os.path.join(ROOT, 'data', 'StellaSoraData', 'CN', 'bin', 'ActivityStoryCondition.json')
    cond_data = json.load(open(cond_file, encoding='utf-8')) if os.path.exists(cond_file) else {}
    evid_file = os.path.join(ROOT, 'data', 'StellaSoraData', 'CN', 'bin', 'ActivityStoryEvidence.json')
    evid_data = json.load(open(evid_file, encoding='utf-8')) if os.path.exists(evid_file) else {}
    act_evidence = {str(k): (row.get('EvId') or '') for k, row in evid_data.items()}

    all_event_pages = [p for p in pages if p['family'] == 'events'] + act_battle_pages
    by_act = collections.defaultdict(list)
    for p in all_event_pages:
        by_act[p['group']['id']].append(p)

    for act_id, act_pages in by_act.items():
        act_pages.sort(key=lambda x: x['id'])
        act_page_map = {p['id']: p for p in act_pages}

        act_parents = collections.defaultdict(list)
        act_children = collections.defaultdict(list)
        for p in act_pages:
            c = cond_data.get(str(p['id']), {})
            pars = (c.get('ActivityStoryId_a') or []) + (c.get('ActivityStoryId_b') or [])
            for par_id in pars:
                if par_id in act_page_map:
                    act_parents[p['id']].append(par_id)
                    act_children[par_id].append(p['id'])

        for p in act_pages:
            cur_d = T.depth_of(p['page'])
            prev_items = []
            for par_id in act_parents[p['id']]:
                par_p = act_page_map.get(par_id)
                if par_p:
                    is_b = par_p.get('kind') == 'battle'
                    prev_items.append({
                        'code': par_p.get('code') or '·',
                        'title': par_p.get('title') or '',
                        'url': T.rel(cur_d, par_p['page']),
                        'cls': 'battle' if is_b else 'story',
                    })
            next_items = []
            ch_ids = sorted(act_children.get(p['id'], []))
            for ch_id in ch_ids:
                ch_p = act_page_map.get(ch_id)
                if ch_p:
                    is_b = ch_p.get('kind') == 'battle'
                    tag = '战斗' if is_b else ('分支' if len(ch_ids) > 1 else '剧情')
                    next_items.append({
                        'code': ch_p.get('code') or '·',
                        'title': ch_p.get('title') or '',
                        'url': T.rel(cur_d, ch_p['page']),
                        'cls': 'battle' if is_b else 'story',
                        'tag': tag,
                    })
            nav_index[p['page']] = {'prev': prev_items, 'next': next_items}
            if len(ch_ids) > 1:
                # option jump EvId -> branch activity level (ActivityStoryEvidence)
                ev_to_act = {}
                for ch_id in ch_ids:
                    ev = act_evidence.get(str(ch_id))
                    if ev:
                        ev_to_act.setdefault(ev, ch_id)
                groups = []
                for choice in (p.get('major_choices') or []):
                    targets = []
                    for opt in choice:
                        ch_p = act_page_map.get(ev_to_act.get(opt.get('ev')))
                        if ch_p:
                            is_b = ch_p.get('kind') == 'battle'
                            targets.append({
                                'opt': opt.get('title') or '',
                                'code': ch_p.get('code') or '·',
                                'title': ch_p.get('title') or '',
                                'url': T.rel(cur_d, ch_p['page']),
                                'cls': 'battle' if is_b else 'story',
                                'tag': '战斗' if is_b else '分支',
                            })
                        elif opt.get('ev'):
                            unresolved_branches.append((p['page'], opt.get('title') or '', opt.get('ev')))
                    if targets:
                        groups.append(targets)
                if groups:
                    branch_index[p['page']] = groups

    # 3. Non-main, non-events linear sequence navigation for remaining groups
    by_grp = collections.defaultdict(list)
    for p in pages:
        if p['family'] not in ('main', 'events'):
            grp_key = (p['family'], p['group'].get('id'))
            by_grp[grp_key].append(p)

    for grp_key, grp_pages in by_grp.items():
        sorted_p = sorted(grp_pages, key=lambda x: x['id'])
        for idx, cur_p in enumerate(sorted_p):
            cur_d = T.depth_of(cur_p['page'])
            prev_items = []
            next_items = []
            if idx > 0:
                prev_p = sorted_p[idx - 1]
                prev_items.append({
                    'code': prev_p.get('code') or '',
                    'title': prev_p.get('title') or '',
                    'url': T.rel(cur_d, prev_p['page']),
                })
            if idx < len(sorted_p) - 1:
                next_p = sorted_p[idx + 1]
                next_items.append({
                    'code': next_p.get('code') or '',
                    'title': next_p.get('title') or '',
                    'url': T.rel(cur_d, next_p['page']),
                })
            nav_index[cur_p['page']] = {'prev': prev_items, 'next': next_items}

    if unresolved_branches:
        print("分支走向角标：%d 个选项未解析到目标关卡（对应上方页面将不显示角标）：" % len(unresolved_branches))
        for page, opt, ev in unresolved_branches:
            print("    %s  选项「%s」ev=%s" % (page, opt, ev))

    return nav_index, branch_index


def main():
    if os.path.isdir(SITE):
        shutil.rmtree(SITE)
    os.makedirs(SITE)

    # Assets & Search Data
    # The release gate has to run before anything consumes the sidecars: a group
    # whose official open time is still in the future is published as a locked
    # placeholder, never as a transcript.
    gate = release_gate.load_gate()
    if gate:
        print('开放时间门控：%d 个组尚未开放，只显示未开放占位：%s'
              % (sum(len(v) for v in gate.groups.values()),
                 '，'.join('%s#%s（%s）' % (f, i, it['open_text'] or '时间待定')
                           for f, items in gate.groups.items() for i, it in items.items())))
    shutil.copytree(DATA, os.path.join(SITE, 'data'))
    if gate:
        strip_locked_from_data(gate)
    index = json.load(open(os.path.join(SITE, 'data', 'search.json'), encoding='utf-8'))
    write(os.path.join(SITE, 'data', 'search.js'),
          'window.STORY_INDEX = %s;\n' % json.dumps(index, ensure_ascii=False,
                                                    separators=(',', ':')))
    write(os.path.join(SITE, 'assets', 'tokens.css'), CSS)
    write(os.path.join(SITE, 'assets', 'site.js'), JS)
    src_assets = os.path.join(ROOT, 'assets')
    if os.path.exists(src_assets):
        for f in os.listdir(src_assets):
            sf = os.path.join(src_assets, f)
            if os.path.isfile(sf):
                shutil.copyfile(sf, os.path.join(SITE, 'assets', f))

    # Core Data
    ch_data = load('chapters.json')
    chapters = [c for c in ch_data['chapters'] if not gate.is_group('main', c['id'])]
    sec_data = load('sections.json')
    pages = [p for p in sec_data['pages'] if not gate.is_page(p['family'], p['id'])]
    pers_data = load('personality.json')
    act_battle_pages = [p for p in load_activity_battle_pages(pages)
                        if not gate.is_page('events', p['id'])]

    by_family = collections.defaultdict(list)
    for p in pages:
        by_family[p['family']].append(p)
    # Include activity battle stages in the events family index
    by_family['events'].extend(act_battle_pages)

    # Compute navigation & branch mapping
    nav_index, branch_index = build_navigation_index(pages, chapters, act_battle_pages)

    # 1. Homepage
    write(os.path.join(SITE, 'index.html'), T.home_page(pages, pers_data))

    # 2. Main story index & chapter graph pages
    write(os.path.join(SITE, 'main', 'index.html'),
          T.main_index(chapters, gate.items('main')))
    for c in chapters:
        cno = c['no'] or 'sp'
        write(os.path.join(SITE, 'main', 'ch%s' % cno, 'index.html'),
              T.chapter_graph_page(c, chapters))

    # 2b. Battle archive pages for main story pure battle stages
    rendered_pages = {p['page'] for p in pages}
    main_battle_nodes = [
        n for c in chapters for n in c['nodes']
        if n.get('kind') == 'battle' and n.get('page') and n['page'] not in rendered_pages
    ]
    node_to_chap = {n['sid']: c for c in chapters for n in c['nodes']}
    for n in main_battle_nodes:
        chap = node_to_chap.get(n['sid'], {})
        stage_info = dict(n, chapter_name=chap.get('name'), chapter_title=chap.get('title'))
        html = T.battle_archive_page(stage_info, nav_info=nav_index.get(n['page']))
        write(os.path.join(SITE, n['page'].replace('/', os.sep)), html)

    # 2c. Activity DAG topology pages for 10106 and 20101 (including battle stages)
    branching_acts = [
        {"id": 10106, "code": "10106", "name": "万送屋", "title": "万送屋的委托"},
        {"id": 20101, "code": "20101", "name": "雪愿节", "title": "雪愿节的使者与圣夜的奇迹"},
    ]
    cond_file = os.path.join(ROOT, "data", "StellaSoraData", "CN", "bin", "ActivityStoryCondition.json")
    cond_data = json.load(open(cond_file, encoding="utf-8")) if os.path.exists(cond_file) else {}
    all_event_pages = [p for p in pages if p['family'] == 'events'] + act_battle_pages

    for b_act in branching_acts:
        act_id = b_act["id"]
        if gate.is_group('events', act_id):
            continue  # still locked: its events/<id>/index.html is a notice page
        act_all = [p for p in all_event_pages if p["group"].get("id") == act_id]
        act_all.sort(key=lambda x: x["id"])

        act_nodes = []
        for p in act_all:
            c = cond_data.get(str(p["id"]), {})
            parents = [str(x) for x in (c.get("ActivityStoryId_a") or []) + (c.get("ActivityStoryId_b") or [])]
            code = p["code"]
            act_nodes.append({
                "sid": p["id"],
                "story_id": str(p["id"]),
                "code": code,
                "title": p["title"],
                "kind": p.get("kind", "story"),
                "state": "released",
                "is_branch": code.endswith(('A', 'B', 'C')),
                "is_last": p["id"] == act_all[-1]["id"],
                "memory": None,
                "condition": p["id"],
                "parents": parents,
                "time": None,
                "page": p["page"]
            })
        geom = graph_layout.layout(act_nodes)
        geom["card"] = [208, 96]
        geom["step_x"] = 264
        geom["step_y"] = 136
        act_info = {
            "id": act_id,
            "name": b_act["name"],
            "title": b_act["title"],
            "nodes": act_nodes,
            "geometry": geom
        }
        html = T.activity_graph_page(act_info, branching_acts)
        write(os.path.join(SITE, "events", str(act_id), "index.html"), html)

    # 2d. Battle archive pages for activity battle stages (19 pages)
    for bp in act_battle_pages:
        html = T.battle_archive_page(bp, nav_info=nav_index.get(bp['page']))
        write(os.path.join(SITE, bp['page'].replace('/', os.sep)), html)

    # 3. Other family indexes
    for family, _, intro in T.FAMILIES:
        if family != 'main':
            write(os.path.join(SITE, T.slug_of(family), 'index.html'),
                  T.family_index(family, intro, by_family[family], gate.items(family)))

    # 3b. Locked-notice pages for every URL a still-locked group would occupy,
    #     so old links read "not open yet" instead of 404 or a transcript.
    for item in [it for items in gate.groups.values() for it in items.values()]:
        for url in item['pages']:
            write(os.path.join(SITE, *url.split('/')), T.locked_notice_page(item, url))

    # 4. Detailed script pages (507 pages)
    for rec in pages:
        md_path = os.path.join(SRC, rec['page_md'])
        md_content = open(md_path, encoding='utf-8').read()
        page_rel = rec['page']
        cur_nav = nav_index.get(page_rel)
        cur_branches = branch_index.get(page_rel)
        html = T.script_page(rec, md_content, nav_info=cur_nav, branch_targets=cur_branches)
        write(os.path.join(SITE, page_rel.replace('/', os.sep)), html)

    graphs = len(chapters) + len(branching_acts)
    battle_pages_total = len(main_battle_nodes) + len(act_battle_pages)
    print("站点生成：site/ 剧本页 %d 篇 + 战斗档案 %d 篇 + 索引 %d 页 + 拓扑地图 %d 页"
          % (len(pages), battle_pages_total, len(T.FAMILIES) + 1, graphs))


if __name__ == '__main__':
    main()
