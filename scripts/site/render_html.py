# -*- coding: utf-8 -*-
"""管线 Stage 5b: HTML 后端 —— PageDoc 侧车（story_docs/_beats/*.json）→ HTML 正文片段。

与 scripts/story/pipeline/render_md.py（Markdown 后端）平行，共同消费同一份
beat IR。本模块从 beat/PageDoc 字段直接构造 HTML，不再经 md 文本正则反解
（取代已删除的 md2html.py）。

输入 doc 为侧车 dict（== pipeline.pagedoc.PageDoc.to_dict() 形状）：
    heading / info_title / info / recap / body_title / meta / appendix / beats
beat 词汇表（passes.extract_beats 产物，键与取值是契约）：
    talk{speaker,text,thought,sticker,channel}  bubble{speaker,text}
    wave{no}  scene{place,date,time}  branch_open{option}
    merge{count,forks,silent}  choice{kind,prompt,options[(t,d,ev)]}

行为与原 md2html.convert(md) 逐字节等价（507 页全量对拍 + 黄金快照门控）。
保留的结构语义（契约 M3，见 _dev/AI_HANDOVER_GUIDE.md 3.5）：
- choice cid 按文档序自增，锚点 choice-{cid} / branch-{cid}-{b_idx} / merge-{cid}；
- 若选归属：帧栈自内向外按选项名（_clean_opt 归一）匹配，无匹配回退栈顶；
- 单选项父抉择的若选整体抑制（上游 CG_126_03 的 SetChoiceEnd 错配），不画
  分支框、不画导航条，选项角标同样跳过被抑制分支；
- 分支导航条在：下一个若选、▲汇合、正文结束（backlog 关闭）处闭合；
- 重大抉择的「分支走向」角标按选项名匹配 branch_targets（build_site 提供）。

md 时代按引文组（quote group）聚合的逻辑在此天然简化：render_md 给每个
引文 beat 前后都留空行，所以一个引文组恰好等于一个 beat（merge 的静默
附注与 choice 的选项行同组），逐 beat 直渲即为原分组语义。

Usage: body, stats = render_body(doc, branch_targets=None)
"""
import os
import re
import sys
from html import escape

# markup 编译器住在剧情管线包里（scripts/story/pipeline/markup.py）；build_site
# 已把 scripts/story 注入 sys.path（graph_layout/release_gate 同此先例），这里
# 兜底保证本模块可独立导入（对拍脚本、pytest）。
_STORY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'story')
if _STORY_DIR not in sys.path:
    sys.path.insert(0, _STORY_DIR)
from pipeline import markup  # noqa: E402

META = re.compile(r'^- \*\*(.+?)\*\*：(.*)$')

BACKLOG_OPEN = ('<div class="backlog-board"><div class="backlog-header">'
                '<div class="backlog-title">'
                '<svg class="backlog-pin" viewBox="0 0 24 24" width="15" height="15" fill="currentColor">'
                '<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>'
                '</svg><span>紀錄</span></div>'
                '<span class="backlog-close">✕</span></div>'
                '<div class="backlog-body">')

CHOICE_LABEL = {'major': '重大抉择', 'personality': '玩家抉择', 'phone': '通讯回复抉择'}


def _inline(s):
    """Ruby, then bold and code spans; the story text itself is never markup."""
    s = ruby_html(s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s)
    return s


def ruby_html(text):
    """Escape a run of story text, turning <r=注音></r> into native <ruby>.

    实现委托给管线 markup 编译器（Phase 3）：parse_inline 把注音锚定到标签前
    一个字符（魔<r=mowang></r>王），serialize_html 输出原生 <ruby><rt>，无需
    任何 CSS。前导 ruby（无 base 字符）抛 markup.MarkupError —— 契约 M 会先
    拦住这种数据。"""
    return markup.serialize_html(markup.parse_inline(text))


