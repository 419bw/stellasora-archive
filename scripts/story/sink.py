# -*- coding: utf-8 -*-
"""SidecarSink：结构化侧车记录与落盘（Phase B-0 上线）。

取代原 build_story.py 的模块级累加器（_PAGES/_SEARCH_ENTRIES/_CHAPTER_NODES/
_RENDERED 与 CODE_MISMATCHES）：全部收为实例属性，族与聚合模块经同一个 sink
实例读写，执行顺序不再由全局可变状态隐式决定。

  * record_page —— sections.json/search.json 的页面记录。R4：扩展字段收敛为
    显式 keyword-only 可选参（签名即当前全部调用点的并集），None=缺省不写入
    （复现原 **extra 只写传入键的行为，保产物字节一致）；未知键 TypeError。
    major_choices 由 rec 构造逻辑内部生成，不是入参。
  * record_node —— chapters.json 的章节点（main 族每个 Story 行一笔）。
  * write_beats —— PageDoc 侧车落盘（story_docs/_beats/<page 的 .html 换 .json>；
    Phase 2 起 HTML 后端 scripts/site/render_html.py 直接消费，不再从 Markdown
    反编译；侧车随 git 提交，门控手册 8.5 认可的位置）。
  * record_battle_map / record_skipped / record_code_mismatch —— R1：主线对账
    记录收归 sink，13 族签名同构；orphan_battles 的 used 从 sink.battle_map
    （attached 项）取，aggregate 从 sink 读对账输入。
  * write / safe_name —— 文件工具（与 context.py 的表工具对称：不设 common 抽屉）。
"""
import os
import re
import json
import collections

from pipeline.conditions import reading_beats
from pipeline import markup
from context import lang_of


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text if text.endswith("\n") else text + "\n")


def safe_name(s):
    return re.sub(r'[\\/:*?"<>|]', '_', s).strip()


def node_time(beats):
    """The official chip is authored per *column* (`StoryChapterTimeStamp.<chapter*100+column>`)
    and reads 「猎月 六角鲸日 10:36」; the column assignment itself lives in the UI prefab, which
    this dump does not carry, and a month's day-names cannot be matched to the numbered days
    the scripts use (「猎月 13日」 is 吠啸枭日, not the 刻木鸟日 that an equal clock would suggest).
    So a node carries its own script's opening scene time, and the chapter keeps the raw slot
    list as reference data instead of pretending the two are joined."""
    head = next((b for b in beats or [] if b['k'] == 'scene'), None)
    if not head:
        return None
    return {'clock': head['time'], 'date': head['date']}


