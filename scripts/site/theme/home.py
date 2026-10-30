# -*- coding: utf-8 -*-
"""首页（Phase D1 从 site_templates.py 拆出，函数体逐字不动）。"""
import collections

from registry import FAMILIES, FAMILY_META, slug_of
from theme.layout import esc, layout


def home_page(pages, personality_data):
    counts = collections.Counter(p['family'] for p in pages)
    anecdote_notes = sum(p['counts'].get('anecdote', 0) for p in pages if p['family'] == 'anecdotes')
    lines = sum(p['counts'].get('talk', 0) + p['counts'].get('bubble', 0) for p in pages)
    
    bento_items = []
    ordered_families = sorted(FAMILIES, key=lambda x: FAMILY_META.get(x[0], {}).get('code', '99'))
    for f, n, _ in ordered_families:
        meta = FAMILY_META.get(f, {})
        cnt = counts.get(f, 0)
        slug = slug_of(f)
        cnt_text = ('%d 篇' % anecdote_notes) if f == 'anecdotes' and anecdote_notes else ('%d 篇' % cnt)
        bento_items.append("""<li class="bento-item %s">
<article class="bento-card" data-slug="%s">
  <a class="bento-card-link" href="%s/index.html" aria-label="%s"></a>
  <div class="bento-top">
    <span class="bento-num">%s</span>
  </div>
  <div class="bento-body">
    <h3 class="bento-title">%s</h3>
    <p class="bento-desc">%s</p>
  </div>
  <div class="bento-foot">
    <span class="bento-count">%s</span>
    <span class="bento-arrow">→</span>
  </div>
</article></li>""" % (
            meta.get('span', ''), slug, slug, esc(n),
            meta.get('code', '00'),
            esc(n), meta.get('desc', ''), cnt_text
        ))

    return layout('首页', """
<div class="hero">
  <h1 class="hero-title">星塔旅人 剧情档案</h1>
  <p class="hero-desc">官方剧本全文、分支抉择与关卡拓扑。</p>
  <div class="hero-badge-wrap">
    <a class="hero-update-pill" href="#updates">
      <span class="pill-dot"></span>
      <span class="pill-date">2026-10-30</span>
      <span class="pill-sep">·</span>
      <span class="pill-text">上次更新：上游数据与剧本文案修正</span>
      <span class="pill-arrow">↓</span>
    </a>
  </div>
  
  <div class="hero-notice-banner">
    <div class="notice-pill notice-spoiler">
      <span class="notice-tag tag-spoiler">剧透提醒</span>
      <span class="notice-msg">本站默认完整展开所有主线及活动的分支抉择与结局走向，包含全流程剧透，请谨慎阅读。</span>
    </div>
    <div class="notice-pill notice-scope">
      <span class="notice-tag tag-scope">收录说明</span>
      <span class="notice-msg">游戏内仅有 CG 动画演示而无文本字幕的片段不会出现在这里，本站仅收录官方剧本中有台词文本的剧情；角色图鉴、剧情立绘与音频、养成数据等本站未收录的资料，可参考下方「相关站点」。</span>
    </div>
    <div class="notice-pill notice-links">
      <span class="notice-tag tag-links">相关站点</span>
      <span class="notice-msg"><a href="https://www.gamekee.com/stellasora/" target="_blank" rel="noopener noreferrer">星塔旅人 Wiki</a>（Gamekee 中文站，综合攻略与玩家社区） · <a href="https://stellasora.miraheze.org/wiki/Stella_Sora_Wiki" target="_blank" rel="noopener noreferrer">Stella Sora Wiki</a>（Miraheze 英文站，全面收录官方素材）。</span>
    </div>
  </div>
  
  <div class="searchbox hero-search">
    <div class="search-input-wrap">
      <svg class="search-icon" viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
      <input type="search" placeholder="检索剧情标题、概要、说话人、关卡代号…" data-scope="_all" data-root="">
    </div>
    <div class="results" hidden></div>
  </div>
</div>

<ul class="bento tiles">
  %s
</ul>

<section class="update-section" id="updates">
  <div class="update-card">
    <div class="update-header">
      <div class="update-title">
        <svg class="update-icon" viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
        <span>最近更新</span>
      </div>
      <div class="update-date-badge">
        <span class="dot"></span>
        <span>更新时间：2026-10-30</span>
      </div>
    </div>
    <div class="update-summary">上游数据与剧本文案修正</div>
  </div>
</section>
""" % ''.join(bento_items), 0, '')