def _clean_opt(s):
    # Strip rubies, html tags, ellipses, and whitespace for robust option-to-branch matching
    s = re.sub(r'<[^>]*>', '', s)
    return re.sub(r'[.…—\s　]', '', s)


def _branch_nav_html(choice_id, merge_id):
    merge_btn = ''
    if merge_id:
        merge_btn = (
            f'<a class="branch-nav-btn to-merge" href="#{merge_id}" title="跳过其它互斥分支，前往剧情汇合处">'
            f'<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2">'
            f'<path d="M12 5v14M19 12l-7 7-7-7"/>'
            f'</svg><span>跳到汇合</span></a>'
        )
    return (
        f'<div class="branch-nav">'
        f'<a class="branch-nav-btn to-choice" href="#{choice_id}" title="回到抉择选项位置">'
        f'<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2">'
        f'<path d="M12 19V5M5 12l7-7 7 7"/>'
        f'</svg><span>返回抉择</span></a>'
        f'{merge_btn}'
        f'</div>'
    )


def choice_tag(b):
    """choice beat → 标记文本（与 render_md 的 label+prompt 拼接一致）。"""
    if b['kind'] == 'generic':
        label = '玩家回应' if len(b['options']) == 1 else '抉择'
    else:
        label = CHOICE_LABEL[b['kind']]
    return "%s：%s" % (label, b['prompt']) if b['prompt'] else label


def merge_tag(b):
    """merge beat → ▲ 标记文本（与 render_md 的三种形态一致）。"""
    if b['forks'] > 1:
        return '▲ 以上 %d 层嵌套抉择的 %d 条分支台词，到此统一汇合' % (b['forks'], b['count'])
    if b['count'] == 1:
        return '▲ 以上台词只出现在所选分支，其余选项直接进入下一段'
    return '▲ 以上 %d 条分支互斥，自此汇合' % b['count']


def _parse_choice_structure(beats):
    """beat 流 → (choices, branches, merges)，与原 md2html._parse_choice_structure
    对 md 引文行的扫描逐字段等价（cid 文档序自增、若选按选项名归属、
    层嵌套抉择整栈闭合、单选项父抉择 single_parent 标记）。"""
    choices = []
    branches = []
    merges = []
    stack = []
    cid = 0

    for b in beats:
        k = b['k']
        if k == 'choice':
            cid += 1
            c_info = {
                'cid': cid,
                'choice_id': f'choice-{cid}',
                'options': [t for t, d, ev in b['options']],
                'branches': [],
                'merge_id': None,
            }
            choices.append(c_info)
            stack.append(c_info)
        elif k == 'branch_open':
            opt_name = b['option']
            # The generator attributes a branch to the choice its option name
            # belongs to (the frame its jump entered), which is not always the
            # most recently opened one — e.g. a 玩家回应 opened inside branch
            # content carries no jump of its own. Match by option name from the
            # innermost frame outward, falling back to the previous stack-top rule.
            parent_c = None
            for fr in reversed(stack):
                if any(_clean_opt(o) == _clean_opt(opt_name) for o in fr['options']):
                    parent_c = fr
                    break
            if parent_c is None and stack:
                parent_c = stack[-1]
            # A choice that offers only one option is not a fork at all: the game
            # cannot branch there, so its 若选 markers are pure presenter noise.
            # See _dev/AI_HANDOVER_GUIDE.md 3.5 — upstream CG_126_03.lua closes choice
            # group a_10 with a_4's SetChoiceEnd, leaving the frame live and making
            # the generator re-emit the same 若选 for every later beat. Rendering it
            # as a branch box would show a "fork" that does not exist, so such a
            # marker is rendered as plain dialogue instead.
            single_parent = bool(parent_c) and len(parent_c['options']) <= 1
            b_idx = len(parent_c['branches']) if parent_c else len(branches)
            c_id_num = parent_c['cid'] if parent_c else 0
            b_info = {
                'bid': f'branch-{c_id_num}-{b_idx}',
                'b_idx': b_idx,
                'opt_name': opt_name,
                'parent_cid': c_id_num,
                'choice_id': parent_c['choice_id'] if parent_c else f'choice-{c_id_num}',
                'single_parent': single_parent,
            }
            branches.append(b_info)
            if parent_c:
                parent_c['branches'].append(b_info)
        elif k == 'merge':
            mid = f'merge-{cid}'
            if stack:
                if b['forks'] > 1:      # 「层嵌套抉择」：整栈统一闭合
                    mid = f'merge-{stack[0]["cid"]}'
                    while stack:
                        sc = stack.pop()
                        sc['merge_id'] = mid
                else:
                    # the merge arrives when the fork structure rejoins, so it
                    # closes the innermost frame that actually owns branches —
                    # a forked-over 玩家回应 frame on top must not steal it
                    sc = next((fr for fr in reversed(stack) if fr['branches']), stack[-1])
                    stack.remove(sc)
                    mid = f'merge-{sc["cid"]}'
                    sc['merge_id'] = mid
            merges.append({'merge_id': mid})

    for br in branches:
        c = next((x for x in choices if x['cid'] == br['parent_cid']), None)
        br['merge_id'] = c['merge_id'] if c else None

    return choices, branches, merges


