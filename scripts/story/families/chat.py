# -*- coding: utf-8 -*-
"""心链（手机聊天）族：Chat.json 挂载的 PM_* 剧本 → story_docs/_chat/ 人读 md。

收录口径与 dispatch 同款自外于站点：一页 = 一个 PM 剧本（按 SetGroupId 切段，
一段一节），**扁平**摆在 `_chat/` 下（63 个文件名按 PM 编号排序即按联系人分组，
角色名在每篇 H1 与 `_index.md` 里）。**不调 sink.record_page**、不进
sections.json / search.json / _beats 侧车，因此不生成任何 HTML、不进导航与离线
检索；`_chat/` 目录名本身带 `_` 前缀，validate_site 的 G2 与 validate_story 的
A/C/F 都不会收编（见 _dev/AI_HANDOVER_GUIDE.md 7.6/7.7）。信息行刻意写
`心链剧本**：` 而不写 `AVG 剧本**：`，避免被 F 的「整本页」对账收编。

注意：**不要在 `_chat/` 下再建子目录**。G2 的 `_` 放行是按"直接所在目录名"判的，
`_chat/103_琥珀/PM10301.md` 会被当成站点页收编、撞"sections.json 没登记"。

脚本段是权威：537 个 SetGroupId 段 vs Chat 表 498 行，多出的 39 个 `08` 段是
上游缺行，照常渲染并标注；空段跳过。两者都在 _chat/_diagnostics.json 登记。

NEEDS：BIN/LANG Chat + BIN/LANG Item（礼物名）+ CFG 目录扫描（PM_*）。
"""
import os
import json
import collections

import phone_chat

from context import lang_of
from sink import write

NEEDS = (('BIN', 'Chat'), ('LANG', 'Chat'), ('BIN', 'Item'), ('LANG', 'Item'))
MOUNTS = (('Chat', 'AVGId'),)


def build(ctx, sink):
    BIN_CHAT = ctx.table('BIN', 'Chat')
    BIN_ITEM = ctx.table('BIN', 'Item')
    LANG_ITEM = ctx.lang_table('LANG', 'Item')
    stats = collections.Counter()
    diag = phone_chat.ChatDiagnostics()
    item_names = {str(r['Id']): lang_of(LANG_ITEM, r.get('Title') or '')
                  for r in BIN_ITEM.values() if r.get('Title')}

    by_file = collections.defaultdict(dict)    # (cid, stem) -> {段号: Chat 行}
    stems_of = collections.defaultdict(list)   # cid -> [stem]（表内出现序）
    for r in BIN_CHAT.values():
        cid, stem = r.get('AddressBookId'), r.get('AVGId')
        if cid is None or not stem:
            continue
        by_file[(cid, stem)][str(r.get('AVGGroupId'))] = r
        if stem not in stems_of[cid]:
            stems_of[cid].append(stem)
    mounted = {stem for _cid, stem in by_file}
    for stem in sorted(f[:-4] for f in os.listdir(ctx.cfg)
                       if f.startswith('PM') and f.endswith('.lua')):
        if stem not in mounted:
            diag.add('script_without_chat_rows', {'stem': stem})

    contacts = []
    for cid in sorted(stems_of):
        cname = ctx.character_name(cid) or ('旅人 %s' % cid)
        files = []
        for stem in sorted(stems_of[cid]):
            path = os.path.join(ctx.cfg, stem + '.lua')
            if not os.path.exists(path):
                for gid, r in sorted(by_file[(cid, stem)].items()):
                    diag.add('chat_row_without_segment',
                             {'stem': stem, 'gid': gid, 'chat_id': r.get('Id')})
                continue
            segments = phone_chat.extract_script(stem, ctx.script_commands(stem),
                                                 ctx.speaker_resolver, ctx.text_compiler, diag)
            rows = by_file[(cid, stem)]
            prepared, skipped = [], []
            for seg in segments:
                if seg['gid'] not in rows:
                    diag.add('segment_without_chat_row', {'stem': stem, 'gid': seg['gid']})
                if seg['n_msg'] == 0 and seg['n_begin'] == 0:
                    diag.add('empty_segment_skipped', {'stem': stem, 'gid': seg['gid']})
                    skipped.append(seg['gid'])
                    continue
                prepared.append((seg, rows.get(seg['gid'])))
                stats['segments'] += 1
                stats['messages'] += seg['n_msg']
                stats['choices'] += seg['n_begin']
            if not prepared:
                continue
            files.append({'stem': stem,
                          'script': os.path.relpath(path, ctx.root).replace(os.sep, '/'),
                          'segments': segments, 'rows': rows,
                          'prepared': prepared, 'skipped_gids': skipped})
            stats['scripts'] += 1
        if files:
            contacts.append({'id': cid, 'name': cname, 'files': files})
            stats['contacts'] += 1

    out = os.path.join(ctx.out, '_chat')
    for contact in contacts:
        for f in contact['files']:
            write(os.path.join(out, f['stem'] + '.md'),
                  phone_chat.render_script_md(contact, f, item_names))
    write(os.path.join(out, '_index.md'), phone_chat.render_index_md(contacts))
    write(os.path.join(out, '_diagnostics.json'),
          json.dumps(diag.as_dict(), ensure_ascii=False, indent=1) + "\n")
    for cat, n in sorted(diag.unexpected().items()):
        print("!! 心链诊断 %s：%d 处（详见 story_docs/_chat/_diagnostics.json）" % (cat, n))
    print("  心链聊天：联系人=%d 剧本=%d 段=%d 短信=%d 抉择=%d"
          % (stats['contacts'], stats['scripts'], stats['segments'],
             stats['messages'], stats['choices']))
    return stats
