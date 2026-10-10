"""Historical condition labels, source boundaries and shared reading text.

兜底方针（与 PR #3 的"未知标记保留原文"一致，见 pipeline/diagnostics.py 的纪律）：
条件标签是给人看的，任何查表失败都**产出可读标签 + 登记**，绝不 KeyError /
StopIteration / IndexError 把整个 build 带崩（auto_sync 以 check=True 跑 build）。
登记走注入的 Diagnostics；未注入时自建一个，保证单测与库用法都不炸。
"""
import collections
import json
from pathlib import Path

from . import markup
from .diagnostics import Diagnostics


class ConditionCatalog:
    """Resolve historical conditions against official story tables."""

    def __init__(self, tables, language, commands, compiler, diagnostics=None):
        self.tables = tables
        self.language = language
        self.commands = commands
        self.compiler = compiler
        self.diagnostics = diagnostics if diagnostics is not None else Diagnostics()
        self.stories = self._index(tables['Story'], 'StoryId', 'Story')
        self.unlocks = self._index(tables['StoryCondition'], 'ConditionId', 'StoryCondition')
        self.evidence = self._index(tables['StoryEvidence'], 'EvId', 'StoryEvidence')
        self.evidence_sources = None

    @classmethod
    def load(cls, bin_dir, lang_dir, commands, compiler, diagnostics=None):
        names = ('Story', 'StoryCondition', 'StoryEvidence', 'StoryChapter', 'Achievement')
        tables = {n: json.loads((Path(bin_dir) / (n + '.json')).read_text(encoding='utf-8'))
                  for n in names}
        language = {n: json.loads((Path(lang_dir) / (n + '.json')).read_text(encoding='utf-8'))
                    for n in ('Story', 'StoryEvidence', 'StoryChapter', 'Achievement')}
        return cls(tables, language, commands, compiler, diagnostics=diagnostics)

    # ------------------------------------------------------------------ 查表
    def _index(self, rows, field, table):
        """按主键建索引；缺主键/结构异常的行跳过并登记，不再让导入期 KeyError。"""
        out = {}
        for tid, row in rows.items():
            if not isinstance(row, dict):
                self.diagnostics.add('condition_row_malformed',
                                     key=(table, str(tid), 'row'),
                                     table=table, row_id=tid, missing='row is not an object')
                continue
            value = row.get(field)
            if value is None or value == '':
                self.diagnostics.add('condition_row_malformed',
                                     key=(table, str(tid), field),
                                     table=table, row_id=tid, missing=field)
                continue
            out[value] = row
        return out

    def _table(self, name):
        rows = self.tables.get(name)
        return rows if isinstance(rows, dict) else {}

    def text(self, table, key):
        return markup.plain(self.compiler.compile(self.language[table].get(key, key)))

    def story(self, ident):
        row = self.stories.get(ident)
        if row is None:
            self.diagnostics.add('condition_story_unknown',
                                 key=('story', str(ident)), ident=str(ident))
            return ident
        code = self.text('Story', row.get('Index', ''))
        title = self.text('Story', row.get('Title', ''))
        return '《%s》' % ' '.join(x for x in (code, title) if x)

    def unlock(self, ident):
        if not ident:
            return '条件始终成立'
        row = self.unlocks.get(ident)
        if row is None:
            self.diagnostics.add('condition_unlock_unknown',
                                 key=('unlock', str(ident)), ident=str(ident))
            return '解锁条件 %s 成立' % ident
        parts = []
        for field, prefix, join in (('StoryId_a', '已阅读', '、'),
                                     ('StoryId_b', '已阅读以下任一剧情：', '、')):
            values = row.get(field)
            if not isinstance(values, list):
                if values:
                    self.diagnostics.add('condition_row_malformed',
                                         key=('StoryCondition', str(ident), field),
                                         table='StoryCondition', row_id=ident, missing=field)
                continue
            if values:
                parts.append(prefix + join.join(self.story(s) for s in values))
        for field, join in (('EvIds_a', '，且'), ('EvIds_b', '，或')):
            values = row.get(field)
            if not isinstance(values, list) or not values:
                continue
            requirements = [self.evidence_condition(e) for e in values]
            if all(kind == 'read' for kind, _value in requirements):
                prefix = '已阅读' if field == 'EvIds_a' else '已阅读以下任一剧情：'
                parts.append(prefix + '、'.join(value for _kind, value in requirements))
            else:
                parts.append(join.join(value for _kind, value in requirements))
        if row.get('PlayerWorldLevel'):
            parts.append('世界等级达到 %s' % row['PlayerWorldLevel'])
        achieve = row.get('AchieveIds')
        if isinstance(achieve, list) and achieve:
            parts.append('已完成成就' + '、'.join('「%s」' % name
                                              for name in self._achievement_names(achieve)))
        return '，且'.join(parts) or '条件始终成立'

    def _achievement_names(self, ids):
        for a in ids:
            row = self._table('Achievement').get(str(a))
            title = row.get('Title') if isinstance(row, dict) else None
            if not title:
                self.diagnostics.add('condition_achievement_unknown',
                                     key=(str(a),), achieve_id=str(a))
                yield str(a)
            else:
                yield self.text('Achievement', title)

    def evidence_condition(self, ident):
        """Describe a historical marker through its source story or choice."""
        from .passes import fork_options
        if self.evidence_sources is None:
            self.evidence_sources = collections.defaultdict(list)
            for stem in self.stories:
                for command in self.commands(stem) or []:
                    if command.cmd == 'GetEvidence':
                        self.evidence_sources[command.param[0]].append(('read', self.story(stem)))
                    elif command.cmd == 'SetMajorChoice':
                        options = fork_options('major', command.param, self.compiler)[1]
                        for title, _desc, marker in options:
                            if marker:
                                label = '已选择%s中的「%s」' % (self.story(stem), markup.plain(title))
                                self.evidence_sources[marker].append(('choice', label))
        sources = self.evidence_sources[ident]
        if sources:
            if all(kind == 'read' for kind, _value in sources):
                return 'read', '或'.join(value for _kind, value in sources)
            return 'choice', '，或'.join('已阅读' + value if kind == 'read' else value
                                       for kind, value in sources)
        row = self.evidence.get(ident)
        name = row.get('Name') if isinstance(row, dict) else None
        if not name:
            extra = {} if row is not None else {'missing': 'row'}
            self.diagnostics.add('condition_evidence_unknown',
                                 key=('evidence', str(ident)), ev_id=str(ident), **extra)
            return 'item', '已取得「%s」' % ident
        return 'item', '已取得「%s」' % self.text('StoryEvidence', name)

    def choice(self, param):
        from .passes import fork_options
        if len(param) != 5:
            # 结构性缺参（上游指令形状变了）：按"未知来源的历史选项"降级，不登记——
            # 与 slot()/fork_options() 的缺参返回 '' 同一性质，逐条登记只会噪声化侧车。
            return '已选择历史选项'
        _group, kind, stem, choice_group, rule = param
        command_name = 'SetMajorChoice' if kind == 0 else 'SetPersonalityChoice'
        command = None
        for c in self.commands(stem) or []:
            if c.cmd == command_name and str(c.param[0]) == str(choice_group):
                command = c
                break
        if command is None:
            self.diagnostics.add('condition_choice_frame_missing',
                                 key=(str(stem), command_name, str(choice_group)),
                                 stem=str(stem), cmd=command_name, group=str(choice_group))
            return '已选择%s中的选项' % self.story(stem)
        options = fork_options('major' if kind == 0 else 'personality', command.param, self.compiler)[1]
        clauses = []
        for alternative in str(rule).split('|'):
            choices = []
            for item in alternative.split('+'):
                if not item:
                    self._bad_option(stem, choice_group, '(空)')
                    continue
                index = ord(item[0].upper()) - ord('A')
                if not 0 <= index < len(options):
                    self._bad_option(stem, choice_group, item)
                    continue
                label = '「%s」' % markup.plain(options[index][0])
                if len(item) > 1:
                    label += '（本轮至少 %s 次）' % item[1:]
                choices.append(label)
            if choices:
                clauses.append('且'.join(choices))
        if not clauses:
            return '已选择%s中的选项' % self.story(stem)
        return '已选择%s中的%s' % (self.story(stem), '，或'.join(clauses))

    def _bad_option(self, stem, choice_group, item):
        self.diagnostics.add('condition_choice_option_missing',
                             key=(str(stem), str(choice_group), item),
                             stem=str(stem), group=str(choice_group), item=item)

    def _be_scope(self, param):
        """CheckBE 的 (范围文案, 阈值)。"""
        _group, start, end, threshold = self._be_scope_parts(param)
        return ('%s至%s的终局已阅读比例' % (self._chapter(start), self._chapter(end)),
                threshold)

    def _be_labels(self, scope, threshold):
        return {1: scope + '为 0%',
                2: scope + f'大于 0%，且不超过 {threshold}%',
                3: scope + f'大于 {threshold}%，且小于 100%',
                4: scope + '为 100%'}

    def be_cases(self, param):
        """四个档位的完整标签表（保留给外部调用；内部走 be_case_label）。"""
        scope, threshold = self._be_scope(param)
        return self._be_labels(scope, threshold)

    def _be_scope_parts(self, param):
        """CheckBE 参数解包；形状不符时登记并退化成 (group, None, None, '')。"""
        if isinstance(param, (list, tuple)) and len(param) == 4:
            return param
        self.diagnostics.add('condition_be_case_unknown',
                             key=('param', str(param)),
                             group=str(param[0]) if param else '',
                             missing='CheckBE 参数不是 4 元组')
        return (param[0] if param else '', None, None, '')

    def _chapter(self, ident):
        row = self._table('StoryChapter').get(str(ident))
        name = row.get('Name') if isinstance(row, dict) else None
        if not name:
            self.diagnostics.add('condition_be_case_unknown',
                                 key=('chapter', str(ident)),
                                 chapter=str(ident), missing='StoryChapter 查不到')
            return str(ident)
        return self.text('StoryChapter', name)

    def be_case_label(self, param, case):
        """单个 CheckBECase 的中文标签；档位越界/章号缺失时降级并登记。"""
        _group, start, end, threshold = self._be_scope_parts(param)
        scope = '%s至%s的终局已阅读比例' % (self._chapter(start), self._chapter(end))
        known = {1: scope + '为 0%',
                 2: scope + f'大于 0%，且不超过 {threshold}%',
                 3: scope + f'大于 {threshold}%，且小于 100%',
                 4: scope + '为 100%'}
        if case in known:
            return known[case]
        self.diagnostics.add('condition_be_case_unknown',
                             key=('case', str(param[0]) if param else '', str(case)),
                             group=str(param[0]) if param else '', case=str(case),
                             missing='档位号不在 1..4')
        return scope + '为未知档位 %s' % case