def render_body(doc, branch_targets=None):
    """Render one PageDoc sidecar dict to the story-body HTML fragment.

    branch_targets: list (document order) of 重大抉择 groups; each group is a list of
    {'opt', 'code', 'title', 'url', 'cls', 'tag'} targets keyed by the option text the
    target belongs to (built by build_site from the option jump EvIds).
    """
    beats = doc['beats']
    choices, branches, merges = _parse_choice_structure(beats)
    choice_iter = iter(choices)
    branch_iter = iter(branches)
    merge_iter = iter(merges)

    out = []
    stats = {'line': 0, 'marker': 0, 'scene': 0, 'choice': 0, 'meta': 0}
    active_branch = None
    # branch_targets is a list of per-major-choice target groups (document order);
    # within a group each target carries the option text it belongs to.
    major_choice_seq = [0]

    def close_active_branch():
        nonlocal active_branch
        if active_branch:
            out.append(_branch_nav_html(active_branch['choice_id'], active_branch.get('merge_id')))
            active_branch = None

    # ---- H1 ----
    out.append('<h1>%s</h1>' % escape(doc['heading'][2:]))

    # ---- 1. 信息节 ----
    out.append('<h2 data-part="1">%s</h2>' % escape(doc['info_title']))
    for ln in doc['info']:
        m = META.match(ln)
        if m:
            k, v = m.groups()
            # the label's own colon comes from CSS, so drop the one in the text
            out.append('<p class="meta"><b>%s</b>%s</p>' % (escape(k), _inline(v.lstrip('：'))))
            stats['meta'] += 1
        else:
            out.append('<p>%s</p>' % _inline(ln))

    # ---- 2. 官方跳过概要（可缺省）----
    if doc['recap']:
        out.append('<h2 data-part="2">官方跳过概要</h2>')
        out.append('<blockquote>%s</blockquote>'
                   % ''.join('<p>%s</p>' % _inline(ln.strip())
                             for ln in doc['recap'].split('\n')))

    # ---- 3. 正文（backlog 板）----
    out.append('<h2 data-part="3">%s</h2>' % escape(doc['body_title']))
    out.append(BACKLOG_OPEN)

    for b in beats:
        k = b['k']
        if k == 'talk':
            if b.get('sticker'):
                out.append('<p class="line sticker"><b class="who">%s</b>'
                           '<span class="say">〔发送表情 <code>%s</code>〕</span></p>'
                           % (escape(b['speaker']), escape(b['text'])))
            else:
                tag = '思考' if b['thought'] else ('短信' if b['channel'] == 'msg' else None)
                cls = 'line'
                if b['speaker'] == '旁白':
                    cls += ' narrator'
                if tag:
                    cls += ' thought' if tag == '思考' else (' chat' if tag == '短信' else ' bubble')
                out.append('<p class="%s"><b class="who">%s%s</b><span class="say">「%s」</span></p>'
                           % (cls, escape(b['speaker']),
                              '<i class="tag">%s</i>' % escape(tag) if tag else '',
                              ruby_html(b['text'])))
            stats['line'] += 1
        elif k == 'bubble':
            cls = 'line bubble'
            if b['speaker'] == '旁白':
                cls = 'line narrator bubble'
            out.append('<p class="%s"><b class="who">%s<i class="tag">战斗气泡</i></b>'
                       '<span class="say">「%s」</span></p>'
                       % (cls, escape(b['speaker']), ruby_html(b['text'])))
            stats['line'] += 1
        elif k == 'scene':
            bits = [x for x in (b['place'], b['date'], b['time']) if x]
            out.append('<aside class="scene">%s</aside>' % escape('场景 · ' + ' · '.join(bits)))
            stats['scene'] += 1
        elif k == 'wave':
            out.append('<p class="wave">%s</p>' % escape('战斗阶段 %s' % b['no']))
            stats['marker'] += 1
        elif k == 'branch_open':
            b_obj = next(branch_iter, None)
            if b_obj and b_obj.get('single_parent'):
                # single-option parent: the 若选 line is not a branch header.
                # Drop it (and its 返回抉择/跳到汇合 nav bar) so the dialogue
                # simply continues; the iterator is consumed to keep every
                # later branch aligned. Compromise for the upstream
                # CG_126_03 SetChoiceEnd mix-up, see _dev/AI_HANDOVER_GUIDE.md 3.5.
                continue
            close_active_branch()
            bid_attr = f' id="{b_obj["bid"]}"' if b_obj else ''
            out.append('<p class="branch-open"%s>%s</p>'
                       % (bid_attr, escape('若选「%s」↓' % b['option'])))
            stats['marker'] += 1
            if b_obj:
                active_branch = {
                    'choice_id': b_obj['choice_id'],
                    'merge_id': b_obj.get('merge_id'),
                }
        elif k == 'merge':
            close_active_branch()
            m_obj = next(merge_iter, None)
            mid_attr = f' id="{m_obj["merge_id"]}"' if m_obj else ''
            out.append('<p class="merge"%s>%s</p>' % (mid_attr, escape(merge_tag(b))))
            stats['marker'] += 1
            if b['silent']:
                out.append('<p class="note">%s</p>'
                           % escape('（其中%s没有专属台词，选中即跳到汇合点）'
                                    % '、'.join('「%s」' % s for s in b['silent'])))
        elif k == 'choice':
            tag_content = choice_tag(b)
            is_major = b['kind'] == 'major'
            c_obj = next(choice_iter, None)
            if b['kind'] == 'generic' and len(b['options']) == 1:
                # 玩家回应：单选项通用回应渲染为聊天气泡（a bare marker has no
                # lead-in; the prompt form carries the fixed first half of the
                # player's reply, kept as a muted line in the bubble）
                lead = tag_content[len('玩家回应'):].lstrip('：').strip()
                resp_items = []
                if lead:
                    resp_items.append('<p class="reply-lead">%s</p>' % _inline(lead))
                for t, d, ev in b['options']:
                    line_text = '<b>%s</b>%s' % (escape(t), _inline('：' + d if d else ''))
                    resp_items.append('<p>%s</p>' % line_text)
                id_attr = ' id="%s"' % c_obj['choice_id'] if c_obj and c_obj.get('choice_id') else ''
                out.append('<div class="player-reply"%s><div class="reply-who">魔王 选择了</div>'
                           '<div class="reply-body">%s</div></div>'
                           % (id_attr, ''.join(resp_items)))
                stats['choice'] += 1
                continue
            cls = 'choice major-choice' if is_major else 'choice'
            cid_attr = f' id="{c_obj["choice_id"]}"' if c_obj else ''
            out.append('<p class="%s"%s>%s</p>' % (cls, cid_attr, escape(tag_content)))
            stats['marker'] += 1
            c_targets = None
            if is_major:
                if branch_targets and major_choice_seq[0] < len(branch_targets):
                    c_targets = branch_targets[major_choice_seq[0]]
                major_choice_seq[0] += 1
            opts = []
            # suppressed branches point at anchors that are never rendered,
            # so the option badges must ignore them (single-option parent)
            c_branches = [br for br in c_obj['branches'] if not br.get('single_parent')] if c_obj else []
            c_merge_id = c_obj.get('merge_id') if c_obj else None

            for t, d, ev in b['options']:
                # badge follows the option by name: several options may share
                # one branch level, so index-based matching cannot be right
                tgt = None
                if c_targets:
                    clean_w = _clean_opt(t)
                    for cand in c_targets:
                        if clean_w == _clean_opt(cand.get('opt') or ''):
                            tgt = cand
                            break
                target_badge = ''
                if tgt and tgt.get('url'):
                    target_badge = ('<a class="opt-target" href="%s" title="前往对应分支关卡">'
                                    '<span>分支走向</span><strong>%s %s →</strong></a>'
                                    % (escape(tgt['url']), escape(tgt['code']), escape(tgt['title'])))

                target_anchor = None
                jump_badge = ''
                if c_branches:
                    matched_b = None
                    clean_w = _clean_opt(t)
                    for br in c_branches:
                        clean_b = _clean_opt(br['opt_name'])
                        if clean_w == clean_b or clean_w.startswith(clean_b) or clean_b.startswith(clean_w):
                            matched_b = br
                            break
                    if matched_b:
                        target_anchor = f"#{matched_b['bid']}"
                        jump_badge = '<span class="opt-jump-badge">跳转分支 ↓</span>'
                    elif c_merge_id:
                        target_anchor = f"#{c_merge_id}"
                        jump_badge = '<span class="opt-jump-badge is-merge">直接汇合 ↓</span>'
                elif c_merge_id:
                    target_anchor = f"#{c_merge_id}"
                    jump_badge = '<span class="opt-jump-badge is-merge">直接汇合 ↓</span>'

                opt_text_html = '<div class="opt-main"><b>%s</b>%s</div>' % (escape(t), _inline('：' + d if d else ''))
                if target_anchor:
                    title_tip = '点击直接跳转至剧情汇合处' if 'is-merge' in jump_badge else '点击跳转至分支台词'
                    item_inner = (
                        f'<a class="opt-link" href="{target_anchor}" title="{title_tip}">'
                        f'{opt_text_html}{jump_badge}</a>{target_badge}'
                    )
                    opts.append(f'<li class="has-jump">{item_inner}</li>')
                else:
                    opts.append(f'<li>{opt_text_html}{target_badge}</li>')

            opts_cls = 'options major-options' if is_major else 'options'
            out.append('<ul class="%s">%s</ul>' % (opts_cls, ''.join(opts)))
            stats['choice'] += 1

    # ---- 正文结束：关闭 backlog 板（附录 h2 与 EOF 在 md2html 里输出相同）----
    close_active_branch()
    out.append('</div></div>')

    # ---- 4. 附录（当前唯一使用方：唱片散文）----
    a = doc.get('appendix')
    if a:
        out.append('<h2 data-part="4">%s</h2>' % escape(a['title']))
        out.append('<blockquote><p>%s</p></blockquote>' % _inline(a['note'].strip()))
        out.append('<blockquote>%s</blockquote>'
                   % ''.join('<p>%s</p>' % _inline(ln.strip())
                             for ln in a['prose'].split('\n')))

    return '\n'.join(out), stats
