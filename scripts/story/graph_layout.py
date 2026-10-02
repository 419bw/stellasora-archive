# -*- coding: utf-8 -*-
"""Deterministic layered layout for the main-story node graph.

Pure functions, no file access: `chapters.json` nodes in, coordinates out, so the
geometry can be asserted independently (see .tmp_verify/validate_site.py contract H).

The official screen authors its columns inside a FairyGUI prefab, which the dump does
not carry, so this reproduces the *shape* of it -- a chain running left to right, forks
fanning out and merges returning -- rather than claiming the game's exact column index.
"""

CARD_W = 208      # node card width, px
CARD_H = 96       # node card height, px
GUT_X = 56        # horizontal gap between columns, px
ROW_H = 40        # vertical gap between lanes, px


def code_key(code):
    """Sort '01' < '02A' < '05A' < '05B' and keep non-numeric labels after them."""
    digits = ''
    for ch in code or '':
        if not ch.isdigit():
            break
        digits += ch
    return (0 if digits else 1, int(digits) if digits else 0, code or '')


def _reachable(node, children, seen=None):
    seen = seen or set()
    for c in children.get(node, ()):
        if c not in seen:
            seen.add(c)
            _reachable(c, children, seen)
    return seen


def _crossings(nodes, edges):
    lane = {n['story_id']: n['lane'] for n in nodes}
    col = {n['story_id']: n['col'] for n in nodes}
    bad = 0
    for a in edges:
        for b in edges:
            if a[0] == b[0] or a[1] == b[1]:
                continue
            if (col[a[0]] - col[b[0]]) * (lane[a[1]] - lane[b[1]]) < 0:
                bad += 1
    return bad


def layout(nodes):
    """nodes: [{'sid','story_id','parents','code'}] -> same dicts plus col/lane/x/y.

    Returns {'nodes', 'edges', 'columns', 'width', 'height', 'roots'}.
    """
    by_sid = {n['story_id']: n for n in nodes}
    if len(by_sid) != len(nodes):
        raise ValueError('duplicate story_id in chapter nodes')
    for n in nodes:
        for p in n['parents']:
            if p not in by_sid:
                raise ValueError('unresolved parent %s on %s' % (p, n['story_id']))

    children = {n['story_id']: [] for n in nodes}
    for n in nodes:
        for p in n['parents']:
            children[p].append(n['story_id'])
    for k in children:
        children[k].sort(key=lambda s: (code_key(by_sid[s]['code']), by_sid[s]['sid']))

    # longest-path column, in topological order
    indeg = {n['story_id']: len(n['parents']) for n in nodes}
    queue = sorted([s for s, d in indeg.items() if not d], key=lambda s: by_sid[s]['sid'])
    order = []
    while queue:
        cur = queue.pop(0)
        order.append(cur)
        for c in children[cur]:
            indeg[c] -= 1
            if not indeg[c]:
                queue.append(c)
        queue.sort(key=lambda s: by_sid[s]['sid'])
    if len(order) != len(nodes):
        raise ValueError('cycle detected in chapter nodes')
    for s in order:
        ps = by_sid[s]['parents']
        by_sid[s]['col'] = 1 + max((by_sid[p]['col'] for p in ps), default=-1)

    # lanes: fan a fork around its parent, widest branch keeps the parent's lane
    occupied = {}
    span = {s: 1 + len(_reachable(s, children)) for s in by_sid}

    def take(col, want):
        free = occupied.setdefault(col, set())
        for offset in sorted(range(-12, 13), key=lambda d: (abs(d), d)):
            if want + offset not in free:
                free.add(want + offset)
                return want + offset
        raise RuntimeError('no free lane in column %s' % col)

    for s in order:
        n = by_sid[s]
        ps = n['parents']
        if not ps:
            n['lane'] = take(n['col'], 0)
        elif len(ps) == 1:
            p = by_sid[ps[0]]
            kids = children[ps[0]]
            if len(kids) > 1:
                rank = sorted(kids, key=lambda k: (-span[k], by_sid[k]['sid'])).index(s)
                side = [0, -1, 1, -2, 2, -3, 3][rank] if rank < 7 else rank
                n['lane'] = take(n['col'], p['lane'] + side)
            else:
                n['lane'] = take(n['col'], p['lane'])
        else:
            want = round(sum(by_sid[p]['lane'] for p in ps) / float(len(ps)))
            n['lane'] = take(n['col'], want)

    edges = [(p, s) for s in order for p in by_sid[s]['parents']]

    # one barycentre sweep: move a node to a nearer free lane only if crossings drop
    for col in sorted({n['col'] for n in nodes}):
        for n in [x for x in nodes if x['col'] == col]:
            neigh = [by_sid[p]['lane'] for p in n['parents']]
            neigh += [by_sid[c]['lane'] for c in children[n['story_id']]]
            if not neigh:
                continue
            want = int(round(sum(neigh) / float(len(neigh))))
            old = n['lane']
            if want == old or want in occupied[col]:
                continue
            before = _crossings(nodes, edges)
            occupied[col].discard(old)
            occupied[col].add(want)
            n['lane'] = want
            if _crossings(nodes, edges) >= before:
                occupied[col].discard(want)
                occupied[col].add(old)
                n['lane'] = old

    top = min(n['lane'] for n in nodes)
    bottom = max(n['lane'] for n in nodes)
    for n in nodes:
        n['x'] = n['col'] * (CARD_W + GUT_X)
        n['y'] = (n['lane'] - top) * (CARD_H + ROW_H)
    columns = 1 + max(n['col'] for n in nodes)
    return {'nodes': nodes, 'edges': edges, 'columns': columns,
            'roots': sorted([s for s in by_sid if not by_sid[s]['parents']]),
            'width': columns * CARD_W + (columns - 1) * GUT_X,
            'height': (bottom - top + 1) * (CARD_H + ROW_H)}
