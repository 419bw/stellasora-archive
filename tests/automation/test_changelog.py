# -*- coding: utf-8 -*-
"""Unit tests for the changelog logic in scripts/automation/auto_sync.py.

Covers the fix for the analyze_diff() top-level-keys bug (it used to diff
{'meta','pages'} keys, so additions were always empty) and the D1/D2/D3
changelog redesign:

  * new sections are detected on the pages list, keyed by (family, id);
  * the reason is collapsed into a single one-line sentence;
  * the homepage gets date + pill-text + update-summary (no update-list);
  * README holds the full commit list but keeps ONLY the newest dated entry
    (older entries are dropped on purpose, so the log never grows);
  * an explicit note (--note / STELLA_SYNC_NOTE) overrides the auto reason.

Network-free: builds small sections.json fixtures and temp template/README files.
"""
import importlib.util
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODULE_PATH = os.path.join(ROOT, 'scripts', 'automation', 'auto_sync.py')

_spec = importlib.util.spec_from_file_location('auto_sync_under_test', MODULE_PATH)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def _page(pid, family, **extra):
    rec = {'id': pid, 'family': family, 'title': f't{pid}'}
    rec.update(extra)
    return rec


def _sections(pages):
    return {'meta': {'pages': len(pages)}, 'pages': pages}


# A minimal homepage template carrying exactly the four markers the script edits.
# Per D1 there is intentionally NO <ul class="update-list"> here.
MIN_TEMPLATE = """
<a class="hero-update-pill" href="#updates">
  <span class="pill-dot"></span>
  <span class="pill-date">2000-01-01</span>
  <span class="pill-sep">·</span>
  <span class="pill-text">上次更新：旧文案</span>
  <span class="pill-arrow">↓</span>
</a>
<section class="update-section" id="updates">
  <div class="update-card">
    <div class="update-header">
      <div class="update-date-badge">
        <span class="dot"></span>
        <span>更新时间：2000-01-01</span>
      </div>
    </div>
    <div class="update-summary">old summary</div>
  </div>
</section>
"""

MIN_README = """# Proj

## 最近更新记录

- legacy bullet

---

## other
"""

TODAY = '2026-10-04'


# --------------------------------------------------------------------------
# analyze_diff (the actual bug fix)
# --------------------------------------------------------------------------

def test_analyze_diff_detects_added_main_page():
    old = _sections([_page(101, 'main'), _page(102, 'main')])
    new = _sections([_page(101, 'main'), _page(102, 'main'), _page(103, 'main')])
    reason = mod.analyze_diff(old, new)
    assert isinstance(reason, str)
    assert '主线剧情' in reason
    assert '新增 1 篇' in reason


def test_analyze_diff_identical_returns_generic_fallback():
    pages = [_page(1, 'main'), _page(2, 'events')]
    reason = mod.analyze_diff(_sections(pages), _sections(list(pages)))
    assert reason == mod._GENERIC_REASON


def test_analyze_diff_keyed_by_family_and_id():
    # Same numeric id but different family must count as a distinct record.
    old = _sections([_page(5, 'main'), _page(5, 'events')])
    new = _sections([_page(5, 'main'), _page(5, 'events'), _page(5, 'characters')])
    reason = mod.analyze_diff(old, new)
    assert '旅人专属故事' in reason
    assert '新增 1 篇' in reason  # only the characters page is new


def test_analyze_diff_unlabeled_family_counts_with_other_label():
    # battles_unmounted / prologue have no dedicated bullet; they must still
    # contribute to the total and surface via the "其他剧情" label.
    old = _sections([_page(1, 'main')])
    new = _sections([
        _page(1, 'main'),
        _page(2, 'battles_unmounted'),
        _page(3, 'prologue'),
    ])
    reason = mod.analyze_diff(old, new)
    assert '其他剧情' in reason
    assert '新增 2 篇' in reason


def test_analyze_diff_unlabeled_and_labeled_combined():
    old = _sections([_page(1, 'main')])
    new = _sections([
        _page(1, 'main'),
        _page(2, 'events'),
        _page(3, 'battles_unmounted'),
    ])
    reason = mod.analyze_diff(old, new)
    assert '限时活动' in reason
    assert '其他剧情' in reason
    assert '新增 2 篇' in reason


