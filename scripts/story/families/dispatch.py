# -*- coding: utf-8 -*-
"""委托结算演出族：AgentSpecialPerformance 的 DP_single*/DP_multi* 演出。

委托完成时，若该委托掉落[特殊报酬]，客户端会从 AgentSpecialPerformance 里按
「上阵旅人组合 + 权重」随机抽一段 DP_* 演出播放（结算面板 DispatchResultCtrl）。
一份 DP 脚本按 SetGroupId 切成多段，每段对应表里一行：CharId=上阵旅人，
AVGGroupId=段号，Weight=随机权重（单人 50 / 双人 150 / 三人 300）。

收录口径：一页 = 一段结算演出（即 AgentSpecialPerformance 的一行），按「该段
出场的旅人 / 组合」归类——单人段归到对应旅人名下（每位 2 变体各一页），双人/三人段
按组合成页。这是委托专场，md 放 dispatch/ 下、**不进各族的 sections/ 子目录**，
也不写 `AVG 剧本**：` 挂载行（一页只含该段而非整份共用脚本）。因此由 validate_story
的「委托分段保真(N)」契约按 (脚本, 段号) 独立切段对账；A/A2/B/C/D/E 与 F/M 对它不适用。
"""
import os
import collections

from sink import safe_name, write
from pipeline.pagedoc import PageDoc
from pipeline.render_md import page_markdown

NEEDS = (('BIN', 'AgentSpecialPerformance'),)
MOUNTS = (('AgentSpecialPerformance', 'Avg'),)


def build(ctx, sink):
    BIN_DISPATCH_PERF = ctx.table('BIN', 'AgentSpecialPerformance')
    stats = collections.Counter()
    parsed = {}

    def segments(stem):
        if stem not in parsed:
            pr = ctx.extract_script(stem) or {'beats': []}
            groups, cur = {}, None
            for b in pr['beats']:
                if b['k'] == 'wave':
                    cur = b['no']
                    groups.setdefault(cur, [])
                elif cur is not None:
                    groups[cur].append(b)
            parsed[stem] = groups
        return parsed[stem]

    variant_no = {}
    for r in ctx.rows(BIN_DISPATCH_PERF):
        stem, gid = r.get('Avg'), str(r.get('AVGGroupId'))
        seg = segments(stem).get(gid) or []
        if not seg:
            print("!! 委托结算演出表行查无该段剧本，跳过: id=%s avg=%s 段=%s" % (r.get('Id'), stem, gid))
            continue
        cast = [int(c) for c in (r.get('CharId') or [])]
        n = len(cast)
        kind = {1: '单人', 2: '双人', 3: '三人'}.get(n, '%d 人' % n)
        names = [ctx.character_name(c) or ('旅人 %d' % c) for c in cast]
        if n == 1:
            variant_no[cast[0]] = variant_no.get(cast[0], 0) + 1
            ordinal = {1: '其一', 2: '其二', 3: '其三'}.get(variant_no[cast[0]], str(variant_no[cast[0]]))
            label = names[0]
            title = '%s · 委托结算演出（%s）' % (names[0], ordinal)
            group = {'kind': 'dispatch', 'id': 'c%d' % cast[0], 'label': label, 'characters': cast}
            sub = 'solo'
        else:
            label = ' ＋ '.join(names)
            title = '%s · %s人委托结算演出' % (label, kind)
            group = {'kind': 'dispatch', 'id': 'm%d' % r['Id'], 'label': label, 'characters': cast}
            sub = 'multi'
        info = [
            "- **结算演出**：`%s`（第 `%s` 段）" % (stem, gid),
            "- **上阵旅人**：%s（Id %s）" % (label, '、'.join(str(c) for c in cast)),
            "- **结算类型**：%s结算演出，出现权重 %s（单人 50 / 双人 150 / 三人 300，越大越易抽中）"
            % (kind, r.get('Weight')),
            "- **触发条件**：委托完成且含「特殊报酬」时，按上阵旅人与权重随机抽一段结算演出播放；"
            "同一份共用剧本按段切分，此处为第 %s 段" % gid,
        ]
        path = os.path.join(ctx.out, 'dispatch', sub, safe_name('%s_%s' % (title, r['Id'])) + '.md')
        doc = PageDoc("# " + title, info, '', '结算演出台词', seg,
                      info_title='委托结算演出信息',
                      meta={'recap': '', 'episode': '', 'title': ''})
        write(path, page_markdown(doc))
        sink.record_page('dispatch', path, doc, r['Id'], title,
                         code='', group=group, stems=[stem],
                         page='dispatch/%s/%s.html' % (sub, r['Id']),
                         cast=cast, weight=r.get('Weight'))
        stats['sections'] += 1
        stats['lines'] += sum(1 for b in seg if b['k'] in ('talk', 'bubble'))
    return stats
