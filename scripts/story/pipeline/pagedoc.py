# -*- coding: utf-8 -*-
"""管线 Stage 4a: PageDoc IR —— 单页文档结构（md/HTML 双后端共同输入）。

一个 PageDoc = 一页剧情档案的完整文档结构：
    heading      H1 行（含 '# ' 前缀）
    info         信息条目行（md 列表项，含 '- ' 前缀），第 1 节内容
    recap        渲染用跳过概要（可为 ''；家族 builder 已做完回退选择，
                 如主线用 meta.recap or hint）
    body_title   第 3 节标题（"逐句台词" / "战斗内气泡对白（…）"）
    beats        beat IR 列表（passes.extract_beats 产物；md/HTML 双后端与
                 sections.json 的共同上游，键与取值是契约）
    info_title   第 1 节标题（"关卡信息" / "剧情档案信息" / …）
    meta         剧本原始 meta {'recap','episode','title'}——sections.json 的
                 recap 字段取这里的原始值，与渲染用的 recap（含回退）区分
    appendix     可选附文节（当前唯一使用方：唱片散文），{'title','note','prose'}

落盘：story_docs/_beats/<page 的 .html 换 .json>，随 git 提交；
Phase 2 起 scripts/site/render_html.py 直接从此侧车渲染 HTML，
Markdown 由 pipeline/render_md.py 渲染（人审真源，永久保留）。
"""
from __future__ import annotations


class PageDoc:
    __slots__ = ('heading', 'info', 'recap', 'body_title', 'beats',
                 'info_title', 'meta', 'appendix')

    def __init__(self, heading, info, recap, body_title, beats,
                 info_title="关卡信息", meta=None, appendix=None):
        self.heading = heading
        self.info = list(info)
        self.recap = recap
        self.body_title = body_title
        self.beats = beats
        self.info_title = info_title
        self.meta = meta if meta is not None else {'recap': '', 'episode': '', 'title': ''}
        self.appendix = appendix

    # ---- 侧车序列化（story_docs/_beats/*.json） ----
    def to_dict(self):
        """JSON 友好的纯结构。beat 内 options 元组序列化为数组；
        读回（from_dict）后为列表，双后端按序解包 (t, d, ev)，两种容器等价。"""
        return {
            'heading': self.heading,
            'info_title': self.info_title,
            'info': self.info,
            'recap': self.recap,
            'body_title': self.body_title,
            'meta': self.meta,
            'appendix': self.appendix,
            'beats': self.beats,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(d['heading'], d['info'], d['recap'], d['body_title'],
                   d['beats'], info_title=d.get('info_title', '关卡信息'),
                   meta=d.get('meta'), appendix=d.get('appendix'))