def condition_markers(commands, catalog):
    """Map source command positions to flat historical branch markers."""
    groups = collections.defaultdict(list)
    families = {'IfTrue': 'choice', 'EndIf': 'choice',
                'IfUnlock': 'unlock', 'IfUnlockElse': 'unlock', 'IfUnlockEnd': 'unlock',
                'CheckBE': 'be', 'CheckBECase': 'be', 'CheckBEEnd': 'be'}
    for c in commands:
        if c.cmd in families:
            groups[(families[c.cmd], str(c.param[0]))].append(c)
    markers = collections.defaultdict(list)
    for (kind, _group), entries in groups.items():
        group = '%s:%s' % (kind, _group)
        previous = False
        if kind == 'be':
            # 组内所有 CheckBE 必须同一 range，否则 be_cases 用第一条生成全部档位标签
            # 会张冠李戴——登记让人来审。
            ranges = {tuple(str(x) for x in e.param) for e in entries if e.cmd == 'CheckBE'}
            if len(ranges) > 1:
                catalog.diagnostics.add('condition_be_case_unknown',
                                        key=('range', group), group=group,
                                        ranges=sorted(ranges), missing='组内 CheckBE range 不一致')
        for c in entries:
            if c.cmd in ('EndIf', 'IfUnlockEnd', 'CheckBEEnd'):
                markers[c.idx].append({'k': 'condition_end', 'group': group})
                continue
            if c.cmd == 'CheckBE':
                continue
            if c.cmd == 'IfUnlockElse':
                label = '否则'
            elif c.cmd == 'CheckBECase':
                case = c.param[1] if len(c.param) > 1 else None
                label = '若' + catalog.be_case_label(entries[0].param, case)
            else:
                label = catalog.unlock(c.param[1] if len(c.param) > 1 else '') \
                    if kind == 'unlock' else catalog.choice(c.param)
                label = ('否则，若' if previous else '若') + label
            markers[c.idx].append({'k': 'condition_branch', 'group': group, 'labels': [label]})
            previous = True
    return markers


def reading_beats(beats):
    """Merge adjacent equal historical case bodies for Markdown and HTML."""
    result = []
    i = 0
    while i < len(beats):
        beat = beats[i]
        if beat['k'] != 'condition_branch':
            result.append(beat)
            i += 1
            continue
        group = beat['group']
        branches = []
        while i < len(beats) and beats[i]['k'] == 'condition_branch' and beats[i]['group'] == group:
            marker = dict(beats[i], labels=list(beats[i]['labels']))
            i += 1
            body = []
            while i < len(beats) and not (beats[i]['k'] in ('condition_branch', 'condition_end')
                                          and beats[i]['group'] == group):
                body.append(beats[i])
                i += 1
            if branches and branches[-1][1] == body:
                branches[-1][0]['labels'].extend(marker['labels'])
            else:
                branches.append((marker, body))
        if any(body for _marker, body in branches):
            for marker, body in branches:
                result.append(marker)
                result.extend(reading_beats(body))
            if i < len(beats) and beats[i]['k'] == 'condition_end':
                result.append(beats[i])
        if i < len(beats) and beats[i]['k'] == 'condition_end':
            i += 1
    return result
