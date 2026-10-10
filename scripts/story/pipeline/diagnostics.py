# -*- coding: utf-8 -*-
"""降级兜底的统一登记处 —— Phase 3 诊断侧车（story_docs/_diagnostics.json）的唯一收集器。

纪律（详见 _dev/AI_HANDOVER_GUIDE.md「兜底与诊断策略」）：
  1. **降级不崩**：解析/渲染路径遇到上游脏数据时产出可读结果，绝不向上抛异常。
     `scripts/automation/auto_sync.py` 以 `check=True` 跑 build，一崩定时同步就全停。
  2. **必登记**：每一次降级都必须经过 `Diagnostics.add()/bump()/extend()` 登记；
     只打 logger/print 的告警**不算**登记（log 给人看，侧车给审 diff 的人）。
  3. **分类必须进注册表**：`CATEGORIES` 是唯一真源，未注册的分类名直接 `KeyError`，
     把"新增兜底忘记写说明"变成开发期的显性失败，而不是运行期的静默通道。

本模块不碰文件系统、不依赖管线其他模块（无环），可被任意层注入。
"""
import logging

logger = logging.getLogger(__name__)

# 分类注册表：键名 -> (shape, 一句话口径说明)。
# shape: 'list' = 去重条目列表（按去重键排序）；'count' = 计数（可按 key 去重）。
# 顶层键名与顺序即 _diagnostics.json 的输出顺序，新增分类只能追加，不得重排——
# 重排会让整个人审 diff 变成噪声。所有分类永远出现在输出里（空列表 [] / 计数 0）。
CATEGORIES = {
    'code_mismatches': ('list', '官方显示代号与自身 StoryId 编号交叉（上游笔误）'),
    'battle_bubble_missing': ('list', '关卡表有行、包内暂无气泡剧本'),
    'unattached_bbm_scripts': ('list', '没有任何关卡表引用的 BBm 剧本'),
    'rows_without_script': ('list', '关卡表已列出、包内无剧本的关卡行（未开放线路）'),
    'speaker_prefix_fallbacks': ('list', '预置表未收录、按最长点分前缀归位的说话人键'),
    'speaker_inline_names': ('count', '剧本把显示名直接写在 speaker 字段的去重 sid 数（正常行为）'),
    'choice_frame_anomalies': ('list', '抉择关闭指令的 group 找不到活跃帧'),
    'emph_tags_preserved': ('count', '成对保留的 <b>/<i> 强调标记数'),
    'orphan_emph_tags_stripped': ('count', '孤儿强调标记被剥离的数（只丢标记不丢字）'),
    # ---- 本次新增 ----
    'unknown_control_markers': ('list', '正文里无法识别的 ==XXX== 控制标记，按原文保留'),
    'unknown_preset_words': ('list', '正文里无法识别的 $nnnn 词条，按原文保留'),
    'bubble_stem_display_code_fallback': ('count', 'StoryId 尾部非 BTnn、按显示代号拼气泡剧本名的关卡行数'),
    'condition_story_unknown': ('list', '条件标签引用的 StoryId 在 Story 表查不到，标签退回原始 id'),
    'condition_unlock_unknown': ('list', '条件标签引用的 ConditionId 在 StoryCondition 表查不到'),
    'condition_evidence_unknown': ('list', '条件标签引用的 EvId 在 StoryEvidence 表查不到'),
    'condition_achievement_unknown': ('list', 'AchieveIds 里的成就在 Achievement 表查不到'),
    'condition_choice_frame_missing': ('list', '历史条件找不到对应的 SetMajorChoice/SetPersonalityChoice 指令'),
    'condition_choice_option_missing': ('list', '历史条件的选项序号越界或为空，该项已跳过'),
    'condition_be_case_unknown': ('list', 'CheckBE/CheckBECase 解析异常：档位号越界、章号查不到、组内 range 不一致'),
    'condition_row_malformed': ('list', 'Story/StoryCondition/StoryEvidence 行结构异常（缺主键或字段类型不符），已跳过'),
}


def warn(msg):
    """统一告警出口：与 _diagnostics.json 登记配套，给跑构建的人看。"""
    logger.warning(msg)


