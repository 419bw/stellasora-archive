# -*- coding: utf-8 -*-
"""Render PageDoc as readable Markdown with adjacent nonempty text variants."""
from __future__ import annotations
from .markup import markdown as md, alternatives


def variant_lines(text, prefix=''):
    return [prefix + '- %s：「%s」' % (label, value)
            for label, value in alternatives(text)]


def beat_lines(beats):
    """One beat list -> markdown lines. Used by both the main and event writers."""
    lines = []
    for b in beats:
        k = b['k']
        if k == 'talk':
            if b.get('sticker'):
                lines.append("**%s**：〔发送表情 `%s`〕" % (b['speaker'], md(b['text'])))
            else:
                tag = "（思考）" if b['thought'] else ("（短信）" if b['channel'] == 'msg' else "")
                lines.append("**%s**%s：「%s」" % (b['speaker'], tag, md(b['text'])))
            extra = variant_lines(b['text'])
            if extra:
                lines += [''] + extra
        elif k == 'bubble':
            lines.append("**%s**（战斗气泡）：「%s」" % (b['speaker'], md(b['text'])))
            extra = variant_lines(b['text'])
            if extra:
                lines += [''] + extra
        elif k == 'wave':
            lines += ["", "> **[战斗阶段 %s]**" % b['no']]
        elif k == 'scene':
            bits = [x for x in (b['place'], b['date'], b['time']) if x]
            lines += ["", "> **【场景 · %s】**" % " · ".join(bits)]
        elif k == 'branch_open':
            lines += ["", "> **[若选「%s」↓]**" % md(b['option'])]
        elif k == 'merge':
            if b['forks'] > 1:
                mk = "> **[▲ 以上 %d 层嵌套抉择的 %d 条分支台词，到此统一汇合]**" % (b['forks'], b['count'])
            elif b['count'] == 1:
                mk = "> **[▲ 以上台词只出现在所选分支，其余选项直接进入下一段]**"
            else:
                mk = "> **[▲ 以上 %d 条分支互斥，自此汇合]**" % b['count']
            lines += ["", mk]
            if b['silent']:
                lines.append("> *（其中%s没有专属台词，选中即跳到汇合点）*" %
                             "、".join("「%s」" % md(s) for s in b['silent']))
        elif k == 'choice':
            label = {'major': '重大抉择', 'personality': '玩家抉择',
                     'generic': '玩家回应' if len(b['options']) == 1 else '抉择',
                     'phone': '通讯回复抉择'}[b['kind']]
            prompt = "：%s" % md(b['prompt']) if b['prompt'] else ""
            lines += ["", "> **[%s%s]**" % (label, prompt)]
            lines += variant_lines(b['prompt'], '> ')
            for t, d, _ev in b['options']:
                lines.append('> - **%s**%s' % (md(t), '：%s' % md(d) if d else ''))
                lines += variant_lines(t, '>   ')
                lines += variant_lines(d, '>   ')
        lines.append("")
    return lines


def page_markdown(doc):
    """Render page metadata, recap, dialogue and optional appendix."""
    lines = [doc.heading, "", "## 1. %s" % doc.info_title, *doc.info, ""]
    if doc.recap:
        lines += ["## 2. 官方跳过概要", "",
                  "> " + md(doc.recap).replace("<br>", "\n> "), ""]
    lines += ["## 3. " + doc.body_title, ""]
    lines += beat_lines(doc.beats)
    text = "\n".join(lines).rstrip() + "\n"
    if doc.appendix:
        a = doc.appendix
        text += ("\n\n## 4. %s\n\n> %s\n\n" % (a['title'], a['note'])
                 + "\n".join("> " + ln for ln in a['prose'].split("\n")) + "\n")
    return text