class SidecarSink:
    """一次构建的全部侧车累加器 + 落盘；实例状态即 sections/chapters/search 的真源。

    ``containers`` 可选：注入外部累加器容器（Phase B 混合调度中间态用——已搬迁
    族经 sink 记录但并入编排器尚在使用的模块级列表，保持产物字节序）。
    键：pages / search_entries / chapter_nodes / rendered / battle_map /
    skipped / code_mismatches。缺省全部自建。
    """

    def __init__(self, out, lang_story, containers=None):
        containers = containers or {}
        self.out = out
        self.lang_story = lang_story          # LANG Story 表（record_node 取展示文案）
        self.pages = containers.get('pages', [])
        self.search_entries = containers.get('search_entries', [])
        self.chapter_nodes = containers.get('chapter_nodes', collections.OrderedDict())
        self.rendered = containers.get('rendered', set())
        # 主线对账记录（R1）：main 族写入，aggregate/orphan_battles 读取
        self.battle_map = containers.get('battle_map', [])
        self.skipped = containers.get('skipped', [])
        self.code_mismatches = containers.get('code_mismatches', [])
        # orphan_battles 族写入：有剧本但无关卡引用的 BBm 清单
        self.unattached = containers.get('unattached', [])

    # ------------------------------------------------------------ 页面记录
    def record_page(self, family, path, doc, ident, title, *, code='', group=None,
                    stems=(), page=None, story_id=None, kind=None, parents=None,
                    hint=None, aim=None, affinity=None, twins=None, prose_lines=None,
                    cast=None, weight=None, notes=None, table_refs=None,
                    mount_note=None, text_chars=None):
        """R4 显式 schema：keyword-only 可选参即原 **extra 的并集；None=缺省不写入。"""
        beats = reading_beats(doc.beats)
        speakers = []
        for b in beats:
            if b['k'] in ('talk', 'bubble') and b['speaker'] not in speakers:
                speakers.append(b['speaker'])
        stems = [s for s in stems if s]
        counts = collections.Counter(b['k'] for b in beats)
        counts['sticker'] = sum(1 for b in beats if b['k'] == 'talk' and b.get('sticker'))
        rec = {
            'id': ident, 'family': family, 'code': code, 'title': title,
            'group': group or {},
            'page_md': os.path.relpath(path, self.out).replace(os.sep, '/'),
            'page': page,
            'stems': stems,
            'recap': markup.text(doc.meta['recap']),
            'speakers': speakers,
            'counts': dict(counts),
            'preview': " ".join(
                [markup.plain(b['text']) for b in beats if b['k'] == 'talk']
                or [markup.plain(b['story']).replace('\n', ' ') for b in beats if b['k'] == 'anecdote']
            )[:180],
        }
        # Document-ordered 重大抉择 blocks with per-option jump EvId; the site joins
        # these against StoryCondition/ActivityStoryEvidence to label branch targets.
        major_choices = [
            [{'title': markup.text(t), 'ev': ev} for (t, _d, ev) in b['options']]
            for b in beats if b['k'] == 'choice' and b['kind'] == 'major' and b['options']
        ]
        if major_choices:
            rec['major_choices'] = major_choices
        # 可选键的写入顺序 = 各调用点原 **extra 的传参顺序并集（npc_bonds 是
        # affinity→hint、main 是 hint→aim，取 affinity 在 hint 前的单一正序可同时
        # 满足两者；键序即 sections.json 的字段序，动了就是字节回退）。
        for key, value in (('story_id', story_id), ('kind', kind), ('parents', parents),
                           ('affinity', affinity), ('hint', hint), ('aim', aim),
                           ('twins', twins), ('prose_lines', prose_lines), ('cast', cast),
                           ('weight', weight), ('notes', notes), ('table_refs', table_refs),
                           ('mount_note', mount_note), ('text_chars', text_chars)):
            if value is not None:
                rec[key] = value
        self.pages.append(rec)
        # 全量台词进检索 hay，中段文本才可被精确检索（issue #7）；男主变体仅在与默认
        # 文本不同时才收录，否则索引体积约翻倍
        lines, male_only = [], []
        for b in beats:
            if b['k'] in ('talk', 'bubble'):
                text_f = markup.plain(b['text'])
                text_m = markup.plain(b['text'], 'male')
                if text_f:
                    lines.append(text_f)
                if text_m and text_m != text_f:
                    male_only.append(text_m)
            elif b['k'] == 'choice':
                # options 首元素是 Text（versions 结构的编译产物），必须过 markup.plain 解码
                lines += [t for t in (markup.plain(o)
                                      for (o, _d, _ev) in b['options']) if t]
            elif b['k'] == 'anecdote':
                for fld in ('title', 'source'):
                    v = markup.plain(b.get(fld, ''))
                    if v:
                        lines.append(v)
                for para in markup.plain(b.get('story', '')).split('\n'):
                    if para.strip():
                        lines.append(para.strip())
        recap_m = markup.text(doc.meta['recap'], 'male')
        search_text = [title, rec['recap']] + lines + male_only
        if recap_m and recap_m != rec['recap']:
            search_text.append(recap_m)
        self.search_entries.append({
            **{key: rec[key] for key in ('id', 'family', 'code', 'title', 'page', 'speakers')},
            'group': rec['group'].get('label', ''),
            'hay': ' '.join(dict.fromkeys(text for text in search_text if text)),
        })
        self.rendered.update(stems)
        self.write_beats(page, doc)
        return rec

    # ------------------------------------------------------------ 章节点
    def record_node(self, ch, row, page, bubble_stem, beats=None):
        """Every Story row is a graph node, even the ones with no script in the pack."""
        nodes = self.chapter_nodes.setdefault(ch, [])
        parents = [p for p in (row.get('ParentStoryId') or []) if isinstance(p, str)]
        nodes.append({
            'sid': row['Id'],
            'story_id': row.get('StoryId'),
            'code': lang_of(self.lang_story, row.get('Index', '')),
            'title': lang_of(self.lang_story, row.get('Title', '')),
            'desc': lang_of(self.lang_story, row.get('Desc', '')),
            'aim': lang_of(self.lang_story, row.get('Aim', '')),
            'kind': 'battle' if row.get('IsBattle') else 'story',
            'is_branch': bool(row.get('IsBranch')),
            'is_last': bool(row.get('IsLast')),
            'memory': row.get('MemoryType'),
            'has_evidence': bool(row.get('HasEvidence')),
            'condition': row.get('ConditionId'),
            'parents': parents,
            'stems': {'story': None if row.get('IsBattle') else row.get('StoryId'),
                      'bubble': bubble_stem},
            'state': 'released' if page else 'unreleased',
            'time': node_time(beats),
            'page': page,
        })
        return parents

    # ------------------------------------------------------------ 对账记录（R1）
    def record_battle_map(self, entry):
        """(sid, expected_stem, state, chapter)；state ∈ {'attached','MISSING'}。"""
        self.battle_map.append(entry)

    def record_skipped(self, entry):
        """(ch, sid, stem, title, kind)：关卡表有行、包内无剧本。"""
        self.skipped.append(entry)

    def record_code_mismatch(self, entry):
        """(sid, story_id, suffix, display, stem, condition, chapter)：官方显示代号与
        StoryId 交叉行（上游笔误）。"""
        self.code_mismatches.append(entry)

    def record_unattached(self, orphans):
        """有剧本但无关卡引用的 BBm 清单（orphan_battles 族写入）。"""
        self.unattached = list(orphans)

    # ------------------------------------------------------------ 侧车落盘
    def write_beats(self, page, doc):
        """PageDoc 侧车落盘：story_docs/_beats/<page 的 .html 换 .json>。

        Phase 2 起 HTML 后端（scripts/site/render_html.py）直接消费这些侧车，
        不再从 Markdown 反编译。侧车随 git 提交（门控手册 8.5 认可的位置）。
        """
        if not page:
            return
        rel = page[:-len('.html')] + '.json' if page.endswith('.html') else page + '.json'
        write(os.path.join(self.out, '_beats', rel),
              json.dumps(doc.to_dict(), ensure_ascii=False, indent=1) + "\n")
