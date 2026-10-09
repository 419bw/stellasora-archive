"""Historical condition labels, source boundaries and shared reading text."""
import collections
import json
from pathlib import Path

from . import markup


class ConditionCatalog:
    """Resolve historical conditions against official story tables."""

    def __init__(self, tables, language, commands, compiler):
        self.tables = tables
        self.language = language
        self.commands = commands
        self.compiler = compiler
        self.stories = {r['StoryId']: r for r in tables['Story'].values()}
        self.unlocks = {r['ConditionId']: r for r in tables['StoryCondition'].values()}
        self.evidence = {r['EvId']: r for r in tables['StoryEvidence'].values()}
        self.evidence_sources = None

    @classmethod
    def load(cls, bin_dir, lang_dir, commands, compiler):
        names = ('Story', 'StoryCondition', 'StoryEvidence', 'StoryChapter', 'Achievement')
        tables = {n: json.loads((Path(bin_dir) / (n + '.json')).read_text(encoding='utf-8'))
                  for n in names}
        language = {n: json.loads((Path(lang_dir) / (n + '.json')).read_text(encoding='utf-8'))
                    for n in ('Story', 'StoryEvidence', 'StoryChapter', 'Achievement')}
        return cls(tables, language, commands, compiler)

    def text(self, table, key):
        return markup.plain(self.compiler.compile(self.language[table].get(key, key)))

    def story(self, ident):
        row = self.stories.get(ident)
        if row is None:
            return ident
        code = self.text('Story', row.get('Index', ''))
        title = self.text('Story', row.get('Title', ''))
        return '《%s》' % ' '.join(x for x in (code, title) if x)

    def unlock(self, ident):
        if not ident:
            return '条件始终成立'
        row = self.unlocks.get(ident)
        if row is None:
            return '解锁条件 %s 成立' % ident
        parts = []
        for field, prefix, join in (('StoryId_a', '已阅读', '、'),
                                     ('StoryId_b', '已阅读以下任一剧情：', '、')):
            if row.get(field):
                parts.append(prefix + join.join(self.story(s) for s in row[field]))
        for field, join in (('EvIds_a', '，且'), ('EvIds_b', '，或')):
            if row.get(field):
                requirements = [self.evidence_condition(e) for e in row[field]]
                if all(kind == 'read' for kind, _value in requirements):
                    prefix = '已阅读' if field == 'EvIds_a' else '已阅读以下任一剧情：'
                    parts.append(prefix + '、'.join(value for _kind, value in requirements))
                else:
                    parts.append(join.join(value for _kind, value in requirements))
        if row.get('PlayerWorldLevel'):
            parts.append('世界等级达到 %s' % row['PlayerWorldLevel'])
        if row.get('AchieveIds'):
            parts.append('已完成成就' + '、'.join('「%s」' % self.text(
                'Achievement', self.tables['Achievement'][str(a)]['Title']) for a in row['AchieveIds']))
        return '，且'.join(parts) or '条件始终成立'

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
        row = self.evidence[ident]
        return 'item', '已取得「%s」' % self.text('StoryEvidence', row['Name'])

    def choice(self, param):
        from .passes import fork_options
        _group, kind, stem, choice_group, rule = param
        command_name = 'SetMajorChoice' if kind == 0 else 'SetPersonalityChoice'
        command = next(c for c in self.commands(stem)
                       if c.cmd == command_name and str(c.param[0]) == str(choice_group))
        options = fork_options('major' if kind == 0 else 'personality', command.param, self.compiler)[1]
        clauses = []
        for alternative in rule.split('|'):
            choices = []
            for item in alternative.split('+'):
                index = ord(item[0].upper()) - ord('A')
                label = '「%s」' % markup.plain(options[index][0])
                if len(item) > 1:
                    label += '（本轮至少 %s 次）' % item[1:]
                choices.append(label)
            clauses.append('且'.join(choices))
        return '已选择%s中的%s' % (self.story(stem), '，或'.join(clauses))

    def be_cases(self, param):
        _group, start, end, threshold = param
        def chapter(ident):
            return self.text('StoryChapter', self.tables['StoryChapter'][str(ident)]['Name'])
        scope = '%s至%s的终局已阅读比例' % (chapter(start), chapter(end))
        return {1: scope + '为 0%',
                2: scope + f'大于 0%，且不超过 {threshold}%',
                3: scope + f'大于 {threshold}%，且小于 100%',
                4: scope + '为 100%'}


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
        labels = catalog.be_cases(entries[0].param) if kind == 'be' else None
        for c in entries:
            if c.cmd in ('EndIf', 'IfUnlockEnd', 'CheckBEEnd'):
                markers[c.idx].append({'k': 'condition_end', 'group': group})
                continue
            if c.cmd == 'CheckBE':
                continue
            if c.cmd == 'IfUnlockElse':
                label = '否则'
            elif c.cmd == 'CheckBECase':
                label = '若' + labels[c.param[1]]
            else:
                label = catalog.unlock(c.param[1]) if kind == 'unlock' else catalog.choice(c.param)
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