def test_analyze_diff_baseline_returns_none():
    # No usable baseline (fresh init) -> None so main() skips writing.
    assert mod.analyze_diff({}, _sections([_page(1, 'main')])) is None
    assert mod.analyze_diff({'meta': {}}, _sections([_page(1, 'main')])) is None
    assert mod.analyze_diff({'meta': {}, 'pages': []}, _sections([_page(1, 'main')])) is None


# --------------------------------------------------------------------------
# D2: reason resolution
# --------------------------------------------------------------------------

def test_resolve_reason_override():
    assert mod._resolve_reason('auto', '  note ') == 'note'
    assert mod._resolve_reason('auto', None) == 'auto'
    assert mod._resolve_reason('auto', '') == 'auto'
    assert mod._resolve_reason(None, 'note') == 'note'   # baseline + manual note still writes
    assert mod._resolve_reason(None, '') is None          # baseline + empty -> skip


# --------------------------------------------------------------------------
# update_changelog_in_files (homepage + README)
# --------------------------------------------------------------------------

@pytest.fixture()
def changelog_paths(tmp_path, monkeypatch):
    tpl = tmp_path / 'site_templates.py'
    rd = tmp_path / 'README.md'
    tpl.write_text(MIN_TEMPLATE, encoding='utf-8')
    rd.write_text(MIN_README, encoding='utf-8')
    monkeypatch.setattr(mod, 'TEMPLATES_PY', str(tpl))
    monkeypatch.setattr(mod, 'README_MD', str(rd))
    return tpl, rd


def test_changelog_updates_homepage_markers(changelog_paths):
    tpl, rd = changelog_paths
    mod.update_changelog_in_files(TODAY, '上线全新章节与限时活动')
    html = tpl.read_text(encoding='utf-8')
    assert '<span class="pill-date">2026-10-04</span>' in html
    assert '<span>更新时间：2026-10-04</span>' in html
    assert '<span class="pill-text">上次更新：上线全新章节与限时活动</span>' in html
    assert '<div class="update-summary">上线全新章节与限时活动</div>' in html
    # D1: the script must not resurrect the multi-item list, and must keep the anchor.
    assert 'update-list' not in html
    assert 'id="updates"' in html


def test_changelog_readme_keeps_only_latest_entry(changelog_paths):
    """Only the newest dated entry survives; older ones are intentionally dropped."""
    tpl, rd = changelog_paths
    mod.update_changelog_in_files('2026-10-03', '上周的更新')
    assert '### 2026-10-03' in rd.read_text(encoding='utf-8')
    mod.update_changelog_in_files(TODAY, '本周的更新')
    text = rd.read_text(encoding='utf-8')
    assert text.count('### 2026-10-04') == 1
    assert '- 本周的更新' in text
    # the previous date's entry is gone entirely
    assert '### 2026-10-03' not in text
    assert '上周的更新' not in text
    # the legacy bullet that used to live under the marker is replaced too
    assert '- legacy bullet' not in text


def test_changelog_readme_preserves_section_separator_and_next_section(changelog_paths):
    """Rewriting the log must not eat the "---" rule or the section that follows it."""
    tpl, rd = changelog_paths
    mod.update_changelog_in_files(TODAY, '新条目')
    text = rd.read_text(encoding='utf-8')
    marker = '## 最近更新记录\n\n'
    assert text.count(marker) == 1
    tail = text.partition(marker)[2]
    assert tail.startswith(f'### {TODAY}\n- 新条目\n')
    # the trailing separator and the following heading are still there
    assert '\n---\n' in tail
    assert '## other' in tail
    assert tail.index('---') < tail.index('## other')


def test_changelog_same_day_idempotent(changelog_paths):
    tpl, rd = changelog_paths
    mod.update_changelog_in_files(TODAY, '第一次同步')
    mod.update_changelog_in_files(TODAY, '第二次同步覆盖')
    text = rd.read_text(encoding='utf-8')
    assert text.count('### 2026-10-04') == 1
    assert '- 第二次同步覆盖' in text
    assert '第一次同步' not in text


