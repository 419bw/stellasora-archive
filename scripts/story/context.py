# -*- coding: utf-8 -*-
"""DataContext：上游数据懒加载 + 共享服务一次构造注入（Phase A 上线）。

取代原 build_story.py 模块级的无条件全量加载（约 40 张表 + 全部共享服务）：
  * 表按 (scope, name) 懒加载并进程内缓存——族各取所需，import 本模块无副作用；
  * TextCompiler / SpeakerResolver / ConditionCatalog / script_commands 缓存 /
    character_name 由编排器构造一次，经 ctx 注入；族模块不得自行构造；
  * ScopedDataContext 在运行期按族 NEEDS 白名单门控表解析（设计 4.5-1）：
    未声明表的任何解析调用立即 raise UndeclaredTableError。共享服务基于全量
    ctx 构造，其表依赖由 SHARED_NEEDS 一次性声明并审计。

路径语义与原模块级常量一致（相对仓库根 ROOT）：
  data/StellaSoraData/CN/bin            -> self.bin   （BIN 表）
  data/StellaSoraData/CN/language/zh_CN -> self.lang  （LANG 表）
  data/ss_lua/.../Avg/_cn/Config        -> self.cfg   （AVG 剧本目录）
  data/ss_lua/.../Avg/_cn/Preset        -> self.preset（官方词表/说话人预设）
"""
import os
import sys
import json
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.lua_parser import T, parse_lua
from pipeline.command_ir import build_commands
from pipeline.speakers import SpeakerResolver
from pipeline.conditions import ConditionCatalog
from pipeline.passes import extract_beats
from pipeline.text_rules import clean_text
from pipeline import markup
from pipeline.diagnostics import Diagnostics
import chapter_path

_MISSING = object()


def lang_of(table, key):
    """本地化表取值 + 文本清洗（原 build_story.lang_of，纯函数）。"""
    return clean_text(table.get(key, ''))


def rows_of(table):
    """表行按 Id 升序（原 build_story.rows_of，纯函数）。"""
    return sorted(table.values(), key=lambda r: r.get('Id', 0))


def field_lang(lang_table, row, field='Name'):
    """行的本地化字段取值（原 build_story.field_lang，纯函数）。"""
    return lang_of(lang_table, row.get(field, ''))


def load_speakers(preset):
    """id -> (name, surfix) from the official AVG character preset."""
    recs = parse_lua(open(os.path.join(preset, 'AvgCharacter.lua'), encoding='utf-8').read())
    out = {}
    for r in recs:
        if isinstance(r, T):
            sid = r.get('id')
            if sid is not None:
                out[str(sid)] = (r.get('name') or "", r.get('surfix') or "")
    return out


# 共享服务的表依赖（编排器声明、审计时并入全集；设计附录 A 末段）。
# SpeakerResolver 读 PRESET/AvgCharacter.lua、script_commands 缓存读 CFG 目录，
# 均非 (scope, name) 表，故不在此列；TextCompiler/ConditionCatalog 各自加载的
# BIN/LANG 表、character_name 的 Character 表、以及构造期急切读取的
# story_lines（StoryLine）与 chapter_slugs（StoryChapter）列示如下。
SHARED_NEEDS = (
    ('BIN', 'ContentWord'), ('LANG', 'ContentWord'),          # TextCompiler 词表
    ('BIN', 'Story'), ('BIN', 'StoryCondition'), ('BIN', 'StoryEvidence'),
    ('BIN', 'StoryChapter'), ('BIN', 'Achievement'),          # ConditionCatalog
    ('LANG', 'Story'), ('LANG', 'StoryEvidence'),
    ('LANG', 'StoryChapter'), ('LANG', 'Achievement'),
    ('BIN', 'Character'), ('LANG', 'Character'),              # character_name
    ('BIN', 'StoryLine'), ('LANG', 'StoryLine'),              # story_lines（急切属性）
    ('BIN', 'StoryChapterTimeStamp'), ('LANG', 'StoryChapterTimeStamp'),  # time_slots
)