class Diagnostics:
    """进程内单例收集器：去重列表 + 去重计数，输出字节稳定。

    `add()` 的 key 必须包含足以区分条目的全部维度（可排序 tuple）；同一 key 重复
    登记只留第一条，因此反复解析同一剧本不会让侧车膨胀。计数类若给 key 则按 key
    去重（如 speaker_inline_names 数的是去重 sid，不是出现次数）。
    """

    def __init__(self):
        self._lists = {}      # category -> {key: payload}
        self._counts = {}     # category -> {key: n} 或 {'': n}

    # ---------------------------------------------------------------- 内部
    def _shape(self, category):
        try:
            return CATEGORIES[category][0]
        except KeyError:
            raise KeyError('未注册的诊断分类 %r：请先加进 pipeline.diagnostics.CATEGORIES'
                           % (category,)) from None

    # ---------------------------------------------------------------- 写入
    def add(self, category, key, **fields):
        """登记一条列表类条目。key 为可排序 tuple，fields 即落盘字段。重复返回 False。"""
        if self._shape(category) != 'list':
            raise TypeError('%r 是计数类分类，请用 bump()' % (category,))
        bucket = self._lists.setdefault(category, {})
        if key in bucket:
            return False
        bucket[key] = dict(fields)
        return True

    def add_value(self, category, value):
        """登记一条标量列表类条目（如未挂载的剧本名），条目本身就是值。"""
        return self._add_scalar(category, value)

    def _add_scalar(self, category, value):
        if self._shape(category) != 'list':
            raise TypeError('%r 是计数类分类，请用 bump()' % (category,))
        bucket = self._lists.setdefault(category, {})
        if (value,) in bucket:
            return False
        bucket[(value,)] = value
        return True

    def extend(self, category, values):
        """批量登记标量列表类条目（去重 + 排序在 as_dict 输出时统一做）。"""
        return sum(1 for v in values if self._add_scalar(category, v))

    def bump(self, category, n=1, key=None):
        """计数类累计。

        不给 key：纯累加（如强调标记数，同一进程内多次解析要相加）。
        给 key：按 key 去重（同一 key 只计一次，不计出现次数）——用于"数的是去重
        对象数"的场合，如 speaker_inline_names 数的是去重 sid。
        """
        if self._shape(category) != 'count':
            raise TypeError('%r 是列表类分类，请用 add()' % (category,))
        bucket = self._counts.setdefault(category, {})
        if key is None:
            bucket[''] = bucket.get('', 0) + n
            return bucket['']
        if key in bucket:                 # 去重键已计过：不重复累计
            return bucket[key]
        bucket[key] = n
        return n

    # ---------------------------------------------------------------- 读取
    def count(self, category):
        """计数类当前值（未登记过返回 0）。"""
        self._shape(category)
        return sum(self._counts.get(category, {}).values())

    def entries(self, category):
        """列表类条目，按去重键排序的副本。"""
        self._shape(category)
        return [dict(v) if isinstance(v, dict) else v
                for _k, v in sorted(self._lists.get(category, {}).items())]

    def as_dict(self):
        """按 CATEGORIES 声明序输出整份侧车 payload（不含 note）。"""
        out = {}
        for name, (shape, _desc) in CATEGORIES.items():
            out[name] = self.count(name) if shape == 'count' else self.entries(name)
        return out

    def note(self):
        """由注册表生成的口径说明，取代原先手抄的长 prose（防文案与代码漂移）。"""
        specs = '；'.join('%s=%s' % (name, desc) for name, (_s, desc) in CATEGORIES.items())
        return ('上游数据异常与编译器兜底的机器可读登记（build_story 生成，只记录、不改变任何行为）。'
                '人读版见 _battle_reconciliation.md 与 _dev/AI_HANDOVER_GUIDE.md「兜底与诊断策略」。'
                '各分类口径：%s。'
                'list 分类按去重键排序、同键只留一条；count 分类为本次构建的累计计数'
                '（给过去重键的按 key 去重，如 speaker_inline_names 数的是去重 sid）。' % specs)

    def nonzero(self):
        """非零分类 -> 数值/条数，供构建摘要打印。"""
        out = {}
        for name, (shape, _desc) in CATEGORIES.items():
            value = self.count(name) if shape == 'count' else len(self.entries(name))
            if value:
                out[name] = value
        return out

    def __bool__(self):
        return bool(self.nonzero())

    def __repr__(self):
        return 'Diagnostics(%s)' % ', '.join('%s=%s' % kv for kv in sorted(self.nonzero().items()))