def test_changelog_escapes_html_and_survives_backslash(changelog_paths):
    tpl, rd = changelog_paths
    reason = '修复 <b>& 分支 \\1 上线'   # a literal backslash must not act as a regex backref
    mod.update_changelog_in_files(TODAY, reason)
    html = tpl.read_text(encoding='utf-8')
    # HTML-escaped on the homepage ...
    assert '&lt;b&gt;' in html and '&amp;' in html
    assert '<span class="pill-text">上次更新：修复 &lt;b&gt;&amp; 分支 \\1 上线</span>' in html
    # ... but literal (and intact) in the README.
    text = rd.read_text(encoding='utf-8')
    assert '- 修复 <b>& 分支 \\1 上线' in text


def test_changelog_empty_reason_is_noop(changelog_paths):
    tpl, rd = changelog_paths
    before_t = tpl.read_text(encoding='utf-8')
    before_r = rd.read_text(encoding='utf-8')
    mod.update_changelog_in_files(TODAY, '   ')
    assert tpl.read_text(encoding='utf-8') == before_t
    assert rd.read_text(encoding='utf-8') == before_r


# --------------------------------------------------------------------------
# D1 source cleanup really applied to the shipped template / CSS
# --------------------------------------------------------------------------

def test_repo_template_and_css_have_no_update_list():
    tpl = open(mod.TEMPLATES_PY, encoding='utf-8').read()
    assert 'update-list' not in tpl
    css = open(os.path.join(ROOT, 'scripts', 'site', 'site_css.py'), encoding='utf-8').read()
    assert '.update-list' not in css


# --------------------------------------------------------------------------
# Commit-driven changelog (push events)
# --------------------------------------------------------------------------

def _commit(sha, name, email, subject):
    return (sha, name, email, subject)


def test_filter_human_commits_keeps_feat_fix_and_perf():
    commits = [
        _commit('a', 'Alice', 'alice@example.com', 'feat: 新增薇洛盛夏剧情'),
        _commit('b', 'Bob', 'bob@example.com', 'fix: 修复 NPC 羁绊标题重复'),
        _commit('c', 'Cara', 'cara@example.com', 'perf: 提速拓扑分层'),
    ]
    kept = mod.filter_human_commits(commits)
    assert [c[3] for c in kept] == ['feat: 新增薇洛盛夏剧情', 'fix: 修复 NPC 羁绊标题重复',
                                    'perf: 提速拓扑分层']


def test_filter_human_commits_drops_bot_and_noise():
    commits = [
        _commit('a', 'github-actions[bot]', 'github-actions[bot]@users.noreply.github.com',
                'docs: 更新站点更新日志 [skip ci]'),
        _commit('b', 'Alice', 'alice@users.noreply.github.com', 'feat: 真人提交'),
        _commit('c', 'Alice', 'alice@example.com', 'chore: 升依赖'),
        _commit('d', 'Alice', 'alice@example.com', 'ci: 修流水线'),
        _commit('e', 'Alice', 'alice@example.com', 'style: 格式化'),
        _commit('f', 'Alice', 'alice@example.com', 'Merge branch "x"'),
        _commit('h', 'Alice', 'alice@example.com', 'merge pull request #12 from y/z'),
        _commit('g', 'Alice', 'alice@example.com', '   '),
    ]
    kept = mod.filter_human_commits(commits)
    assert [c[3] for c in kept] == ['feat: 真人提交']


def test_filter_human_commits_prefix_match_is_case_insensitive():
    commits = [_commit('a', 'Alice', 'alice@example.com', 'CHORE: 大写也过滤')]
    assert mod.filter_human_commits(commits) == []


def test_collect_commits_returns_empty_on_bad_range():
    # A nonexistent range must degrade to [] rather than raise, so the deploy never breaks.
    assert mod.collect_commits('deadbeef..notacommit') == []


def test_update_changelog_from_commits_homepage_summary_and_readme_list(changelog_paths):
    tpl, rd = changelog_paths
    commits = [_commit(f'sha{i}', 'Alice', 'alice@example.com', f'feat: 第 {i} 项')
               for i in range(1, 4)]
    changed = mod.update_changelog_from_commits(TODAY, commits)
    assert changed is True
    html = tpl.read_text(encoding='utf-8')
    # homepage: one-line summary only, no per-commit list
    assert '<span class="pill-date">2026-10-04</span>' in html
    assert '<span class="pill-text">上次更新：同步 3 项代码更新</span>' in html
    assert '<div class="update-summary">同步 3 项代码更新</div>' in html
    assert '第 1 项' not in html
    # README: the full commit list (the old section body is replaced entirely)
    text = rd.read_text(encoding='utf-8')
    assert text.count('### 2026-10-04') == 1
    assert '- legacy bullet' not in text
    assert '- feat: 第 1 项' in text
    assert '- feat: 第 2 项' in text
    assert '- feat: 第 3 项' in text


