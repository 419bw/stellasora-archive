# -*- coding: utf-8 -*-
"""管线 Stage 4b: Markdown 后端 —— PageDoc → md 文本（人审真源）。

自 build_story.py 的 render_beats/section_doc（+ build_discs 内联的唱片附文
拼接）原样迁出（Phase 1d），逐行为等价。md 行格式是契约 A–F/I/M3 的对照
真源与 validate_story/validate_site 的扫描对象，任何改动必须过黄金对拍。

HTML 后端（scripts/site/render_html.py，Phase 2）与本模块平行，两者共同
消费 PageDoc/beat IR；beat 渲染逻辑如需变更，必须双后端同步。
"""
from __future__ import annotations


def beat_lines(beats):
    """One beat list -> markdown lines. Used by both the main and event writers."""
    lines = []
    for b in beats:
        k = b['k']
        if k == 'talk':
            if b.get('sticker'):
                lines.append("**%s**：〔发送表情 `%s`〕" % (b['speaker'], b['text']))
            else:
                tag = "（思考）" if b['thought'] else ("（短信）" if b['channel'] == 'msg' else "")
                lines.append("**%s**%s：「%s」" % (b['speaker'], tag, b['text']))
        elif k == 'bubble':
            lines.append("**%s**（战斗气泡）：「%s」" % (b['speaker'], b['text']))
        elif k == 'wave':
            lines += ["", "> **[战斗阶段 %s]**" % b['no']]
        elif k == 'scene':
            bits = [x for x in (b['place'], b['date'], b['time']) if x]
            lines += ["", "> **【场景 · %s】**" % " · ".join(bits)]
        elif k == 'branch_open':
            lines += ["", "> **[若选「%s」↓]**" % b['option']]
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
                             "、".join("「%s」" % s for s in b['silent']))
        elif k == 'choice':
            label = {'major': '重大抉择', 'personality': '玩家抉择',
                     'generic': '玩家回应' if len(b['options']) == 1 else '抉择',
                     'phone': '通讯回复抉择'}[b['kind']]
            prompt = "：%s" % b['prompt'] if b['prompt'] else ""
            lines += ["", "> **[%s%s]**" % (label, prompt)]
            lines += ["> - **%s**%s" % (t, "：%s" % d if d else "") for t, d, _ev in b['options']]
        lines.append("")
    return lines


def page_markdown(doc):
    """Shared page skeleton for every story family（原 section_doc + 唱片附文）。

    The skip recap is authored inside the script (SetIntro[3], with ==RT== as the line
    break); the stage table's Desc is a one-line flavour hint and is not the recap.
    """
    lines = [doc.heading, "", "## 1. %s" % doc.info_title, *doc.info, ""]
    if doc.recap:
        lines += ["## 2. 官方跳过概要", "",
                  "> " + doc.recap.replace("\n", "\n> "), ""]
    lines += ["## 3. " + doc.body_title, ""]
    lines += beat_lines(doc.beats)
    text = "\n".join(lines).rstrip() + "\n"
    if doc.appendix:
        a = doc.appendix
        text += ("\n\n## 4. %s\n\n> %s\n\n" % (a['title'], a['note'])
                 + "\n".join("> " + ln for ln in a['prose'].split("\n")) + "\n")
    return text