class DataContext:
    """上游数据与共享服务的唯一入口；表懒加载 + 进程内缓存。"""

    def __init__(self, root, out=None):
        self.root = root
        self.bin = os.path.join(root, 'data', 'StellaSoraData', 'CN', 'bin')
        self.lang = os.path.join(root, 'data', 'StellaSoraData', 'CN', 'language', 'zh_CN')
        self.cfg = os.path.join(root, 'data', 'ss_lua', 'Lua', 'Game', 'UI', 'Avg', '_cn', 'Config')
        self.preset = os.path.join(root, 'data', 'ss_lua', 'Lua', 'Game', 'UI', 'Avg', '_cn', 'Preset')
        self.out = out if out is not None else os.path.join(root, 'story_docs')
        self._tables = {}
        self._tag_cache = {}
        self._slots = None
        # 进程级唯一诊断收集器：所有降级通道注入这同一个 DIAG
        # （pipeline/diagnostics.py 的 CATEGORIES 注册表描述口径）。
        self.diag = Diagnostics()
        # 共享服务：构造一次，经 ctx 注入（族模块不得自行构造）。
        self.text_compiler = markup.TextCompiler.load(
            self.preset, self.bin, self.lang, diagnostics=self.diag)
        self.speakers = load_speakers(self.preset)
        self.speaker_resolver = SpeakerResolver(self.speakers, diag=self.diag)
        self.conditions = ConditionCatalog.load(
            self.bin, self.lang, self.script_commands, self.text_compiler,
            diagnostics=self.diag)
        # 章节目录与时间线：URL slug 的唯一来源。build_slug_map 断言全局唯一
        # （撞车直接 raise，不再静默覆盖），main 族与 write_data 共用这一份。
        # 两处均经 self.table 取数：读取落进表登记簿，打烊对账可见（4.5-1）。
        self.story_lines = chapter_path.story_lines_from_tables(
            self.table('BIN', 'StoryLine'), self.table('LANG', 'StoryLine'))
        self.chapter_slugs = chapter_path.build_slug_map(self.table('BIN', 'StoryChapter'))

    # ------------------------------------------------------------- 表访问
    def table(self, scope, name):
        """scope ∈ {'BIN','LANG'}；懒加载 + 进程内缓存（缺文件返回 {}）。"""
        key = (scope, name)
        cached = self._tables.get(key, _MISSING)
        if cached is _MISSING:
            folder = self.bin if scope == 'BIN' else self.lang
            path = os.path.join(folder, name + '.json')
            if not os.path.exists(path):
                cached = {}
            else:
                with open(path, encoding='utf-8') as f:
                    cached = json.load(f)
            self._tables[key] = cached
        return cached

    def lang_table(self, scope, name):
        return self.table(scope, name)

    def rows(self, table):
        return rows_of(table)

    def field_lang(self, lang_table, row, field='Name'):
        return field_lang(lang_table, row, field)

    # ------------------------------------------------------- 剧本解析服务
    def script_commands(self, stem):
        """Parse one AVG script into an ordered [Command] list (stable idx identity)."""
        if stem in self._tag_cache:
            return self._tag_cache[stem]
        path = os.path.join(self.cfg, stem + '.lua')
        if not os.path.exists(path):
            self._tag_cache[stem] = None
            return None
        recs = parse_lua(open(path, encoding='utf-8').read(), stem)
        cmds = build_commands(recs)
        self._tag_cache[stem] = cmds
        return cmds

    def extract_script(self, stem):
        """Turn one AVG script into an ordered beat list with branch attribution."""
        cmds = self.script_commands(stem)
        if cmds is None:
            return None
        return extract_beats(cmds, self.speaker_resolver, self.text_compiler,
                             diag=self.diag, conditions=self.conditions, stem=stem or '')

    def character_name(self, cid):
        row = self.table('BIN', 'Character').get(str(cid))
        return field_lang(self.table('LANG', 'Character'), row) if row else ''

    def time_slots(self, chapter):
        """官方时段文案按章缓存（原 build_story.time_slots，_SLOTS 改实例级）。"""
        if self._slots is None:
            self._slots = collections.defaultdict(dict)
            bin_ts = self.table('BIN', 'StoryChapterTimeStamp')
            lang_ts = self.table('LANG', 'StoryChapterTimeStamp')
            for k in bin_ts:
                txt = lang_of(lang_ts, 'StoryChapterTimeStamp.%s.1' % k)
                if txt:
                    self._slots[int(k) // 100][int(k) % 100] = txt
        return self._slots.get(chapter, {})

    def resolved_tables(self):
        """本次构建经 table() 解析过的表（构建末端声明面对账用）。"""
        return frozenset(self._tables)


class UndeclaredTableError(RuntimeError):
    """族 build 解析了未在 NEEDS 声明的表（设计 4.5-1 运行时门控）。"""


class ScopedDataContext:
    """按族 NEEDS 白名单门控的 DataContext 包装器（设计 4.5-1 / R2）。

    - ``table`` / ``lang_table`` 都会解析表名，同样在门控范围内：透传
      lang_table 会直接凿穿门控，故不做透传；
    - 其余属性按 ``PASSTHROUGH`` 显式白名单透传（取代早期的全能
      ``__getattr__``）：名单来自 families + aggregate 的实际用法并集，
      DataContext 新增属性默认对族不可见——加面须有意识决定，读表者
      同步登记 SHARED_NEEDS；
    - 注意白名单内的惰性读表方法（``character_name`` / ``time_slots``）
      是绑定在全量 ctx 上的，其内部取数不经门控也不进 ``touched()``；
      这类读取由构建末端的打烊对账（resolved_tables ⊆ 全部声明面）兜底；
    - ``touched`` 记录本次门控解析到的表，供全量构建收尾输出
      declared-but-untouched 非阻塞 warning。
    """

    # 透传面显式白名单（设计 4.5-1 风险对策"仅透传列明属性"的落地）。
    # 刻意排除：bin/lang/preset/speakers/conditions/field_lang（全仓无消费方）。
    PASSTHROUGH = frozenset((
        'root', 'cfg', 'out', 'diag',                # 路径与诊断
        'text_compiler', 'speaker_resolver',         # 共享服务（急切构造）
        'story_lines', 'chapter_slugs',              # 急切构造的数据属性
        'script_commands', 'extract_script',         # 剧本解析（读 CFG 目录，非表）
        'character_name', 'time_slots',              # 惰性读表方法（表依赖在 SHARED_NEEDS）
        'rows',                                      # 纯函数便利面（吃已加载表）
    ))

    def __init__(self, ctx, needs):
        self._ctx = ctx
        self._needs = {(s, n) for s, n in needs}
        self.touched = set()

    def table(self, scope, name):
        key = (scope, name)
        if key not in self._needs:
            raise UndeclaredTableError(
                '族 NEEDS 未声明表 %s/%s：在族模块文件头补一行 NEEDS 后重跑' % (scope, name))
        self.touched.add(key)
        return self._ctx.table(scope, name)

    # lang_table 与 table 同门控（二者都解析表名）
    lang_table = table

    def untouched(self, needs):
        """声明了但本次构建未触发的表（非阻塞提示用）。"""
        return sorted({(s, n) for s, n in needs} - self.touched)

    def __getattr__(self, name):
        if name not in self.PASSTHROUGH:
            raise AttributeError(
                '%r 不在 ScopedDataContext 透传白名单：直接读表请走 table/lang_table '
                '并在族模块文件头声明 NEEDS；新共享面先评审加入 PASSTHROUGH'
                '（读表者同步 SHARED_NEEDS）' % name)
        return getattr(self._ctx, name)