def test_update_changelog_from_commits_escapes_html(changelog_paths):
    # The homepage only ever shows the fixed summary, so a commit subject with
    # markup can only leak into the README -- where it must stay verbatim.
    tpl, rd = changelog_paths
    commits = [_commit('a', 'Alice', 'alice@example.com', 'feat: 修复 <b>& </b> 渲染')]
    mod.update_changelog_from_commits(TODAY, commits)
    html = tpl.read_text(encoding='utf-8')
    assert '<span class="pill-text">上次更新：同步 1 项代码更新</span>' in html
    assert '<b>' not in html and '&lt;b' not in html   # subject must not reach the template
    text = rd.read_text(encoding='utf-8')
    assert '- feat: 修复 <b>& </b> 渲染' in text


def test_update_changelog_from_commits_empty_returns_false(changelog_paths):
    tpl, rd = changelog_paths
    before_t, before_r = tpl.read_text(encoding='utf-8'), rd.read_text(encoding='utf-8')
    assert mod.update_changelog_from_commits(TODAY, []) is False
    assert tpl.read_text(encoding='utf-8') == before_t
    assert rd.read_text(encoding='utf-8') == before_r


def test_update_changelog_from_commits_same_day_replaces_list(changelog_paths):
    tpl, rd = changelog_paths
    mod.update_changelog_from_commits(TODAY, [_commit('a', 'Alice', 'a@x.com', 'feat: 第一轮')])
    mod.update_changelog_from_commits(TODAY, [_commit('b', 'Alice', 'a@x.com', 'feat: 第二轮')])
    text = rd.read_text(encoding='utf-8')
    assert text.count('### 2026-10-04') == 1
    assert '- feat: 第二轮' in text
    assert '第一轮' not in text


def test_commit_cap_protects_readme(changelog_paths):
    tpl, rd = changelog_paths
    # Input order is newest-first (as git log returns), so index 0 is newest.
    commits = [_commit(f's{i}', 'Alice', 'a@x.com', f'feat: 提交 {i}') for i in range(50)]
    mod.update_changelog_from_commits(TODAY, commits)
    text = rd.read_text(encoding='utf-8')
    # Only the newest _MAX_COMMIT_ENTRIES are written.
    assert text.count('- feat: 提交') == mod._MAX_COMMIT_ENTRIES
    assert '- feat: 提交 0' in text        # newest first
    assert '- feat: 提交 9' in text        # last kept
    assert '- feat: 提交 10' not in text   # beyond the cap


def test_readme_write_latest_replaces_whole_same_day_block(changelog_paths):
    """A multi-bullet same-day entry must be fully replaced, not partially merged."""
    tpl, rd = changelog_paths
    mod.update_changelog_in_files(TODAY, '同步写入的一条')
    mod.update_changelog_from_commits(TODAY, [_commit('a', 'Alice', 'a@x.com', 'feat: 改为多条')])
    text = rd.read_text(encoding='utf-8')
    assert text.count('### 2026-10-04') == 1
    assert '- feat: 改为多条' in text
    assert '同步写入的一条' not in text
    assert '---' in text and '## other' in text   # structure survived the rewrite


def test_readme_write_latest_drops_history_across_dates(changelog_paths):
    """The log never grows: entry B replaces entry A even on a different date."""
    tpl, rd = changelog_paths
    mod.update_changelog_from_commits('2026-10-03',
                                      [_commit('a', 'Alice', 'a@x.com', 'feat: 昨天')])
    mod.update_changelog_from_commits(TODAY,
                                      [_commit('b', 'Alice', 'a@x.com', 'feat: 今天')])
    text = rd.read_text(encoding='utf-8')
    assert '### 2026-10-04' in text and 'feat: 今天' in text
    assert '2026-10-03' not in text and 'feat: 昨天' not in text


def test_today_str_format():
    today = mod._today_str()
    assert len(today) == 10 and today[4] == '-' and today[7] == '-'
