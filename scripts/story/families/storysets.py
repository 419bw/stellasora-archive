# -*- coding: utf-8 -*-
"""故事集支线族：StorySet* 三表挂载的 STsp_<chapter>_<part> 短剧。

Tab (栏目) -> Chapter (故事集) -> Section (小节)；tab 1 是站点级「全部」筛选，
不是分类，故章节只归入其真实栏目。

NEEDS：StorySetTab/Chapter/Section 三对 BIN/LANG 表。
"""
import os
import collections

from context import lang_of
from sink import safe_name, write
from pipeline.pagedoc import PageDoc
from pipeline.render_md import page_markdown

NEEDS = (('BIN', 'StorySetTab'), ('BIN', 'StorySetChapter'), ('BIN', 'StorySetSection'),
         ('LANG', 'StorySetTab'), ('LANG', 'StorySetChapter'), ('LANG', 'StorySetSection'))
MOUNTS = (('StorySetSection', 'AVGId'),)


def build(ctx, sink):
    BIN_SST_TAB = ctx.table('BIN', 'StorySetTab')
    BIN_SST_CHAPTER = ctx.table('BIN', 'StorySetChapter')
    BIN_SST_SECTION = ctx.table('BIN', 'StorySetSection')
    LANG_SST_TAB = ctx.lang_table('LANG', 'StorySetTab')
    LANG_SST_CHAPTER = ctx.lang_table('LANG', 'StorySetChapter')
    LANG_SST_SECTION = ctx.lang_table('LANG', 'StorySetSection')
    stats = collections.Counter()
    tabs = {r['Id']: lang_of(LANG_SST_TAB, r.get('TabName', ''))
            for r in ctx.rows(BIN_SST_TAB) if not r.get('IsAll')}
    sections = collections.defaultdict(list)
    for s in ctx.rows(BIN_SST_SECTION):
        sections[s['ChapterId']].append(s)
    for chap in ctx.rows(BIN_SST_CHAPTER):
        secs = sections.get(chap['Id'])
        if not secs:
            continue
        cname = lang_of(LANG_SST_CHAPTER, chap.get('Name', ''))
        cno = lang_of(LANG_SST_CHAPTER, chap.get('Title', ''))
        tab = tabs.get(chap.get('TabId'), '未分类')
        folder = os.path.join(ctx.out, 'storysets', safe_name(tab),
                              safe_name('%s_%s' % (chap['Id'], cname)))
        for s in secs:
            parsed = ctx.extract_script(s.get('AVGId'))
            if not parsed:
                continue
            idx = lang_of(LANG_SST_SECTION, s.get('Title', ''))
            desc = lang_of(LANG_SST_SECTION, s.get('Desc', ''))
            info = [
                "- **所属故事集**：%s《%s》" % (cno, cname),
                "- **栏目**：%s" % tab,
                "- **小节 ID**：`%s`" % s['Id'],
                "- **AVG 剧本**：`%s`" % s.get('AVGId'),
            ]
            path = os.path.join(folder, 'sections',
                                safe_name('%s_%s' % (s['Id'], idx or desc)) + '.md')
            doc = PageDoc("# %s" % (desc or idx), info, parsed['meta']['recap'],
                          "逐句台词", parsed['beats'], info_title="故事集小节信息",
                          meta=parsed['meta'])
            write(path, page_markdown(doc))
            sink.record_page('storysets', path, doc, s['Id'], desc or idx, code=idx,
                             group={'kind': 'storyset', 'id': chap['Id'], 'label': cname,
                                    'no': cno, 'tab': tab},
                             stems=[s.get('AVGId')],
                             page='storysets/%s/%s.html' % (chap['Id'], s['Id']))
            stats['sections'] += 1
            stats['lines'] += sum(1 for b in parsed['beats'] if b['k'] in ('talk', 'bubble'))
    return stats
